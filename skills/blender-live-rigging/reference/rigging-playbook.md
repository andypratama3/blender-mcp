# Rigging playbook — condensed

Full version with case-study numbers: `docs/RIGGING_PLAYBOOK.md` (this repo).
Primary rule: **rigid parts, rigid weights, numeric verification, no render by
default** (render only when the owner asks).

## 1. Inspect

```bash
python3 scripts/blender_mcp.py "$(cat snippet.py)"    # or run headless:
blender -b --factory-startup \
    --python scripts/inspect_glb.py -- "/path/asset.glb"
```

Bake `matrix_world` into mesh data and drop glTF empty parents (they usually carry
0.001 scale). Weld with `remove_doubles(1e-5)` first — glTF splits vertices per
normal/UV seam, so raw shell counts lie. Use the ASCII silhouette to find the flat
plane, the pivot, and which parts move.

## 2. Choose topology

- Mechanical asset → one bone per rigid piece, weight 1.0, no blend zones.
- Scissor/plier → **diagonal pairing**: left handle + right jaw half in one bone,
  mirrored for the other. Midline split is wrong: handles open while jaws close.
- Pivot at the handle crotch, seam cut on the same plane, so the joint barely moves
  (`cos θ` shrink only).

| Bone | Role |
|---|---|
| `root` | master transform + hinge point, non-deform |
| `arm_L` | left handle + opposite jaw half, deform |
| `arm_R` | right handle + other jaw half, deform |

## 3. Cut and cap

1. Bisect on the rigid boundaries with `use_fill=True`.
2. Offset each cap ±0.0004 along the seam normal to avoid z-fighting.
3. Flip only the cap faces; keep glTF custom split normals intact.
4. Assign vertex groups per piece **before** joining.
5. Parent with an `ARMATURE` modifier (`use_vertex_groups=True`).

Health targets: 0 non-manifold edges, 0 zero-area faces, 100% weighted vertices.

## 4. Hinge axis

```python
d = (Vector(b.tail) - Vector(b.head)).normalized()
b.align_roll(Vector((d.z, 0.0, -d.x)))   # local X == world Y exactly
```

Then `pose_bone.rotation_mode = "XYZ"` — the default `QUATERNION` silently ignores
drivers on `rotation_euler`. Verify by printing `bone.matrix.to_3x3()`; column X must
be `(0, 1, 0)`.

## 5. One control property

```python
rig["open"] = 0.0
rig.id_properties_ui("open").update(min=0, max=1, soft_min=0, soft_max=1,
                                    description="0 = closed, 1 = fully open")
for name, sign in (("arm_L", 1.0), ("arm_R", -1.0)):
    pb = rig.pose.bones[name]
    fc = pb.driver_add("rotation_euler", 0)
    drv = fc.driver
    drv.type = "SCRIPTED"
    var = drv.variables.new(); var.name = "open"; var.type = "SINGLE_PROP"
    var.targets[0].id_type = "OBJECT"
    var.targets[0].id = rig
    var.targets[0].data_path = '["open"]'
    drv.expression = "open*%f" % (sign * math.radians(4))
    limit = pb.constraints.new("LIMIT_ROTATION")
    limit.owner_space = "LOCAL"
    limit.use_limit_x = True
    limit.min_x, limit.max_x = -math.radians(4.2), math.radians(4.2)
```

Loop action: keyframe the **property**, not the bones, at frames 1 / mid / last,
then set every keyframe to `BEZIER` + `AUTO_CLAMPED` via
`act.layers[0].strips[0].channelbags[*].fcurves`.

## 6. Verification gates

Read the evaluated mesh, never the source:

```python
scene.frame_set(30)
deps = bpy.context.evaluated_depsgraph_get()
ev = tool.evaluated_get(deps); me = ev.to_mesh()
```

| Metric | Threshold | Crimping-tool result |
|---|---|---|
| Rest deviation | < 1e-5 | 2e-7 |
| Loop seam (last vs first) | 0 | 0.0 |
| Face area ratio open/closed | 0.99–1.01 | 0.999–1.0005 |
| Handle opening | > 0 | 0.2869 → 0.3569 |
| Jaw opening | > 0 | 0.1738 → 0.1895 |
| Weighted vertices | 100% | 100% |

Face stretch > 1% means a weight boundary cuts geometry without a cut — add a cut or
fix the quadrant split.

## 7. Scene hygiene

Collection per asset, excluded `Rig_Widgets` collection with the root circle,
`show_in_front`, `OCTAHEDRAL`, bone collections `Controls`/`Deform`,
`README_RIG` text block inside the `.blend`, `obj.asset_mark()` + description + tags.
Save at the rest frame.

## 8. glTF export

glTF has no drivers, custom properties, or constraints. Bake:

1. Rename the source action to `*_src`.
2. Unlink the widget object from its collection.
3. `animation_data.action = None`, `driver_remove(...)`, keyframe
   `pose_bones[arm].rotation_euler[0]` at extremes, BEZIER/AUTO_CLAMPED.
4. `bpy.ops.export_scene.gltf(filepath=..., export_format="GLB",
   use_selection=False, export_apply=False, export_animations=True,
   export_animation_mode="ACTIONS", export_skins=True, export_yup=True)`.
5. Restore action, delete bake, relink widget, re-add drivers, `frame_set(1)`, save.

"Baking animation because of unsupported constraints" warnings are expected.

Verify by re-importing in a separate Blender process:

```bash
blender -b --factory-startup \
    --python scripts/verify_rig_glb.py -- "/path/rig.glb"
```

Expect: one mesh with the original primitive count, one skin with all joints, one
animation with the right name/range, no `WGT_` node, width delta between first and
mid frame, identical first/last frames.

## 9. Checklist

1. Import → bake transform → weld → manifold check.
2. ASCII silhouette → pivot, axis, moving parts.
3. Rigid-part pairing decided.
4. Cuts + caps + offset + cap normals.
5. Vertex groups before join.
6. Bones with `align_roll`, rotation mode XYZ, limits.
7. Property + drivers + loop action.
8. Numeric verification gates.
9. Scene tidy + README text block.
10. Save → bake → export → restore → save.
11. Re-import verify.
12. Update project docs with final numbers.
