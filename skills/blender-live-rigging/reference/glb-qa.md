# Render-free GLB QA

Parse the shipped bytes instead of judging a screenshot. Standard library only, no
Blender, so the same command runs in CI and over an MCP `execute`.

```bash
python3 scripts/glb_qa.py export/model.glb --loop --max-tris 20000
python3 scripts/glb_qa.py export/tool.glb --manifold        # props only
```

Exit code 1 means a gate failed; every gate prints `value` next to `limit`.

## Gates

| Gate | Passes when | Catches |
|---|---|---|
| `header_length` | declared == actual bytes | truncated write |
| `glb_version` | 2 | wrong container |
| `position_min_error` | ≤ 1e-5 | stale accessor bounds after edits |
| `weight_sum_error` | ≤ `--tol` | un-normalised skin weights |
| `unweighted_vertices` | 0 | vertices left behind when posed |
| `max_influences` | ≤ 4 | engines that silently drop the 5th weight |
| `joint_index_out_of_range` | 0 | skin/joint list mismatch |
| `ibm_count_matches_joints` | 0 | broken bind pose |
| `max_joints`, `max_triangles` | ≤ your limit | platform budgets (no default: set them) |
| `time_strictly_increasing` | 0 | duplicate or unsorted keyframes |
| `sampler_output_count` | 0 | sampler/accessor key mismatch |
| `quaternion_norm_error` | ≤ `--tol` | un-normalised rotations |
| `loop_closure_error` (`--loop`) | ≤ `--tol` | pop at the cycle seam |
| `starts_at_zero` (`--start-at-zero`) | ≤ `--tol` | clip that starts at 1/fps (see `blender-5x-api.md`) |
| `boundary_edges`, `nonmanifold_edges` (`--manifold`) | 0 | holes; characters are open meshes, props are not |
| `nonfinite_values` | 0 | NaN/Inf from a bad bake |
| `khronos_errors` | 0, only when `gltf_validator` is on PATH | spec violations the gates above do not model |

`--max-joints` and `--max-tris` have no defaults on purpose: take them from the target
platform (Roblox R15: 20 000 tris per mesh, see `roblox-avatar.md`).

## Baselines

Real exports from this repo's case studies, all passing:

| File | nodes | meshes | skins | tris | joints | animation |
|---|---|---|---|---|---|---|
| `Knight_R15_Walk.glb` | 33 | 15 | 1 | 324 | 17 | `Walk`, 51 channels, 25 keys, 1.0 s from 0.0417 s |
| `Knight_R15.glb` | 33 | 15 | 1 | 324 | 17 | none |
| `Test_Hinge_Tool.glb` | 5 | 1 | 1 | 24 | 3 | `Hinge_Open`, 9 channels, 60 keys, 2.4583 s |
| `Tang Crimping_Rig.glb` | 5 | 1 | 1 | 1176 | 3 | `Crimping_OpenClose`, 9 channels, 60 keys, 2.4583 s |

## The gates were tested against broken files

Byte-patching a known-good GLB and re-running proves each gate fires (exit 1 in every
case):

| Patch | Gate that failed |
|---|---|
| first rotation quaternion × 2 | `quaternion_norm_error` = 1.0 (and `loop_closure_error`) |
| last rotation key replaced with `(0,1,0,0)` | `loop_closure_error` |
| file truncated to 4 KiB | parse error, `pass: false` |
| `JOINTS_0[0] = 99` on a 17-joint skin | `joint_index_out_of_range` = 1 |
| `WEIGHTS_0[0] = (0,0,0,0)` | `unweighted_vertices` = 1 |

A gate that has never failed on purpose is a gate you cannot quote.

## Relationship to `verify_rig_glb.py`

`verify_rig_glb.py` needs Blender: it re-imports the GLB and measures widths at frames.
`glb_qa.py` needs nothing and reads the container, accessors, skins and animation
samplers. Run both when the asset has moving jaws or handles; run `glb_qa.py` alone for
locomotion and CI.
