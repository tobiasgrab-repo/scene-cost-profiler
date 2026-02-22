"""Material and shader complexity analysis."""

from ..data.models import MaterialMetrics
from ..utils.constants import (
    NODE_WEIGHT_DEFAULT,
    NODE_WEIGHT_TEXTURE,
    NODE_WEIGHT_MATH,
    NODE_WEIGHT_PROCEDURAL,
    MAX_SHADER_COMPLEXITY,
    PROCEDURAL_NOISE_TYPES,
    MATH_NODE_TYPES,
)


def analyze_material(mat):
    """Analyze a single material's shader complexity.

    Args:
        mat: bpy.types.Material to analyze.

    Returns:
        MaterialMetrics with complexity score.
    """
    metrics = MaterialMetrics(material_name=mat.name if mat else "")

    if mat is None or mat.node_tree is None:
        return metrics

    nodes = mat.node_tree.nodes
    metrics.total_node_count = len(nodes)

    for node in nodes:
        if node.type == 'TEX_IMAGE':
            metrics.texture_node_count += 1
        elif node.type in MATH_NODE_TYPES:
            metrics.math_node_count += 1
        elif node.type in PROCEDURAL_NOISE_TYPES:
            metrics.procedural_noise_count += 1

    # Weighted complexity
    raw = (
        metrics.total_node_count * NODE_WEIGHT_DEFAULT
        + metrics.texture_node_count * NODE_WEIGHT_TEXTURE
        + metrics.math_node_count * NODE_WEIGHT_MATH
        + metrics.procedural_noise_count * NODE_WEIGHT_PROCEDURAL
    )
    metrics.complexity_score = min(raw / MAX_SHADER_COMPLEXITY, 1.0)

    return metrics


def analyze_materials(obj):
    """Analyze all materials on an object.

    Args:
        obj: bpy.types.Object to analyze.

    Returns:
        List of MaterialMetrics.
    """
    results = []

    materials = getattr(obj.data, 'materials', None) if obj.data else None
    if materials is None:
        return results

    for mat in materials:
        results.append(analyze_material(mat))

    return results


def compute_shader_score(materials):
    """Compute object-level shader score from material list.

    Args:
        materials: List of MaterialMetrics.

    Returns:
        Float in [0.0, 1.0] — average complexity across materials.
    """
    if not materials:
        return 0.0

    total = sum(m.complexity_score for m in materials)
    return min(total / len(materials), 1.0)
