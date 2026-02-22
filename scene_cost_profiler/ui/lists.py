"""UIList for object rankings."""

import bpy


def _severity_icon(score):
    """Return an icon based on score severity."""
    if score < 0.25:
        return 'CHECKMARK'
    if score < 0.50:
        return 'INFO'
    if score < 0.75:
        return 'ERROR'
    return 'CANCEL'


def _format_sort_value(item, sort_by):
    """Return a formatted string for the sort-relevant metric."""
    if sort_by == 'TRIANGLES':
        n = item.triangle_count
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n // 1_000}k"
        return str(n)
    if sort_by == 'VRAM':
        if item.total_vram_mb >= 1.0:
            return f"{item.total_vram_mb:.0f}MB"
        if item.total_vram_mb > 0:
            return f"{item.total_vram_mb:.1f}MB"
        return "-"
    # Score-based sorts
    attr = {
        'COMBINED': 'combined_score',
        'GEOMETRY': 'geometry_score',
        'SHADER': 'shader_score',
        'MODIFIER': 'modifier_score',
    }.get(sort_by, 'combined_score')
    return f"{getattr(item, attr):.2f}"


class SCP_UL_ObjectResults(bpy.types.UIList):
    """UIList showing analyzed objects ranked by score."""
    bl_idname = "SCP_UL_object_results"

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_property, index):
        scp = context.scene.scp

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)

            # Object name — budget ERROR takes priority, otherwise severity icon
            if item.exceeds_budget:
                icon = 'ERROR'
            else:
                icon = _severity_icon(item.combined_score)
            op = row.operator("scp.select_object", text=item.object_name,
                              icon=icon, emboss=False)
            op.object_name = item.object_name

            # Sort-relevant value (right-aligned)
            sub = row.row(align=True)
            sub.alignment = 'RIGHT'
            sub.label(text=_format_sort_value(item, scp.sort_by))

        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text=item.object_name, icon='OBJECT_DATA')

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        scp = context.scene.scp

        # Filtering by score threshold
        flt_flags = [self.bitflag_filter_item] * len(items)
        for i, item in enumerate(items):
            if item.combined_score < scp.filter_threshold:
                flt_flags[i] = 0

        # Sorting is handled by physically reordering the collection
        # (via _sort_results_update callback on sort_by/sort_descending)
        flt_neworder = list(range(len(items)))

        return flt_flags, flt_neworder
