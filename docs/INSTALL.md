# Install

Two layers are installed separately:

1. **Blender side** — the official MCP add-on, once per Blender version.
2. **Agent side** — the `blender-live-rigging` skill, once per agent/harness.

The repo itself has no Python dependencies.

## 1. Requirements

| Item | Notes |
|---|---|
| Blender 5.2+ | Verified on 5.4.0 Alpha, macOS. Older versions may work but are untested. |
| Official add-on | `bl_ext.blenderlab.mcp` (Blender Lab) from *Get Extensions* |
| Python 3.10+ | For `scripts/doctor.py` and the MCP client |
| Free port | `127.0.0.1:9876` at Blender startup |
| Git | To clone and update |

## 2. Install the Blender add-on

1. Open Blender.
2. **Edit → Preferences → Get Extensions**.
3. Search for **MCP**, publisher **Blender Lab**, and install it.
4. Enable it if it is not enabled.
5. Keep the default host `127.0.0.1` and port `9876`.

The add-on directory is version-specific:

| OS | Path |
|---|---|
| macOS | `~/Library/Application Support/Blender/<version>/extensions/blenderlab/mcp` |
| Linux | `~/.config/blender/<version>/extensions/blenderlab/mcp` |
| Windows | `%APPDATA%\Blender Foundation\Blender\<version>\extensions\blenderlab\mcp` |

`scripts/doctor.py` searches all of these and prints what it finds.

## 3. Launch Blender so the bridge autostarts

The add-on only autostarts when **all** of these are true:

1. The add-on preference `use_autostart` is on (default).
2. `bpy.app.online_access == True` — launch with `--online-mode`.
3. Port `9876` is free at startup.
4. The extension is enabled (do **not** use `--factory-startup`).

```bash
# macOS
open -a Blender --args --online-mode "/absolute/path/scene.blend"

# Linux
blender --online-mode "/absolute/path/scene.blend" &

# Windows PowerShell
& "C:\Program Files\Blender Foundation\Blender 5.4\blender.exe" --online-mode "C:\path\scene.blend"
```

Autostart runs once, about one second after startup, and does **not** retry. If the port
was busy, quit Blender, free the port, and relaunch the same file.

### Background mode (batch/CI)

Only for your own files, never the file a user is editing in the GUI:

```bash
blender -b --online-mode --command blender_mcp
```

This blocks and serves the bridge. It has no viewport, so commands that rely on
`view3d` are no-ops.

## 4. Install the skill

```bash
cd ~/Development/blender-mcp

./scripts/install.sh --agent opencode          # one harness
./scripts/install.sh --agent all               # every supported harness
./scripts/install.sh --agent claude --copy     # copy instead of symlink
./scripts/install.sh --agent opencode --scope project --project ~/my-project
./scripts/install.sh --agent opencode --uninstall
```

Agent → directory:

| Flag | Directory |
|---|---|
| `opencode` | `~/.config/opencode/skills/` |
| `claude` | `~/.claude/skills/` |
| `agents`, `codex`, `gemini`, `copilot` | `~/.agents/skills/` |
| `cursor` | `~/.cursor/skills/` |

Windows:

```powershell
.\scripts\install.ps1 -Agent opencode
.\scripts\install.ps1 -Agent all -Copy
.\scripts\install.ps1 -Agent opencode -Uninstall
```

`install.ps1` copies by default because symlinks need Developer Mode or admin rights.

### Manual install

```bash
mkdir -p ~/.config/opencode/skills
ln -s "$PWD/skills/blender-live-rigging" ~/.config/opencode/skills/blender-live-rigging
```

The installer is safe by design: it only creates/removes its own skill name, refuses to
overwrite a non-symlink directory unless `--force`, and never deletes unrelated skills.

## 5. Verify

```bash
python3 scripts/doctor.py
echo $?
```

Optional MCP round-trip (prints Blender version and open file):

```bash
python3 skills/blender-live-rigging/scripts/blender_mcp.py \
  'import bpy
result = {"gui": not bpy.app.background, "file": bpy.data.filepath}'
```

## 6. Update

```bash
cd ~/Development/blender-mcp
git pull --ff-only
./scripts/install.sh --agent opencode     # refresh symlinks/copies if needed
python3 scripts/doctor.py
```

Symlink installs pick up repo changes immediately. Copy installs need the installer to
run again.

## 7. Uninstall

```bash
./scripts/install.sh --agent all --uninstall
```

Then remove the clone if you no longer need it. The Blender add-on is removed from
**Preferences → Get Extensions**.

## 8. Common install failures

| Error | Cause | Fix |
|---|---|---|
| `permission denied: ./scripts/install.sh` | not executable after unzip | `bash scripts/install.sh ...` |
| `Unrecognized command: "blender_mcp"` | launched with `--factory-startup` or extension disabled | relaunch with `--online-mode`, enable add-on |
| Bridge never starts | port busy or no `--online-mode` | free port, quit, relaunch |
| Skill not detected | wrong harness directory | run with `--agent all` or the matching flag |
| `open -a` ignores arguments | Blender already running | quit Blender first, then `open -a ... --args` |
