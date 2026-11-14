# Roblox R15 avatar + walk cycle

Measured in Blender 5.4.0 Alpha over MCP. Case study with every number:
`docs/CASE_STUDY_KNIGHT.md` in the repo root.

## 1. Units and orientation

| Item | Value |
|---|---|
| Unit | 1 stud ≈ 0.28 m; author the mesh in studs |
| Axis | Blender Z up, character faces −Y |
| Height | Default R15 character ≈ 5 studs (this rig: 5.35 with helmet crest) |
| Export | FBX preset `roblox` (`FBX_SCALE_UNITS`, no 100× scale) or GLB preset `roblox_gltf` |
| Limits | ≤ 20 000 tris per mesh, 10 742 total for an R15 body, one UV set inside 0–1, one animation per exported file |

## 2. Rig naming is the contract

Roblox maps parts by name, so the armature must use the R15 part names, one mesh per
part named `<Part>_Geo`:

`Head`, `UpperTorso`, `LowerTorso`, `Left/RightUpperArm`, `Left/RightLowerArm`,
`Left/RightHand`, `Left/RightUpperLeg`, `Left/RightLowerLeg`, `Left/RightFoot`
(15 meshes), plus `HumanoidRootNode` as the root part and `Root` as an optional
transform wrapper (17 bones here).

Hierarchy used by this rig: `Root → HumanoidRootNode → LowerTorso → UpperTorso →
(Head, arms…)`, legs from `LowerTorso`. Skin rigidly: one bone per part, weight 1.0,
0 unweighted vertices.

Armor must be merged into the body part it belongs to (helmet + crest into `Head_Geo`,
pauldron into `UpperArm_Geo`), otherwise the 15-mesh contract breaks.

## 3. Bone axis conventions (measured, not assumed)

These hold for axis-aligned bones built from `head`/`tail` with roll 0 in 5.4:

| Bone | local X | local Y | local Z | positive `rotation_euler.x` |
|---|---|---|---|---|
| Down-pointing (arms, legs) | world +X | world −Z | world +Y | swings the bone **backward** (+Y) |
| Up-pointing (torso, root) | world +X | world +Z | world −Y | leans **forward** (−Y) |
| Foot | world −X | world −Y | world +Z | toe **up** |

Torso `rotation_euler.y` is a world-Z twist (left shoulder back for positive values).
Probe before trusting this on a new rig: set 30°, read `pose_bone.head`/`tail`, reset.

## 4. Walk cycle: IK first, then keys

A hand-keyed 5-pose walk looked plausible but drove the boots 0.29 studs through the
floor. Solve the legs instead:

```python
def leg_ik(y, z, hip_z, L1=0.9, L2=0.9):
    dy, dz = y, z - hip_z                     # hip at y=0
    reach = min(math.hypot(dy, dz), L1 + L2 - 1e-4)
    beta = math.acos((reach**2 - L1**2 - L2**2) / (2*L1*L2))   # knee, backward
    alpha = math.atan2(L2*math.sin(beta), L1 + L2*math.cos(beta))
    phi = math.atan2(dy, -dz)                 # hip -> ankle vs straight down
    return math.degrees(phi - alpha), math.degrees(beta)

hip_rx, knee_rx = leg_ik(foot_y, foot_z, hip_z)
foot_rx = hip_rx + knee_rx        # keeps the sole horizontal
```

Recipe that produced a clean loop (24 frames at 24 fps, in place):

| Parameter | Value |
|---|---|
| Stance / swing split | 62% stance, 38% swing |
| Stride half-length | 0.50 stud (ankle y −0.50 … +0.50) |
| Foot lift | 0.32 stud, `sin(π s)` on the swing |
| Hip height | 2.19 − 0.07 (lowest at contact), bob on `HumanoidRootNode` local Y |
| Ankle target during stance | rest ankle height, constant → sole exactly on z=0 |
| Arms | ±30°, counter-phase to the legs, elbow 10–18° flexion |
| Torso | 4° forward lean, ±5° twist, head counter-twist |

Ankle IK is in-place: the stance foot slides backward at constant speed, and the game
engine supplies the forward motion. Foot travel per step (1.0 stud here) sets the
playback speed you need in Roblox: `AdjustSpeed(walkSpeed / (2 * stride * fps / cycle))`.

## 5. Ground contact must be measured on the mesh

Bone tails are not the ground. The foot bone tail sits ~0.4 stud above the sole, so a
gate built on `pose_bone.tail.z` passes while the boot is buried. Measure the evaluated
mesh:

```python
deps = bpy.context.evaluated_depsgraph_get()
ev = obj.evaluated_get(deps)
mesh = ev.to_mesh()
low = min((ev.matrix_world @ v.co).z for v in mesh.vertices)
ev.to_mesh_clear()
```

| Gate | Threshold |
|---|---|
| Lowest mesh vertex, all frames | ≥ −0.006 stud |
| Stance foot lowest vertex | within 0.006 of 0 |
| Swing foot peak lowest vertex | > 0.25 stud |
| Loop seam (last vs first pose matrix) | < 1e-6 |
| Arms counter-swing | hands swap sides between contact poses |

## 6. FBX: bake, ship, verify without Blender's importer

`bake_anim=True` writes one curve set per bone. Two traps:

- **Blender's FBX importer lies about bone translation.** It rebuilds bones from
  head/tail and marks `HumanoidRootNode` as *connected* to `Root` (the parent's tail
  meets the child's head), so the animated root translation is dropped on reimport and
  the character floats by the bob amount (0.18 stud in the failed version, 0.08 after
  the fix). The shipped file is fine: reading it directly shows `HumanoidRootNode`
  `T Y` 2.470 → 2.540 and `T X` ±0.03, 25 keys.
- **Clip start.** Blender frame 1 lands on FBX frame 2 (FBX time is offset by one
  frame at 24 fps). Expect `frame_range == [2, 26]` after a round trip.

Verify the file itself, not the round trip:

```bash
python3 scripts/inspect_fbx.py export/Knight_R15_Walk.fbx --model HumanoidRootNode
```

This parses the binary FBX node tree (no Blender, no importer) and prints each animated
channel: model, `T`/`R`/`S`, axis, key count, frame span, min and max. A walk export
must show 25 keys on the root translation and on every leg/arm rotation channel.

GLB round-trips correctly (`export_animation_mode="ACTIONS"` → animation name `Walk`,
frames 1–25, feet at 0.0), so use GLB when you need a verifiable reimport and FBX for
Roblox Studio.

## 7. Roblox Studio

1. **Avatar tab → Avatar Setup → Import 3D**, pick the body FBX (no animation).
   Target height 5 studs, then save the model.
2. Animation: open the rig, upload the `*_Walk.fbx` clip (one clip per file), or use
   *Avatar → Animation* in Studio. Keep the part names intact or retargeting fails.
3. Roblox drives the character's position; the clip must stay in place. Do not key
   world translation beyond the vertical bob and lateral sway.
