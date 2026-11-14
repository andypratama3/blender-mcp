"""Minimal binary FBX reader: dump animation channels per model without Blender.

Blender's own FBX importer rebuilds bones from head/tail and marks a child as
"connected" when the parent's tail meets its head, which silently drops animated
bone translation. Reading the file directly avoids that.

    python3 inspect_fbx.py export/Hero_Walk.fbx --model HumanoidRootNode
"""

import argparse
import os
import struct
import sys
import zlib

TIME_UNIT = 46186158000.0


def _read_prop(f, kind):
    if kind == b"Y":
        return struct.unpack("<h", f.read(2))[0]
    if kind == b"C":
        return bool(f.read(1)[0])
    if kind == b"I":
        return struct.unpack("<i", f.read(4))[0]
    if kind == b"F":
        return struct.unpack("<f", f.read(4))[0]
    if kind == b"D":
        return struct.unpack("<d", f.read(8))[0]
    if kind == b"L":
        return struct.unpack("<q", f.read(8))[0]
    if kind in (b"f", b"d", b"l", b"i", b"b"):
        count, encoding, raw_len = struct.unpack("<III", f.read(12))
        raw = f.read(raw_len)
        if encoding == 1:
            raw = zlib.decompress(raw)
        code = {b"f": "f", b"d": "d", b"l": "q", b"i": "i", b"b": "?"}[kind]
        size = struct.calcsize("<" + code)
        return list(struct.unpack("<%d%s" % (count, code), raw[: count * size]))
    if kind in (b"S", b"R"):
        length = struct.unpack("<I", f.read(4))[0]
        return f.read(length)
    raise ValueError("unknown property type %r" % kind)


class Node:
    __slots__ = ("name", "props", "children")

    def __init__(self, name, props, children):
        self.name = name
        self.props = props
        self.children = children

    def find(self, name):
        return [c for c in self.children if c.name == name]

    def first(self, name):
        for c in self.children:
            if c.name == name:
                return c
        return None


def _read_node(f, version, stop):
    width = 8 if version >= 7500 else 4
    head = f.read(width * 3 + 1)
    if len(head) < width * 3 + 1:
        return None
    fmt = "<QQQB" if width == 8 else "<IIIB"
    end, num_props, prop_len, name_len = struct.unpack(fmt, head)
    if end == 0:
        return None
    if name_len == 0:
        return Node("", [], [])
    name = f.read(name_len)
    props = [_read_prop(f, f.read(1)) for _ in range(num_props)]
    children = []
    while f.tell() < min(end, stop):
        child = _read_node(f, version, end)
        if child is None:
            break
        children.append(child)
    f.seek(end)
    return Node(name.decode("utf-8", "replace"), props, children)


def parse(path):
    with open(path, "rb") as f:
        magic = f.read(21)
        if not magic.startswith(b"Kaydara FBX Binary"):
            raise SystemExit("not a binary FBX: %s" % path)
        f.read(2)
        version = struct.unpack("<I", f.read(4))[0]
        size = os.path.getsize(path)
        nodes = []
        while f.tell() < size - 20:
            node = _read_node(f, version, size)
            if node is None:
                break
            nodes.append(node)
    return version, nodes


def model_names(top):
    names = {}
    for model in top.find("Objects")[0].find("Model"):
        uid, name = model.props[0], model.props[1]
        names[uid] = name.split(b"\x00")[0].decode("utf-8", "replace").split("::")[-1]
    return names


def channel_map(top, names):
    """(model name, channel, values, times) for every animated curve."""
    objects = top.find("Objects")[0]
    curves = {c.props[0]: c for c in objects.find("AnimationCurve")}
    curve_nodes = {c.props[0]: c for c in objects.find("AnimationCurveNode")}

    links = {}
    for conn in top.find("Connections")[0].find("C"):
        kind = conn.props[0]
        if kind == b"OP":
            child, parent, prop = conn.props[1], conn.props[2], conn.props[3]
            links.setdefault(parent, []).append((child, prop.decode()))
        elif kind == b"OO":
            child, parent = conn.props[1], conn.props[2]
            links.setdefault(parent, []).append((child, None))

    out = []
    for model_id, model_name in names.items():
        for curve_id, _ in links.get(model_id, []):
            curve_node = curve_nodes.get(curve_id)
            if curve_node is None:
                continue
            channel = curve_node.props[1].split(b"\x00")[0].decode()
            for target, prop in links.get(curve_id, []):
                curve = curves.get(target)
                if curve is None or not prop:
                    continue
                values = curve.first("KeyValueFloat")
                times = curve.first("KeyTime")
                if values is None or times is None:
                    continue
                values = values.props[0] if isinstance(values.props[0], list) else values.props
                times = times.props[0] if isinstance(times.props[0], list) else times.props
                out.append(
                    {
                        "model": model_name,
                        "channel": channel,
                        "axis": prop.split("|")[-1],
                        "values": values,
                        "frames": [
                            round(t / TIME_UNIT * 24.0 + 1.0, 2) for t in times
                        ],
                    }
                )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--model", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    version, nodes = parse(args.file)
    top = Node("", [], nodes)
    names = model_names(top)
    rows = channel_map(top, names)
    if args.model:
        rows = [r for r in rows if r["model"] == args.model]

    if args.json:
        import json

        print(json.dumps({"version": version, "channels": rows}, indent=1))
        return

    print("FBX %d, %d models, %d animated channels" % (version, len(names), len(rows)))
    for row in rows:
        values = row["values"]
        print(
            "%-22s %s %-2s n=%2d frames %s..%s  min %8.3f max %8.3f"
            % (
                row["model"],
                row["channel"][-1],
                row["axis"],
                len(values),
                row["frames"][0],
                row["frames"][-1],
                min(values),
                max(values),
            )
        )


if __name__ == "__main__":
    sys.exit(main())
