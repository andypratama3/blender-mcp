# Skills

## 1. What a skill is

A skill is a folder with a `SKILL.md` that an agent loads on demand. The frontmatter
tells the agent *when* to use it; the body tells it *how*. In this repo:

```text
skills/
└── blender-live-rigging/
    ├── SKILL.md
    ├── reference/
    │   ├── mcp-bridge.md
    │   ├── rigging-playbook.md
    │   ├── roblox-avatar.md
    │   ├── blender-5x-api.md
    │   └── glb-qa.md
    └── scripts/
        ├── blender_mcp.py
        ├── action_compat.py
        ├── glb_qa.py
        ├── inspect_glb.py
        ├── inspect_fbx.py
        └── verify_rig_glb.py
```

- `SKILL.md` must stay short enough to read in one pass.
- `reference/` holds detail the agent opens only when needed.
- `scripts/` holds executables the agent calls instead of retyping code.
- The skill must be usable from any working directory: resolve the repo root relative
  to the skill file, never from the current directory.

## 2. Frontmatter contract

```markdown
---
name: blender-live-rigging
description: "Rig, edit, verify and export 3D assets live in the user's open Blender app through the official Blender MCP socket bridge. Use for armatures, skinning, mechanical/hinge rigs, drivers, custom-property controls, evaluated-mesh verification, baked glTF export, and renders only when the owner explicitly requests them."
---
```

Rules enforced by `scripts/validate_repo.py`:

| Field | Rule |
|---|---|
| `name` | matches `^[a-z0-9]+(-[a-z0-9]+)*$`, max 64, equals the folder name |
| `description` | 20–1024 characters, trigger-oriented, mentions the words a user would say |
| `compatibility` | 1–500 characters when present |
| `license` | short name of the bundled license (`MIT`) |
| body | non-empty, starts with an H1 |

Conformance with the [Agent Skills specification](https://agentskills.io/specification):
the spec names the optional documentation directory `references/` (plural); this repo
uses `reference/`. That directory is optional and free-form, so the difference is
cosmetic — but copying a skill into a client that hard-codes the plural name will not
find the pages. Keep the paths in `SKILL.md` relative and one level deep, which is what
the spec asks for.

Write descriptions for retrieval, not for marketing. If a user says "rig this in my open
Blender", the description must contain enough of those words to match.

## 3. Inventory

| Skill | Purpose | Requires |
|---|---|---|
| `blender-live-rigging` | Drive the user's open Blender over MCP: inspect, rig, skin, verify, export, optional render | Blender 5.2+, official MCP add-on |

This is intentionally a single skill. Domain skills (modeling, materials, animation)
belong to the wider ecosystem; see [`ECOSYSTEM.md`](ECOSYSTEM.md). Installing 30
overlapping skills makes retrieval worse, not better.

## 4. Adding a skill

1. Create `skills/<name>/SKILL.md` with valid frontmatter.
2. Put large tables and long recipes in `skills/<name>/reference/*.md`.
3. Put runnable helpers in `skills/<name>/scripts/` and make them stdlib-only Python
   (or POSIX shell) with useful `--help` text.
4. Add the skill to the inventory table above and to `CHANGELOG.md`.
5. Run `make check`.
6. Test the install path: `./scripts/install.sh --agent opencode --copy` then confirm
   the agent sees it.

## 5. What makes a skill good here

- **Trigger words in the description.** Name the tasks and the nouns.
- **Hard rules near the top.** Safety, no-render default, live-session-only.
- **Commands that run.** Every block should be copy-pasteable.
- **Numbers instead of adjectives.** "Rest deviation < 1e-5" beats "verify carefully".
- **Failure tables.** Symptom → cause → fix, not paragraphs.
- **No manual UI steps** when a scriptable path exists.

## 6. What gets rejected

- A skill that runs a render as its default verification.
- A skill that closes or restarts Blender without asking.
- A skill that duplicates an existing one with a different name.
- A skill that depends on `pip install` or a network service.
- A skill with personal paths, credentials, or proprietary assets.
- A skill whose description would never match a real request.

## 7. Install targets

| Agent | Directory |
|---|---|
| OpenCode | `~/.config/opencode/skills/` |
| Claude Code | `~/.claude/skills/` |
| Codex, Gemini CLI, Copilot | `~/.agents/skills/` |
| Cursor | `~/.cursor/skills/` |

`./scripts/install.sh --agent all` covers every row. Symlink is the default on
macOS/Linux; Windows copies. See [`INSTALL.md`](INSTALL.md) §4.

## 8. Versioning a skill

- Behavior change: bump the minor version in `CHANGELOG.md` and `CITATION.cff`.
- Breaking change to paths or flags: bump major.
- Typo or wording fix: patch.
- Keep the skill name stable; renames break existing installs.
