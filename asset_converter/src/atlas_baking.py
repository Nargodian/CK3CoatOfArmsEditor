"""
Atlas baking for CK3 emblem and pattern textures.

Extracts individual color channels from CK3's packed DDS textures and
composites them into atlas sheets for use by the editor's shaders.

Emblem Atlas (512x512): 4 quadrants - Red(0,0), Green(256,0), Blue(0,256), Alpha(256,256)
Pattern Atlas (512x256): 2 tiles - Green(0,0), Blue(256,0)
"""

from typing import Callable, Dict

import numpy as np
from PIL import Image


# ============================================================================
# EMBLEM CHANNEL EXTRACTORS
# ============================================================================

def extract_red_channel(img_array: np.ndarray) -> np.ndarray:
    """White image (1,1,1) with r*a as alpha."""
    if len(img_array.shape) == 3:
        red = img_array[:, :, 0].astype(np.float32)
        alpha = img_array[:, :, 3].astype(np.float32) if img_array.shape[2] == 4 else np.full(red.shape, 255.0, dtype=np.float32)
    else:
        red = img_array.astype(np.float32)
        alpha = np.full(red.shape, 255.0, dtype=np.float32)
    
    h, w = red.shape
    result = np.ones((h, w, 4), dtype=np.uint8) * 255
    result[:, :, 3] = np.clip((red / 255.0) * (alpha / 255.0) * 255.0, 0, 255).astype(np.uint8)
    return result


def extract_green_channel(img_array: np.ndarray) -> np.ndarray:
    """White image (1,1,1) with g*a as alpha."""
    if len(img_array.shape) == 3:
        green = img_array[:, :, 1].astype(np.float32)
        alpha = img_array[:, :, 3].astype(np.float32) if img_array.shape[2] == 4 else np.full(green.shape, 255.0, dtype=np.float32)
    else:
        green = img_array.astype(np.float32)
        alpha = np.full(green.shape, 255.0, dtype=np.float32)
    
    h, w = green.shape
    result = np.ones((h, w, 4), dtype=np.uint8) * 255
    result[:, :, 3] = np.clip((green / 255.0) * (alpha / 255.0) * 255.0, 0, 255).astype(np.uint8)
    return result


def extract_blue_channel(img_array: np.ndarray) -> np.ndarray:
    """Blue*2 for RGB ((b*2),(b*2),(b*2)), original alpha."""
    if len(img_array.shape) == 3:
        blue = img_array[:, :, 2].astype(np.float32)
        alpha = img_array[:, :, 3] if img_array.shape[2] == 4 else np.full(blue.shape, 255, dtype=np.uint8)
    else:
        blue = img_array.astype(np.float32)
        alpha = np.full(blue.shape, 255, dtype=np.uint8)
    
    h, w = blue.shape
    blue_scaled = np.clip(blue * 2.0, 0, 255).astype(np.uint8)
    result = np.zeros((h, w, 4), dtype=np.uint8)
    result[:, :, 0] = blue_scaled
    result[:, :, 1] = blue_scaled
    result[:, :, 2] = blue_scaled
    result[:, :, 3] = alpha
    return result


def extract_alpha_channel(img_array: np.ndarray) -> np.ndarray:
    """White image (1,1,1) with (1-a) as alpha."""
    if len(img_array.shape) == 3 and img_array.shape[2] == 4:
        alpha = img_array[:, :, 3]
    else:
        alpha = np.full((img_array.shape[0], img_array.shape[1]), 255, dtype=np.uint8)
    
    h, w = alpha.shape
    result = np.ones((h, w, 4), dtype=np.uint8) * 255
    result[:, :, 3] = 255 - alpha
    return result


QUADRANT_EXTRACTORS: Dict[str, Callable[[np.ndarray], np.ndarray]] = {
    'red': extract_red_channel,
    'green': extract_green_channel,
    'blue': extract_blue_channel,
    'alpha': extract_alpha_channel
}


def create_emblem_atlas(img_array: np.ndarray) -> Image.Image:
    """Create 512x512 emblem atlas with 4 quadrants.
    
    Quadrant layout:
        Red   (0,0)     Green (256,0)
        Blue  (0,256)   Alpha (256,256)
    """
    atlas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
    
    # Resize source to 256x256 if needed
    h, w = img_array.shape[:2]
    if h != 256 or w != 256:
        img = Image.fromarray(img_array)
        img = img.resize((256, 256), Image.Resampling.LANCZOS)
        img_array = np.array(img)
    
    positions = {
        'red': (0, 0),
        'green': (256, 0),
        'blue': (0, 256),
        'alpha': (256, 256)
    }
    
    for channel, extractor in QUADRANT_EXTRACTORS.items():
        rgba_quadrant = extractor(img_array)
        quadrant_img = Image.fromarray(rgba_quadrant, mode='RGBA')
        atlas.paste(quadrant_img, positions[channel])
    
    return atlas


# ============================================================================
# PATTERN TILE EXTRACTORS
# ============================================================================

def extract_green_tile(img_array: np.ndarray) -> np.ndarray:
    """White image (1,1,1) with green channel as alpha."""
    if len(img_array.shape) == 3:
        green = img_array[:, :, 1].astype(np.float32)
    else:
        green = img_array.astype(np.float32)
    
    h, w = green.shape if len(green.shape) == 2 else (green.shape[0], green.shape[1])
    result = np.ones((h, w, 4), dtype=np.uint8) * 255
    result[:, :, 3] = green.astype(np.uint8)
    return result


def extract_blue_tile(img_array: np.ndarray) -> np.ndarray:
    """White image (1,1,1) with blue channel as alpha."""
    if len(img_array.shape) == 3:
        blue = img_array[:, :, 2].astype(np.float32)
    else:
        blue = img_array.astype(np.float32)
    
    h, w = blue.shape if len(blue.shape) == 2 else (blue.shape[0], blue.shape[1])
    result = np.ones((h, w, 4), dtype=np.uint8) * 255
    result[:, :, 3] = blue.astype(np.uint8)
    return result


def create_pattern_atlas(img_array: np.ndarray) -> Image.Image:
    """Create 512x256 pattern atlas with 2 tiles.
    
    Tile layout:
        Green (0,0)   Blue (256,0)
    """
    atlas = Image.new('RGBA', (512, 256), (0, 0, 0, 0))
    
    # Resize source to 256x256 if needed
    h, w = img_array.shape[:2]
    if h != 256 or w != 256:
        img = Image.fromarray(img_array)
        img = img.resize((256, 256), Image.Resampling.LANCZOS)
        img_array = np.array(img)
    
    green_tile = Image.fromarray(extract_green_tile(img_array), mode='RGBA')
    blue_tile = Image.fromarray(extract_blue_tile(img_array), mode='RGBA')
    
    atlas.paste(green_tile, (0, 0))
    atlas.paste(blue_tile, (256, 0))
    
    return atlas
