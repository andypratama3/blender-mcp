# Troubleshooting

Symptom first. Each row names the cause and the smallest fix. Start with
`python3 scripts/doctor.py --json` — it covers most rows below.

## 1. Bridge will not start

| Symptom | Cause | Fix |
|---|---|---|
| `port 9876 closed` after launch | Blender started without `--online-mode` | Quit, relaunch with `--online-mode "<file>"` |
| Bridge never appears, log is silent | Port was busy at startup; autostart runs once and does not retry | Free the port, quit Blender, relaunch |
| `Unrecognized command: "blender_mcp"` | `--factory-startup`, or the extension is disabled | Relaunch without `--factory-startup`, enable the add-on |
| `open -a Blender --args ...` ignores the file | Blender was already running; `open` reused the process | Quit Blender fully, then run the command |
| Port held by something else | Another MCP server or a stale process | `lsof -nP -iTCP:9876 -sTCP:LISTEN`, ask before killing |
| Works, then dies after a while | Blender quit or the add-on was disabled | Re-run `doctor.py`; relaunch if needed |

Never "fix" a dead bridge by launching a headless Blender on the file the user is
editing.

## 2. Add-on problems

| Symptom | Cause | Fix |
|---|---|---|
| Extension list has no MCP entry | Blender older than 5.2, or no online access | Update Blender, enable online access |
| Add-on installed but not in Preferences | Installed for another Blender version | Install under the version you actually run |
| `doctor.py` says `add-on not found` | Non-standard user path | Pass `--blender` or set `BLENDER_USER_EXTENSIONS` |
| MCP panel visible, socket absent | Autostart preference off | Enable `use_autostart` in the add-on preferences |

## 3. Connection and protocol errors

| Symptom | Cause | Fix |
|---|---|---|
| `ConnectionRefusedError` | Nothing listening | Launch Blender with `--online-mode` |
| `TimeoutError` | Long operation still running | Wait; raise `--timeout` to 600–1800 |
| `empty response` | Blender closed mid-call | Check the Blender process; relaunch if it crashed |
| `status: error` with traceback | Bug in your snippet | Read the traceback; fix the snippet, not the bridge |
| `strict JSON` failure | `result` is not JSON-serializable | Convert to plain `dict`, `list`, `str`, `int`, `float`, `bool` |
| `result not set` | Snippet forgot `result = ...` | Always assign `result` |
| Works in terminal, fails from agent | Shell quoting of the snippet | Use `--file snippet.py` or stdin |

## 4. Nothing happens in the viewport

| Symptom | Cause | Fix |
|---|---|---|
| Viewport does not move | No `VIEW_3D` area (background mode) | Focus is GUI-only; skip it in background |
| Selection empty | Objects hidden or in an excluded collection | `hide_set(False)`, check collection exclusion |
| Camera view stuck | `view_perspective` left as `CAMERA` | Set `view_perspective = "PERSP"` or re-run `view_axis` |
| Pose bones not framed | Object selected instead of bones | Select bones in pose mode before `view_selected` |

## 5. Rigging and deformation

| Symptom | Cause | Fix |
|---|---|---|
| Driver changes nothing | Depsgraph not re-evaluated | `scene.frame_set(frame)` |
| Rotation axis wrong | Bone roll skew | `edit_bone.align_roll(...)`, verify `matrix.to_3x3()` |
| `rotation_euler` driver ignored | Pose bone is in `QUATERNION` mode | `pose_bone.rotation_mode = "XYZ"` |
| Mesh tears at a boundary | Vertices split across rigid groups without a cut | Cut at the seam, fill, assign groups |
| `Action.fcurves` missing | Slotted actions in Blender 5.x | `action.layers[0].strips[0].channelbags[*].fcurves` |
| Property keyframes ignored | Wrong data path | Use `'["open"]'`, not `open` |
| Weights leak across parts | Groups assigned after joining | Assign per piece before `join` |
| Jaws close when handles open | Midline split instead of diagonal pairing | Re-pair the halves |
| Rest pose shifts the mesh | Bind pose mismatch | Apply armature rest, re-check deviation `< 1e-5` |

## 6. glTF export

| Symptom | Cause | Fix |
|---|---|---|
| Animation missing in GLB | Drivers and custom properties are not exportable | Bake bone keyframes before export |
| Baked action becomes `.001` | Source action still holds the name | Rename source to `*_src` first |
| Widget appears as an empty node | Custom-shape object still linked | Unlink it during export |
| `Baking animation because of unsupported constraints` | Expected warning | Nothing to fix |
| Scale is 0.001 in another engine | glTF empty parent scale not baked | Bake `matrix_world` into mesh before rigging |
| Textures lost | Unpacked external files | Pack images before export |
| Normals look broken | Recalculated split normals | Flip only cap faces, keep custom split normals |

## 7. Installer problems

| Symptom | Cause | Fix |
|---|---|---|
| `permission denied: ./scripts/install.sh` | Lost executable bit (zip download) | `bash scripts/install.sh ...` |
| Refuses to overwrite a directory | Existing skill with the same name from another source | Check what it is; use `--force` only if you own it |
| Skill not visible to the agent | Wrong harness flag | `--agent all`, or the matching flag |
| Windows symlink error | Symlink privilege missing | `install.ps1` copies by default; keep it |
| `python3: command not found` | Only `python` exists (Windows) | Use `python scripts/doctor.py` |

## 8. Diagnostic commands

```bash
python3 scripts/doctor.py --json
lsof -nP -iTCP:9876 -sTCP:LISTEN
pgrep -fl "Blender.app/Contents/MacOS/Blender"
python3 skills/blender-live-rigging/scripts/blender_mcp.py \
  'import bpy
result = {"version": bpy.app.version_string, "gui": not bpy.app.background}'
```

If you need to escalate, include:

1. OS and Blender version.
2. `doctor.py --json` output.
3. The exact snippet and the full traceback.
4. Whether Blender is GUI or background.
