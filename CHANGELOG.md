# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions use
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-11-14

### Added

- `reference/roblox-avatar.md`: R15 body contract (15 part meshes, R15 bone names, stud
  units, tri/UV limits), measured bone-axis conventions, the analytic two-bone leg IK
  used for in-place locomotion, ground-contact gates, and the Roblox Studio import path.
- `scripts/inspect_fbx.py`: minimal binary FBX reader that prints every animated channel
  (model, T/R/S, axis, key count, frame span, min/max) without Blender and without the
  importer's bone reconstruction.
- `docs/CASE_STUDY_KNIGHT.md`: R15 knight avatar and walk loop built live over MCP, with
  every gate number, including the failed first attempt.
- `docs/VERIFICATION.md` section 2b/9 and `docs/TROUBLESHOOTING.md` 6b: measure the
  deformed mesh at the floor, and verify FBX exports from the shipped bytes.

### Fixed

- `inspect_glb.py` and `verify_rig_glb.py` now ignore the `glTF_not_exported` helper
  collection and bone-widget meshes created by the glTF importer, so bounds, shells, and
  width measurements are no longer polluted by an `Icosphere` helper.

### Added

- `verify_rig_glb.py` accepts `--low-z` / `--high-z` to set measurement bands for assets
  that do not match the crimping-tool proportions.

## [0.1.0] - 2026-11-14

### Added

- `blender-live-rigging` skill for driving the user's open Blender through the official
  Blender Lab MCP add-on, including viewport focus, numeric verification, and a
  bake/restore glTF export recipe.
- MCP client `blender_mcp.py` (stdin or argument, null-terminated JSON protocol).
- Asset inspector `inspect_glb.py` with transform baking, weld-aware shell counting,
  and an ASCII silhouette that replaces a render during exploration.
- GLB verifier `verify_rig_glb.py` that re-imports the export in a separate process and
  checks nodes, skin, animation range, and deformation widths.
- `scripts/doctor.py` environment check: Blender version, add-on path, socket probe,
  skill install state, JSON output.
- `scripts/install.sh` and `scripts/install.ps1` for OpenCode, Claude Code, Codex,
  Cursor, Gemini CLI, and Copilot, with project scope, copy mode, and uninstall.
- `scripts/validate_repo.py` and GitHub Actions CI.
- Documentation: agent setup, per-OS install, bridge protocol, rigging playbook,
  verification gates, render policy, troubleshooting, skills, ecosystem, case study.
- Issue forms, PR template, contribution guide, security policy, code of conduct,
  citation metadata.

### Verified

- Blender 5.4.0 Alpha on macOS, official `bl_ext.blenderlab.mcp` bridge on port 9876.
- Crimping tool case study: 606 verts, rest deviation `2e-7`, loop seam `0.0`,
  face-area ratio `0.999–1.0005`, handle `0.2869 → 0.3569`, jaw `0.1738 → 0.1895`.
