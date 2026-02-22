"""Texture detection and VRAM estimation."""

import bpy
from ..data.models import TextureInfo
from ..utils.constants import DEFAULT_MIPMAP_FACTOR


def estimate_vram(image, mipmap_factor=DEFAULT_MIPMAP_FACTOR):
    """Estimate VRAM in bytes for a single texture.

    Args:
        image: bpy.types.Image to estimate.
        mipmap_factor: Multiplier for mipmap overhead (1.33 standard).

    Returns:
        Estimated VRAM in bytes.
    """
    width, height = image.size
    if width == 0 or height == 0:
        return 0

    channels = image.channels
    if channels == 0:
        channels = 4  # Fallback: assume RGBA

    # image.depth is total bits (e.g. 32 for 8-bit RGBA)
    if image.depth > 0 and channels > 0:
        bits_per_channel = image.depth // channels
    else:
        bits_per_channel = 8

    bytes_per_pixel = channels * (bits_per_channel / 8)
    base_vram = width * height * bytes_per_pixel
    return int(base_vram * mipmap_factor)


def _build_texture_info(image, mipmap_factor):
    """Build a TextureInfo from a bpy.types.Image."""
    channels = image.channels if image.channels > 0 else 4
    depth = image.depth
    if depth > 0 and channels > 0:
        bit_depth = depth // channels
    else:
        bit_depth = 8

    return TextureInfo(
        image_name=image.name,
        filepath=image.filepath or "",
        width=image.size[0],
        height=image.size[1],
        bit_depth=bit_depth,
        channels=channels,
        vram_bytes=estimate_vram(image, mipmap_factor),
        is_packed=image.packed_file is not None,
    )


def analyze_textures(obj, mipmap_factor=DEFAULT_MIPMAP_FACTOR, seen_textures=None):
    """Detect all textures used by an object's materials.

    Args:
        obj: bpy.types.Object to analyze.
        mipmap_factor: Mipmap overhead multiplier.
        seen_textures: Optional dict of image_name -> TextureInfo for
            scene-level deduplication. Will be updated in place.

    Returns:
        Tuple of (list of TextureInfo for this object, total VRAM bytes).
        Shared textures are included per-object but deduplicated in seen_textures.
    """
    if seen_textures is None:
        seen_textures = {}

    textures = []
    obj_image_names = set()

    if not hasattr(obj, 'data') or obj.data is None:
        return textures, 0

    materials = getattr(obj.data, 'materials', None)
    if materials is None:
        return textures, 0

    for mat in materials:
        if mat is None or mat.node_tree is None:
            continue

        for node in mat.node_tree.nodes:
            if node.type != 'TEX_IMAGE' or node.image is None:
                continue

            image = node.image
            if image.name in obj_image_names:
                continue  # Already counted for this object
            obj_image_names.add(image.name)

            if image.name not in seen_textures:
                info = _build_texture_info(image, mipmap_factor)
                seen_textures[image.name] = info
            textures.append(seen_textures[image.name])

    total_vram = sum(t.vram_bytes for t in textures)
    return textures, total_vram
