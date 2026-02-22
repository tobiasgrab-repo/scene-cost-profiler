"""Modifier detection and cost scoring."""

from ..data.models import ModifierInfo
from ..utils.constants import (
    HIGH_COST_MODIFIER_TYPES,
    MODIFIER_BASE_COST,
    DEFAULT_MODIFIER_COST,
    MAX_MODIFIER_COST_RAW,
)


def _compute_modifier_cost(mod):
    """Compute cost score for a single modifier."""
    mod_type = mod.type
    base = MODIFIER_BASE_COST.get(mod_type, DEFAULT_MODIFIER_COST)

    if mod_type == 'SUBSURF':
        level = getattr(mod, 'levels', 1)
        return base * (4 ** level)

    if mod_type == 'MULTIRES':
        level = getattr(mod, 'levels', 1)
        return base * (4 ** level)

    if mod_type == 'ARRAY':
        count = getattr(mod, 'count', 1)
        return base * count

    return base


def analyze_modifiers(obj):
    """Analyze all modifiers on an object.

    Args:
        obj: bpy.types.Object to analyze.

    Returns:
        List of ModifierInfo with cost scores.
    """
    results = []

    for mod in obj.modifiers:
        viewport_level = 0
        render_level = 0

        if mod.type in {'SUBSURF', 'MULTIRES'}:
            viewport_level = getattr(mod, 'levels', 0)
            render_level = getattr(mod, 'render_levels', 0)

        cost = _compute_modifier_cost(mod)

        results.append(ModifierInfo(
            modifier_name=mod.name,
            modifier_type=mod.type,
            is_high_cost=mod.type in HIGH_COST_MODIFIER_TYPES,
            viewport_level=viewport_level,
            render_level=render_level,
            cost_score=cost,
        ))

    return results


def compute_modifier_score(modifiers):
    """Compute a normalized 0-1 modifier cost score from modifier list.

    Args:
        modifiers: List of ModifierInfo.

    Returns:
        Float in [0.0, 1.0].
    """
    if not modifiers:
        return 0.0

    raw = sum(m.cost_score for m in modifiers)
    return min(raw / MAX_MODIFIER_COST_RAW, 1.0)
