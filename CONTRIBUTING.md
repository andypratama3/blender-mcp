# Contributing

Thanks for improving Blender MCP Agent Kit. This repo is small on purpose: scripts use
the Python standard library only, docs stay executable, and every Blender claim must be
reproducible without a render.

## Good first contributions

- Fix a setup failure on your OS (include the exact error and `doctor.py --json`).
- Add a rigging case study with measured numbers.
- Improve a doc where you got stuck.
- Add a verification gate for a deformation or export problem.
- Translate docs (open an issue first so we do not duplicate work).

## Development setup

```bash
git clone https://github.com/andypratama3/blender-mcp.git
cd blender-mcp
make check
```

`make check` runs:

1. `scripts/validate_repo.py` — required files, skill frontmatter, Python syntax,
   personal absolute paths, oversized files.
2. `bash -n` on shell scripts.

Blender is **not** required for CI. If you want to test against Blender locally, use
your own install and never commit `.blend` files.

## Adding or changing a skill

Skills live in `skills/<name>/SKILL.md` with YAML frontmatter:

```markdown
---
name: blender-something
description: "One sentence that says when to use it, keyed to the words a user would say."
---

# Title
...
```

Rules:

- `name` must equal the folder name.
- `description` must be trigger-oriented, 20–1024 characters, and mention the task
  words a user would actually type.
- Keep `SKILL.md` focused; put long material in `reference/` and scripts in `scripts/`.
- Prefer concrete commands and thresholds over prose.
- Update `docs/SKILLS.md` and `CHANGELOG.md`.
- Never include a real username path, API key, or proprietary asset.

## Script style

- Python 3.10+, standard library only, no `pip install`.
- `argparse` with `--help`, meaningful exit codes (`0` ok, `1` failure, `2` usage).
- No printing secrets. No network calls except localhost.
- Shell: `set -euo pipefail`, quote paths, support spaces in paths.
- Windows paths must work through `install.ps1`; do not assume `bash`.

## Documentation style

- English is canonical; `README.id.md` mirrors the top-level intro.
- Every code block must be runnable. Prefer one verified command over five guesses.
- Use tables for symptom → cause → fix.
- State the Blender version a claim was verified on.
- Do not claim studio adoption, benchmarks, or compatibility that was not tested.

## Testing with Blender

Optional but valuable:

1. Launch Blender with `--online-mode` and a throwaway file.
2. Run your snippet through `skills/blender-live-rigging/scripts/blender_mcp.py`.
3. Paste the measured output in the PR description.
4. Do not attach renders unless the PR is specifically about rendering.

## Commit and PR

- Commit style: `type(scope): summary` — `feat`, `fix`, `docs`, `test`, `chore`.
- One logical change per PR.
- PR checklist:
  - [ ] `make check` passes.
  - [ ] Docs updated for behavior changes.
  - [ ] `CHANGELOG.md` updated.
  - [ ] No binaries, renders, credentials, or personal paths.
  - [ ] Blender version used for any manual test is stated.

## Third-party skills and code

- Do not copy code without checking the license; record the source and commit hash.
- Third-party skill installs are listed in `docs/ECOSYSTEM.md`, not vendored.
- Reject skills that assume manual UI steps or mandatory renders when a scripted,
  numeric path exists.

## Review and release

Maintainers review for correctness, portability, safety, and doc accuracy. Releases are
tagged `vX.Y.Z`; update `CHANGELOG.md` in the same PR.

## Code of conduct

Participation is covered by `CODE_OF_CONDUCT.md`. Be direct about technical problems,
never about people.
