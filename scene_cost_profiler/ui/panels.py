"""Sidebar panels for the Scene Cost Profiler."""

import bpy


def _format_count(n):
    """Format large numbers compactly."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _score_label(score):
    """Return (label, icon) for a score value."""
    if score < 0.25:
        return "Low", 'CHECKMARK'
    if score < 0.50:
        return "Medium", 'INFO'
    if score < 0.75:
        return "High", 'ERROR'
    return "Critical", 'CANCEL'


# --- Main Panel ---

class SCP_PT_Main(bpy.types.Panel):
    bl_label = "Scene Cost Profiler"
    bl_idname = "SCP_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Profiler"

    def draw(self, context):
        layout = self.layout
        scp = context.scene.scp

        row = layout.row(align=True)
        row.scale_y = 1.4
        row.operator("scp.analyze_scene", icon='VIEWZOOM')

        layout.prop(scp, "analyze_selection_only")

        if scp.is_analyzed:
            if scp.is_stale:
                layout.label(text="Results outdated — re-analyze",
                             icon='ERROR')
            else:
                layout.label(
                    text=f"Analyzed {scp.total_objects} objects in "
                         f"{scp.analysis_time_ms:.0f}ms",
                    icon='CHECKMARK',
                )
        else:
            layout.label(text="Not analyzed yet", icon='INFO')


# --- Summary ---

class SCP_PT_Summary(bpy.types.Panel):
    bl_label = "Scene Summary"
    bl_idname = "SCP_PT_summary"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Profiler"
    bl_parent_id = "SCP_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.scene.scp.is_analyzed

    def draw(self, context):
        layout = self.layout
        scp = context.scene.scp

        def _stat_row(label_text, value_text):
            row = layout.row()
            row.label(text=label_text)
            sub = row.row()
            sub.alignment = 'RIGHT'
            sub.label(text=value_text)

        _stat_row("Objects:", str(scp.total_objects))
        _stat_row("Vertices:", _format_count(scp.total_vertices))
        if scp.total_triangles_draw != scp.total_triangles:
            _stat_row("Tris (unique):", _format_count(scp.total_triangles))
            _stat_row("Tris (draw):", _format_count(scp.total_triangles_draw))
        else:
            _stat_row("Triangles:", _format_count(scp.total_triangles))

        vram_text = (f"{scp.total_vram_mb / 1024:.2f} GB" if scp.total_vram_mb >= 1024
                     else f"{scp.total_vram_mb:.1f} MB")
        _stat_row("VRAM (est.):", vram_text)
        if scp.total_vram_mb == 0 and scp.total_objects > 0:
            layout.label(text="No textures — VRAM is geometry only", icon='INFO')

        # High-cost object count
        if scp.budget_enabled:
            over_count = sum(1 for r in scp.object_results if r.exceeds_budget)
            if over_count > 0:
                row = layout.row()
                row.label(text="Over budget:", icon='ERROR')
                sub = row.row()
                sub.alignment = 'RIGHT'
                sub.label(text=str(over_count))

            # VRAM budget usage summary
            if scp.budget_max_vram_mb > 0:
                total_obj_vram = sum(
                    r.total_vram_mb for r in scp.object_results
                )
                pct = min(total_obj_vram / scp.budget_max_vram_mb * 100, 999)
                icon = 'ERROR' if pct > 100 else 'CHECKMARK'
                layout.label(
                    text=f"VRAM: {total_obj_vram:.0f} / "
                         f"{scp.budget_max_vram_mb:.0f} MB ({pct:.0f}%)",
                    icon=icon,
                )


# --- Budget ---

class SCP_PT_Budget(bpy.types.Panel):
    bl_label = "Performance Budget"
    bl_idname = "SCP_PT_budget"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Profiler"
    bl_parent_id = "SCP_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        self.layout.prop(context.scene.scp, "budget_enabled", text="")

    def draw(self, context):
        layout = self.layout
        scp = context.scene.scp
        layout.active = scp.budget_enabled

        layout.prop(scp, "budget_preset")

        col = layout.column(align=True)
        col.prop(scp, "budget_max_vram_mb")
        col.prop(scp, "budget_max_tris_per_object")
        col.prop(scp, "budget_max_shader_complexity", slider=True)

        layout.separator()
        layout.operator("scp.optimize_to_budget", icon='AUTO')


# --- Weights ---

class SCP_PT_Weights(bpy.types.Panel):
    bl_label = "Scoring Weights"
    bl_idname = "SCP_PT_weights"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Profiler"
    bl_parent_id = "SCP_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        self.layout.prop(context.scene.scp, "use_custom_weights", text="")

    def draw(self, context):
        layout = self.layout
        scp = context.scene.scp

        if scp.use_custom_weights:
            layout.active = True
            col = layout.column(align=True)
            col.prop(scp, "weight_geometry", slider=True)
            col.prop(scp, "weight_shader", slider=True)
            col.prop(scp, "weight_modifier", slider=True)
            col.prop(scp, "weight_texture", slider=True)
        else:
            layout.active = False
            from .. import get_preferences
            prefs = get_preferences()
            if prefs:
                col = layout.column(align=True)
                col.label(text=f"Geometry: {prefs.weight_geometry:.2f}")
                col.label(text=f"Shader: {prefs.weight_shader:.2f}")
                col.label(text=f"Modifier: {prefs.weight_modifier:.2f}")
                col.label(text=f"Texture: {prefs.weight_texture:.2f}")
                col.label(text="(from addon preferences)", icon='INFO')
            else:
                layout.label(text="Using defaults", icon='INFO')


# --- Object Rankings ---

class SCP_PT_ObjectList(bpy.types.Panel):
    bl_label = "Object Rankings"
    bl_idname = "SCP_PT_object_list"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Profiler"
    bl_parent_id = "SCP_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.scene.scp.is_analyzed

    def draw(self, context):
        layout = self.layout
        scp = context.scene.scp

        if len(scp.object_results) == 0:
            layout.label(text="No analyzable objects", icon='INFO')
            return

        # Sort controls
        row = layout.row(align=True)
        row.prop(scp, "sort_by", text="")
        row.prop(scp, "sort_descending", text="",
                 icon='SORT_DESC' if scp.sort_descending else 'SORT_ASC')

        # Filter
        row = layout.row(align=True)
        row.prop(scp, "filter_threshold", slider=True)

        # Column header
        sort_labels = {
            'COMBINED': "Score", 'GEOMETRY': "Geo Score",
            'SHADER': "Shader", 'MODIFIER': "Modifier",
            'VRAM': "VRAM", 'TRIANGLES': "Tris",
        }
        header = layout.row(align=True)
        header.label(text="Object")
        sub = header.row(align=True)
        sub.alignment = 'RIGHT'
        sub.label(text=sort_labels.get(scp.sort_by, "Score"))

        # Object list
        layout.template_list(
            "SCP_UL_object_results", "",
            scp, "object_results",
            scp, "object_results_index",
            rows=8,
        )

        # Select top N button
        layout.operator("scp.select_top_costly", icon='RESTRICT_SELECT_OFF')


# --- Object Detail ---

class SCP_PT_ObjectDetail(bpy.types.Panel):
    bl_label = "Object Detail"
    bl_idname = "SCP_PT_object_detail"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Profiler"
    bl_parent_id = "SCP_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        scp = context.scene.scp
        return scp.is_analyzed and len(scp.object_results) > 0

    def draw(self, context):
        layout = self.layout
        scp = context.scene.scp

        # Index -1 or out of range = active object not in results
        idx = scp.object_results_index
        if idx < 0 or idx >= len(scp.object_results):
            layout.label(text="Object not in analyzed scene",
                         icon='INFO')
            return

        result = scp.object_results[idx]

        # Stale pointer guard
        obj = result.object_ptr
        if obj is None:
            layout.label(text=f"{result.object_name} (removed)",
                         icon='GHOST_DISABLED')
            return

        row = layout.row()
        row.label(text=result.object_name, icon='OBJECT_DATA')
        row.label(text=obj.type, icon='MESH_DATA')

        # Score interpretation label
        label, icon = _score_label(result.combined_score)
        layout.label(
            text=f"Cost: {label} ({result.combined_score:.2f}) — relative to scene",
            icon=icon,
        )

        # Instance tag
        if result.is_instance:
            layout.label(text="Instanced — shared mesh data", icon='LINKED')

        # Budget violation indicator
        if scp.budget_enabled and result.exceeds_budget:
            layout.label(text="Exceeds performance budget", icon='ERROR')

        # Scores overview
        box = layout.box()
        box.label(text="Scores", icon='GRAPH')
        col = box.column(align=True)

        def _score_row(parent, label_text, value):
            row = parent.row()
            row.label(text=label_text)
            sub = row.row()
            sub.alignment = 'RIGHT'
            sub.label(text=f"{value:.2f}")

        _score_row(col, "Combined:", result.combined_score)
        _score_row(col, "Geometry:", result.geometry_score)
        _score_row(col, "Shader:", result.shader_score)
        _score_row(col, "Modifier:", result.modifier_score)
        _score_row(col, "VRAM:", result.texture_memory_score)

        # Geometry
        box = layout.box()
        box.label(text="Geometry", icon='MESH_DATA')

        def _detail_row(parent, label_text, value_text):
            row = parent.row()
            row.label(text=label_text)
            sub = row.row()
            sub.alignment = 'RIGHT'
            sub.label(text=value_text)

        col = box.column(align=True)
        _detail_row(col, "Vertices:", _format_count(result.vertex_count))
        _detail_row(col, "Edges:", _format_count(result.edge_count))
        _detail_row(col, "Faces:", _format_count(result.face_count))
        _detail_row(col, "Triangles:", _format_count(result.triangle_count))

        # Materials
        if len(result.materials) > 0:
            box = layout.box()
            box.label(text="Materials", icon='MATERIAL')
            for mat in result.materials:
                row = box.row()
                row.label(text=mat.material_name or "(unnamed)")
                row.label(text=f"Nodes: {mat.node_count}")
                row.label(text=f"Score: {mat.complexity_score:.2f}")

        # Modifiers
        if len(result.modifiers) > 0:
            box = layout.box()
            box.label(text="Modifiers", icon='MODIFIER')
            for mod in result.modifiers:
                row = box.row()
                icon = 'ERROR' if mod.is_high_cost else 'MODIFIER'
                row.label(text=mod.modifier_name, icon=icon)
                row.label(text=mod.modifier_type)
                row.label(text=f"{mod.cost_score:.2f}")

        # Textures
        if len(result.textures) > 0:
            box = layout.box()
            box.label(text="Textures", icon='TEXTURE')
            for tex in result.textures:
                row = box.row()
                row.label(text=tex.image_name)
                row.label(text=tex.resolution)
                row.label(text=f"{tex.vram_mb:.1f} MB")


# --- Heatmap ---

class SCP_PT_Heatmap(bpy.types.Panel):
    bl_label = "Heatmap Overlay"
    bl_idname = "SCP_PT_heatmap"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Profiler"
    bl_parent_id = "SCP_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.scene.scp.is_analyzed

    def draw(self, context):
        layout = self.layout
        scp = context.scene.scp

        # Check if we're in Solid shading mode
        shading_ok = False
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        if space.shading.type == 'SOLID':
                            shading_ok = True
                        break
                break

        row = layout.row()
        if scp.heatmap_active:
            row.operator("scp.toggle_heatmap", text="Disable Heatmap",
                         icon='HIDE_ON')
            if not shading_ok:
                layout.label(
                    text="Switch to Solid shading to see heatmap",
                    icon='ERROR',
                )
            # Metric selector
            layout.prop(scp, "heatmap_metric")

            # Range controls
            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop(scp, "heatmap_range_min")
            row.prop(scp, "heatmap_range_max")

            # Color legend
            col.scale_y = 0.8
            col.label(text=f"Green = Low cost ({scp.heatmap_range_min:.2f})")
            col.label(text=f"Red = High cost ({scp.heatmap_range_max:.2f})")
        else:
            layout.prop(scp, "heatmap_metric")
            row.operator("scp.toggle_heatmap", text="Enable Heatmap",
                         icon='HIDE_OFF')


# --- Optimization ---

class SCP_PT_Optimize(bpy.types.Panel):
    bl_label = "Optimization"
    bl_idname = "SCP_PT_optimize"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Profiler"
    bl_parent_id = "SCP_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.operator("scp.decimate_selected", icon='MOD_DECIM')
        row.operator("scp.remove_decimate", text="", icon='X')

        col = layout.column(align=True)
        col.operator("scp.reduce_subdivision", icon='MOD_SUBSURF')
        col.operator("scp.merge_vertices", icon='AUTOMERGE_ON')
        col.operator("scp.merge_materials", icon='MATERIAL')
        col.operator("scp.apply_modifiers", icon='CHECKMARK')


# --- Export ---

class SCP_PT_Export(bpy.types.Panel):
    bl_label = "Export"
    bl_idname = "SCP_PT_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Profiler"
    bl_parent_id = "SCP_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.scene.scp.is_analyzed

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.operator("scp.export_json", icon='FILE')
        col.operator("scp.export_csv", icon='FILE_TEXT')
