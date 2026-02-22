"""Apply high-cost modifiers destructively."""

import bpy

from ..utils.constants import HIGH_COST_MODIFIER_TYPES

# Modifier types for the enum choices
APPLY_TYPES = {
    'BOOLEAN': {'BOOLEAN'},
    'REMESH': {'REMESH'},
    'ALL_HIGH_COST': set(HIGH_COST_MODIFIER_TYPES),
}


def apply_modifiers(context, objects, apply_type='ALL_HIGH_COST'):
    """Apply modifiers matching the requested type category.

    Args:
        context: bpy.types.Context.
        objects: Iterable of bpy.types.Object.
        apply_type: One of 'BOOLEAN', 'REMESH', 'ALL_HIGH_COST'.

    Returns:
        Number of modifiers successfully applied.
    """
    target_types = APPLY_TYPES.get(apply_type, APPLY_TYPES['ALL_HIGH_COST'])
    applied_count = 0

    for obj in objects:
        if obj.type != 'MESH' or obj.library is not None:
            continue

        # Collect modifier names first (applying changes the list)
        to_apply = [
            mod.name for mod in obj.modifiers
            if mod.type in target_types
        ]

        if not to_apply:
            continue

        # Must be active object for modifier_apply operator
        context.view_layer.objects.active = obj

        for mod_name in to_apply:
            try:
                bpy.ops.object.modifier_apply(modifier=mod_name)
                applied_count += 1
            except RuntimeError:
                pass  # Modifier may not be applicable (e.g. disabled)

    return applied_count
