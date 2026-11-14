# Agent setup

This page is for the human handing the repo to an agent, and for the agent reading it
afterwards. The canonical machine instructions are in [`AGENTS.md`](../AGENTS.md).

## 1. Copy-paste prompt

Universal (works in OpenCode, Claude Code, Codex, Cursor, Gemini CLI, Copilot):

```text
Set up https://github.com/andypratama3/blender-mcp for me.

1. Clone it to ~/Development/blender-mcp (skip if it exists, then git pull).
2. Read AGENTS.md and follow it exactly.
3. Install the skill with scripts/install.sh --agent <my-agent>.
4. Ask me to start Blender with --online-mode if the bridge is down; never kill it.
5. Run python3 scripts/doctor.py and show me the raw output.
6. Stop there and report what passed, what failed, and the exact next command.
Do not render anything unless I explicitly ask.
```

Replace `<my-agent>` with `opencode`, `claude`, `agents`, `cursor`, `gemini`, or
`copilot`. If you are unsure, tell the agent to use `--agent all`.

The agent is expected to stop after setup and report. It should not start rigging or
modeling until you give a task.

## 2. What a correct run looks like

```text
$ git clone https://github.com/andypratama3/blender-mcp.git ~/Development/blender-mcp
Cloning into '/Users/you/Development/blender-mcp'...
$ ~/Development/blender-mcp/scripts/install.sh --agent opencode
installed blender-live-rigging -> /Users/you/.config/opencode/skills (opencode)
$ python3 ~/Development/blender-mcp/scripts/doctor.py
Blender       PASS  5.4.0 Alpha (/Applications/Blender.app/Contents/MacOS/Blender)
MCP add-on    PASS  bl_ext.blenderlab.mcp at .../extensions/blenderlab/mcp
Port 9876     PASS  listening, PID 12345
Bridge        PASS  gui=true version=5.4.0 alpha file=/.../scene.blend
Skill         PASS  ~/.config/opencode/skills/blender-live-rigging
Python        PASS  3.12.4
6 PASS / 0 WARN / 0 FAIL
```

Exit code is `0`. If any line is `FAIL`, the agent must fix that item or ask you; it
must not "work around" a dead bridge by opening a headless Blender on the same file.

## 3. If Blender is not running yet

The agent should ask you to launch it, because only you know which file to open:

```bash
# macOS
open -a Blender --args --online-mode "/absolute/path/scene.blend"
# Linux
blender --online-mode "/absolute/path/scene.blend" &
# Windows
& "C:\Program Files\Blender Foundation\Blender 5.4\blender.exe" --online-mode "C:\path\scene.blend"
```

Wait for the file to load, then run `scripts/doctor.py` again. The bridge autostarts
about one second after startup, **once**. It does not retry, so if the port was busy the
only fix is quit + relaunch.

## 4. If the add-on is missing

In Blender: **Edit → Preferences → Get Extensions**, search for **MCP** by
*Blender Lab*, install, and enable it. It appears as `bl_ext.blenderlab.mcp`.

Check from a terminal (no Blender needed):

```bash
python3 scripts/doctor.py --json
```

The `addon` object shows the exact paths that were searched.

## 5. After setup: the first task

Once `doctor.py` is green, the agent can work. A good first prompt:

```text
Open my scene in Blender, tell me what is selected and how many objects there are,
then frame the viewport on the main mesh. Do not change anything yet.
```

The agent should use the MCP client and return numbers, not a screenshot.

## 6. Non-negotiables the agent must repeat back

- Work in the live GUI session (`bpy.app.background == False`).
- Never close or kill Blender.
- No render unless you explicitly ask.
- Focus the viewport on the edited object.
- Verify on the evaluated mesh and report measured numbers.

## 7. Troubleshooting shortcut

| Doctor line | Meaning | First action |
|---|---|---|
| `Blender not found` | not installed or not on PATH | install 5.2+, or pass `--blender` |
| `MCP add-on` FAIL | extension missing/disabled | install from Get Extensions |
| `Port 9876` FAIL | nothing listening | relaunch Blender with `--online-mode` |
| `Bridge` FAIL | port open but protocol error | check the add-on version and log |
| `Skill` WARN | skill not installed | re-run `install.sh --agent <agent>` |

Full table: [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md).
