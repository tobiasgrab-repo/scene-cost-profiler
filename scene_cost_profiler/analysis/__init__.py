"""Analysis engine: scene and object analysis pipeline."""

import time
import bpy

from ..data.models import ObjectAnalysis, SceneAnalysis, ScoringWeights
from ..utils.constants import ANALYZABLE_TYPES
from .geometry import analyze_geometry
from .textures import analyze_textures
from .modifiers import analyze_modifiers, compute_modifier_score
from .materials import analyze_materials, compute_shader_score
from .scoring import compute_scene_maximums, compute_object_scores


def _get_preferences():
    """Get addon preferences, with fallback defaults."""
    from .. import get_preferences
    return get_preferences()


def _get_weights(context, prefs):
    """Build ScoringWeights from scene overrides, preferences, or defaults."""
    scp = context.scene.scp
    if scp.use_custom_weights:
        return ScoringWeights(
            geometry=scp.weight_geometry,
            shader=scp.weight_shader,
            modifier=scp.weight_modifier,
            texture=scp.weight_texture,
        )
    if prefs is None:
        return ScoringWeights()
    return ScoringWeights(
        geometry=prefs.weight_geometry,
        shader=prefs.weight_shader,
        modifier=prefs.weight_modifier,
        texture=prefs.weight_texture,
    )


def _get_mipmap_factor(prefs):
    """Get mipmap factor from preferences or default."""
    if prefs is None:
        return 1.33
    return prefs.mipmap_factor


def analyze_object(obj, depsgraph, seen_textures, mipmap_factor=1.33):
    """Analyze a single object.

    Args:
        obj: bpy.types.Object to analyze.
        depsgraph: Evaluated depsgraph.
        seen_textures: Dict for texture deduplication across objects.
        mipmap_factor: VRAM mipmap multiplier.

    Returns:
        ObjectAnalysis with raw scores (not yet normalized).
    """
    result = ObjectAnalysis(
        object_name=obj.name,
        object_type=obj.type,
    )

    # Geometry
    result.geometry = analyze_geometry(obj, depsgraph)

    # Textures
    textures, total_vram = analyze_textures(obj, mipmap_factor, seen_textures)
    result.total_vram_bytes = total_vram

    # Materials
    result.materials = analyze_materials(obj)
    result.shader_score = compute_shader_score(result.materials)

    # Store texture info on materials for detail view
    for mat_metrics in result.materials:
        mat_metrics.textures = [
            t for t in textures
            if _texture_used_by_material(obj, mat_metrics.material_name, t.image_name)
        ]

    # Modifiers
    result.modifiers = analyze_modifiers(obj)
    result.modifier_score = compute_modifier_score(result.modifiers)

    return result


def _texture_used_by_material(obj, mat_name, image_name):
    """Check if a specific image is used by a named material on the object."""
    materials = getattr(obj.data, 'materials', None)
    if materials is None:
        return False

    for mat in materials:
        if mat is None or mat.name != mat_name:
            continue
        if mat.node_tree is None:
            continue
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image and node.image.name == image_name:
                return True
    return False


def analyze_scene(context):
    """Main entry point: analyze all objects in the scene.

    Args:
        context: bpy.types.Context.

    Returns:
        SceneAnalysis with all results scored and sorted.
    """
    start = time.perf_counter()

    depsgraph = context.evaluated_depsgraph_get()
    prefs = _get_preferences()
    weights = _get_weights(context, prefs)
    mipmap_factor = _get_mipmap_factor(prefs)

    seen_textures = {}
    objects_analysis = []

    scp = context.scene.scp
    source = context.selected_objects if scp.analyze_selection_only else context.scene.objects

    for obj in source:
        if obj.type not in ANALYZABLE_TYPES:
            continue
        obj_result = analyze_object(obj, depsgraph, seen_textures, mipmap_factor)
        objects_analysis.append(obj_result)

    # Compute scene maximums for normalization
    scene_max = compute_scene_maximums(objects_analysis)

    # Normalize and compute combined scores
    for obj_result in objects_analysis:
        compute_object_scores(obj_result, scene_max, weights)

    # Build scene totals — deduplicate instanced mesh data for unique count
    seen_meshes = set()
    total_vertices = 0
    total_triangles = 0
    total_triangles_draw = sum(o.geometry.triangle_count for o in objects_analysis)
    for o in objects_analysis:
        mesh_key = o.geometry.mesh_datablock
        if mesh_key and mesh_key in seen_meshes:
            continue
        if mesh_key:
            seen_meshes.add(mesh_key)
        total_vertices += o.geometry.vertex_count
        total_triangles += o.geometry.triangle_count
    total_vram = sum(t.vram_bytes for t in seen_textures.values())

    elapsed_ms = (time.perf_counter() - start) * 1000

    return SceneAnalysis(
        total_objects=len(objects_analysis),
        total_vertices=total_vertices,
        total_triangles=total_triangles,
        total_triangles_draw=total_triangles_draw,
        total_vram_bytes=total_vram,
        unique_textures=seen_textures,
        objects=objects_analysis,
        analysis_time_ms=elapsed_ms,
    )


def write_results_to_properties(context, scene_analysis):
    """Write SceneAnalysis results into Blender PropertyGroups for UI display.

    Args:
        context: bpy.types.Context.
        scene_analysis: SceneAnalysis to write.
    """
    scp = context.scene.scp

    # Scene totals
    scp.total_objects = scene_analysis.total_objects
    scp.total_vertices = scene_analysis.total_vertices
    scp.total_triangles = scene_analysis.total_triangles
    scp.total_triangles_draw = scene_analysis.total_triangles_draw
    scp.total_vram_mb = scene_analysis.total_vram_bytes / (1024 * 1024)
    scp.analysis_time_ms = scene_analysis.analysis_time_ms
    scp.is_analyzed = True
    scp.is_stale = False

    # Clear and rebuild object results
    scp.object_results.clear()

    for obj_data in scene_analysis.objects:
        entry = scp.object_results.add()
        entry.object_name = obj_data.object_name
        entry.object_ptr = context.scene.objects.get(obj_data.object_name)
        entry.vertex_count = obj_data.geometry.vertex_count
        entry.edge_count = obj_data.geometry.edge_count
        entry.face_count = obj_data.geometry.face_count
        entry.triangle_count = obj_data.geometry.triangle_count
        entry.geometry_score = obj_data.geometry_score
        entry.shader_score = obj_data.shader_score
        entry.modifier_score = obj_data.modifier_score
        entry.texture_memory_score = obj_data.texture_memory_score
        entry.combined_score = obj_data.combined_score
        entry.total_vram_mb = obj_data.total_vram_bytes / (1024 * 1024)
        entry.is_instance = obj_data.geometry.is_instance

        # Detail: textures
        entry.textures.clear()
        seen_for_obj = set()
        for mat in obj_data.materials:
            for tex in mat.textures:
                if tex.image_name not in seen_for_obj:
                    seen_for_obj.add(tex.image_name)
                    t = entry.textures.add()
                    t.image_name = tex.image_name
                    t.resolution = f"{tex.width}x{tex.height}"
                    t.vram_mb = tex.vram_bytes / (1024 * 1024)
                    t.bit_depth = tex.bit_depth

        # Detail: modifiers
        entry.modifiers.clear()
        for mod in obj_data.modifiers:
            m = entry.modifiers.add()
            m.modifier_name = mod.modifier_name
            m.modifier_type = mod.modifier_type
            m.is_high_cost = mod.is_high_cost
            m.cost_score = mod.cost_score

        # Detail: materials
        entry.materials.clear()
        for mat in obj_data.materials:
            me = entry.materials.add()
            me.material_name = mat.material_name
            me.node_count = mat.total_node_count
            me.texture_count = mat.texture_node_count
            me.noise_count = mat.procedural_noise_count
            me.complexity_score = mat.complexity_score

    # Compute budget violations
    if scp.budget_enabled:
        for entry in scp.object_results:
            entry.exceeds_budget = (
                entry.triangle_count > scp.budget_max_tris_per_object
                or entry.total_vram_mb > scp.budget_max_vram_mb
                or entry.shader_score > scp.budget_max_shader_complexity
            )

    # Apply initial sort
    from ..data.properties import _sort_results_update
    _sort_results_update(scp, None)

    # Reset selection index
    scp.object_results_index = 0
