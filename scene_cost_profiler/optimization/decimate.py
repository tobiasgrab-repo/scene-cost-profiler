"""Decimate optimization: non-destructive modifier-based decimation."""

import bpy

SCP_DECIMATE_NAME = "SCP_Decimate"


def decimate_objects(context, objects, ratio):
    """Add a Decimate modifier to mesh objects.

    Non-destructive: adds a modifier that can be removed or adjusted.
    Relies on Blender's undo system for reversal.

    Args:
        context: bpy.types.Context.
        objects: Iterable of bpy.types.Object.
        ratio: Float 0.01-1.0, target ratio of faces to keep.

    Returns:
        Number of objects that received a decimate modifier.
    """
    count = 0
    for obj in objects:
        if obj.type != 'MESH':
            continue
        if len(obj.data.polygons) == 0:
            continue

        # Remove existing SCP decimate if present (to avoid stacking)
        existing = obj.modifiers.get(SCP_DECIMATE_NAME)
        if existing:
            obj.modifiers.remove(existing)

        mod = obj.modifiers.new(name=SCP_DECIMATE_NAME, type='DECIMATE')
        mod.decimate_type = 'COLLAPSE'
        mod.ratio = ratio
        count += 1

    return count


def remove_decimate(obj):
    """Remove the SCP decimate modifier without applying.

    Args:
        obj: bpy.types.Object.

    Returns:
        True if a modifier was removed, False otherwise.
    """
    mod = obj.modifiers.get(SCP_DECIMATE_NAME)
    if mod is None:
        return False
    obj.modifiers.remove(mod)
    return True
