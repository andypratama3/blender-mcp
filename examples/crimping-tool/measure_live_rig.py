"""Measure a live hinge rig through the Blender MCP bridge.

Send this file to a running Blender with:

    python3 skills/blender-live-rigging/scripts/blender_mcp.py \
        --file examples/crimping-tool/measure_live_rig.py

Read-only: it changes the frame, measures the evaluated mesh, and restores the frame.
Adjust the constants below if your object, rig, or frame range differs.
"""

import bpy

OBJECT = "Crimping_Tool"
RIG = "Crimping_Rig"
FRAME_CLOSED = 1
FRAME_OPEN = 30
FRAME_LOOP = 60
HANDLE_Z_MAX = 0.0
JAW_Z_MIN = 0.25


def evaluated_geometry(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    verts = [obj.matrix_world @ v.co for v in mesh.vertices]
    faces = [[mesh.vertices[i].co.copy() for i in poly.vertices] for poly in mesh.polygons]
    evaluated.to_mesh_clear()
    return verts, faces


def poly_area(points):
    total = 0.0
    for k in range(1, len(points) - 1):
        total += (points[k] - points[0]).cross(points[k + 1] - points[0]).length * 0.5
    return total


def widths(verts):
    handles = [v for v in verts if v.z < HANDLE_Z_MAX]
    jaws = [v for v in verts if v.z > JAW_Z_MIN]
    out = {}
    if handles:
        xs = [v.x for v in handles]
        out["handle"] = round(max(xs) - min(xs), 4)
    if jaws:
        xs = [v.x for v in jaws]
        out["jaw"] = round(max(xs) - min(xs), 4)
    return out


def measure(obj, frame):
    scene = bpy.context.scene
    scene.frame_set(frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    verts, faces = evaluated_geometry(obj, depsgraph)
    return verts, faces


def main():
    obj = bpy.data.objects.get(OBJECT)
    if obj is None:
        result = {"status": "error", "message": "object not found: %s" % OBJECT}
        return result

    scene = bpy.context.scene
    original_frame = scene.frame_current

    rest = [obj.matrix_world @ v.co for v in obj.data.vertices]
    closed_v, closed_f = measure(obj, FRAME_CLOSED)
    open_v, open_f = measure(obj, FRAME_OPEN)
    loop_v, _ = measure(obj, FRAME_LOOP)

    rest_deviation = max(
        ((closed_v[i] - rest[i]).length for i in range(len(rest))), default=0.0
    )
    loop_seam = max(
        ((loop_v[i] - closed_v[i]).length for i in range(len(rest))), default=0.0
    )

    ratios = []
    for closed_face, open_face in zip(closed_f, open_f):
        a = poly_area(closed_face)
        if a > 1e-12:
            ratios.append(poly_area(open_face) / a)

    weighted = sum(
        1
        for v in obj.data.vertices
        if v.groups and sum(g.weight for g in v.groups) > 1e-6
    )

    scene.frame_set(original_frame)

    rig = bpy.data.objects.get(RIG)
    result = {
        "object": obj.name,
        "rig": rig.name if rig else None,
        "frames": {"closed": FRAME_CLOSED, "open": FRAME_OPEN, "loop": FRAME_LOOP},
        "rest_deviation": float("%.3g" % rest_deviation),
        "loop_seam": float("%.3g" % loop_seam),
        "face_area_ratio": {
            "min": round(min(ratios), 5) if ratios else None,
            "max": round(max(ratios), 5) if ratios else None,
        },
        "widths": {
            "closed": widths(closed_v),
            "open": widths(open_v),
        },
        "weighted_vertices": {"total": len(obj.data.vertices), "weighted": weighted},
    }
    return result


result = main()
