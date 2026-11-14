# Ecosystem

This repo ships one skill and assumes Blender's official MCP add-on. Everything else is
optional. This page records what exists, how it was verified, and where it conflicts, so
you can choose without installing something that breaks the bridge.

## 1. The bridge

| Component | Source | Role |
|---|---|---|
| `bl_ext.blenderlab.mcp` | Blender *Get Extensions*, publisher Blender Lab | Official MCP add-on; exposes `exec(python)` on `127.0.0.1:9876` |

This is the only bridge this kit supports. It is shipped by Blender's own extension
platform, so it updates with Blender and needs no separate server.

## 2. Not the same as `ahujasid/blender-mcp`

| | `ahujasid/blender-mcp` | This kit |
|---|---|---|
| Type | Community MCP server + Blender add-on | Skill + scripts on top of Blender's official add-on |
| Default port | `9876` | `9876` |
| Startup | Separate server process | Add-on autostart inside Blender |
| Conflict | Same port as the official add-on | — |

Do not run both on the same port. If you already use the community server, either stop
it while using this kit or change one port. Running two servers that both claim `9876`
is the single most common reason the bridge "silently fails".

## 3. Third-party skill packs

Verified by cloning, listing, and reading `SKILL.md` files. Reported here from actual
inspection, not from README claims.

| Repo | Commit | License | Outcome |
|---|---|---|---|
| `EL4CTEO/blender-skills` | `389f28addc79b87b28764898e38e7bf408d14b77` | MIT | 28 domain skills, compatible, no name conflicts |
| `composio-community/opencode-skills` | `5076f6673e5bf8b1f46dc5e934d1e3dd37250e10` | MIT | 4 Blender skills, all duplicate or conflict; none recommended |

### EL4CTEO pack (recommended as domain skills)

Covers core execution, scene setup, hard-surface modeling, sculpting, retopology/UV,
materials, texturing, baking, geometry nodes, character rigging, facial shape keys,
animation, clothing, hair, optimization, export pipelines, rendering, lighting, NPR,
environments, video, simulation, time of day, weather, add-on development, pipeline
automation, QA, and end-to-end recipes.

Notes:

- `install/install.sh` in the clone is not executable; run `bash install/install.sh`.
- No skill collides with `blender-live-rigging`.
- These are complementary: use `blender-core` for API rules and `blender-live-rigging`
  for live execution over MCP.

### composio pack (skipped)

| Skill | Reason |
|---|---|
| `blender-geometry-nodes` | Duplicate of the newer EL4CTEO skill |
| `blender-hard-surface-modeling` | Duplicate, differs only by hyphen |
| `blender-python-integration` | Generic, assumes manual Claude workflow and render-based validation |
| `blender-rigging-animation` | Manual UI flow with a final render; conflicts with the live, no-render-default rule |

## 4. How to record a third-party install

If you add a pack, open a PR that updates this table with:

1. Repository URL.
2. Exact commit hash you installed.
3. License.
4. Whether any skill name collides.
5. Conflict notes (port, render policy, manual UI steps).

Do not vendor third-party code into `skills/`. Link, record the commit, and let users
install it themselves.

## 5. Compatibility rules

A third-party skill is compatible if it:

- Uses the official add-on, or does not require a bridge at all.
- Leaves port `9876` alone.
- Does not require a render for validation.
- Does not close or restart Blender.
- Does not assume a specific personal directory layout.

## 6. Recommended combinations

| Task | Skills |
|---|---|
| Rig a mechanical asset live | `blender-live-rigging` |
| Model, then rig live | `blender-hardsurface-modeling` + `blender-live-rigging` |
| Rig a character, then animate | `blender-character-rigging` + `blender-animation` + `blender-live-rigging` |
| Export to a game engine | `blender-export-pipelines` + `blender-live-rigging` |
| QA a mesh before delivery | `blender-asset-qa` + `blender-live-rigging` |
| Render for a client | `blender-rendering` + `blender-lighting-lookdev` |

## 7. MCP clients

The bridge is a raw socket with a null-terminated JSON protocol, so any client works:
the bundled `blender_mcp.py`, a custom script, or an agent tool that speaks TCP. There is
no dependency on a specific MCP framework.
