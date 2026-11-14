# Blender 5.x action API (measured)

Every value on this page was printed by Blender 5.4.0 Alpha (`bpy.app.version ==
(5, 4, 0)`, build hash `f9495703eb0b`), not copied from release notes. Re-run
`scripts/action_compat.py` on a new build before trusting it there.

```bash
blender -b file.blend --python scripts/action_compat.py     # JSON audit, exit 1 on unbound slots

# live: cwd = skill folder, return the audit through the bridge
python3 scripts/blender_mcp.py "import sys; sys.path.insert(0, 'scripts')
import action_compat
result = action_compat.audit()"
```

A script run with `-f` cannot report a `result` object to the bridge, and `sys.exit`
inside the GUI is unsafe — that is why the live form imports the module instead of
executing it as `__main__`.

## What was removed

| Attribute | Present in 5.4 | Replacement |
|---|---|---|
| `Action.fcurves` | no | `action.layers[*].strips[*].channelbags[*].fcurves` |
| `Action.groups` | no | groups live on the channelbag |
| `Action.id_root` | no | the slot's `target_id_type` |

`channelbag.fcurves.new()` also renamed its group argument:

```python
bag.fcurves.new("location", index=0, group_name="Group")   # correct
bag.fcurves.new("location", index=0, action_group="Group") # TypeError: expected (data_path, index, group_name)
```

## Slots

Measured behaviour, each line a probe:

| Action | Code | Result |
|---|---|---|
| New action assigned to an ID | `ad.action = act` | `act.slots == []`, `ad.action_slot is None` |
| First `keyframe_insert` | `obj.keyframe_insert(...)` | creates slot `OB<object name>` **and** binds it |
| Existing action, same ID | `ad.action = act` | slot auto-bound (`OBKnight_R15_Rig`) |
| Existing action, **different** ID | `ad.action = act` | `ad.action_slot is None` → **animates nothing** |
| Bind explicitly | `ad.action_slot = slot` | works across IDs of the same `id_type` |
| Slot fields | — | `identifier`, `name_display`, `target_id_type`, `handle` |
| Create | `act.slots.new(obj.id_type, obj.name)` | identifier `OB<name>`; repeat calls give `.001` |
| Ensure channelbag | `anim_utils.action_ensure_channelbag_for_slot(act, slot)` | creates layer + `KEYFRAME` strip |

The silent failure is the dangerous one: assigning a walk action to a second armature
left the head bone at its rest height `4.0` instead of the animated `3.92`, with no
error. `scripts/action_compat.py` prints `slot_assigned` and `slot_fcurves` per object
and exits 1 when either is missing.

## Reading curves generically

```python
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:          # one per slot
            bag.slot_handle                    # matches slot.handle
            for fc in bag.fcurves:
                ...
```

`strip.channelbag(slot)` returns the bag for one slot, or `None` when that slot has no
animation yet.

## glTF time origin

Four exports measured (`Knight_R15_Walk.glb`, `Test_Hinge_Tool.glb`,
`Tang Crimping_Rig.glb`): the first keyframe sits at `t = 1/fps` (0.0417 s at 24 fps),
not at 0, and the clip length is `last - first` (1.0 s for a 24-frame walk, 2.4583 s for
a 59-frame hinge). Report duration as a span, and gate the offset with
`glb_qa.py --start-at-zero` when the target player assumes the clip starts at 0.
