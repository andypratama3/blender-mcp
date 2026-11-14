# Rigging playbook — mechanical assets

Method used to rig the crimping-tool case study live in Blender 5.4 over MCP. The order
is generic and reusable for pliers, scissors, clamps, hinged tools, and other assets made
of rigid parts.

Principles: **rigid parts, rigid weights, numeric verification, no render by default.**

## 0. Constraints

- Work in the user's open Blender; never close it.
- Verify with numbers (positions, widths, face areas), not screenshots.
- Keep the source file untouched; write deliverables into the project folder.
- Save the `.blend` after every milestone.
- Render only if the owner asks.

## 1. Inspect before touching anything

Import, bake the world transform into mesh data, drop glTF empty parents (they often
carry `0.001` scale), weld, then measure.

```python
import bpy
from mathutils import Matrix

bpy.ops.import_scene.gltf(filepath="/path/asset.glb")
bpy.context.view_layer.update()
for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
    ob.data.transform(ob.matrix_world)
    ob.parent = None
    ob.matrix_basis = Matrix.Identity(4)
```

What to learn:

1. **Transforms** — glTF splits scale between empty parent and mesh; bake it.
2. **Shell count** — weld first (`remove_doubles(dist=1e-5)`); glTF splits vertices per
   normal/UV seam, so the raw count lies.
3. **Silhouette** — rasterise triangles to an ASCII grid on the dominant plane. This
   replaces a render and shows the V of the handles, the neck, and the die.
4. **Plane** — the smallest bounding-box extent is the flat axis. For a tool that is
   flat in Y, work in XZ and use the `FRONT` viewport.

Run the bundled inspector:

```bash
blender -b --factory-startup --python scripts/inspect_glb.py -- "/path/asset.glb"
```

It prints JSON (`bounds`, `flat_axis`, per-mesh shells, non-manifold edges) followed by
the ASCII silhouette.

## 2. Choose the topology (the decision that matters)

Question: how do handles open **and** jaws open at the same time?

- **Midline split at `x=0`, one bone per side — wrong.** Each side is a rigid body
  rotating around the pivot, so the left handle opens while the left jaw moves inward.
  The jaws close when the handles open.
- **Diagonal pairing — correct.** One arm owns the left handle plus the *right* jaw
  half; the other owns the mirror. Both rotate the same way around the pivot, so handles
  and jaws open together.
- **Pivot at the crotch of the V.** The horizontal seam barely moves (only `cos θ`
  shrink), so the joint does not open a gap.
- **Angle budget.** 4° per arm (8° total) is enough for crimping; on this asset that is
  +70 mm at the handles and +15.7 mm at the jaws.

Bone layout:

| Bone | Head → Tail | Deform | Owns |
|---|---|---|---|
| `root` | pivot → +0.22 Z | no | master transform, hinge point |
| `arm_L` | pivot → left handle tip | yes | left handle + right jaw half |
| `arm_R` | pivot → right handle tip | yes | right handle + left jaw half |

## 3. Cut and cap the mesh

1. Weld `remove_doubles(1e-5)` until the mesh is manifold.
2. **Vertical cut** at `x=0`: duplicate the mesh and `mesh.bisect(plane_no=(1,0,0),
   use_fill=True)`, one copy with `clear_inner=True`, one with `clear_outer=True`.
   Offset the caps by ±0.0004 on X so they do not z-fight when closed.
3. **Horizontal cut** at the pivot `z`: split each half again, both with `use_fill=True`.
4. Fix cap normals only: vertical caps face ±X, horizontal caps face −Z. Flip only the
   cap faces with `reverse_faces`; do not recalculate everything, or glTF custom split
   normals are lost.
5. `dissolve_degenerate` to remove zero-length edges left by the fill.
6. Assign vertex groups **per piece before joining**. After joining, `z ≈ pivot` is
   ambiguous, so assigning afterwards can leak weights across parts.
7. Parent to the armature with an `ARMATURE` modifier (`use_vertex_groups=True`).

Healthy result for this asset: 606 verts, 892 polys, 3 shells, 0 non-manifold edges,
0 zero-area faces, 3 materials intact.

## 4. Align the hinge axis

So that `rotation_euler.x` is exactly the world hinge axis (Y here):

```python
from mathutils import Vector

b = arm.edit_bones.new("arm_L")
b.head = (0.0, y_mid, z_pivot)
b.tail = (x_min + 0.01, y_mid, -0.425)
d = (Vector(b.tail) - Vector(b.head)).normalized()
b.align_roll(Vector((d.z, 0.0, -d.x)))   # local X == world Y
b.use_deform = True
```

Verify by printing `bone.matrix.to_3x3()`; column X must be `(0, 1, 0)`.
`align_roll` is exact; `roll = 0` leaves a few degrees of skew.

Then set `pose_bone.rotation_mode = "XYZ"`. The default `QUATERNION` silently ignores
drivers on `rotation_euler`.

## 5. One control property

```python
import math

rig["open"] = 0.0
rig.id_properties_ui("open").update(
    min=0, max=1, soft_min=0, soft_max=1,
    description="0 = closed, 1 = fully open",
)

for name, sign in (("arm_L", 1.0), ("arm_R", -1.0)):
    pb = rig.pose.bones[name]
    pb.rotation_mode = "XYZ"
    fc = pb.driver_add("rotation_euler", 0)
    drv = fc.driver
    drv.type = "SCRIPTED"
    var = drv.variables.new()
    var.name = "open"
    var.type = "SINGLE_PROP"
    var.targets[0].id_type = "OBJECT"
    var.targets[0].id = rig
    var.targets[0].data_path = '["open"]'
    drv.expression = "open*%.8f" % (sign * math.radians(4))

    limit = pb.constraints.new("LIMIT_ROTATION")
    limit.owner_space = "LOCAL"
    limit.use_limit_x = True
    limit.min_x, limit.max_x = -math.radians(4.2), math.radians(4.2)
```

Loop action (60 frames at 24 fps): keyframe the **property**, not the bones.

```python
for frame, value in ((1, 0.0), (30, 1.0), (60, 0.0)):
    rig["open"] = value
    rig.keyframe_insert(data_path='["open"]', frame=frame)

action = rig.animation_data.action
for bag in action.layers[0].strips[0].channelbags:
    for fcurve in bag.fcurves:
        for key in fcurve.keyframe_points:
            key.interpolation = "BEZIER"
            key.handle_left_type = key.handle_right_type = "AUTO_CLAMPED"
        fcurve.update()
```

## 6. Verification gates

Always read the evaluated mesh:

```python
scene.frame_set(30)
deps = bpy.context.evaluated_depsgraph_get()
evaluated = tool.evaluated_get(deps)
mesh = evaluated.to_mesh()
```

| Metric | Threshold | Case study |
|---|---|---|
| Rest deviation vs source | < 1e-5 | 2e-7 |
| Loop seam (last vs first frame) | 0 | 0.0 |
| Face area ratio open/closed | 0.99–1.01 | 0.999–1.0005 |
| Handle opening | > 0 | +0.0700 |
| Jaw opening | > 0 | +0.0157 |
| Weighted vertices | 100% | 100% |
| Non-manifold / zero-area faces | 0 | 0 / 0 |

If face stretch exceeds 1%, a weight boundary cuts geometry without a matching edge
loop. Add a cut or fix the quadrant split; do not hide it with smoother weights.

Full snippets and a standalone checker: [`VERIFICATION.md`](VERIFICATION.md).

## 7. Scene hygiene

- One collection per asset (`Crimping_Tool`), plus an excluded `Rig_Widgets` collection.
- Root custom shape: a 48-vertex circle, `use_custom_shape_bone_size = True`.
- `rig.show_in_front = True`, `display_type = "OCTAHEDRAL"`, bone collections
  `Controls` and `Deform`.
- `README_RIG` text block inside the `.blend` with pivot, bones, property, angles.
- `rig.asset_mark()` + description + tags (API, not the operator).
- Scene renamed, frame range 1–60, 24 fps, saved at the rest frame.

## 8. Export glTF (bake, then restore)

glTF has no drivers, custom properties, or constraints, so bake bone keyframes.

1. Rename the source action (`..._src`) so the baked action gets the clean name.
2. Unlink the widget object from its collection, or it becomes an empty node.
3. `animation_data.action = None`; `pose_bone.driver_remove("rotation_euler", 0)`.
4. Keyframe `pose_bones[arm].rotation_euler[0]` at 1/30/60 with `0 / ±A / 0`; set
   `BEZIER` + `AUTO_CLAMPED`.
5. Export:

```python
bpy.ops.export_scene.gltf(
    filepath="/abs/out.glb",
    export_format="GLB",
    use_selection=False,
    export_apply=False,
    export_animations=True,
    export_animation_mode="ACTIONS",
    export_skins=True,
    export_yup=True,
)
```

6. Restore: reassign the original action, delete the baked action, relink the widget,
   re-add the drivers with the same expressions, `frame_set(1)`, save.

Warnings like `Baking animation because of unsupported constraints` are expected.

Verify by re-importing in a separate Blender process:

```bash
blender -b --factory-startup --python scripts/verify_rig_glb.py -- "/abs/out.glb"
```

Expect: one mesh with the original primitive count, one skin with all joints, the right
animation name/range, no `WGT_` node, widths changing between first and mid frame, and
identical first/last frames.

## 9. Checklist

1. Import → bake transform → weld → manifold check.
2. Silhouette → plane, pivot, moving parts.
3. Decide rigid-part pairing (diagonal for scissors/pliers).
4. Cut, cap, offset, fix cap normals only.
5. Vertex groups before join.
6. Bones with `align_roll`, rotation mode XYZ, rotation limits.
7. Property + drivers + loop action.
8. Run every verification gate.
9. Tidy scene + `README_RIG` text block.
10. Save → bake → export → restore → save.
11. Re-import verify.
12. Update project docs with final numbers.
