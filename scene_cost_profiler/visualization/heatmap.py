"""Heatmap overlay: color objects by performance score."""

import colorsys
import bpy

# Module-level storage for original state (transient — lost on reload)
_original_colors = {}   # object_name -> (r, g, b, a)
_original_shading = {}  # id(space) -> original color_type


def score_to_color(score, range_min=0.0, range_max=1.0):
    """Map a score to a green-to-red gradient.

    Scores at or below range_min -> green, at or above range_max -> red.
    Uses HSV interpolation for smooth color transition.
    """
    span = range_max - range_min
    if span <= 0:
        t = 1.0 if score >= range_max else 0.0
    else:
        t = min(max((score - range_min) / span, 0.0), 1.0)
    hue = 0.33 * (1.0 - t)
    r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 0.9)
    return (r, g, b, 1.0)


def apply_heatmap(context):
    """Apply heatmap colors to all analyzed objects."""
    scp = context.scene.scp
    if not scp.is_analyzed:
        return

    _original_colors.clear()
    _original_shading.clear()

    # Resolve which score attribute to use
    metric_attr = {
        'COMBINED': 'combined_score',
        'GEOMETRY': 'geometry_score',
        'SHADER': 'shader_score',
        'MODIFIER': 'modifier_score',
        'VRAM': 'texture_memory_score',
    }.get(scp.heatmap_metric, 'combined_score')

    # Auto-fit range to actual scores in scene
    if len(scp.object_results) > 0:
        scores = [getattr(r, metric_attr) for r in scp.object_results]
        scp.heatmap_range_min = min(scores)
        scp.heatmap_range_max = max(scores)
        # Ensure some spread if all scores are identical
        if scp.heatmap_range_max - scp.heatmap_range_min < 0.01:
            scp.heatmap_range_min = max(0.0, scp.heatmap_range_max - 0.1)

    range_min = scp.heatmap_range_min
    range_max = scp.heatmap_range_max
    for result in scp.object_results:
        obj = result.object_ptr
        if obj is None:
            continue
        _original_colors[obj.name] = tuple(obj.color)
        obj.color = score_to_color(getattr(result, metric_attr), range_min, range_max)

    # Switch viewport shading to Solid + OBJECT color
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    _original_shading[id(space)] = (
                        space.shading.type,
                        space.shading.color_type,
                    )
                    # Auto-switch to Solid if not already
                    if space.shading.type != 'SOLID':
                        space.shading.type = 'SOLID'
                    space.shading.color_type = 'OBJECT'

    scp.heatmap_active = True


def remove_heatmap(context):
    """Restore original object colors and viewport shading."""
    scp = context.scene.scp

    for obj_name, color in _original_colors.items():
        obj = context.scene.objects.get(obj_name)
        if obj:
            obj.color = color
    _original_colors.clear()

    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    original = _original_shading.get(id(space))
                    if original:
                        shading_type, color_type = original
                        space.shading.type = shading_type
                        space.shading.color_type = color_type
    _original_shading.clear()

    scp.heatmap_active = False


def recolor_heatmap(context):
    """Update object colors using current range without resetting range or shading."""
    scp = context.scene.scp
    if not scp.is_analyzed:
        return

    metric_attr = {
        'COMBINED': 'combined_score',
        'GEOMETRY': 'geometry_score',
        'SHADER': 'shader_score',
        'MODIFIER': 'modifier_score',
        'VRAM': 'texture_memory_score',
    }.get(scp.heatmap_metric, 'combined_score')

    range_min = scp.heatmap_range_min
    range_max = scp.heatmap_range_max
    for result in scp.object_results:
        obj = result.object_ptr
        if obj is None:
            continue
        obj.color = score_to_color(getattr(result, metric_attr), range_min, range_max)


def toggle_heatmap(context):
    """Toggle heatmap on/off."""
    scp = context.scene.scp
    if scp.heatmap_active:
        remove_heatmap(context)
    else:
        apply_heatmap(context)
