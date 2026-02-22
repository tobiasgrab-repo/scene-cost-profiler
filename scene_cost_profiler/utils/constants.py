"""Constants for scoring, modifier costs, and thresholds."""

# Modifier types considered high-cost
HIGH_COST_MODIFIER_TYPES = {
    'SUBSURF', 'BOOLEAN', 'REMESH', 'NODES',
    'MULTIRES', 'FLUID', 'CLOTH', 'SOFTBODY',
    'PARTICLE_SYSTEM', 'OCEAN', 'DYNAMIC_PAINT',
}

# Base cost per modifier type (before level/count multipliers)
MODIFIER_BASE_COST = {
    'SUBSURF': 0.3,
    'BOOLEAN': 0.5,
    'REMESH': 0.6,
    'NODES': 0.4,
    'MULTIRES': 0.4,
    'FLUID': 0.8,
    'CLOTH': 0.6,
    'SOFTBODY': 0.5,
    'PARTICLE_SYSTEM': 0.5,
    'OCEAN': 0.7,
    'DYNAMIC_PAINT': 0.5,
    'ARRAY': 0.2,
    'MIRROR': 0.1,
    'SOLIDIFY': 0.15,
    'BEVEL': 0.2,
    'SCREW': 0.15,
    'SKIN': 0.2,
    'WIREFRAME': 0.1,
    'WELD': 0.05,
    'SHRINKWRAP': 0.1,
    'CURVE': 0.05,
    'LATTICE': 0.05,
    'ARMATURE': 0.05,
}
DEFAULT_MODIFIER_COST = 0.05

# Maximum raw modifier cost before normalization
MAX_MODIFIER_COST_RAW = 5.0

# Shader complexity node weights
NODE_WEIGHT_DEFAULT = 1.0
NODE_WEIGHT_TEXTURE = 3.0
NODE_WEIGHT_MATH = 0.5
NODE_WEIGHT_PROCEDURAL = 5.0

# Maximum shader complexity for normalization
MAX_SHADER_COMPLEXITY = 100.0

# Procedural texture node types
PROCEDURAL_NOISE_TYPES = {
    'TEX_NOISE', 'TEX_VORONOI', 'TEX_WAVE', 'TEX_MUSGRAVE',
    'TEX_MAGIC', 'TEX_CHECKER', 'TEX_BRICK', 'TEX_GRADIENT',
}

# Math-like node types
MATH_NODE_TYPES = {
    'MATH', 'VECT_MATH', 'MIX', 'MAP_RANGE', 'CLAMP',
    'COMBINE_XYZ', 'SEPARATE_XYZ', 'COMBINE_COLOR', 'SEPARATE_COLOR',
}

# Object types we analyze
ANALYZABLE_TYPES = {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'}

# Default scoring weights
DEFAULT_WEIGHT_GEOMETRY = 0.30
DEFAULT_WEIGHT_SHADER = 0.25
DEFAULT_WEIGHT_MODIFIER = 0.20
DEFAULT_WEIGHT_TEXTURE = 0.25

# Default mipmap factor (full chain = 4/3)
DEFAULT_MIPMAP_FACTOR = 1.33
