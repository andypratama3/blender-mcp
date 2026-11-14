# Case study: R15 knight avatar with a walk cycle

A blocky Roblox R15 knight built, rigged, animated and exported **live** in a running
Blender 5.4.0 Alpha session over MCP. No render was used; every number below was printed
by the scripts in the project folder (`build_knight.py`, `make_knight.py`,
`walk_cycle.py`, `inspect_fbx.py`).

## 1. Brief

| Property | Choice |
|---|---|
| Style | R15 blocky classic (15 body parts, R15 bone names) |
| Theme | Knight: helmet + crest, pauldrons, chest plate, belt, greaves, boots |
| Animation | In-place walk loop, one clip per exported file |
| Export | FBX (Roblox Studio) + GLB (preview / web) |

## 2. Body

| Metric | Value |
|---|---|
| Meshes | 15, one per R15 part, named `<Part>_Geo` |
| Bones | 17: `Root → HumanoidRootNode → LowerTorso → UpperTorso → (Head, arms…)`, legs from `LowerTorso` |
| Vertices / triangles | 216 / 324 (limit 10 742 for an R15 body) |
| Dimensions | 3.92 × 1.33 × 5.35 stud (body 5.0, crest 0.35), feet at z = 0 |
| Materials | `M_Metal`, `M_Cloth`, `M_Leather`, `M_Gold`, `M_Dark` |
| UVs | one set, all inside 0–1, axis-projected per face |
| Skinning | rigid, one bone per part |
| Object transforms | scale 1.0, origin 0,0,0 on every mesh |

Armor is merged into the body part it belongs to (helmet and crest into `Head_Geo`,
pauldron into `UpperArm_Geo`, chest plate into `UpperTorso_Geo`, belt into
`LowerTorso_Geo`), so the 15-mesh contract holds.

| Gate | Result |
|---|---|
| Non-manifold edges | 0 |
| Zero-area faces | 0 |
| Signed volume per mesh | positive (normals outward) |
| Vertices without weights | 0 / 216 |
| Live skin test (`LeftUpperArm` 45°) | 40 vertices moved, max 0.5657 stud, then reset |
| FBX round-trip | rig scale 1.0, 17 bones, 15 meshes, 324 tris, identical dimensions |
| GLB summary | 15 meshes, 5 materials, 1 skin, 324 tris |

## 3. Walk cycle

First attempt: five hand-keyed poses (frames 1/7/13/19/25) with a root bob. It passed
every gate that was written at the time — loop seam 0.0, legs leading, arms
counter-swinging, "feet not below ground" — because that gate read `pose_bone.tail.z`.
Measuring the deformed mesh showed the boots up to **0.2923 stud below the floor**. The
foot bone tail sits 0.4 stud above the sole; the gate was measuring the wrong thing.

Second attempt: analytic two-bone IK per frame, so the ankle target *is* the contact
condition.

| Parameter | Value |
|---|---|
| Cycle | 24 frames at 24 fps, keys on every frame (25 poses), in place |
| Stance / swing | 62% / 38%, swing arc `sin(π s)` |
| Stride | ankle y −0.50 … +0.50 stud, foot lift 0.32 stud |
| Hip height | 2.19 − 0.07 stud, lowest at contact, keyed on `HumanoidRootNode` local Y |
| Arms | ±30°, counter-phase, elbow 10–18° |
| Torso / head | 4° lean, ±5° twist, head counter-twist |
| Channels | 39 f-curves, 25 keys each |

| Gate | Result |
|---|---|
| Lowest mesh vertex, all frames | `-0.0` (no penetration) |
| Stance foot lowest vertex | `0.0` (sole exactly on the floor) |
| Swing foot peak | `0.3163` stud |
| Loop seam (frame 1 vs 25, pose matrices) | `7.35e-18` |
| Arms counter-swing | hands swap sides between contact poses |
| GLB re-import | animation `Walk`, frames 1–25, feet at 0.0, loop closed |

## 4. FBX verification without the importer

Reimporting the FBX into Blender is misleading: the importer rebuilds bones from
head/tail, marks `HumanoidRootNode` as *connected* to `Root`, and silently drops the
animated root translation, so the character floats by the bob amount on reimport.

`scripts/inspect_fbx.py` parses the shipped binary FBX instead:

```text
FBX 7400, 33 models, 162 animated channels
HumanoidRootNode       T X  n=25 frames 2.0..26.0  min   -0.030 max    0.030
HumanoidRootNode       T Y  n=25 frames 2.0..26.0  min    2.470 max    2.540
LeftUpperLeg           R X  n=25 frames 2.0..26.0  min  137.013 max  195.397
LeftLowerLeg           R X  n=25 frames 2.0..26.0  min    1.208 max   71.448
LeftFoot               R X  n=25 frames 2.0..26.0  min   79.459 max  130.669
```

Root height 2.470–2.540 is the 2.55 rest height minus the 0–0.08 bob: the translation
is in the file, and the Blender importer is the component that loses it. Rotation values
are Euler angles in the FBX Y-up frame, hence the offsets.

## 5. Other 5.4 traps hit on the way

| Symptom | Cause | Fix |
|---|---|---|
| `enum "OCTAHEDRAL" not found in ('BOUNDS','WIRE','SOLID','TEXTURED')` | `object.display_type` is viewport shading; armature display lives on the data | `rig.data.display_type = "OCTAHEDRAL"` |
| `AttributeError` on `bpy.context.window` in a background build | no window in `-b` | guard with `if bpy.context.window:` / `window_manager.windows` |
| New action named `Walk.001` | a fake-user action named `Walk` still exists | clear `use_fake_user`, remove, then create |
| FBX clip starts at frame 2 | FBX time origin is 1-based at 24 fps | expect `[2, 26]`, do not shift the action |

## 6. Reproduce

```bash
# body + rig
blender -b --factory-startup --python make_knight.py -- "$PWD"

# walk (headless); live: import walk_cycle and call main(save=True)
blender -b Knight_R15.blend --python walk_cycle.py -- --save

# exports
blender -b Knight_R15.blend -P ~/.config/opencode/skills/blender-export-pipelines/scripts/export_asset.py -- \
  --preset roblox --collection Knight_R15 --out "$PWD/export/Knight_R15_Walk.fbx"
blender -b Knight_R15.blend -P ~/.config/opencode/skills/blender-export-pipelines/scripts/export_asset.py -- \
  --preset roblox_gltf --collection Knight_R15 --out "$PWD/export/Knight_R15_Walk.glb"

# inspect the FBX without Blender
python3 inspect_fbx.py export/Knight_R15_Walk.fbx --model HumanoidRootNode
```

Roblox Studio: **Avatar → Avatar Setup → Import 3D** with the body FBX (target height
5 stud), then upload the walk FBX as one animation clip.
