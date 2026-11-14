#!/usr/bin/env python3
"""Render-free GLB QA: parse the shipped bytes with the standard library.

    python3 scripts/glb_qa.py out/model.glb [--loop] [--manifold]
                              [--max-joints N] [--max-tris N] [--tol 1e-3]

Prints one JSON object and exits 1 if a gate fails. No Blender, no render, no
screenshot: it reads the buffer views the exporter actually wrote.
"""

import argparse
import json
import math
import shutil
import struct
import subprocess
import sys
from collections import Counter

CT = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
CS = {"b": 1, "B": 1, "h": 2, "H": 2, "I": 4, "f": 4}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}
NORM = {5120: 127.0, 5121: 255.0, 5122: 32767.0, 5123: 65535.0}


def load_glb(path):
    with open(path, "rb") as handle:
        data = handle.read()
    if len(data) < 20:
        raise ValueError("file too short for GLB")
    magic, ver, length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF":
        raise ValueError("bad magic (not a GLB)")
    off, js, binc = 12, None, b""
    while off + 8 <= len(data):
        clen, ctype = struct.unpack_from("<II", data, off)
        body = data[off + 8 : off + 8 + clen]
        if ctype == 0x4E4F534A and js is None:
            js = json.loads(body.decode("utf-8"))
        elif ctype == 0x004E4942 and not binc:
            binc = body
        off += 8 + clen
    if js is None:
        raise ValueError("no JSON chunk")
    return js, binc, {"version": ver, "declared": length, "actual": len(data)}


def read_acc(g, b, i):
    a = g["accessors"][i]
    if "sparse" in a:
        raise NotImplementedError("sparse accessor")
    f, n, cnt = CT[a["componentType"]], NC[a["type"]], a["count"]
    if "bufferView" not in a:
        return [(0.0,) * n] * cnt
    bv = g["bufferViews"][a["bufferView"]]
    bv0 = bv.get("byteOffset", 0)
    base = bv0 + a.get("byteOffset", 0)
    stride = bv.get("byteStride") or CS[f] * n
    need = base + (stride * (cnt - 1) + CS[f] * n if cnt else 0)
    if need > bv0 + bv["byteLength"] or need > len(b):
        raise ValueError("accessor %d out of bounds" % i)
    norm = NORM.get(a["componentType"]) if a.get("normalized") else None
    out = []
    for k in range(cnt):
        t = struct.unpack_from("<" + f * n, b, base + k * stride)
        if norm:
            t = tuple(max(x / norm, -1.0) for x in t)
        out.append(t)
    return out


def gate(gates, name, value, ok, limit=None):
    gates[name] = {"value": value, "limit": limit, "pass": bool(ok)}


def run(path, a):
    try:
        g, b, h = load_glb(path)
    except Exception as e:  # noqa: BLE001
        return {"file": path, "error": str(e), "pass": False}

    gates, info, bad, sparse = {}, {}, [], 0
    cache = {}

    def acc(i):
        nonlocal sparse
        if i in cache:
            return cache[i]
        try:
            cache[i] = read_acc(g, b, i)
        except NotImplementedError:
            sparse += 1
            cache[i] = None
        except Exception as e:  # noqa: BLE001
            bad.append(str(e))
            cache[i] = None
        return cache[i]

    gate(gates, "header_length", [h["declared"], h["actual"]], h["declared"] == h["actual"])
    gate(gates, "glb_version", h["version"], h["version"] == 2, 2)

    mesh_skin = {n["mesh"]: n["skin"] for n in g.get("nodes", []) if "mesh" in n and "skin" in n}
    skins = g.get("skins", [])
    tris = nonfinite = 0
    pos_err = wsum_err = 0.0
    unweighted = max_infl = jbad = 0
    boundary = nonmanifold = 0

    for mi, m in enumerate(g.get("meshes", [])):
        edges = Counter()
        wid = {}
        for p in m.get("primitives", []):
            at = p.get("attributes", {})
            if "POSITION" not in at:
                continue
            pos = acc(at["POSITION"])
            if pos is None:
                continue
            nonfinite += sum(1 for v in pos for c in v if not math.isfinite(c))
            pa = g["accessors"][at["POSITION"]]
            if "min" in pa and pos:
                mn = [min(v[k] for v in pos) for k in range(3)]
                pos_err = max(pos_err, max(abs(x - y) for x, y in zip(mn, pa["min"])))
            if p.get("mode", 4) == 4:
                if "indices" in p:
                    ix = acc(p["indices"])
                    idx = [t[0] for t in ix] if ix else []
                else:
                    idx = list(range(len(pos)))
                tris += len(idx) // 3
                if a.manifold:
                    keys = [tuple(round(c, 5) for c in v) for v in pos]
                    ids = [wid.setdefault(k, len(wid)) for k in keys]
                    for t in range(0, len(idx) - 2, 3):
                        v0, v1, v2 = ids[idx[t]], ids[idx[t + 1]], ids[idx[t + 2]]
                        if len({v0, v1, v2}) < 3:
                            continue
                        for e in ((v0, v1), (v1, v2), (v2, v0)):
                            edges[tuple(sorted(e))] += 1
            k = 0
            while "JOINTS_%d" % k in at and "WEIGHTS_%d" % k in at:
                k += 1
            if k:
                J = [acc(at["JOINTS_%d" % s]) for s in range(k)]
                W = [acc(at["WEIGHTS_%d" % s]) for s in range(k)]
                if all(x is not None for x in J + W):
                    si = mesh_skin.get(mi)
                    nj = len(skins[si]["joints"]) if si is not None else None
                    for v in range(len(pos)):
                        ws = [w for s in range(k) for w in W[s][v]]
                        js = [j for s in range(k) for j in J[s][v]]
                        tot = sum(ws)
                        if tot < 1e-6:
                            unweighted += 1
                        else:
                            wsum_err = max(wsum_err, abs(tot - 1.0))
                        used = [(j, w) for j, w in zip(js, ws) if w > 1e-6]

                        max_infl = max(max_infl, len(used))
                        if nj is not None:
                            jbad += sum(1 for j, _ in used if j >= nj)
        if a.manifold:
            boundary += sum(1 for c in edges.values() if c == 1)
            nonmanifold += sum(1 for c in edges.values() if c > 2)

    info.update(
        {
            "nodes": len(g.get("nodes", [])),
            "meshes": len(g.get("meshes", [])),
            "skins": len(skins),
            "triangles": tris,
            "sparse_accessors_skipped": sparse,
        }
    )
    gate(gates, "position_min_error", round(pos_err, 8), pos_err <= 1e-5, 1e-5)
    if any(
        k.startswith("JOINTS_")
        for m in g.get("meshes", [])
        for p in m.get("primitives", [])
        for k in p.get("attributes", {})
    ):
        gate(gates, "weight_sum_error", round(wsum_err, 6), wsum_err <= a.tol, a.tol)
        gate(gates, "unweighted_vertices", unweighted, unweighted == 0, 0)
        gate(gates, "max_influences", max_infl, max_infl <= 4, 4)
        gate(gates, "joint_index_out_of_range", jbad, jbad == 0, 0)

    ibm_bad = 0
    maxj = 0
    for s in skins:
        maxj = max(maxj, len(s["joints"]))
        if "inverseBindMatrices" in s:
            ibm = acc(s["inverseBindMatrices"])
            if ibm is not None and len(ibm) != len(s["joints"]):
                ibm_bad += 1
    info["joints_max"] = maxj
    if skins:
        gate(gates, "ibm_count_matches_joints", ibm_bad, ibm_bad == 0, 0)
    if a.max_joints is not None:
        gate(gates, "max_joints", maxj, maxj <= a.max_joints, a.max_joints)
    if a.max_tris is not None:
        gate(gates, "max_triangles", tris, tris <= a.max_tris, a.max_tris)
    if a.manifold:
        info["boundary_edges"], info["nonmanifold_edges"] = boundary, nonmanifold
        gate(gates, "boundary_edges", boundary, boundary == 0, 0)
        gate(gates, "nonmanifold_edges", nonmanifold, nonmanifold == 0, 0)

    anims, nonmono, count_bad, qerr, loop_err = [], 0, 0, 0.0, 0.0
    start_s = None
    for an in g.get("animations", []):
        dur, keys, t0 = 0.0, 0, None
        for ch in an.get("channels", []):
            sm = an["samplers"][ch["sampler"]]
            inp, out = acc(sm["input"]), acc(sm["output"])
            if inp is None or out is None:
                continue
            t = [x[0] for x in inp]
            interp = sm.get("interpolation", "LINEAR")
            target = ch["target"]["path"]
            nonfinite += sum(1 for v in out for c in v if not math.isfinite(c))
            if any(t[i + 1] <= t[i] for i in range(len(t) - 1)):
                nonmono += 1
            if target != "weights":
                want = len(t) * (3 if interp == "CUBICSPLINE" else 1)
                if len(out) != want:
                    count_bad += 1
            if t:
                dur = max(dur, t[-1] - t[0])
                keys = max(keys, len(t))
                t0 = t[0] if t0 is None else min(t0, t[0])
            if interp != "CUBICSPLINE" and out:
                if target == "rotation":
                    qerr = max(qerr, max(abs(math.sqrt(sum(c * c for c in q)) - 1.0) for q in out))
                if a.loop:
                    first, last = out[0], out[-1]
                    d1 = max(abs(x - y) for x, y in zip(first, last))
                    d2 = max(abs(x + y) for x, y in zip(first, last)) if target == "rotation" else d1
                    loop_err = max(loop_err, min(d1, d2))
        anims.append(
            {
                "name": an.get("name"),
                "start_s": round(t0, 4) if t0 is not None else None,
                "duration_s": round(dur, 4),
                "channels": len(an.get("channels", [])),
                "keys_max": keys,
            }
        )
        if t0 is not None:
            start_s = t0 if start_s is None else min(start_s, t0)
    info["animations"] = anims
    if anims:
        gate(gates, "time_strictly_increasing", nonmono, nonmono == 0, 0)
        gate(gates, "sampler_output_count", count_bad, count_bad == 0, 0)
        gate(gates, "quaternion_norm_error", round(qerr, 6), qerr <= a.tol, a.tol)
        if a.start_at_zero:
            gate(gates, "starts_at_zero", round(start_s or 0.0, 6), abs(start_s or 0.0) <= a.tol, a.tol)
        if a.loop:
            gate(gates, "loop_closure_error", round(loop_err, 6), loop_err <= a.tol, a.tol)
    gate(gates, "nonfinite_values", nonfinite, nonfinite == 0, 0)
    gate(gates, "accessors_readable", bad[:5], not bad, "none")

    exe = shutil.which("gltf_validator")
    kh = {"available": bool(exe)}
    if exe:
        try:
            r = subprocess.run([exe, "-o", path], capture_output=True, text=True, timeout=120)
            rep = json.loads(r.stdout)
            kh["errors"] = rep["issues"]["numErrors"]
            kh["warnings"] = rep["issues"]["numWarnings"]
            gate(gates, "khronos_errors", kh["errors"], kh["errors"] == 0, 0)
        except Exception as e:  # noqa: BLE001
            kh["error"] = str(e)
    info["khronos"] = kh

    return {
        "file": path,
        "info": info,
        "gates": gates,
        "pass": all(x["pass"] for x in gates.values()),
    }


def main():
    ap = argparse.ArgumentParser(description="render-free GLB QA (stdlib only)")
    ap.add_argument("glb")
    ap.add_argument("--loop", action="store_true", help="require the last keyframe to match the first")
    ap.add_argument("--manifold", action="store_true", help="boundary/non-manifold edge gates (props only)")
    ap.add_argument("--max-joints", type=int)
    ap.add_argument("--max-tris", type=int)
    ap.add_argument("--start-at-zero", action="store_true",
                    help="require the first keyframe at t=0 (glTF exports from frame 1 start at 1/fps)")
    ap.add_argument("--tol", type=float, default=1e-3)
    a = ap.parse_args()
    res = run(a.glb, a)
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["pass"] else 1)


if __name__ == "__main__":
    main()
