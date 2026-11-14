# Verification

A rig is done when measured numbers pass, not when the viewport looks plausible. Use the
evaluated mesh: modifiers, drivers, constraints, and armature deformation are applied
only there.

## 1. Read the evaluated mesh

```python
import bpy

def evaluated_vertices(obj, frame):
    scene = bpy.context.scene
    scene.frame_set(frame)                  # forces driver re-evaluation
    deps = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(deps)
    mesh = ev.to_mesh()
    verts = [obj.matrix_world @ v.co for v in mesh.vertices]
    faces = [[mesh.vertices[i].co.copy() for i in p.vertices] for p in mesh.polygons]
    ev.to_mesh_clear()
    return verts, faces
```

Never compare against `obj.data.vertices`; that mesh is undeformed.

## 2. Gates

| Metric | Threshold | Why |
|---|---|---|
| Rest deviation vs source mesh | < 1e-5 | skinning must not move the mesh at rest |
| Loop seam (last frame vs first) | exactly 0 | no pop when the clip loops |
| Face area ratio open / closed | 0.99–1.01 | rigid parts must not stretch |
| Handle width delta | > 0 | handles actually open |
| Jaw width delta | > 0 | jaws open in the same direction |
| Left/right symmetry | < 1 mm at equal angles | mirrored drivers |
| Weighted vertices | 100% | no unweighted geometry left behind |
| Non-manifold edges | 0 | watertight mechanical parts |
| Zero-area faces | 0 | no degenerate caps |
| Lowest deformed vertex vs floor | ≥ −0.006 | feet must not sink (locomotion) |
| Stance foot lowest vertex | 0 ± 0.006 | the support foot is actually planted |

## 2b. Ground contact: measure the mesh, not the bone

A foot bone's tail sits above the sole (0.4 stud on the R15 knight), so a gate written
against `pose_bone.tail.z` reports "feet on the ground" while the boot is buried 0.29
stud. Always take the lowest world-space vertex of the evaluated mesh, per frame:

```python
scene.frame_set(frame)
deps = bpy.context.evaluated_depsgraph_get()
ev = obj.evaluated_get(deps)
mesh = ev.to_mesh()
low = min((ev.matrix_world @ v.co).z for v in mesh.vertices)
ev.to_mesh_clear()
```

Report the minimum over all frames, the stance-foot maximum gap and the swing-foot peak
in one row. A walk that passes the bone gate and fails the mesh gate is a walking bug,
not a measurement bug.

## 3. Measuring widths

Pick bands that isolate the handles and the jaws. For the crimping tool: `z < 0` is the
handle region and `z > 0.25` is the jaw region.

```python
def widths(verts):
    handles = [v for v in verts if v.z < 0.0]
    jaws = [v for v in verts if v.z > 0.25]
    return {
        "handle": round(max(v.x for v in handles) - min(v.x for v in handles), 4),
        "jaw": round(max(v.x for v in jaws) - min(v.x for v in jaws), 4),
    }
```

Measure three states: rest (`open=0`), open (`open=1`), and the last frame.

## 4. Rest and loop checks

```python
rest = [v.co.copy() for v in tool.data.vertices]
v1, _ = evaluated_vertices(tool, 1)
v60, _ = evaluated_vertices(tool, 60)

max_rest_dev = max((v1[i] - rest[i]).length for i in range(len(rest)))
max_loop_dev = max((v60[i] - v1[i]).length for i in range(len(rest)))
```

`max_rest_dev` should be on the order of `1e-7`. A large value means the armature rest
pose differs from the mesh bind pose, or weights leak.

## 5. Face stretch

```python
def area(points):
    total = 0.0
    for k in range(1, len(points) - 1):
        total += (points[k] - points[0]).cross(points[k + 1] - points[0]).length * 0.5
    return total

ratios = [area(b) / area(a) for a, b in zip(faces_closed, faces_open) if area(a) > 1e-12]
```

`min(ratios)` and `max(ratios)` must stay inside 0.99–1.01. A spike means a vertex is
split between two rigid groups without a cut.

## 6. Weight coverage

```python
missing = 0
for v in tool.data.vertices:
    if not v.groups or sum(g.weight for g in v.groups) < 1e-6:
        missing += 1
```

`missing` must be 0.

## 7. Exported GLB

Re-import in a **separate** Blender process so the live session is untouched:

```bash
blender -b --factory-startup --python skills/blender-live-rigging/scripts/verify_rig_glb.py -- "/abs/rig.glb"

# different asset proportions: override the measurement bands
blender -b --factory-startup --python skills/blender-live-rigging/scripts/verify_rig_glb.py -- \
  "/abs/rig.glb" --low-z -0.05 --high-z 0.10
```

The default bands (`z < 0` handles, `z > 0.25` jaws) fit the crimping tool. Override them
for a smaller or differently placed asset. The GLB importer creates a `glTF_not_exported`
collection with bone-widget meshes; both scripts skip it so bounds and measurements are
not polluted by helpers.

The script prints JSON plus boolean gates:

| Gate | Meaning |
|---|---|
| `single_mesh` | one mesh, primitives preserved |
| `has_skin` | skin with joints present |
| `has_animation` | animation channels present |
| `no_widget_nodes` | custom-shape widget not exported |
| `moves_when_open` | measured width changes between first and mid frame |
| `loop_closed` | first and last frame measurements match |

Exit code is 0 only when every gate passes.

## 7b. Render-free GLB gates

`verify_rig_glb.py` needs Blender because it re-imports the file. When you only need to
prove the container and the animation data are sound, read the shipped bytes:

```bash
python3 skills/blender-live-rigging/scripts/glb_qa.py "/abs/rig.glb" --loop
python3 skills/blender-live-rigging/scripts/glb_qa.py "/abs/prop.glb" --manifold --max-tris 20000
```

Standard library only, exit 1 on any failed gate, one JSON object on stdout. It checks
header length, accessor bounds, weight sums, unweighted vertices, joint indices, bind
pose count, keyframe order, quaternion norm, loop closure, NaN/Inf and, with
`--manifold`, boundary and non-manifold edges. Gates, baselines for every case-study
asset, and the five deliberately broken files each gate caught:
`skills/blender-live-rigging/reference/glb-qa.md`.

Report the span, not the last timestamp: glTF exports start at `1/fps`, so a 24-frame
walk is `start_s 0.0417, duration_s 1.0`.

## 8. Reporting

Quote numbers and the frame they came from:

```text
rest deviation 2e-7 | loop seam 0.0 | face area 0.999-1.0005
handle 0.2869 -> 0.3569 | jaw 0.1738 -> 0.1895 | weights 100%
```

If a gate fails, say which one, the measured value, and the next diagnostic step. Do not
substitute a render for a failed number.

## 9. Exported FBX

Blender's FBX importer rebuilds bones from head/tail and marks a child as *connected*
when the parent's tail meets its head. Animated translation on that bone is then dropped
on reimport, so a correct file can look broken (a floating character) and a bad file can
look fine. Verify the shipped bytes instead:

```bash
python3 scripts/inspect_fbx.py export/Hero_Walk.fbx --model HumanoidRootNode
```

Expect the frame count you authored (25 keys for a 24-frame clip), the frame span
(`2..26` at 24 fps — FBX time is offset by one frame), and translation values that match
the authored bob. GLB has no such quirk: reimport it and compare measurements at the
first, middle and last frame.
