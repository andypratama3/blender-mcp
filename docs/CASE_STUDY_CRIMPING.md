# Case study: crimping tool rig

A real 16 MB glTF crimping tool, rigged and exported **live** inside a running Blender
5.4.0 Alpha session over MCP, without a single render. Every number on this page was
printed by the snippets in [`examples/crimping-tool/`](../examples/crimping-tool/).

## 1. Input

| Property | Value |
|---|---|
| Format | glTF, 16 MB, 9 embedded textures, 3 materials |
| Structure | Empty parent with `0.001` scale, mesh child |
| Shape | Flat in Y, V-shaped handles, jaws with a crimping die |
| Problem | Raw glTF vertex count inflated by per-seam vertex splits |

## 2. Inspection

The first step was to bake `matrix_world` into the mesh, drop the empty parent, and weld
duplicates. Then shell counting became meaningful.

| Metric | Raw import | After weld |
|---|---|---|
| Vertices | 3 412 | 606 |
| Polygons | — | 892 |
| Connected shells | — | 3 |
| Non-manifold edges | — | 0 |
| Flat axis | — | Y |

An ASCII silhouette on the XZ plane replaced a render for identifying the pivot (the
crotch of the V), the handle tips, and the jaw/die region.

## 3. Topology decision

The obvious split — cut at `x = 0`, one bone per side — is wrong for a plier-shaped
asset. Each half is a rigid body rotating about the pivot, so the left handle opens
while the left jaw swings inward. Jaws close as handles open.

Correct pairing is **diagonal**: one arm owns the left handle plus the *right* jaw half;
the other owns the mirror. Both rotate the same direction, so handles and jaws open
together.

| Bone | Head | Tail | Deform |
|---|---|---|---|
| `root` | pivot | +0.22 Z | no |
| `arm_L` | pivot | left handle tip | yes |
| `arm_R` | pivot | right handle tip | yes |

Hinge: pivot `(0, -0.26792, 0.02)`, axis = world Y, ±4° per arm (8° total).

Bone roll was aligned so `rotation_euler.x` is exactly world Y:

```python
d = (tail - head).normalized()
edit_bone.align_roll(Vector((d.z, 0.0, -d.x)))
```

Verified `matrix.to_3x3()` column X equals `(0, 1, 0)`.

## 4. Mesh preparation

1. Weld `remove_doubles(1e-5)`.
2. Vertical cut at `x = 0` with `bisect(use_fill=True)`; caps offset ±0.0004 on X.
3. Horizontal cut at the pivot height, `use_fill=True`.
4. Flip only the cap faces; keep glTF custom split normals.
5. `dissolve_degenerate`.
6. Assign vertex groups **per piece before joining**.
7. Parent with `ARMATURE` modifier, `use_vertex_groups=True`.

Result: 606 verts, 892 polys, 3 shells, 0 non-manifold edges, 0 zero-area faces, 3
materials intact.

## 5. Control

One custom property drives everything:

```python
rig["open"] = 0.0                       # 0 = closed, 1 = open
pb.rotation_mode = "XYZ"                # quaternion ignores euler drivers
driver.expression = "open*%.8f" % sign * math.radians(4)
```

`LIMIT_ROTATION` ±4.2° per arm acts as a safety net. The loop action (60 frames, 24 fps)
keyframes the **property**, not the bones: `0 → 1 → 0` at frames 1 / 30 / 60, `BEZIER`
plus `AUTO_CLAMPED`.

## 6. Verification results

Measured on `obj.evaluated_get(depsgraph).to_mesh()`, with `scene.frame_set(f)` forcing
driver evaluation.

| Gate | Threshold | Measured |
|---|---|---|
| Rest deviation vs source | < 1e-5 | **2e-7** |
| Loop seam, frame 60 vs 1 | exactly 0 | **0.0** |
| Face area ratio open/closed | 0.99–1.01 | **0.999–1.0005** |
| Handle width | > 0 increase | **0.2869 → 0.3569** |
| Jaw width | > 0 increase | **0.1738 → 0.1895** |
| Weighted vertices | 100% | **100%** |
| Non-manifold edges | 0 | **0** |
| Zero-area faces | 0 | **0** |

Both handles and jaws open, and the closed loop returns exactly to the start.

## 7. Export

glTF cannot carry drivers, custom properties, or constraints, so the rig was baked:

1. Rename the source action to `*_src`.
2. Unlink the custom-shape widget (otherwise it exports as an empty node).
3. Clear the action and remove drivers.
4. Keyframe `rotation_euler[0]` at frames 1 / 30 / 60 with `0 / ±4° / 0`.
5. Export with `export_skins=True`, `export_animations=True`,
   `export_animation_mode="ACTIONS"`, `export_yup=True`.
6. Restore: reassign the action, delete the bake, relink the widget, re-add drivers,
   `frame_set(1)`, save.

Exported GLB:

| Check | Result |
|---|---|
| Mesh / primitives | 1 mesh, 3 primitives |
| Skin / joints | 1 skin, 3 joints |
| Animation | 1 action, frames 1–60 |
| Textures | 9 embedded |
| Widget nodes | none |
| Width change frame 1 → 30 | non-zero |
| Width match frame 1 vs 60 | exact |

Re-imported in a **separate** Blender process to avoid disturbing the live session.

## 8. What this demonstrates

- Live GUI rigging over MCP is viable for a real 16 MB asset.
- Rigid-part assets need part pairing decided by the mechanism, not by symmetry.
- Numeric gates catch the exact failure a render would hide: jaws moving the wrong way.
- Baking and restoring is a repeatable export path, not a one-off hack.

## 9. Reproduce it

```bash
# inspect an asset
blender -b --factory-startup \
  --python skills/blender-live-rigging/scripts/inspect_glb.py -- "/path/asset.glb"

# measure a live rig (needs the bridge)
python3 skills/blender-live-rigging/scripts/blender_mcp.py \
  --file examples/crimping-tool/measure_live_rig.py

# verify the export
blender -b --factory-startup \
  --python skills/blender-live-rigging/scripts/verify_rig_glb.py -- "/path/rig.glb"
```

The asset itself is not included: it is a proprietary model. The method and the numbers
are the reproducible part.
