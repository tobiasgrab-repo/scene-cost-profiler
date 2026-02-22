"""JSON and CSV export for analysis reports."""

import csv
import json
import time
import bpy


def build_report(context):
    """Build a JSON-serializable report dict from scene properties.

    Args:
        context: bpy.types.Context.

    Returns:
        Dict ready for json.dump().
    """
    scp = context.scene.scp

    # Get weights from preferences
    from .. import get_preferences
    prefs = get_preferences()
    if prefs:
        weights = {
            "geometry": round(prefs.weight_geometry, 3),
            "shader": round(prefs.weight_shader, 3),
            "modifier": round(prefs.weight_modifier, 3),
            "texture_memory": round(prefs.weight_texture, 3),
        }
    else:
        weights = {
            "geometry": 0.3, "shader": 0.25,
            "modifier": 0.2, "texture_memory": 0.25,
        }

    report = {
        "format_version": "1.0",
        "generator": "Scene Cost Profiler",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "blend_file": bpy.data.filepath or "(unsaved)",
        "scoring_weights": weights,
        "scene_summary": {
            "total_objects_analyzed": scp.total_objects,
            "total_vertices": scp.total_vertices,
            "total_triangles": scp.total_triangles,
            "total_vram_mb": round(scp.total_vram_mb, 2),
            "analysis_time_ms": round(scp.analysis_time_ms, 1),
        },
        "objects": [],
    }

    for result in scp.object_results:
        obj_entry = {
            "name": result.object_name,
            "scores": {
                "combined": round(result.combined_score, 4),
                "geometry": round(result.geometry_score, 4),
                "shader": round(result.shader_score, 4),
                "modifier": round(result.modifier_score, 4),
                "texture_memory": round(result.texture_memory_score, 4),
            },
            "geometry": {
                "vertices": result.vertex_count,
                "edges": result.edge_count,
                "faces": result.face_count,
                "triangles": result.triangle_count,
            },
            "vram_mb": round(result.total_vram_mb, 2),
            "textures": [],
            "modifiers": [],
            "materials": [],
        }

        for tex in result.textures:
            obj_entry["textures"].append({
                "name": tex.image_name,
                "resolution": tex.resolution,
                "vram_mb": round(tex.vram_mb, 2),
                "bit_depth": tex.bit_depth,
            })

        for mod in result.modifiers:
            obj_entry["modifiers"].append({
                "name": mod.modifier_name,
                "type": mod.modifier_type,
                "high_cost": mod.is_high_cost,
                "cost_score": round(mod.cost_score, 3),
            })

        for mat in result.materials:
            obj_entry["materials"].append({
                "name": mat.material_name,
                "node_count": mat.node_count,
                "texture_count": mat.texture_count,
                "procedural_count": mat.noise_count,
                "complexity_score": round(mat.complexity_score, 3),
            })

        report["objects"].append(obj_entry)

    # Sort by combined score descending
    report["objects"].sort(
        key=lambda x: x["scores"]["combined"], reverse=True
    )

    return report


def export_json(context, filepath):
    """Write JSON report to file.

    Args:
        context: bpy.types.Context.
        filepath: Output file path.
    """
    report = build_report(context)

    if not filepath.endswith(".json"):
        filepath += ".json"

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def export_csv(context, filepath):
    """Write CSV report with one row per analyzed object.

    Columns: object_name, combined_score, geometry_score, shader_score,
    modifier_score, texture_memory_score, vertex_count, edge_count,
    face_count, triangle_count, vram_mb, material_count, modifier_count,
    texture_count, exceeds_budget.

    Sorted by combined score descending.

    Args:
        context: bpy.types.Context.
        filepath: Output file path.
    """
    scp = context.scene.scp

    if not filepath.endswith(".csv"):
        filepath += ".csv"

    fieldnames = [
        "object_name", "combined_score", "geometry_score", "shader_score",
        "modifier_score", "texture_memory_score", "vertex_count",
        "edge_count", "face_count", "triangle_count", "vram_mb",
        "material_count", "modifier_count", "texture_count",
        "exceeds_budget",
    ]

    # Sort by combined score descending
    results = sorted(
        scp.object_results,
        key=lambda r: r.combined_score,
        reverse=True,
    )

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "object_name": r.object_name,
                "combined_score": round(r.combined_score, 4),
                "geometry_score": round(r.geometry_score, 4),
                "shader_score": round(r.shader_score, 4),
                "modifier_score": round(r.modifier_score, 4),
                "texture_memory_score": round(r.texture_memory_score, 4),
                "vertex_count": r.vertex_count,
                "edge_count": r.edge_count,
                "face_count": r.face_count,
                "triangle_count": r.triangle_count,
                "vram_mb": round(r.total_vram_mb, 2),
                "material_count": len(r.materials),
                "modifier_count": len(r.modifiers),
                "texture_count": len(r.textures),
                "exceeds_budget": r.exceeds_budget,
            })
