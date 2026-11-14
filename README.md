# Blender MCP Agent Kit

Live Blender control for AI coding agents, built on **Blender's official MCP bridge**.
This repo is not an MCP server and it does not patch Blender. It is the missing
operating manual: one skill, a setup that runs itself, and verification that proves a
rig actually deforms the mesh.

[![CI](https://github.com/andypratama3/blender-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/andypratama3/blender-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Blender](https://img.shields.io/badge/Blender-5.2%2B-orange)](https://www.blender.org)

> **Not the same as `ahujasid/blender-mcp`.** That project is a community MCP server.
> This kit assumes the official Blender Lab add-on `bl_ext.blenderlab.mcp` (default
> `127.0.0.1:9876`). Do not run both servers on the same port.

---

## What this gives you

| Piece | Why it matters |
|---|---|
| `skills/blender-live-rigging/` | Agent skill: rig and edit inside the user's **open** Blender, no headless batch, no surprise renders |
| `scripts/doctor.py` | One command that checks Blender, the add-on, the socket, and the installed skill |
| `scripts/install.sh` / `install.ps1` | Idempotent skill install for OpenCode, Claude Code, Codex, Cursor, Gemini CLI, Copilot |
| `docs/` | Bridge protocol, install per OS, rigging playbook, numeric verification, render policy, troubleshooting |
| `examples/crimping-tool/` | A real case study with measured numbers and the snippet that produced them |
| `.github/` | CI, issue forms, PR template, contribution and security policy |

No Python dependencies. No telemetry. Scripts use the standard library only.

---

## 60-second setup (human)

```bash
git clone https://github.com/andypratama3/blender-mcp.git
cd blender-mcp
./scripts/install.sh --agent opencode      # or claude, agents, cursor, gemini, copilot, all

# start Blender with online access so the official add-on can autostart its bridge
open -a Blender --args --online-mode "/absolute/path/to/file.blend"

python3 scripts/doctor.py                  # must print 6 PASS, exit 0
```

Linux:

```bash
blender --online-mode "/absolute/path/file.blend" &
python3 scripts/doctor.py
```

Windows (PowerShell):

```powershell
.\scripts\install.ps1 -Agent opencode
& "C:\Program Files\Blender Foundation\Blender 5.4\blender.exe" --online-mode "C:\path\file.blend"
python .\scripts\doctor.py
```

Then talk to your agent normally: *"Rig this tool in my open Blender and prove the
deformation with numbers."*

---

## 60-second setup (agent)

Paste this into OpenCode, Claude Code, Codex, Cursor, Gemini CLI or Copilot:

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

`AGENTS.md` is written for machines: exact commands, expected outputs, failure
branches, and a hard safety contract. `docs/AGENT_SETUP.md` shows what a correct run
looks like.

---

## Requirements

| Item | Detail |
|---|---|
| Blender | 5.2+ (developed and verified on 5.4.0 Alpha, macOS) |
| Add-on | `bl_ext.blenderlab.mcp` from Blender's *Get Extensions* (Blender Lab), enabled |
| Online access | Launch with `--online-mode`; autostart needs `bpy.app.online_access` |
| Port | `127.0.0.1:9876` free at Blender startup |
| Python | 3.10+ on your PATH (client scripts and doctor only) |
| OS | macOS, Linux, Windows |

Never launch with `--factory-startup`: it disables the extension and the
`blender_mcp` command becomes unknown.

---

## Safety contract

These rules are enforced by the skill and repeated in `AGENTS.md`:

1. **Work in the user's live GUI session.** Confirm `bpy.app.background == False`.
2. **Never close or kill Blender.** If a restart is unavoidable, save the `.blend`,
   explain why, and reopen the same file.
3. **No render unless the owner asks.** Default proof is numeric: vertex positions,
   widths, face areas, weight coverage.
4. **Focus the viewport on what you edit** (`view3d.view_axis` + `view_selected`).
5. **Verify on the evaluated mesh** (`evaluated_get(depsgraph).to_mesh()`), never on
   the source mesh.
6. **One atomic step per MCP call**, idempotent, returning the metrics that prove it.
7. **Save incrementally**, keep deliverables inside the project folder.

The full render policy, including the Blender 5.4 engine name (`BLENDER_EEVEE`, not
`BLENDER_EEVEE_NEXT`) and the fact that glTF scenes ship without camera or lights, is
in `docs/RENDERING.md`.

---

## How it works

```text
agent  ──TCP 127.0.0.1:9876──►  MCP add-on inside Blender  ──►  exec(python)
        JSON + "\0"             bpy / scene / depsgraph          sets `result`
```

- Request: `{"type":"execute","code":"...","strict_json":true}` plus a null byte.
- Reply: `{"status":"ok","result":{...},"stdout":"..."}` or `{"status":"error","message":"<traceback>"}`.
- The snippet must assign a JSON-serializable `result` dict.
- Exceptions do not kill the session.

Protocol details, sandbox limits and the viewport-focus helper: `docs/MCP_BRIDGE.md`.

---

## Case study: crimping tool rig

A 16 MB glTF crimping tool was rigged live, without rendering:

| Metric | Result |
|---|---|
| Mesh after weld + cuts | 606 verts, 892 polys, 3 shells, 0 non-manifold |
| Rig | `root` control, `arm_L` / `arm_R` deform, diagonal pairing |
| Hinge | pivot `(0, -0.26792, 0.02)`, world Y axis, ±4° per arm |
| Control | custom property `open` 0–1 driving both bones |
| Rest deviation | `2e-7` |
| Loop seam (frame 60 vs 1) | `0.0` |
| Face-area ratio open/closed | `0.999–1.0005` |
| Handle width | `0.2869 → 0.3569` |
| Jaw width | `0.1738 → 0.1895` |
| Exported GLB | 1 mesh / 3 primitives, 1 skin / 3 joints, animation 1–60, 9 embedded textures |

Why the arms are paired diagonally: a midline split makes the jaws close while the
handles open. Full reasoning and the exact cut/pivot/export sequence:
`docs/CASE_STUDY_CRIMPING.md` and `docs/RIGGING_PLAYBOOK.md`.

A second case study covers a Roblox R15 avatar and its walk loop — 15 body meshes, 17
bones, analytic two-bone leg IK, and the ground-contact and FBX traps found on the way:
`docs/CASE_STUDY_KNIGHT.md`.

---

## Repository layout

```text
blender-mcp/
├── AGENTS.md                 machine-facing setup + guardrails
├── README.md / README.id.md  English / Indonesian
├── docs/
│   ├── AGENT_SETUP.md        copy-paste prompt and expected transcript
│   ├── INSTALL.md            per-OS install, autostart rules, uninstall
│   ├── MCP_BRIDGE.md         protocol, client, pitfalls, viewport focus
│   ├── RIGGING_PLAYBOOK.md   rigid-part rigging method and gates
│   ├── VERIFICATION.md       evaluated-mesh metrics and thresholds
│   ├── RENDERING.md          owner-request render path
│   ├── TROUBLESHOOTING.md    symptom → cause → fix
│   ├── SKILLS.md             skill format, inventory, how to add one
│   ├── ECOSYSTEM.md          third-party skills and MCP servers
│   ├── CASE_STUDY_CRIMPING.md
│   └── CASE_STUDY_KNIGHT.md  R15 avatar + in-place walk, measured
├── scripts/
│   ├── install.sh            macOS / Linux installer
│   ├── install.ps1           Windows installer
│   ├── doctor.py             environment + bridge + skill check
│   └── validate_repo.py      CI checks (frontmatter, python, paths)
├── skills/blender-live-rigging/
│   ├── SKILL.md
│   ├── reference/            bridge, rigging, Roblox, 5.x API, GLB QA quick refs
│   └── scripts/              MCP client, action compat, GLB QA, GLB/FBX inspectors, GLB verifier
└── examples/crimping-tool/
    ├── README.md
    └── measure_live_rig.py   snippet that prints the case-study metrics
```

---

## Supported agents

| Agent | Install target |
|---|---|
| OpenCode | `~/.config/opencode/skills/` |
| Claude Code | `~/.claude/skills/` |
| Codex / Gemini CLI / Copilot / Cursor | `~/.agents/skills/` |
| Cursor only | `~/.cursor/skills/` |

`scripts/install.sh --agent all` covers all of them. Project-scoped installs:
`--scope project --project /path/to/repo`. Windows: copy mode by default.

---

## Contributing

Issues and PRs are welcome, including new skills, OS fixes, and clearer docs.

- Read `CONTRIBUTING.md` for the workflow and PR checklist.
- Run `make check` before pushing (frontmatter, Python syntax, personal paths).
- Bug reports: use the issue form, include `python3 scripts/doctor.py --json` output.
- Security: do not open a public issue; follow `SECURITY.md`.

If you add a third-party skill, record its repo and commit hash in
`docs/ECOSYSTEM.md`; do not vendor code without a license check.

---

## License

MIT © 2026 Andy Pratama. See `LICENSE`.
