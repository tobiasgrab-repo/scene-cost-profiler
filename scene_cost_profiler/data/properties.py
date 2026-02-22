"""Blender PropertyGroups for storing analysis results and settings."""

import bpy
from bpy.props import (
    FloatProperty, IntProperty, StringProperty, BoolProperty,
    CollectionProperty, EnumProperty, PointerProperty,
)

from ..utils.constants import (
    DEFAULT_WEIGHT_GEOMETRY, DEFAULT_WEIGHT_SHADER,
    DEFAULT_WEIGHT_MODIFIER, DEFAULT_WEIGHT_TEXTURE,
    DEFAULT_MIPMAP_FACTOR,
)


# --- Budget Preset Definitions ---

BUDGET_PRESETS = {
    'MOBILE_VR': (10_000, 64.0, 0.3),
    'DESKTOP_GAME': (100_000, 512.0, 0.7),
    'HIGH_END': (500_000, 2048.0, 1.0),
}


def _heatmap_metric_update(self, context):
    """Re-apply heatmap when the metric changes (auto-fits range)."""
    if not self.heatmap_active:
        return
    from ..visualization.heatmap import remove_heatmap, apply_heatmap
    remove_heatmap(context)
    apply_heatmap(context)


def _heatmap_range_update(self, context):
    """Re-color objects when min/max range changes (keeps current range)."""
    if not self.heatmap_active:
        return
    from ..visualization.heatmap import recolor_heatmap
    recolor_heatmap(context)


def _sort_results_update(self, context):
    """Re-sort object_results collection when sort settings change."""
    results = self.object_results
    n = len(results)
    if n <= 1:
        return

    sort_attr = {
        'COMBINED': 'combined_score',
        'GEOMETRY': 'geometry_score',
        'SHADER': 'shader_score',
        'MODIFIER': 'modifier_score',
        'VRAM': 'total_vram_mb',
        'TRIANGLES': 'triangle_count',
    }.get(self.sort_by, 'combined_score')

    descending = self.sort_descending

    # Insertion sort using CollectionProperty.move()
    for i in range(1, n):
        j = i
        while j > 0:
            curr = getattr(results[j], sort_attr)
            prev = getattr(results[j - 1], sort_attr)
            should_swap = curr > prev if descending else curr < prev
            if should_swap:
                results.move(j, j - 1)
                j -= 1
            else:
                break


def _budget_preset_update(self, context):
    """Populate budget fields when a preset is selected."""
    preset = self.budget_preset
    if preset in BUDGET_PRESETS:
        tris, vram, shader = BUDGET_PRESETS[preset]
        self.budget_max_tris_per_object = tris
        self.budget_max_vram_mb = vram
        self.budget_max_shader_complexity = shader


class SCP_TextureEntry(bpy.types.PropertyGroup):
    """Single texture entry for display in object detail."""
    image_name: StringProperty(name="Texture", description="Texture image name")
    resolution: StringProperty(name="Resolution", description="Image resolution (WxH)")
    vram_mb: FloatProperty(name="VRAM (MB)", description="Estimated VRAM usage in megabytes")
    bit_depth: IntProperty(name="Bit Depth", description="Bits per channel")


class SCP_ModifierEntry(bpy.types.PropertyGroup):
    """Single modifier entry for display."""
    modifier_name: StringProperty(name="Modifier", description="Modifier name")
    modifier_type: StringProperty(name="Type", description="Modifier type identifier")
    is_high_cost: BoolProperty(name="High Cost", description="Whether this modifier is expensive to compute")
    cost_score: FloatProperty(name="Cost Score", description="Relative cost of this modifier (0-1)")


class SCP_MaterialEntry(bpy.types.PropertyGroup):
    """Single material entry for display."""
    material_name: StringProperty(name="Material", description="Material name")
    node_count: IntProperty(name="Nodes", description="Total number of shader nodes")
    texture_count: IntProperty(name="Textures", description="Number of texture image nodes")
    noise_count: IntProperty(name="Procedural", description="Number of procedural noise nodes")
    complexity_score: FloatProperty(name="Complexity", description="Material complexity score (0-1)")


class SCP_ObjectResult(bpy.types.PropertyGroup):
    """Per-object analysis result stored on the Scene for the ranked list."""
    object_name: StringProperty(name="Object", description="Name of the analyzed object")
    object_ptr: PointerProperty(type=bpy.types.Object, name="Object Ref")
    vertex_count: IntProperty(name="Vertices", description="Number of vertices")
    triangle_count: IntProperty(name="Triangles", description="Number of triangles after triangulation")
    geometry_score: FloatProperty(
        name="Geo Score",
        description="Triangle count relative to the heaviest object in the scene",
    )
    shader_score: FloatProperty(
        name="Shader Score",
        description="Material node complexity relative to the most complex material",
    )
    modifier_score: FloatProperty(
        name="Modifier Score",
        description="Modifier stack cost relative to the most expensive modifier stack",
    )
    texture_memory_score: FloatProperty(
        name="Tex Memory Score",
        description="Estimated VRAM usage relative to the highest VRAM object",
    )
    combined_score: FloatProperty(
        name="Combined Score",
        description="Overall performance cost (0 = cheap, 1 = most expensive in scene)",
    )
    total_vram_mb: FloatProperty(
        name="VRAM (MB)",
        description="Estimated texture VRAM usage in megabytes",
    )

    # Detail data (stored as collections on the object result)
    textures: CollectionProperty(type=SCP_TextureEntry)
    modifiers: CollectionProperty(type=SCP_ModifierEntry)
    materials: CollectionProperty(type=SCP_MaterialEntry)

    edge_count: IntProperty(name="Edges", description="Number of edges")
    face_count: IntProperty(name="Faces", description="Number of faces (quads/ngons)")

    exceeds_budget: BoolProperty(name="Exceeds Budget", default=False,
                                 description="Object exceeds one or more performance budget limits")
    is_instance: BoolProperty(name="Instanced", default=False,
                              description="Mesh data is shared with other objects (linked duplicate)")


class SCP_SceneProperties(bpy.types.PropertyGroup):
    """Main scene-level properties for the profiler."""

    is_analyzed: BoolProperty(default=False)
    analysis_time_ms: FloatProperty(name="Analysis Time (ms)")
    is_stale: BoolProperty(
        default=False,
        description="Results are outdated due to scene changes",
    )

    total_objects: IntProperty(name="Total Objects")
    total_vertices: IntProperty(name="Total Vertices")
    total_triangles: IntProperty(
        name="Total Triangles",
        description="Unique triangles (shared mesh data counted once)",
    )
    total_triangles_draw: IntProperty(
        name="Draw Triangles",
        description="Total triangles submitted for drawing (instances counted separately)",
    )
    total_vram_mb: FloatProperty(name="Total VRAM (MB)")

    object_results: CollectionProperty(type=SCP_ObjectResult)
    object_results_index: IntProperty(
        name="Active Result Index", default=0, min=-1,
        description="Index of the selected object in rankings (-1 = none)",
    )

    sort_by: EnumProperty(
        name="Sort By",
        items=[
            ('COMBINED', "Combined Score", "Sort by combined performance score"),
            ('GEOMETRY', "Geometry", "Sort by geometry score"),
            ('SHADER', "Shader", "Sort by shader complexity"),
            ('MODIFIER', "Modifier", "Sort by modifier cost"),
            ('VRAM', "VRAM", "Sort by texture memory"),
            ('TRIANGLES', "Triangles", "Sort by triangle count"),
        ],
        default='COMBINED',
        update=_sort_results_update,
    )
    sort_descending: BoolProperty(
        name="Descending", default=True,
        description="Sort highest cost first (descending) or lowest first (ascending)",
        update=_sort_results_update,
    )

    heatmap_active: BoolProperty(
        name="Heatmap Active",
        default=False,
        description="Show performance heatmap overlay on objects",
    )
    heatmap_metric: EnumProperty(
        name="Metric",
        items=[
            ('COMBINED', "Combined", "Color by overall combined score"),
            ('GEOMETRY', "Geometry", "Color by triangle count score"),
            ('SHADER', "Shader", "Color by shader complexity"),
            ('MODIFIER', "Modifier", "Color by modifier cost"),
            ('VRAM', "VRAM", "Color by texture memory usage"),
        ],
        default='COMBINED',
        description="Which score metric drives the heatmap colors",
        update=_heatmap_metric_update,
    )
    heatmap_range_min: FloatProperty(
        name="Min", default=0.0, min=0.0, max=1.0,
        description="Score mapped to green (low cost). Raise to see differences in simple scenes",
        update=_heatmap_range_update,
    )
    heatmap_range_max: FloatProperty(
        name="Max", default=1.0, min=0.0, max=1.0,
        description="Score mapped to red (high cost). Lower to see differences in simple scenes",
        update=_heatmap_range_update,
    )

    filter_threshold: FloatProperty(
        name="Min Score",
        default=0.0, min=0.0, max=1.0,
        description="Hide objects with combined score below this value",
    )

    analyze_selection_only: BoolProperty(
        name="Selected Only",
        default=False,
        description="Analyze only selected objects instead of the entire scene",
    )

    # Budget system
    budget_preset: EnumProperty(
        name="Budget Preset",
        items=[
            ('CUSTOM', "Custom", "Use custom budget values"),
            ('MOBILE_VR', "Mobile VR", "Low-poly targets for mobile and standalone VR"),
            ('DESKTOP_GAME', "Desktop Game", "Standard real-time game budgets"),
            ('HIGH_END', "High-End / Film", "High-fidelity rendering or film production"),
        ],
        default='CUSTOM',
        description="Pre-filled performance budget for common target platforms",
        update=_budget_preset_update,
    )
    budget_enabled: BoolProperty(
        name="Enable Budget", default=False,
        description="Flag objects that exceed performance budget limits",
    )
    budget_max_vram_mb: FloatProperty(
        name="VRAM Budget (MB)", default=512.0,
        min=0.0, soft_max=4096.0,
        description="Maximum VRAM per object in MB",
    )
    budget_max_tris_per_object: IntProperty(
        name="Max Tris/Object", default=100000, min=0,
        description="Maximum triangle count per object",
    )
    budget_max_shader_complexity: FloatProperty(
        name="Max Shader Complexity", default=0.7,
        min=0.0, max=1.0,
        description="Maximum shader complexity score (0-1). Use presets for typical targets",
    )

    # Inline weight overrides (per-scene)
    use_custom_weights: BoolProperty(
        name="Custom Weights", default=False,
        description="Override addon preference weights for this scene",
    )
    weight_geometry: FloatProperty(
        name="Geometry", default=DEFAULT_WEIGHT_GEOMETRY,
        min=0.0, max=1.0,
        description="How much geometry contributes to the combined score (re-analyze to apply)",
    )
    weight_shader: FloatProperty(
        name="Shader", default=DEFAULT_WEIGHT_SHADER,
        min=0.0, max=1.0,
        description="How much shader complexity contributes to the combined score (re-analyze to apply)",
    )
    weight_modifier: FloatProperty(
        name="Modifier", default=DEFAULT_WEIGHT_MODIFIER,
        min=0.0, max=1.0,
        description="How much modifier cost contributes to the combined score (re-analyze to apply)",
    )
    weight_texture: FloatProperty(
        name="Texture", default=DEFAULT_WEIGHT_TEXTURE,
        min=0.0, max=1.0,
        description="How much texture VRAM contributes to the combined score (re-analyze to apply)",
    )


class SCP_AddonPreferences(bpy.types.AddonPreferences):
    # Must match the module name Blender uses to load the package.
    # For legacy addons: "scene_cost_profiler"
    # For Blender 5.0 extensions: "bl_ext.user_default.scene_cost_profiler"
    bl_idname = __package__.rsplit(".", 1)[0] if "." in __package__ else __package__

    weight_geometry: FloatProperty(
        name="Geometry Weight",
        default=DEFAULT_WEIGHT_GEOMETRY, min=0.0, max=1.0,
        description="Weight for geometry (triangle count) in combined score",
    )
    weight_shader: FloatProperty(
        name="Shader Weight",
        default=DEFAULT_WEIGHT_SHADER, min=0.0, max=1.0,
        description="Weight for shader complexity in combined score",
    )
    weight_modifier: FloatProperty(
        name="Modifier Weight",
        default=DEFAULT_WEIGHT_MODIFIER, min=0.0, max=1.0,
        description="Weight for modifier cost in combined score",
    )
    weight_texture: FloatProperty(
        name="Texture Memory Weight",
        default=DEFAULT_WEIGHT_TEXTURE, min=0.0, max=1.0,
        description="Weight for texture VRAM usage in combined score",
    )

    mipmap_factor: FloatProperty(
        name="Mipmap Factor",
        default=DEFAULT_MIPMAP_FACTOR, min=1.0, max=2.0,
        description="Multiplier for mipmap chain VRAM overhead (1.33 is standard)",
    )

    high_cost_triangle_threshold: IntProperty(
        name="High Triangle Threshold",
        default=100000,
        description="Triangle count above which an object is considered high-cost",
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="Scoring Weights:")
        col = layout.column(align=True)
        col.prop(self, "weight_geometry")
        col.prop(self, "weight_shader")
        col.prop(self, "weight_modifier")
        col.prop(self, "weight_texture")
        layout.separator()
        layout.label(text="VRAM Estimation:")
        layout.prop(self, "mipmap_factor")
        layout.separator()
        layout.label(text="Thresholds:")
        layout.prop(self, "high_cost_triangle_threshold")
