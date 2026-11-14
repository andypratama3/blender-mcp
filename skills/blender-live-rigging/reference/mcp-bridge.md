# Blender MCP bridge — quick reference

Full version: `docs/MCP_BRIDGE.md` (this repo).

## Architecture

```
agent --TCP 127.0.0.1:9876--> MCP add-on inside Blender --> exec(python) --> `result`
```

The add-on is `bl_ext.blenderlab.mcp` (Blender Lab, 1.0.3), located at
`~/Library/Application Support/Blender/5.4/extensions/blenderlab/mcp`.

## Protocol

Request, UTF-8 + `\0`:

```json
{"type": "execute", "code": "import bpy\nresult = {...}", "strict_json": true}
```

Reply, JSON + `\0`:

```json
{"status": "ok", "result": {...}, "stdout": "..."}
{"status": "error", "message": "<traceback>"}
```

`result` must be a JSON-serializable dict. `print()` output comes back in `stdout`.
Exceptions never kill the session. Use a client timeout ≥ 300 s for heavy imports
and exports.

Client: `scripts/blender_mcp.py` (stdin or one argument).

## Launch

```bash
lsof -nP -iTCP:9876 -sTCP:LISTEN                     # must be free
open -a Blender --args --online-mode "/abs/file.blend"
sleep 8 && lsof -nP -iTCP:9876 -sTCP:LISTEN
```

- Autostart fires once, ~1 s after startup. It needs the add-on preference
  `use_autostart`, `bpy.app.online_access` (`--online-mode`), and a free port. If any
  condition fails it does **not** retry — save, quit, relaunch.
- Never `--factory-startup`: it disables the extension and the `blender_mcp`
  command becomes unknown.
- `open -a` ignores `--args` when the app is already running.
- Background/batch alternative:
  `Blender -b --online-mode --command blender_mcp` (blocking serve, no viewport).

## Verifying you are on the live GUI

```python
import bpy
result = {"gui": not bpy.app.background, "file": bpy.data.filepath}
```

## Blocked operators (`weak_sandbox.py`)

`wm.quit_blender`, `wm.read_factory_settings`, `wm.read_factory_userpref`,
`wm.read_userpref`, `sys.exit`. Use `wm.read_homefile(use_empty=True,
use_factory_startup=True)` for a clean scene in a throwaway process.

## Viewport focus (required in GUI sessions)

```python
import bpy

def focus(names, axis="FRONT"):
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for name in names:
        ob = bpy.data.objects.get(name)
        if ob:
            ob.hide_set(False)
            ob.select_set(True)
            bpy.context.view_layer.objects.active = ob
    views = []
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type != "VIEW_3D":
                continue
            region = next((r for r in area.regions if r.type == "WINDOW"), None)
            if region is None:
                continue
            with bpy.context.temp_override(window=win, area=area, region=region):
                bpy.ops.view3d.view_axis(type=axis, align_active=False)
                bpy.ops.view3d.view_selected(use_all_regions=False)
            r3d = area.spaces.active.region_3d
            views.append({"center": list(r3d.view_location),
                          "distance": r3d.view_distance,
                          "perspective": r3d.view_perspective})
    return views
```

Axis choice: `FRONT` for a flat XZ asset, `RIGHT`/`TOP` otherwise. In pose mode
select the bones so `view_selected` frames the bones, not just the object. In
background mode the area loop is empty, so the function is a no-op.

## Safe operation pattern

1. Snapshot state in one call.
2. One logical change per call, returning post-change metrics.
3. Make calls idempotent (`bpy.data.objects.get`, remove old drivers first).
4. Save after each milestone, inside the project folder.
5. Force driver evaluation with `scene.frame_set(f)`.
6. Verify numerically. Render only when the owner explicitly asks.

## Render (only when the owner asks)

Default verification is numeric. If the owner explicitly requests an image or video,
render from the live session and keep output inside the project:

```python
import bpy
s = bpy.context.scene
engines = [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
s.render.engine = next(e for e in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT") if e in engines)
# glTF scenes have no camera/lights: create them, put them in a Render_Setup collection
s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = 1920, 1080, 100
s.render.image_settings.file_format = "PNG"
s.render.filepath = "/abs/project/render/preview.png"
bpy.ops.render.render(write_still=True)
result = {"file": s.render.filepath}
```

- Blender 5.4 uses `BLENDER_EEVEE`, not `BLENDER_EEVEE_NEXT` — select from the enum.
- Save the `.blend` first; write to `<project>/render/`, never `/tmp`.
- Write backgrounds/lights into a `Render_Setup` collection so they never reach the glTF export.
- For a sequence set `frame_start/frame_end` and use `bpy.ops.render.render(animation=True)`
  with `FFMPEG`/`MPEG4`/`H264`.
- Rendering blocks the MCP call — raise the client timeout.
- Don't start a headless `-b` render of a file the owner has unsaved changes in.
- Report the absolute output path and file size.

## Proven Blender 5.4 pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Driver seems dead | depsgraph not re-evaluated | `scene.frame_set(f)` |
| `Action.fcurves` missing | slotted actions | `act.layers[0].strips[0].channelbags[*].fcurves` |
| `asset.mark()` poll fails | operator reads Outliner selection | `obj.asset_mark()` |
| Custom-prop keyframes ignored | wrong data path | `'["open"]'` |
| glTF loses animation | drivers/properties not exportable | bake to bone keyframes |
| Baked action named `.001` | source action still holds the name | rename source first |
| Widget becomes an empty node | object still linked | unlink during export |
| Z-fighting at seam | coincident caps | offset ±0.0004 |
