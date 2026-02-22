"""Scoring system: normalization and weighted combination."""

from ..data.models import ObjectAnalysis, SceneMaximums, ScoringWeights


def compute_scene_maximums(objects):
    """Compute maximum values across all analyzed objects.

    Args:
        objects: List of ObjectAnalysis.

    Returns:
        SceneMaximums with max values (min 1 to avoid division by zero).
    """
    maxs = SceneMaximums()

    for obj in objects:
        if obj.geometry.triangle_count > maxs.max_triangles:
            maxs.max_triangles = obj.geometry.triangle_count
        if obj.total_vram_bytes > maxs.max_vram_bytes:
            maxs.max_vram_bytes = obj.total_vram_bytes
        if obj.shader_score > maxs.max_shader_complexity:
            maxs.max_shader_complexity = obj.shader_score
        if obj.modifier_score > maxs.max_modifier_cost:
            maxs.max_modifier_cost = obj.modifier_score

    # Ensure no division by zero
    maxs.max_triangles = max(maxs.max_triangles, 1)
    maxs.max_vram_bytes = max(maxs.max_vram_bytes, 1)
    maxs.max_shader_complexity = max(maxs.max_shader_complexity, 0.001)
    maxs.max_modifier_cost = max(maxs.max_modifier_cost, 0.001)

    return maxs


def compute_object_scores(obj_analysis, scene_max, weights):
    """Normalize sub-scores and compute combined score.

    Modifies obj_analysis in place.

    Args:
        obj_analysis: ObjectAnalysis to score.
        scene_max: SceneMaximums for normalization.
        weights: ScoringWeights with relative weights.
    """
    # Normalize to scene-relative 0-1
    obj_analysis.geometry_score = (
        obj_analysis.geometry.triangle_count / scene_max.max_triangles
    )
    obj_analysis.texture_memory_score = (
        obj_analysis.total_vram_bytes / scene_max.max_vram_bytes
    )

    # Shader and modifier scores are already 0-1 from their analyzers,
    # but re-normalize against scene max for relative ranking
    if scene_max.max_shader_complexity > 0:
        obj_analysis.shader_score = (
            obj_analysis.shader_score / scene_max.max_shader_complexity
        )
    if scene_max.max_modifier_cost > 0:
        obj_analysis.modifier_score = (
            obj_analysis.modifier_score / scene_max.max_modifier_cost
        )

    # Weighted combination
    w_sum = weights.geometry + weights.shader + weights.modifier + weights.texture
    if w_sum <= 0:
        w_sum = 1.0

    obj_analysis.combined_score = (
        weights.geometry * obj_analysis.geometry_score
        + weights.shader * obj_analysis.shader_score
        + weights.modifier * obj_analysis.modifier_score
        + weights.texture * obj_analysis.texture_memory_score
    ) / w_sum
