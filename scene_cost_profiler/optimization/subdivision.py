"""Reduce subdivision levels on objects."""


def reduce_subdivision(objects, target_level=1):
    """Reduce SUBSURF/MULTIRES viewport levels to at most target_level.

    Args:
        objects: Iterable of bpy.types.Object.
        target_level: Maximum viewport subdivision level to allow.

    Returns:
        Number of objects that had modifiers reduced.
    """
    count = 0
    for obj in objects:
        if obj.type != 'MESH' or obj.library is not None:
            continue
        modified = False
        for mod in obj.modifiers:
            if mod.type in ('SUBSURF', 'MULTIRES'):
                if mod.levels > target_level:
                    mod.levels = target_level
                    modified = True
        if modified:
            count += 1
    return count
