#!/usr/bin/env python3
"""Blender 5.x slotted-action helpers and a JSON audit. Standard library only.

Blender 5.0 removed ``Action.fcurves``, ``Action.groups`` and ``Action.id_root``.
Curves now live in a channelbag owned by a slot, and an action assigned to an ID
without a matching slot silently animates nothing.

Inside Blender (MCP bridge or ``blender -b --python``)::

    blender -b file.blend --python scripts/action_compat.py

prints one JSON object:

    {"blender": [5, 4, 0], "legacy_fcurves_attr_present": false, "actions": [...],
     "objects": [...], "pass": true}

From another script::

    from action_compat import iter_fcurves, ensure_fcurve, assign_action
"""

import json
import sys


def iter_fcurves(action, slot=None):
    """Yield ``(slot, fcurve)`` for one slot, or every slot when slot is None."""
    slots = [slot] if slot is not None else list(action.slots)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", []):
                if slot is not None and bag.slot_handle != slot.handle:
                    continue
                for fcurve in bag.fcurves:
                    yield slot, fcurve


def _channelbag(action, slot):
    from bpy_extras import anim_utils

    return anim_utils.action_ensure_channelbag_for_slot(action, slot)


def ensure_fcurve(action, slot, data_path, index=0, group_name=""):
    """Return the fcurve for data_path[index], creating it inside the slot's channelbag."""
    bag = _channelbag(action, slot)
    fcurve = bag.fcurves.find(data_path, index=index)
    if fcurve is not None:
        return fcurve
    if group_name:
        return bag.fcurves.new(data_path, index=index, group_name=group_name)
    return bag.fcurves.new(data_path, index=index)


def pick_slot(obj, action):
    """Slot to bind, or None when the action has no slot for this ID yet."""
    for slot in action.slots:
        if slot.target_id_type == obj.id_type and slot.name_display == obj.name:
            return slot
    for slot in action.slots:
        if slot.target_id_type == obj.id_type:
            return slot
    return None


def assign_action(obj, action, slot=None, create_slot=True):
    """Assign action to obj and bind a slot. Returns the slot actually bound.

    Assigning an action that already has a slot for another ID leaves
    ``animation_data.action_slot`` as None, which animates nothing. This binds a slot
    explicitly instead.
    """
    ad = obj.animation_data or obj.animation_data_create()
    ad.action = action
    if slot is None:
        slot = pick_slot(obj, action)
    if slot is None and create_slot:
        slot = action.slots.new(obj.id_type, obj.name)
    if slot is not None:
        ad.action_slot = slot
    return slot


def audit():
    import bpy

    result = {
        "blender": list(bpy.app.version),
        "legacy_fcurves_attr_present": False,
        "actions": [],
        "objects": [],
    }
    for action in bpy.data.actions:
        if hasattr(action, "fcurves") or hasattr(action, "id_root"):
            result["legacy_fcurves_attr_present"] = True
        curves = list(iter_fcurves(action))
        keys = [point.co[0] for _, fcurve in curves for point in fcurve.keyframe_points]
        result["actions"].append(
            {
                "name": action.name,
                "slots": [slot.identifier for slot in action.slots],
                "layers": len(action.layers),
                "fcurves": len(curves),
                "keyframes": len(keys),
                "frame_min": min(keys) if keys else None,
                "frame_max": max(keys) if keys else None,
                "users": action.users,
            }
        )
    for obj in bpy.data.objects:
        ad = obj.animation_data
        if ad is None or ad.action is None:
            continue
        slot = ad.action_slot
        count = sum(1 for _ in iter_fcurves(ad.action, slot)) if slot is not None else 0
        result["objects"].append(
            {
                "object": obj.name,
                "action": ad.action.name,
                "slot": slot.identifier if slot is not None else None,
                "slot_assigned": slot is not None,
                "slot_fcurves": count,
            }
        )
    result["pass"] = all(o["slot_assigned"] and o["slot_fcurves"] > 0 for o in result["objects"])
    return result


def main():
    try:
        result = audit()
    except ImportError:
        print(json.dumps({"error": "bpy not available: run inside Blender", "pass": False}))
        return 1
    print(json.dumps(result, indent=1))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    status = main()
    try:
        import bpy

        live = not bpy.app.background
    except ImportError:
        live = False
    if not live:  # an exit code is meaningless in a GUI session, and SystemExit is not safe there
        sys.exit(status)
