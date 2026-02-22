"""Operators for the Scene Cost Profiler."""

import os

import bpy
from bpy.props import FloatProperty, IntProperty, StringProperty, EnumProperty


def _mesh_count(context):
    """Count mesh objects in selection (for dialog info)."""
    return sum(1 for obj in context.selected_objects if obj.type == 'MESH')


class SCP_OT_AnalyzeScene(bpy.types.Operator):
    """Analyze all objects in the scene for performance cost"""
    bl_idname = "scp.analyze_scene"
    bl_label = "Analyze Scene"
    bl_options = {'REGISTER'}

    def execute(self, context):
        from ..analysis import analyze_scene, write_results_to_properties
        from ..utils.cache import invalidate_active_cache

        result = analyze_scene(context)
        write_results_to_properties(context, result)

        # Force re-sync of active object → rankings index
        invalidate_active_cache()

        self.report(
            {'INFO'},
            f"Analyzed {result.total_objects} objects in {result.analysis_time_ms:.0f}ms"
        )
        return {'FINISHED'}


class SCP_OT_ExportJSON(bpy.types.Operator):
    """Export analysis results as a JSON report"""
    bl_idname = "scp.export_json"
    bl_label = "Export JSON Report"
    bl_options = {'REGISTER'}

    filepath: StringProperty(
        subtype='FILE_PATH',
        default="scene_report.json",
    )

    filter_glob: StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )

    def invoke(self, context, event):
        # Default filename from blend file, without .blend extension
        if bpy.data.filepath:
            base = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
            self.filepath = base + ".json"
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        from ..utils.export import export_json
        export_json(context, self.filepath)
        self.report({'INFO'}, f"Report exported to {self.filepath}")
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return context.scene.scp.is_analyzed


class SCP_OT_ToggleHeatmap(bpy.types.Operator):
    """Toggle performance heatmap overlay on objects"""
    bl_idname = "scp.toggle_heatmap"
    bl_label = "Toggle Heatmap"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from ..visualization.heatmap import toggle_heatmap
        toggle_heatmap(context)
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return context.scene.scp.is_analyzed


class SCP_OT_DecimateSelected(bpy.types.Operator):
    """Add a Decimate modifier to selected mesh objects"""
    bl_idname = "scp.decimate_selected"
    bl_label = "Decimate Selected"
    bl_options = {'REGISTER', 'UNDO'}

    ratio: FloatProperty(
        name="Ratio",
        default=0.5, min=0.01, max=1.0,
        description="Target ratio of faces to keep",
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        from ..optimization.decimate import decimate_objects
        count = decimate_objects(context, context.selected_objects, self.ratio)
        if count > 0:
            self.report({'INFO'}, f"Added Decimate modifier to {count} object(s)")
        else:
            self.report({'WARNING'}, "No mesh objects selected")
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return any(obj.type == 'MESH' for obj in context.selected_objects)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Affects {_mesh_count(context)} mesh object(s)")
        layout.prop(self, "ratio", slider=True)


class SCP_OT_SelectObject(bpy.types.Operator):
    """Select an object from the profiler list"""
    bl_idname = "scp.select_object"
    bl_label = "Select Object"
    bl_options = {'REGISTER', 'UNDO'}

    object_name: StringProperty()

    def execute(self, context):
        obj = context.scene.objects.get(self.object_name)
        if obj:
            # Exit edit mode first if active
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj

        # Sync the detail panel to show this object
        scp = context.scene.scp
        for i, result in enumerate(scp.object_results):
            if result.object_name == self.object_name:
                scp.object_results_index = i
                break
        return {'FINISHED'}


class SCP_OT_RemoveDecimate(bpy.types.Operator):
    """Remove SCP Decimate modifiers from selected objects"""
    bl_idname = "scp.remove_decimate"
    bl_label = "Remove Decimate"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from ..optimization.decimate import remove_decimate
        count = 0
        for obj in context.selected_objects:
            if remove_decimate(obj):
                count += 1
        if count > 0:
            self.report({'INFO'}, f"Removed Decimate from {count} object(s)")
        else:
            self.report({'WARNING'}, "No SCP Decimate modifiers found")
        return {'FINISHED'}


class SCP_OT_ReduceSubdivision(bpy.types.Operator):
    """Reduce SUBSURF/MULTIRES viewport levels on selected objects"""
    bl_idname = "scp.reduce_subdivision"
    bl_label = "Reduce Subdivision"
    bl_options = {'REGISTER', 'UNDO'}

    target_level: IntProperty(
        name="Target Level",
        default=1, min=0, max=6,
        description="Maximum viewport subdivision level",
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        from ..optimization.subdivision import reduce_subdivision
        count = reduce_subdivision(context.selected_objects, self.target_level)
        if count > 0:
            self.report({'INFO'}, f"Reduced subdivision on {count} object(s)")
        else:
            self.report({'WARNING'}, "No subdivision modifiers to reduce")
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return any(obj.type == 'MESH' for obj in context.selected_objects)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Affects {_mesh_count(context)} mesh object(s)")
        layout.prop(self, "target_level")


class SCP_OT_MergeDuplicateVertices(bpy.types.Operator):
    """Merge duplicate vertices on selected objects via bmesh"""
    bl_idname = "scp.merge_vertices"
    bl_label = "Merge Duplicate Vertices"
    bl_options = {'REGISTER', 'UNDO'}

    threshold: FloatProperty(
        name="Threshold",
        default=0.001, min=0.0, max=100.0,
        soft_max=1.0,
        precision=4,
        description="Merge distance in meters — vertices closer than this get merged into one",
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        from ..optimization.merge_verts import merge_duplicate_vertices
        modified, merged = merge_duplicate_vertices(
            context.selected_objects, self.threshold
        )
        if modified > 0:
            self.report(
                {'INFO'},
                f"Merged {merged} vertices on {modified} object(s)"
            )
        else:
            self.report({'WARNING'}, "No vertices to merge")
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return any(obj.type == 'MESH' for obj in context.selected_objects)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Affects {_mesh_count(context)} mesh object(s)")
        layout.prop(self, "threshold")


class SCP_OT_MergeIdenticalMaterials(bpy.types.Operator):
    """Find and consolidate identical materials scene-wide"""
    bl_idname = "scp.merge_materials"
    bl_label = "Merge Identical Materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from ..optimization.merge_materials import merge_identical_materials
        removed, groups, descriptions = merge_identical_materials()
        if removed > 0:
            detail = ", ".join(descriptions[:5])
            if len(descriptions) > 5:
                detail += f" (+{len(descriptions) - 5} more)"
            self.report(
                {'INFO'},
                f"Merged {removed} slot(s) in {groups} group(s): {detail}"
            )
        else:
            self.report({'INFO'}, "No identical materials found")
        return {'FINISHED'}


class SCP_OT_ApplyModifiers(bpy.types.Operator):
    """Apply high-cost modifiers on selected objects"""
    bl_idname = "scp.apply_modifiers"
    bl_label = "Apply Modifiers"
    bl_options = {'REGISTER', 'UNDO'}

    apply_type: EnumProperty(
        name="Type",
        items=[
            ('ALL_HIGH_COST', "All High-Cost",
             "Apply all high-cost modifiers (Subsurf, Boolean, Remesh, etc.)"),
            ('BOOLEAN', "Boolean Only", "Apply only Boolean modifiers"),
            ('REMESH', "Remesh Only", "Apply only Remesh modifiers"),
        ],
        default='ALL_HIGH_COST',
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        from ..optimization.apply_modifiers import apply_modifiers
        count = apply_modifiers(context, context.selected_objects, self.apply_type)
        if count > 0:
            self.report({'INFO'}, f"Applied {count} modifier(s)")
        else:
            self.report({'WARNING'}, "No matching modifiers to apply")
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return any(obj.type == 'MESH' for obj in context.selected_objects)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Affects {_mesh_count(context)} mesh object(s)")
        layout.prop(self, "apply_type")


class SCP_OT_OptimizeToBudget(bpy.types.Operator):
    """Auto-decimate objects that exceed the performance budget"""
    bl_idname = "scp.optimize_to_budget"
    bl_label = "Optimize to Budget"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from ..optimization.decimate import decimate_objects
        scp = context.scene.scp

        over_budget = []
        for entry in scp.object_results:
            if not entry.exceeds_budget:
                continue
            obj = entry.object_ptr
            if obj is None or obj.library is not None:
                continue
            if obj.type != 'MESH':
                continue
            # Compute ratio: target tris / current tris
            if entry.triangle_count > scp.budget_max_tris_per_object > 0:
                ratio = scp.budget_max_tris_per_object / entry.triangle_count
                ratio = max(ratio, 0.01)
            else:
                ratio = 0.5
            over_budget.append((obj, ratio))

        if not over_budget:
            self.report({'INFO'}, "No objects exceed the budget")
            return {'FINISHED'}

        total = 0
        for obj, ratio in over_budget:
            count = decimate_objects(context, [obj], ratio)
            total += count

        self.report(
            {'INFO'},
            f"Added Decimate to {total} over-budget object(s)"
        )
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        scp = context.scene.scp
        return scp.is_analyzed and scp.budget_enabled


class SCP_OT_ExportCSV(bpy.types.Operator):
    """Export analysis results as a CSV file"""
    bl_idname = "scp.export_csv"
    bl_label = "Export CSV Report"
    bl_options = {'REGISTER'}

    filepath: StringProperty(
        subtype='FILE_PATH',
        default="scene_report.csv",
    )

    filter_glob: StringProperty(
        default="*.csv",
        options={'HIDDEN'},
    )

    def invoke(self, context, event):
        if bpy.data.filepath:
            base = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
            self.filepath = base + ".csv"
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        from ..utils.export import export_csv
        export_csv(context, self.filepath)
        self.report({'INFO'}, f"CSV exported to {self.filepath}")
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return context.scene.scp.is_analyzed


class SCP_OT_SelectTopCostly(bpy.types.Operator):
    """Select the N most expensive objects in the scene"""
    bl_idname = "scp.select_top_costly"
    bl_label = "Select Top Costly"
    bl_options = {'REGISTER', 'UNDO'}

    count: IntProperty(
        name="Count",
        default=5, min=1, max=100,
        description="Number of top costly objects to select",
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        scp = context.scene.scp
        # Sort results by combined score descending
        ranked = sorted(
            scp.object_results,
            key=lambda r: r.combined_score,
            reverse=True,
        )

        bpy.ops.object.select_all(action='DESELECT')
        selected = 0
        for entry in ranked[:self.count]:
            obj = entry.object_ptr
            if obj is None:
                continue
            obj.select_set(True)
            selected += 1

        if selected > 0:
            # Make the top one active
            top_obj = ranked[0].object_ptr
            if top_obj:
                context.view_layer.objects.active = top_obj

        self.report({'INFO'}, f"Selected {selected} object(s)")
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return context.scene.scp.is_analyzed

    def draw(self, context):
        self.layout.prop(self, "count")
