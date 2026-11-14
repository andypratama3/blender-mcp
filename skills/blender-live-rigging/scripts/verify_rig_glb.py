"""Verify an exported rigged GLB by re-importing it in a separate Blender process.

    blender -b --factory-startup \
        --python verify_rig_glb.py -- "/path/rig.glb"

Checks: node list (widgets must be absent), skin/joint count, animation name and
range, and measured widths at several frames. A hinge rig must show a non-zero
delta between frame 1 and the mid frame, and identical widths at first/last frame.
"""

import json
import struct
import sys

import bpy

LOW_Z = 0.0
HIGH_Z = 0.25


def argv_after_ddash():
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def glb_json(path):
    with open(path, "rb") as handle:
        data = handle.read()
    _, _, length = struct.unpack_from("<III", data, 0)
    off = 12
    while off < length:
        chunk_len, chunk_type = struct.unpack_from("<II", data, off)
        if chunk_type == 0x4E4F534A:
            return json.loads(data[off + 8 : off + 8 + chunk_len].decode("utf-8"))
        off += 8 + chunk_len
    raise ValueError("no JSON chunk in %s" % path)


def parse_bands(args):
    """Read optional --low-z / --high-z overrides; keep the case-study defaults."""
    low, high = LOW_Z, HIGH_Z
    rest = list(args)
    for flag in ("--low-z", "--high-z"):
        if flag in rest:
            index = rest.index(flag)
            value = float(rest[index + 1])
            if flag == "--low-z":
                low = value
            else:
                high = value
            del rest[index : index + 2]
    return low, high, rest


def is_helper_object(ob):
    return any(coll.name == "glTF_not_exported" for coll in ob.users_collection)


def measure(tool, scene, frame, low_z, high_z):
    scene.frame_set(frame)
    deps = bpy.context.evaluated_depsgraph_get()
    evaluated = tool.evaluated_get(deps)
    mesh = evaluated.to_mesh()
    points = [tool.matrix_world @ v.co for v in mesh.vertices]
    evaluated.to_mesh_clear()
    low = [p for p in points if p.z < low_z]
    high = [p for p in points if p.z > high_z]

    def width(items):
        return round(max(p.x for p in items) - min(p.x for p in items), 4) if items else None

    return {"handle": width(low), "jaw": width(high)}


def main():
    args = argv_after_ddash()
    if not args:
        print("usage: -- <rig.glb> [--low-z FLOAT] [--high-z FLOAT]")
        return 2
    low_z, high_z, args = parse_bands(args)
    path = args[0]
    raw = glb_json(path)

    bpy.ops.wm.read_homefile(use_empty=True, use_factory_startup=True)
    bpy.ops.import_scene.gltf(filepath=path)

    scene = bpy.context.scene
    meshes = [
        ob
        for ob in bpy.data.objects
        if ob.type == "MESH" and not is_helper_object(ob)
    ]
    tool = next(
        (ob for ob in meshes if any(m.type == "ARMATURE" for m in ob.modifiers)),
        max(meshes, key=lambda ob: len(ob.data.vertices)),
    )
    rig = next((ob for ob in bpy.data.objects if ob.type == "ARMATURE"), None)
    action = bpy.data.actions[0] if bpy.data.actions else None
    start, end = (int(round(v)) for v in action.frame_range) if action else (1, 1)
    mid = (start + end) // 2

    frames = {}
    for frame in sorted({start, start + (mid - start) // 2, mid, end}):
        frames[frame] = measure(tool, scene, frame, low_z, high_z)

    report = {
        "file": path,
        "glb": {
            "nodes": [n.get("name") for n in raw.get("nodes", [])],
            "meshes": [m.get("name") for m in raw.get("meshes", [])],
            "primitives": [len(m.get("primitives", [])) for m in raw.get("meshes", [])],
            "skins": [(s.get("name"), len(s.get("joints", []))) for s in raw.get("skins", [])],
            "animations": [(a.get("name"), len(a.get("channels", []))) for a in raw.get("animations", [])],
            "materials": [m.get("name") for m in raw.get("materials", [])],
            "images": len(raw.get("images", [])),
        },
        "imported": {
            "objects": [(ob.name, ob.type) for ob in bpy.data.objects],
            "bones": [b.name for b in rig.data.bones] if rig else [],
            "verts": len(tool.data.vertices),
            "materials": [m.name for m in tool.data.materials if m],
            "action": (action.name, [start, end]) if action else None,
            "frames": frames,
        },
        "gates": {},
        "bands": {"low_z": low_z, "high_z": high_z},
    }

    first, last = frames[start], frames[end]
    node_names = [str(n.get("name", "")) for n in raw.get("nodes", [])]
    report["gates"] = {
        "single_mesh": len(raw.get("meshes", [])) == 1,
        "has_skin": bool(raw.get("skins")),
        "has_animation": bool(raw.get("animations")),
        "no_widget_nodes": not any(n.startswith("WGT_") for n in node_names),
        "moves_when_open": bool(frames[mid]["handle"]) and bool(first["handle"])
        and abs(frames[mid]["handle"] - first["handle"]) > 1e-4,
        "loop_closed": first == last,
    }

    print("JSON_START")
    print(json.dumps(report, indent=1))
    print("JSON_END")
    return 0 if all(report["gates"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
