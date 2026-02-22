"""Merge identical materials across the scene."""

import bpy


def _material_fingerprint(mat):
    """Create a hashable fingerprint from a material's node graph structure."""
    if mat.node_tree is None:
        return ("empty",)

    nodes = frozenset(node.type for node in mat.node_tree.nodes)
    links = frozenset(
        (link.from_node.type, link.to_node.type)
        for link in mat.node_tree.links
    )
    return (nodes, links)


def _deduplicate_slots(obj):
    """Remove material slots that point to the same material, keeping the first.

    Remaps face material indices so faces stay assigned to the correct material.
    Returns the number of slots removed.
    """
    mats = obj.data.materials
    if len(mats) <= 1:
        return 0

    # Build mapping: for each slot index, which index should it map to?
    # (first occurrence of that material)
    first_index = {}  # material name -> first slot index
    remap = {}        # old index -> new index (after removals)
    keep_indices = []

    for i, mat in enumerate(mats):
        key = mat.name if mat else None
        if key not in first_index:
            first_index[key] = len(keep_indices)
            keep_indices.append(i)
            remap[i] = len(keep_indices) - 1
        else:
            remap[i] = first_index[key]

    removed_count = len(mats) - len(keep_indices)
    if removed_count == 0:
        return 0

    # Remap face material indices
    mesh = obj.data
    for poly in mesh.polygons:
        old_idx = poly.material_index
        if old_idx in remap:
            poly.material_index = remap[old_idx]

    # Remove duplicate slots (back to front)
    keep_set = set(keep_indices)
    for i in range(len(mats) - 1, -1, -1):
        if i not in keep_set:
            mats.pop(index=i)

    return removed_count


def merge_identical_materials():
    """Find materials with identical node graph structure and consolidate them.

    Picks the first alphabetically as canonical for each group, then remaps
    all material slots on all objects to use the canonical material.
    After remapping, removes redundant duplicate slots from each object.

    Returns:
        Tuple of (slots_removed, unique_groups_found, merge_descriptions).
        merge_descriptions is a list of strings like "Mat.002 -> Mat.001".
    """
    # Group materials by fingerprint
    groups = {}
    for mat in bpy.data.materials:
        fp = _material_fingerprint(mat)
        groups.setdefault(fp, []).append(mat)

    slots_remapped = 0
    unique_groups = 0
    descriptions = []

    for fp, mats in groups.items():
        if len(mats) <= 1:
            continue
        unique_groups += 1
        # Sort alphabetically, pick first as canonical
        mats.sort(key=lambda m: m.name)
        canonical = mats[0]
        duplicates = mats[1:]

        for dup in duplicates:
            descriptions.append(f"{dup.name} -> {canonical.name}")

        # Remap all objects using duplicate materials
        for obj in bpy.data.objects:
            if not hasattr(obj.data, 'materials'):
                continue
            for i, slot_mat in enumerate(obj.data.materials):
                if slot_mat in duplicates:
                    obj.data.materials[i] = canonical
                    slots_remapped += 1

    # Second pass: remove duplicate slots per object
    slots_removed = 0
    for obj in bpy.data.objects:
        if obj.library is not None:
            continue
        if not hasattr(obj.data, 'materials') or obj.type != 'MESH':
            continue
        slots_removed += _deduplicate_slots(obj)

    total_removed = slots_remapped + slots_removed
    return total_removed, unique_groups, descriptions
