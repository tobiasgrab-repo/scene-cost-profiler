"""Geometry analysis: vertex, edge, face, and triangle counts."""

import bpy
from ..data.models import GeometryMetrics


def analyze_geometry(obj, depsgraph=None):
    """Compute geometry metrics for an object.

    Args:
        obj: bpy.types.Object to analyze.
        depsgraph: Evaluated dependency graph. Required for non-mesh types.

    Returns:
        GeometryMetrics with counts populated.
    """
    metrics = GeometryMetrics()

    if obj.type == 'MESH':
        base_mesh = obj.data

        # Detect instanced (shared) mesh data (from the base mesh)
        metrics.is_instance = base_mesh.users > 1
        metrics.mesh_datablock = base_mesh.name

        # Use evaluated mesh (with modifiers applied) when depsgraph available
        if depsgraph and obj.modifiers:
            try:
                eval_obj = obj.evaluated_get(depsgraph)
                mesh = eval_obj.to_mesh()
                if mesh:
                    metrics.vertex_count = len(mesh.vertices)
                    metrics.edge_count = len(mesh.edges)
                    metrics.face_count = len(mesh.polygons)
                    mesh.calc_loop_triangles()
                    metrics.triangle_count = len(mesh.loop_triangles)
                    eval_obj.to_mesh_clear()
                else:
                    # Fallback to base mesh
                    metrics.vertex_count = len(base_mesh.vertices)
                    metrics.edge_count = len(base_mesh.edges)
                    metrics.face_count = len(base_mesh.polygons)
                    base_mesh.calc_loop_triangles()
                    metrics.triangle_count = len(base_mesh.loop_triangles)
            except RuntimeError:
                metrics.vertex_count = len(base_mesh.vertices)
                metrics.edge_count = len(base_mesh.edges)
                metrics.face_count = len(base_mesh.polygons)
                base_mesh.calc_loop_triangles()
                metrics.triangle_count = len(base_mesh.loop_triangles)
        else:
            metrics.vertex_count = len(base_mesh.vertices)
            metrics.edge_count = len(base_mesh.edges)
            metrics.face_count = len(base_mesh.polygons)
            base_mesh.calc_loop_triangles()
            metrics.triangle_count = len(base_mesh.loop_triangles)

    elif obj.type in {'CURVE', 'SURFACE', 'META', 'FONT'} and depsgraph:
        # Evaluate to get the actual mesh representation
        try:
            eval_obj = obj.evaluated_get(depsgraph)
            mesh = eval_obj.to_mesh()
            if mesh:
                metrics.vertex_count = len(mesh.vertices)
                metrics.edge_count = len(mesh.edges)
                metrics.face_count = len(mesh.polygons)

                mesh.calc_loop_triangles()
                metrics.triangle_count = len(mesh.loop_triangles)

                eval_obj.to_mesh_clear()
        except RuntimeError:
            pass  # Object cannot be converted to mesh

    return metrics
