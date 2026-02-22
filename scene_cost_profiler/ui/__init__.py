"""UI registration: operators, lists, panels."""

from .operators import (
    SCP_OT_AnalyzeScene,
    SCP_OT_ExportJSON,
    SCP_OT_ToggleHeatmap,
    SCP_OT_DecimateSelected,
    SCP_OT_SelectObject,
    SCP_OT_RemoveDecimate,
    SCP_OT_ReduceSubdivision,
    SCP_OT_MergeDuplicateVertices,
    SCP_OT_MergeIdenticalMaterials,
    SCP_OT_ApplyModifiers,
    SCP_OT_OptimizeToBudget,
    SCP_OT_ExportCSV,
    SCP_OT_SelectTopCostly,
)
from .lists import SCP_UL_ObjectResults
from .panels import (
    SCP_PT_Main,
    SCP_PT_Summary,
    SCP_PT_ObjectList,
    SCP_PT_ObjectDetail,
    SCP_PT_Heatmap,
    SCP_PT_Optimize,
    SCP_PT_Export,
    SCP_PT_Budget,
    SCP_PT_Weights,
)

# Registration order: operators first, then UILists, then panels
_classes = (
    SCP_OT_AnalyzeScene,
    SCP_OT_ExportJSON,
    SCP_OT_ToggleHeatmap,
    SCP_OT_DecimateSelected,
    SCP_OT_SelectObject,
    SCP_OT_RemoveDecimate,
    SCP_OT_ReduceSubdivision,
    SCP_OT_MergeDuplicateVertices,
    SCP_OT_MergeIdenticalMaterials,
    SCP_OT_ApplyModifiers,
    SCP_OT_OptimizeToBudget,
    SCP_OT_ExportCSV,
    SCP_OT_SelectTopCostly,
    SCP_UL_ObjectResults,
    # Panels: results first, then config, then actions
    SCP_PT_Main,
    SCP_PT_Summary,
    SCP_PT_ObjectList,
    SCP_PT_ObjectDetail,
    SCP_PT_Heatmap,
    SCP_PT_Budget,
    SCP_PT_Weights,
    SCP_PT_Optimize,
    SCP_PT_Export,
)


def register():
    from bpy.utils import register_class
    for cls in _classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(_classes):
        unregister_class(cls)
