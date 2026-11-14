"""Inspect a glTF/GLB before rigging: transforms, shells, bounds, ASCII silhouette.

Run headless, it never touches the live session:

    blender -b --factory-startup \
        --python inspect_glb.py -- "/path/asset.glb"

Prints a JSON block between JSON_START / JSON_END plus a filled ASCII projection on
the dominant plane, which replaces a render when deciding pivot and moving parts.
"""

import json
import sys

import bpy
from mathutils import Matrix

AXES = {"XZ": (0, 2), "XY": (0, 1), "YZ": (1, 2)}


def argv_after_ddash():
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def reset_scene():
    bpy.ops.wm.read_homefile(use_empty=True, use_factory_startup=True)


def import_asset(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    bpy.context.view_layer.update()
    return [ob for ob in bpy.data.objects if ob not in before]


def bake_transforms(objects):
    meshes = [ob for ob in objects if ob.type == "MESH"]
    for ob in meshes:
        ob.data.transform(ob.matrix_world)
        ob.parent = None
        ob.matrix_basis = Matrix.Identity(4)
    for ob in [o for o in objects if o.type != "MESH"]:
        bpy.data.objects.remove(ob, do_unlink=True)
    return meshes


def weld_and_components(mesh, dist=1e-5):
    import bmesh

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=dist)
    remaining = set(bm.verts)
    shells = 0
    while remaining:
        shells += 1
        stack = [remaining.pop()]
        while stack:
            v = stack.pop()
            for e in v.link_edges:
                other = e.other_vert(v)
                if other in remaining:
                    remaining.remove(other)
                    stack.append(other)
    verts = len(bm.verts)
    faces = len(bm.faces)
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    return {"verts": verts, "faces": faces, "shells": shells, "non_manifold": non_manifold}


def silhouette(meshes, plane="XZ", width=64):
    """Rasterise every triangle onto a character grid on the given plane."""
    a, b = AXES[plane]
    points = [v.co for ob in meshes for v in ob.data.vertices]
    x0 = min(p[a] for p in points)
    x1 = max(p[a] for p in points)
    y0 = min(p[b] for p in points)
    y1 = max(p[b] for p in points)
    sx = (x1 - x0) or 1.0
    sy = (y1 - y0) or 1.0
    rows = max(12, int(width * sy / sx * 0.5))
    grid = [[False] * width for _ in range(rows)]

    def to_grid(p):
        return ((p[a] - x0) / sx * (width - 1), (p[b] - y0) / sy * (rows - 1))

    for ob in meshes:
        mesh = ob.data
        for poly in mesh.polygons:
            idx = list(poly.vertices)
            corners = [to_grid(mesh.vertices[i].co) for i in idx]
            for k in range(1, len(corners) - 1):
                tri = [corners[0], corners[k], corners[k + 1]]
                gx0 = max(0, int(min(c[0] for c in tri)))
                gx1 = min(width - 1, int(max(c[0] for c in tri)) + 1)
                gy0 = max(0, int(min(c[1] for c in tri)))
                gy1 = min(rows - 1, int(max(c[1] for c in tri)) + 1)
                (ax, ay), (bx, by), (cx, cy) = tri
                area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
                if abs(area) < 1e-12:
                    continue
                for gy in range(gy0, gy1 + 1):
                    for gx in range(gx0, gx1 + 1):
                        px, py = gx + 0.5, gy + 0.5
                        w0 = ((bx - ax) * (py - ay) - (px - ax) * (by - ay)) / area
                        w1 = ((px - ax) * (cy - ay) - (cx - ax) * (py - ay)) / area
                        if w0 >= -0.02 and w1 >= -0.02 and (w0 + w1) <= 1.02:
                            grid[gy][gx] = True

    lines = []
    for gy in range(rows - 1, -1, -1):
        z = y0 + (gy + 0.5) / (rows - 1) * sy
        lines.append("%7.3f |%s|" % (z, "".join("#" if c else " " for c in grid[gy])))
    return lines, (x0, x1)


def main():
    args = argv_after_ddash()
    if not args:
        print("usage: -- <asset.glb>")
        return 2
    path = args[0]
    reset_scene()
    imported = import_asset(path)
    object_list = [(ob.name, ob.type) for ob in imported]
    meshes = bake_transforms(imported)
    points = [v.co for ob in meshes for v in ob.data.vertices]
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    zs = [p.z for p in points]
    extents = {"x": max(xs) - min(xs), "y": max(ys) - min(ys), "z": max(zs) - min(zs)}
    flat = min(extents, key=extents.get)
    plane = {"y": "XZ", "z": "XY", "x": "YZ"}[flat]

    report = {
        "file": path,
        "objects": object_list,
        "meshes": [],
        "bounds": {
            "min": [round(v, 4) for v in (min(xs), min(ys), min(zs))],
            "max": [round(v, 4) for v in (max(xs), max(ys), max(zs))],
            "extents": {k: round(v, 4) for k, v in extents.items()},
        },
        "flat_axis": flat,
        "silhouette_plane": plane,
        "materials": [m.name for m in bpy.data.materials],
    }
    for ob in meshes:
        stats = weld_and_components(ob.data)
        stats.update(
            {
                "name": ob.name,
                "raw_verts": len(ob.data.vertices),
                "polys": len(ob.data.polygons),
                "materials": [m.name for m in ob.data.materials if m],
            }
        )
        report["meshes"].append(stats)

    print("JSON_START")
    print(json.dumps(report, indent=1))
    print("JSON_END")

    lines, (x0, x1) = silhouette(meshes, plane)
    print("SILHOUETTE %s  x: %.3f .. %.3f  (right = +%s, up = +%s)" % (plane, x0, x1, plane[0], plane[1]))
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    main()
