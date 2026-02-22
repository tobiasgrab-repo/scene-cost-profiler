"""Cache invalidation via depsgraph handler + active-object polling timer."""

import bpy


# --- Depsgraph handler (stale detection) ---

def _on_depsgraph_update(scene, depsgraph):
    """Mark analysis results as stale when scene changes."""
    scp = getattr(scene, 'scp', None)
    if scp is None or not scp.is_analyzed:
        return

    for update in depsgraph.updates:
        if update.is_updated_geometry or update.is_updated_transform:
            scp.is_stale = True
            return
        if isinstance(update.id, (bpy.types.Object, bpy.types.Mesh,
                                  bpy.types.Material)):
            scp.is_stale = True
            return


# --- Timer: sync viewport active object → object_results_index ---

_last_active_name = [None]
_timer_registered = [False]


def _tag_sidebar_redraw():
    """Force the 3D viewport sidebar (N-panel) to redraw."""
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    for region in area.regions:
                        if region.type == 'UI':
                            region.tag_redraw()
    except Exception:
        pass


def _poll_active_object():
    """Timer callback: sync viewport active object to rankings index."""
    context = bpy.context
    scene = getattr(context, 'scene', None)
    if scene is None:
        return 0.1

    scp = getattr(scene, 'scp', None)
    if scp is None or not scp.is_analyzed:
        return 0.1

    view_layer = getattr(context, 'view_layer', None)
    active = view_layer.objects.active if view_layer else None
    active_name = active.name if active else None

    if active_name != _last_active_name[0]:
        _last_active_name[0] = active_name
        if active_name:
            found = False
            for i, r in enumerate(scp.object_results):
                if r.object_name == active_name:
                    scp.object_results_index = i
                    found = True
                    break
            if not found:
                scp.object_results_index = -1
        else:
            scp.object_results_index = -1

        # Force sidebar to redraw immediately
        _tag_sidebar_redraw()

    return 0.1  # poll every 100ms


def invalidate_active_cache():
    """Reset the cached active object name so the timer re-syncs on next poll."""
    _last_active_name[0] = None


def register_handlers():
    """Register depsgraph update handler and active-object timer."""
    if _on_depsgraph_update not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_on_depsgraph_update)
    if not _timer_registered[0]:
        bpy.app.timers.register(_poll_active_object, persistent=True)
        _timer_registered[0] = True


def unregister_handlers():
    """Remove depsgraph update handler and active-object timer."""
    if _on_depsgraph_update in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_on_depsgraph_update)
    if _timer_registered[0]:
        if bpy.app.timers.is_registered(_poll_active_object):
            bpy.app.timers.unregister(_poll_active_object)
        _timer_registered[0] = False
