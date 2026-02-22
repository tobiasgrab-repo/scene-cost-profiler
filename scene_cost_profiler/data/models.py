"""Pure Python dataclasses for analysis results.

These are the computation layer — not stored in Blender, used transiently
during analysis, then flattened into PropertyGroups for UI display.
"""

from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class GeometryMetrics:
    vertex_count: int = 0
    edge_count: int = 0
    face_count: int = 0
    triangle_count: int = 0
    is_instance: bool = False
    mesh_datablock: str = ""


@dataclass
class TextureInfo:
    image_name: str = ""
    filepath: str = ""
    width: int = 0
    height: int = 0
    bit_depth: int = 8
    channels: int = 4
    vram_bytes: int = 0
    is_packed: bool = False


@dataclass
class MaterialMetrics:
    material_name: str = ""
    total_node_count: int = 0
    texture_node_count: int = 0
    math_node_count: int = 0
    procedural_noise_count: int = 0
    complexity_score: float = 0.0
    textures: List[TextureInfo] = field(default_factory=list)


@dataclass
class ModifierInfo:
    modifier_name: str = ""
    modifier_type: str = ""
    is_high_cost: bool = False
    viewport_level: int = 0
    render_level: int = 0
    cost_score: float = 0.0


@dataclass
class ObjectAnalysis:
    object_name: str = ""
    object_type: str = ""
    geometry: GeometryMetrics = field(default_factory=GeometryMetrics)
    materials: List[MaterialMetrics] = field(default_factory=list)
    modifiers: List[ModifierInfo] = field(default_factory=list)
    geometry_score: float = 0.0
    shader_score: float = 0.0
    modifier_score: float = 0.0
    texture_memory_score: float = 0.0
    combined_score: float = 0.0
    total_vram_bytes: int = 0


@dataclass
class SceneMaximums:
    """Track maximum values across all objects for normalization."""
    max_triangles: int = 0
    max_vram_bytes: int = 0
    max_shader_complexity: float = 0.0
    max_modifier_cost: float = 0.0


@dataclass
class ScoringWeights:
    geometry: float = 0.30
    shader: float = 0.25
    modifier: float = 0.20
    texture: float = 0.25


@dataclass
class SceneAnalysis:
    total_objects: int = 0
    total_vertices: int = 0
    total_triangles: int = 0
    total_triangles_draw: int = 0
    total_vram_bytes: int = 0
    unique_textures: Dict[str, TextureInfo] = field(default_factory=dict)
    objects: List[ObjectAnalysis] = field(default_factory=list)
    analysis_time_ms: float = 0.0
