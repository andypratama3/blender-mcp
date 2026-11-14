---
name: blender-live-rigging
description: "Rig, edit, verify and export 3D assets live in the user's open Blender app through the official Blender MCP socket bridge. Use for armatures, skinning, mechanical/hinge rigs, drivers, custom-property controls, evaluated-mesh verification, baked glTF export, and renders only when the owner explicitly requests them."
license: MIT
compatibility: "Blender 5.2+ with the official Blender Lab MCP add-on enabled on 127.0.0.1:9876. Scripts are Python 3 standard library only."
---

# Blender Live Rigging

Drive the Blender instance the user is already looking at. No headless batches, no
closing their app. Every claim of "done" must be backed by numbers read from the
evaluated depsgraph. Rendering is off by default and only happens when the owner asks.

Repository docs (read when you need depth, not every time):

- `docs/MCP_BRIDGE.md` — protocol, launch modes, pitfalls, viewport focus
- `docs/RIGGING_PLAYBOOK.md` — full rigging method and export/restore recipe
- `docs/VERIFICATION.md` — metric thresholds and snippets
- `docs/RENDERING.md` — owner-request render path
- `reference/roblox-avatar.md` — R15 body contract, in-place walk IK, FBX verification
- `reference/blender-5x-api.md` — slotted actions, measured 5.4 API, glTF time origin
- `reference/glb-qa.md` — render-free GLB gates, baselines, negative-test evidence
- `docs/CASE_STUDY_KNIGHT.md` — measured R15 avatar + walk loop (repo root)

If this skill was installed from `andypratama3/blender-mcp`, the repo root is three
levels up from this file (`skills/blender-live-rigging/SKILL.md`).

## Hard rules

1. **Live GUI only.** Confirm `bpy.app.background == False`. Never kill Blender while
   the user is working; if you must restart for a port conflict, save `.blend` first
   and reopen the same file.
2. **No render unless the owner asks.** Default verification is numeric: vertex
   coordinates, widths, areas, ratios. When the owner explicitly requests a render, do
   it in the live session (see *Render on request*).
3. **Focus the viewport on what you edit**, before and after the change: select the
   object/bones, make one active, run `view3d.view_axis` + `view3d.view_selected`.
   Pick the axis matching the asset plane (`FRONT` for flat XZ assets).
4. **Use the evaluated mesh**, never the original:
   `obj.evaluated_get(depsgraph).to_mesh()`.
5. **Force driver evaluation with `scene.frame_set(f)`** — `view_layer.update()` is not
   enough.
6. **Save incrementally** with `bpy.ops.wm.save_as_mainfile(filepath=..., compress=True)`
   at each milestone; keep deliverables inside the project folder.
7. **One `execute` = one atomic, idempotent step** that returns the metrics proving it.
8. **Measure what touches the floor on the mesh, not the bone.** A bone tail can sit
   0.4 stud above the sole, so a bone-tail gate passes while the boot sinks through the
   ground. Use the evaluated mesh's lowest world vertex.

## 1. Connect

The bridge is the official add-on `bl_ext.blenderlab.mcp` on `127.0.0.1:9876`.

```bash
lsof -nP -iTCP:9876 -sTCP:LISTEN          # must be free before launch
open -a Blender --args --online-mode "/abs/path/file.blend"   # macOS
sleep 8 && lsof -nP -iTCP:9876 -sTCP:LISTEN
```

`--online-mode` is mandatory (autostart requires `bpy.app.online_access`), and never
use `--factory-startup` (it disables the extension). Then:

```bash
python3 scripts/blender_mcp.py 'import bpy
result = {"gui": not bpy.app.background, "file": bpy.data.filepath}'
```

## 2. Inspect the asset

Import glTF, bake `matrix_world` into mesh data, drop empty parents, weld duplicates
(`remove_doubles(1e-5)`), count connected shells, and print an ASCII silhouette to find
the plane, pivot, and moving parts:

```bash
blender -b --factory-startup --python scripts/inspect_glb.py -- "/path/asset.glb"
```

## 3. Decide the rig topology

For mechanical assets: **rigid parts, rigid weights, one bone per part**. For
scissor/plier shapes, pair parts **diagonally** (left handle + right jaw half) so
handles and jaws open together; a midline split makes jaws close as handles open.

Put the hinge pivot where the handles meet, put the seam cut there too, and align the
bone so `rotation_euler.x` is exactly the world hinge axis:

```python
d = (Vector(b.tail) - Vector(b.head)).normalized()
b.align_roll(Vector((d.z, 0.0, -d.x)))   # local X == world Y
```

## 4. Prepare the mesh

Bisect at every rigid-part boundary with `use_fill=True`, offset caps ~0.0004 to kill
z-fighting, flip only the cap faces (keep glTF custom split normals), assign vertex
groups per part **before** joining, then parent with an `ARMATURE` modifier.

## 5. Controls and animation

One custom property (`open`, 0–1) drives every bone through simple driver expressions,
plus `LIMIT_ROTATION` as a safety net. Set `rotation_mode = "XYZ"` before driving
`rotation_euler`. Keyframe the property — not the bones — for the loop action, and set
`BEZIER` + `AUTO_CLAMPED`.

## 6. Verify (gate before claiming success)

| Metric | Threshold |
|---|---|
| Rest deviation vs source mesh | < 1e-5 |
| Loop seam (last frame vs first) | 0 |
| Face area ratio open/closed | 0.99–1.01 |
| Handle and jaw both move outward | > 0 |
| Vertices weighted | 100% |
| Non-manifold / zero-area faces | 0 |
| Lowest deformed vertex vs floor | ≥ −0.006, stance foot 0 ± 0.006 |

`scripts/verify_rig_glb.py` re-imports the exported GLB in a separate Blender process
(never disturb the live session) and prints node/skin/animation counts plus widths at
frames 1/15/30/60.

For locomotion, solve the legs with two-bone IK against an ankle target instead of
hand-keying joint angles, then measure every frame:

```python
low = min((ev.matrix_world @ v.co).z for v in ev.to_mesh().vertices)  # per frame
```

If a bone gate and a mesh gate disagree, the mesh gate is right.

### 6d. Render-free GLB QA

```bash
python3 scripts/glb_qa.py export/model.glb --loop --max-tris 20000
python3 scripts/glb_qa.py export/tool.glb --manifold
```

Standard library only, no Blender: it reads the GLB container directly and gates header
length, accessor bounds, weight sums, unweighted vertices, joint indices, bind-pose
counts, keyframe order, quaternion norm, loop closure, NaN and (with `--manifold`)
boundary edges. Exit 1 on any failure. `verify_rig_glb.py` still owns the moving-parts
width measurement. Gates, baselines and the five deliberately broken files they caught:
`reference/glb-qa.md`.

## 6b. Run a multi-file project script live

Scripts that import their own modules must be loaded by path inside the live session:

```python
import importlib.util, sys
spec = importlib.util.spec_from_file_location("walk_cycle", "/abs/project/walk_cycle.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["walk_cycle"] = mod          # otherwise dataclasses/imports see a duplicate
spec.loader.exec_module(mod)
result = mod.main(save=True)             # return a dict of measured gates
```

Keep `__main__` for the headless run (`blender -b file.blend --python walk_cycle.py
-- --save`) and call `main()` from the bridge, so one script serves both paths.

## 6c. Actions on Blender 5.x (slotted)

`Action.fcurves`, `Action.groups` and `Action.id_root` do not exist in 5.4. Use the
helpers instead of retyping the channelbag walk, and bind the slot explicitly:

```bash
# live session (cwd = this skill folder); returns the audit as `result`
python3 scripts/blender_mcp.py "import sys; sys.path.insert(0, 'scripts')
import action_compat
result = action_compat.audit()"

# headless; exit 1 when a slot is unbound
blender -b file.blend --python scripts/action_compat.py
```

```python
from action_compat import iter_fcurves, ensure_fcurve, assign_action
slot = assign_action(obj, action)                 # assigning alone leaves action_slot None
ensure_fcurve(action, slot, 'pose.bones["Head"].rotation_euler', 1, group_name="HeadTwist")
```

Measured failure mode: assigning an action that already has a slot to a *different* ID
leaves `animation_data.action_slot is None` and the rig sits at rest with no error
(head at `4.0` instead of the animated `3.92`). Gate: `action_compat.py` reports
`slot_assigned: true` and `slot_fcurves > 0` for every animated object. Also
`channelbag.fcurves.new(..., group_name=...)`, never `action_group=`.

Details and the rest of the measured API: `reference/blender-5x-api.md`.

## 7. Export glTF

glTF has no drivers, custom properties, or constraints. Bake them:

1. Rename the source action (`*_src`) so the baked action gets a clean name.
2. Unlink the custom-shape widget object, else it becomes an empty node.
3. Clear the action, `pose_bone.driver_remove(...)`, keyframe `rotation_euler[0]` at
   the pose extremes.
4. Export with `export_skins=True`, `export_animations=True`,
   `export_animation_mode="ACTIONS"`, `export_yup=True`.
5. Restore: reassign the action, delete the bake, relink the widget, re-add the
   drivers, `frame_set(1)`, save.

Warnings about "Baking animation because of unsupported constraints" are expected.

## Render on request (owner only)

Trigger: the owner explicitly says render, or asks for a preview image/video. Do not
render on your own initiative, and do not render as verification.

Blender 5.4 exposes EEVEE as `BLENDER_EEVEE` (not `BLENDER_EEVEE_NEXT`), so pick from
the enum instead of hardcoding a version-specific name. glTF scenes have **no camera
and no lights** — create them first, in a `Render_Setup` collection.

```python
import bpy, math, os

scene = bpy.context.scene
engines = [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
scene.render.engine = next(e for e in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT") if e in engines)

if scene.camera is None:
    cam_data = bpy.data.cameras.new("Preview_Cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 1.0
    cam = bpy.data.objects.new("Preview_Cam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (0.0, -2.0, -0.055)
    cam.rotation_euler = (math.radians(90), 0.0, 0.0)
    scene.camera = cam

if not any(o.type == "LIGHT" for o in bpy.data.objects):
    light_data = bpy.data.lights.new("Preview_Key", "AREA")
    light_data.energy = 300
    light_data.size = 2.0
    light = bpy.data.objects.new("Preview_Key", light_data)
    scene.collection.objects.link(light)
    light.location = (1.5, -2.0, 1.5)
    light.rotation_euler = (math.radians(55), 0.0, math.radians(35))

scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = "/abs/project/render/preview.png"
bpy.ops.render.render(write_still=True)
result = {"image": scene.render.filepath,
          "size": os.path.getsize(scene.render.filepath),
          "engine": scene.render.engine, "camera": scene.camera.name}
```

Rules for this path: save `.blend` first, write inside `<project>/render/`, report the
absolute path and file size, raise the client timeout, and never start a headless render
of a file with unsaved changes.

## Blender 5.4 traps

| Symptom | Cause | Fix |
|---|---|---|
| Driver changes nothing | depsgraph not evaluated | `scene.frame_set(f)` |
| `Action.fcurves` missing | slotted actions | `act.layers[0].strips[0].channelbags[*].fcurves`, or `scripts/action_compat.py` |
| Rig does not move, no error | assigned action has no slot bound to this ID | `assign_action()` / set `animation_data.action_slot` |
| `fcurves.new(action_group=...)` TypeError | 5.4 keyword is `group_name` | `cb.fcurves.new(path, index, group_name="...")` |
| `asset.mark()` poll fails | operator reads Outliner selection | `obj.asset_mark()` API |
| Property keyframes ignored | wrong data path | `'["open"]'` |
| `.001` action suffix | name collision | rename source action first |
| Widget in GLB | object still in a scene collection | unlink during export |
| `Unrecognized command` | `--factory-startup` / extension off | relaunch online |
| Autostart silent | port taken | free port, relaunch (no retry) |
| Render enum error | wrong engine name | select `BLENDER_EEVEE` from the enum |
| `enum "OCTAHEDRAL" not found` | armature display is data, not object | `rig.data.display_type = "OCTAHEDRAL"` |
| `bpy.context.window` is `None` | background build has no window | guard with `window_manager.windows` |
| FBX reimport floats the character | importer marks the root as a connected bone and drops its translation | verify the file with `scripts/inspect_fbx.py`, not the round trip |

## Deliverables

- `.blend` — authoritative rig, saved at rest frame, with a `README_RIG` text block.
- `.glb` — skinned + animated, verified by re-import.
- `README.md` in the project folder with pivot, bones, property, angles, numbers.
