"""Scene Cost Profiler & Auto-Optimizer — Blender Add-on.

Analyzes scene performance cost at the object, material, texture,
and modifier levels. Provides heatmap visualization and optimization tools.
"""

bl_info = {
    "name": "Scene Cost Profiler",
    "author": "tobiasgrab-repo",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Profiler",
    "description": "Analyze scene performance cost and optimize objects",
    "warning": "",
    "doc_url": "",
    "category": "3D View",
}

import bpy

# The addon module name varies between legacy addons and Blender 5.0 extensions:
#   Legacy:    "scene_cost_profiler"
#   Extension: "bl_ext.user_default.scene_cost_profiler"
ADDON_MODULE_NAME = __package__


def get_preferences():
    """Get addon preferences safely, returns None if unavailable."""
    try:
        return bpy.context.preferences.addons[ADDON_MODULE_NAME].preferences
    except (KeyError, AttributeError):
        return None


def register():
    from . import data
    from . import ui
    from .utils import cache

    # 1. PropertyGroups first (other classes depend on them)
    data.register()

    # 2. Operators, UILists, Panels
    ui.register()

    # 3. Attach scene properties
    bpy.types.Scene.scp = bpy.props.PointerProperty(
        type=data.properties.SCP_SceneProperties
    )

    # 4. Register depsgraph handler
    cache.register_handlers()


def unregister():
    from . import data
    from . import ui
    from .utils import cache
    from .visualization import heatmap

    # Clean up heatmap if active
    try:
        for scene in bpy.data.scenes:
            if hasattr(scene, 'scp') and scene.scp.heatmap_active:
                heatmap.remove_heatmap(bpy.context)
    except Exception:
        pass

    # Reverse order
    cache.unregister_handlers()

    if hasattr(bpy.types.Scene, 'scp'):
        del bpy.types.Scene.scp

    ui.unregister()
    data.unregister()


if __name__ == "__main__":
    register()
