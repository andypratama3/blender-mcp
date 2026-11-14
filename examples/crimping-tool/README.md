# Example: crimping tool

This folder documents the case study in
[`docs/CASE_STUDY_CRIMPING.md`](../../docs/CASE_STUDY_CRIMPING.md) with runnable
measurement code. The `.blend` and `.glb` are **not** included: the asset is
proprietary and binary files are excluded by `.gitignore`.

## What it does

`measure_live_rig.py` runs inside a live Blender session through the MCP bridge and
prints the numbers used as the acceptance criteria:

- rest deviation versus the source mesh,
- loop seam between the last and first frame,
- face-area ratio open vs closed,
- handle and jaw width at rest and open,
- weight coverage.

It is read-only: it changes the frame, measures, and restores the frame.

## Run it

```bash
# the bridge must be up (Blender launched with --online-mode)
python3 skills/blender-live-rigging/scripts/blender_mcp.py \
  --file examples/crimping-tool/measure_live_rig.py
```

Edit the constants at the top of the file if your object or frame range differs:

```python
OBJECT = "Crimping_Tool"
RIG = "Crimping_Rig"
FRAME_CLOSED = 1
FRAME_OPEN = 30
FRAME_LOOP = 60
HANDLE_Z_MAX = 0.0
JAW_Z_MIN = 0.25
```

## Expected output shape

```json
{
  "status": "ok",
  "result": {
    "object": "Crimping_Tool",
    "frames": {"closed": 1, "open": 30, "loop": 60},
    "rest_deviation": 2e-07,
    "loop_seam": 0.0,
    "face_area_ratio": {"min": 0.999, "max": 1.0005},
    "widths": {
      "closed": {"handle": 0.2869, "jaw": 0.1738},
      "open": {"handle": 0.3569, "jaw": 0.1895}
    },
    "weighted_vertices": {"total": 606, "weighted": 606}
  }
}
```

## Gates

| Metric | Pass condition |
|---|---|
| `rest_deviation` | `< 1e-5` |
| `loop_seam` | `== 0` |
| `face_area_ratio` | inside `0.99–1.01` |
| handle and jaw delta | both `> 0` |
| `weighted_vertices` | weighted == total |

A failure is a real rig defect. Fix the geometry or weights; do not loosen the gate.

## Related scripts

```bash
# inspect an asset before rigging
blender -b --factory-startup \
  --python skills/blender-live-rigging/scripts/inspect_glb.py -- "/path/asset.glb"

# verify the exported GLB in a separate process
blender -b --factory-startup \
  --python skills/blender-live-rigging/scripts/verify_rig_glb.py -- "/path/rig.glb"
```
