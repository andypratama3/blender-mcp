# CLAUDE.md

Read `AGENTS.md` first and follow it exactly. It contains the setup procedure and the
safety contract for this repository.

Short version:

- This repo is a skill + toolkit for controlling the user's **open** Blender through
  the official MCP add-on (`bl_ext.blenderlab.mcp`, `127.0.0.1:9876`).
- Install with `./scripts/install.sh --agent claude`, then run
  `python3 scripts/doctor.py`.
- Never close or kill Blender, never render unless the user asks, and verify Blender
  changes with measured numbers instead of screenshots.
- When contributing to the repo, run `make check` before committing.

Docs index: `README.md`, `docs/AGENT_SETUP.md`, `docs/INSTALL.md`,
`docs/MCP_BRIDGE.md`, `docs/RIGGING_PLAYBOOK.md`, `docs/VERIFICATION.md`,
`docs/RENDERING.md`, `docs/TROUBLESHOOTING.md`.
