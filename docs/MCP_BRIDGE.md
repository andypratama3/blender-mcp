# MCP bridge

How an agent talks to a running Blender process, and the traps that cost the most time.

## 1. Architecture

```text
agent --TCP 127.0.0.1:9876--> MCP add-on inside Blender --> exec(python) --> `result`
        JSON + "\0"           bpy / scene / depsgraph
```

- One connection = one snippet.
- The snippet runs inside Blender with full `bpy` access.
- The add-on returns `result`, captured `stdout`, and a traceback on error.
- No isolation: any Python can run. See [`SECURITY.md`](../SECURITY.md).

## 2. Protocol

Request, UTF-8 and terminated by a null byte:

```json
{"type": "execute", "code": "import bpy\nresult = {...}", "strict_json": true}
```

Reply, JSON and terminated by a null byte:

```json
{"status": "ok", "result": {...}, "stdout": "..."}
{"status": "error", "message": "<traceback>"}
```

Rules:

1. The snippet must assign `result` as a JSON-serializable dict.
2. `strict_json: true` is required; if a value is not serializable, fix the snippet
   instead of relaxing the flag.
3. `print()` is captured in `stdout` and is safe to use for logging.
4. Exceptions come back as `status: "error"`; the Blender session stays alive.
5. Use a client timeout of 300 s or more for imports, exports, and welding large meshes.

## 3. Client

`skills/blender-live-rigging/scripts/blender_mcp.py`:

```bash
# code as an argument (mind shell quoting)
python3 blender_mcp.py 'import bpy
result = {"frame": bpy.context.scene.frame_current}'

# code from stdin or a file
python3 blender_mcp.py < snippet.py

# custom host/port/timeouts (flags are available via --help)
python3 blender_mcp.py --port 9876 --timeout 600 --file snippet.py
```

Minimal implementation:

```python
import json, socket

def call(code, host="127.0.0.1", port=9876, timeout=300):
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.sendall((json.dumps({"type": "execute", "code": code, "strict_json": True}) + "\0").encode())
        buf = b""
        while b"\0" not in buf:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
    raw = buf.split(b"\0")[0]
    return json.loads(raw) if raw else {"status": "error", "message": "empty response"}
```

## 4. Launch modes

| | GUI (`--online-mode file.blend`) | Background (`-b --command blender_mcp`) |
|---|---|---|
| Bridge | autostart timer | blocking CLI command |
| Visible to user | yes | no |
| Viewport operators | work | no-op |
| Use for | real work | batch/CI only |

Autostart conditions and failure handling: [`INSTALL.md`](INSTALL.md) §3.

Confirm which instance you reached:

```python
import bpy
result = {"gui": not bpy.app.background, "file": bpy.data.filepath,
          "version": bpy.app.version_string}
```

If `gui` is false while the user has Blender open, you are on the wrong process. Stop.

## 5. Sandbox limits

A small blocklist rejects `wm.quit_blender`, `wm.read_factory_settings`,
`wm.read_factory_userpref`, `wm.read_userpref`, and `sys.exit`. Everything else is
allowed. Do not try to bypass it.

For a clean scene in a **throwaway** process:

```python
bpy.ops.wm.read_homefile(use_empty=True, use_factory_startup=True)
```

Never do that in the live GUI: it discards the user's scene.

## 6. Safe operation pattern

1. **Snapshot** the state in one call (`objects`, `frame`, custom properties).
2. **One logical change per call**, returning post-change metrics.
3. **Idempotent**: look up existing objects/drivers before creating them.
4. **Save** after each milestone: `bpy.ops.wm.save_as_mainfile(filepath=..., compress=True)`.
5. **Force driver evaluation** with `scene.frame_set(f)`; `view_layer.update()` is not enough.
6. **Verify numerically**; render only when the owner asks.

## 7. Viewport focus (required in GUI sessions)

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

- Use `FRONT` for a flat XZ asset, `RIGHT`/`TOP` for other planes.
- In pose mode select the bones so `view_selected` frames the bones, not the object.
- Background mode has no `VIEW_3D` area, so the loop is empty and the function is a no-op.

## 8. Performance and timeouts

| Operation | Suggested timeout |
|---|---|
| Read state, set properties | 30 s |
| Import glTF/FBX, weld a large mesh | 300 s |
| Export GLB with textures | 600 s |
| Render (owner-requested) | 1800 s |

Long operations block the call. Do not poll a running call; wait for the reply.

## 9. Proven Blender 5.4 pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Driver seems dead | depsgraph not re-evaluated | `scene.frame_set(f)` |
| `Action.fcurves` missing | slotted actions | `act.layers[0].strips[0].channelbags[*].fcurves` |
| `asset.mark()` poll fails | operator reads Outliner selection | `obj.asset_mark()` API |
| Custom-prop keyframes ignored | wrong data path | `'["open"]'` |
| glTF loses animation | drivers/properties not exportable | bake to bone keyframes |
| Baked action named `.001` | source action holds the name | rename source first |
| Widget becomes an empty node | object still linked | unlink during export |
| Z-fighting at a seam | coincident caps | offset ±0.0004 |
| Render engine enum error | 5.4 uses `BLENDER_EEVEE` | select from the enum, not a hardcoded name |

More: [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md).
