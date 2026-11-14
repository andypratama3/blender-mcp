# AGENTS.md

You are setting up or using **Blender MCP Agent Kit**. This file is the contract.
Follow it literally; do not improvise commands that are not listed here.

## 0. Non-negotiables

1. **Never close, kill, or restart Blender unless the user explicitly approves.**
   If a restart is unavoidable (port conflict, extension disabled): save the `.blend`,
   state the reason, then reopen the same file with `--online-mode`.
2. **Do not render** images, animations, viewports, or playblasts unless the owner
   explicitly asks for a render. Default verification is numeric.
3. **Use the live GUI session** (`bpy.app.background == False`). Do not start a
   headless Blender while the user is working on the same file.
4. **Do not start another MCP server.** The bridge is Blender's official add-on
   `bl_ext.blenderlab.mcp` on `127.0.0.1:9876`. Do not install `ahujasid/blender-mcp`
   alongside it; both default to the same port.
5. **Never overwrite the user's files.** Save new deliverables inside their project
   folder, keep the source `.blend`/`.glb` untouched unless asked.
6. **Every completed claim needs evidence**: command output, file path, or measured
   numbers. No "should work".

## 1. Detect the environment

```bash
uname -s                                   # Darwin | Linux
python3 --version                          # need 3.10+
command -v git
```

Windows: use PowerShell equivalents and `python` instead of `python3`.

Pick an install directory:

- macOS/Linux: `~/Development/blender-mcp`
- Windows: `%USERPROFILE%\Development\blender-mcp`

If the user already cloned the repo elsewhere, use that path instead.

## 2. Clone or update

```bash
if [ -d "$HOME/Development/blender-mcp/.git" ]; then
  git -C "$HOME/Development/blender-mcp" pull --ff-only
else
  git clone https://github.com/andypratama3/blender-mcp.git "$HOME/Development/blender-mcp"
fi
```

Then read, in this order:

1. `README.md`
2. `docs/INSTALL.md`
3. `docs/AGENT_SETUP.md`

Do not skip `docs/INSTALL.md`; it explains why `--online-mode` is mandatory and why
`--factory-startup` breaks the bridge.

## 3. Install the skill

```bash
cd "$HOME/Development/blender-mcp"
./scripts/install.sh --agent <agent>
```

`<agent>` is one of `opencode`, `claude`, `agents`, `codex`, `cursor`, `gemini`,
`copilot`, `all`. If you do not know which harness you are, use:

```bash
./scripts/install.sh --agent all
```

Windows:

```powershell
.\scripts\install.ps1 -Agent all
```

Expected output (one line per target):

```text
installed blender-live-rigging -> ~/.config/opencode/skills (opencode)
```

The script is idempotent: an existing symlink pointing at this repo is left alone, and
a foreign directory with the same name is never deleted (it aborts unless `--force`).

## 4. Check the bridge

```bash
python3 scripts/doctor.py
```

Exit code `0` and six PASS lines means the environment is usable. If the bridge line
fails, choose the matching branch:

| Doctor says | Do this |
|---|---|
| `Blender not found` | Ask the user to install Blender 5.2+, or pass `--blender /path/to/blender` |
| `add-on not found` | Tell the user: Blender → Edit → Preferences → Get Extensions → install **MCP** (Blender Lab) → enable it |
| `port 9876 closed` | Ask the user to quit Blender and reopen with `open -a Blender --args --online-mode "<file>"` (macOS) or `blender --online-mode "<file>"` |
| `port held by another process` | Ask before killing anything; identify with `lsof -nP -iTCP:9876 -sTCP:LISTEN` |
| `bridge error` | Re-run doctor with `--json`; include the traceback in the report |
| `skill not installed` | Re-run step 3 with the correct `--agent` |

Do **not** try to start Blender yourself with `--factory-startup`, `--background`, or
a different file. The user's current GUI session is the workspace.

## 5. Prove the session is live

```bash
python3 skills/blender-live-rigging/scripts/blender_mcp.py \
  'import bpy
result = {"gui": not bpy.app.background, "file": bpy.data.filepath,
          "version": bpy.app.version_string, "objects": len(bpy.data.objects)}'
```

Expected: `status: ok`, `gui: true`, and the user's file path. If `gui` is false, you
are attached to a background instance: stop and fix that before editing anything.

## 6. Report back

Use this shape, keep it short:

```text
Repo:       <path> (commit <sha>)
Skill:      installed for <agents>
Blender:    <version>, GUI <yes/no>, file <path>
Bridge:     PASS/FAIL on 127.0.0.1:9876
Doctor:     <n> PASS / <n> WARN / <n> FAIL, exit <code>
Next:       <one concrete action, or "ready">
Guardrails: Blender left open; no render; port unchanged
```

## 7. Working on Blender tasks (after setup)

- Load the skill: `blender-live-rigging`. Use `blender-core` and a domain skill when
  the task is broader than live control.
- One `execute` call = one atomic, idempotent change that returns its own metrics.
- Force driver evaluation with `scene.frame_set(frame)`, not `view_layer.update()`.
- Measure on `evaluated_get(depsgraph).to_mesh()`.
- Focus the viewport before/after editing: select the object/bones, make one active,
  run `view3d.view_axis` then `view3d.view_selected`.
- Save with `bpy.ops.wm.save_as_mainfile(filepath=..., compress=True)` at milestones.
- Keep the user's session open when you finish, framed on the asset.

Rigging method: `docs/RIGGING_PLAYBOOK.md`.
Verification gates: `docs/VERIFICATION.md`.
Export + bake/restore recipe: `docs/RIGGING_PLAYBOOK.md` §8.
Render on request: `docs/RENDERING.md` (only after an explicit request).

## 8. Contributing to this repo

If the task is "improve the repo", not "use it":

```bash
cd blender-mcp
make check          # frontmatter, python syntax, personal paths, required files
```

Then:

- Add or edit skills only under `skills/<name>/SKILL.md`.
- Update `CHANGELOG.md` and, for behavior changes, the matching doc.
- Keep scripts standard-library only and cross-platform.
- Commit messages: `type(scope): summary` (`feat`, `fix`, `docs`, `chore`).
- Do not add binaries, `.blend` files, or generated renders.
- Never add an absolute path containing a real username.

Read `CONTRIBUTING.md` before opening a PR.
