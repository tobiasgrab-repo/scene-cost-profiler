"""Merge duplicate vertices via bmesh."""

import bpy
import bmesh


def merge_duplicate_vertices(objects, threshold=0.0001):
    """Remove duplicate vertices within a distance threshold.

    Ensures object mode before operating. Skips multi-user meshes
    (mesh.users > 1) to avoid shared data issues.

    Args:
        objects: Iterable of bpy.types.Object.
        threshold: Merge distance.

    Returns:
        Tuple of (objects_modified, total_verts_merged).
    """
    # Must be in object mode for bmesh to read committed mesh data
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    objects_modified = 0
    total_merged = 0

    for obj in objects:
        if obj.type != 'MESH' or obj.library is not None:
            continue
        if obj.data.users > 1:
            # Make single-user copy so we don't affect other linked objects
            obj.data = obj.data.copy()
        mesh = obj.data

        bm = bmesh.new()
        bm.from_mesh(mesh)
        before = len(bm.verts)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=threshold)
        after = len(bm.verts)
        merged = before - after

        if merged > 0:
            bm.to_mesh(mesh)
            mesh.update()
            objects_modified += 1
            total_merged += merged

        bm.free()

    return objects_modified, total_merged
