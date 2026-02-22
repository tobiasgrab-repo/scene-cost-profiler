"""Data layer: dataclasses and Blender PropertyGroups."""

from .properties import (
    SCP_TextureEntry,
    SCP_ModifierEntry,
    SCP_MaterialEntry,
    SCP_ObjectResult,
    SCP_SceneProperties,
    SCP_AddonPreferences,
)

_classes = (
    SCP_TextureEntry,
    SCP_ModifierEntry,
    SCP_MaterialEntry,
    SCP_ObjectResult,
    SCP_SceneProperties,
    SCP_AddonPreferences,
)


def register():
    from bpy.utils import register_class
    for cls in _classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(_classes):
        unregister_class(cls)
