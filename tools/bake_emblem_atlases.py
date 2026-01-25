"""
Bake emblem textures into 512x512 quadrant atlases.

Each atlas contains 4 quadrants (256x256 each) organized in Morton order:
┌─────────┬─────────┐
│ R (TL)  │ G (TR)  │  Top-Left:  White (111) with red channel as alpha
│ 256x256 │ 256x256 │  Top-Right: White (111) with green channel as alpha
├─────────┼─────────┤
│ B (BL)  │ A (BR)  │  Bottom-Left:  White (111) with blue channel as alpha
│ 256x256 │ 256x256 │  Bottom-Right: White (111) with alpha channel
└─────────┴─────────┘

This allows runtime color composition by applying color tints to white quadrants.
"""

import os
from pathlib import Path
from typing import Callable, Dict, Tuple
from PIL import Image
import numpy as np

# Quadrant configuration - easily adjustable
QUADRANT_CONFIG = {
    'size': 256,  # Individual quadrant size
    'atlas_size': 512,  # Final atlas size
    'positions': {
        'red': (0, 0),      # Top-Left
        'green': (256, 0),   # Top-Right
        'blue': (0, 256),    # Bottom-Left
        'alpha': (256, 256)  # Bottom-Right
    }
}


def extract_red_channel(img_array: np.ndarray) -> np.ndarray:
    """White image (1,1,1) with r*a as alpha"""
    if len(img_array.shape) == 3:
        red = img_array[:, :, 0].astype(np.float32)
        alpha = img_array[:, :, 3].astype(np.float32) if img_array.shape[2] == 4 else np.full(red.shape, 255.0, dtype=np.float32)
    else:
        red = img_array.astype(np.float32)
        alpha = np.full(red.shape, 255.0, dtype=np.float32)
    
    # Create RGBA: white RGB (255,255,255) with r*a as alpha
    h, w = red.shape
    result = np.ones((h, w, 4), dtype=np.uint8) * 255
    result[:, :, 3] = np.clip((red / 255.0) * (alpha / 255.0) * 255.0, 0, 255).astype(np.uint8)
    return result


def extract_green_channel(img_array: np.ndarray) -> np.ndarray:
    """White image (1,1,1) with g*a as alpha"""
    if len(img_array.shape) == 3:
        green = img_array[:, :, 1].astype(np.float32)
        alpha = img_array[:, :, 3].astype(np.float32) if img_array.shape[2] == 4 else np.full(green.shape, 255.0, dtype=np.float32)
    else:
        green = img_array.astype(np.float32)
        alpha = np.full(green.shape, 255.0, dtype=np.float32)
    
    # Create RGBA: white RGB (255,255,255) with g*a as alpha
    h, w = green.shape
    result = np.ones((h, w, 4), dtype=np.uint8) * 255
    result[:, :, 3] = np.clip((green / 255.0) * (alpha / 255.0) * 255.0, 0, 255).astype(np.uint8)
    return result


def extract_blue_channel(img_array: np.ndarray) -> np.ndarray:
    """Blue*2 for RGB ((b*2),(b*2),(b*2)), original alpha"""
    if len(img_array.shape) == 3:
        blue = img_array[:, :, 2].astype(np.float32)
        alpha = img_array[:, :, 3] if img_array.shape[2] == 4 else np.full(blue.shape, 255, dtype=np.uint8)
    else:
        blue = img_array.astype(np.float32)
        alpha = np.full(blue.shape, 255, dtype=np.uint8)
    
    # Create RGBA: (b*2, b*2, b*2, a)
    h, w = blue.shape
    blue_scaled = np.clip(blue * 2.0, 0, 255).astype(np.uint8)
    result = np.zeros((h, w, 4), dtype=np.uint8)
    result[:, :, 0] = blue_scaled  # R = b*2
    result[:, :, 1] = blue_scaled  # G = b*2
    result[:, :, 2] = blue_scaled  # B = b*2
    result[:, :, 3] = alpha        # A = original alpha
    return result


def extract_alpha_channel(img_array: np.ndarray) -> np.ndarray:
    """White image (1,1,1) with (1-a) as alpha"""
    if len(img_array.shape) == 3 and img_array.shape[2] == 4:
        alpha = img_array[:, :, 3]
    else:
        # If no alpha channel, assume fully opaque
        alpha = np.full((img_array.shape[0], img_array.shape[1]), 255, dtype=np.uint8)
    
    # Create RGBA: white RGB with (1-alpha) = inverted alpha
    h, w = alpha.shape
    result = np.ones((h, w, 4), dtype=np.uint8) * 255
    result[:, :, 3] = 255 - alpha  # Alpha = 1 - a
    return result


# Extraction functions for each quadrant - easily swappable
QUADRANT_EXTRACTORS: Dict[str, Callable[[np.ndarray], np.ndarray]] = {
    'red': extract_red_channel,
    'green': extract_green_channel,
    'blue': extract_blue_channel,
    'alpha': extract_alpha_channel
}


def load_emblem_texture(dds_path: Path) -> np.ndarray:
    """
    Load emblem texture from DDS file.
    
    TODO: Implement DDS loading. For now assumes PNG conversion exists.
    """
    png_path = dds_path.with_suffix('.png')
    
    if not png_path.exists():
        raise FileNotFoundError(f"PNG conversion not found: {png_path}")
    
    img = Image.open(png_path).convert('RGBA')
    return np.array(img)


def create_quadrant_atlas(
    img_array: np.ndarray,
    extractors: Dict[str, Callable] = None,
    config: Dict = None
) -> Image.Image:
    """
    Create 512x512 atlas with 4 quadrants from emblem texture.
    
    Args:
        img_array: Source RGBA image as numpy array
        extractors: Dictionary of extraction functions (optional, uses defaults)
        config: Quadrant configuration (optional, uses defaults)
    
    Returns:
        PIL Image of the atlas
    """
    if extractors is None:
        extractors = QUADRANT_EXTRACTORS
    if config is None:
        config = QUADRANT_CONFIG
    
    # Create blank RGBA atlas
    atlas = Image.new('RGBA', (config['atlas_size'], config['atlas_size']), (0, 0, 0, 0))
    
    # Resize source image to quadrant size if needed
    h, w = img_array.shape[:2]
    if h != config['size'] or w != config['size']:
        img = Image.fromarray(img_array)
        img = img.resize((config['size'], config['size']), Image.Resampling.LANCZOS)
        img_array = np.array(img)
    
    # Extract and place each quadrant
    for channel, extractor in extractors.items():
        if channel not in config['positions']:
            continue
        
        # Extract channel as RGBA (white with channel as alpha)
        rgba_quadrant = extractor(img_array)
        quadrant_img = Image.fromarray(rgba_quadrant, mode='RGBA')
        
        # Paste into atlas at configured position
        pos = config['positions'][channel]
        atlas.paste(quadrant_img, pos)
    
    return atlas


def batch_bake_emblems_from_list(
    file_list_path: Path,
    source_dir: Path,
    output_dir: Path,
    extractors: Dict[str, Callable] = None,
    config: Dict = None
):
    """
    Batch process emblem textures from a text file list.
    
    Args:
        file_list_path: Path to .txt file containing full or relative paths (one per line)
        source_dir: Base directory (unused if paths in file are absolute/relative to working dir)
        output_dir: Directory to save atlas PNGs
        extractors: Custom extraction functions (optional)
        config: Custom quadrant configuration (optional)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Read file list - support comments starting with #
    with open(file_list_path, 'r') as f:
        filenames = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    
    total = len(filenames)
    
    print(f"Found {total} files in list: {file_list_path.name}")
    print(f"Output: {output_dir}")
    print(f"Quadrant config: {config or QUADRANT_CONFIG}")
    print("-" * 60)
    
    processed = 0
    errors = []
    
    for idx, filename in enumerate(filenames, 1):
        # Use path as provided in file (can be relative or absolute)
        file_path = Path(filename)
        
        try:
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Load source texture
            # Load source texture - handles both .png and .dds
            if file_path.suffix.lower() == '.png':
                img = Image.open(file_path).convert('RGBA')
                img_array = np.array(img)
            else:
                img_array = load_emblem_texture(file_path)
            
            # Create atlas
            atlas = create_quadrant_atlas(img_array, extractors, config)
            
            # Save atlas
            output_name = file_path.stem + '_atlas.png'
            output_path = output_dir / output_name
            atlas.save(output_path, 'PNG', optimize=True)
            
            processed += 1
            print(f"[{idx}/{total}] Created: {output_name}")
            print(f"[{idx}/{total}] Created: {output_name}")
        
        except Exception as e:
            errors.append((filename, str(e)))
            print(f"ERROR processing {filename}: {e}")
    
    print("-" * 60)
    print(f"Completed: {processed}/{total} atlases created")
    
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for filename, error in errors:
            print(f"  {filename}: {error}")


def preview_atlas_split(atlas_path: Path, config: Dict = None):
    """
    Preview how an atlas will be split into quadrants.
    Useful for debugging extraction order.
    """
    if config is None:
        config = QUADRANT_CONFIG
    
    atlas = Image.open(atlas_path)
    
    print(f"Atlas: {atlas_path.name}")
    print(f"Size: {atlas.size}")
    print("\nQuadrant layout:")
    
    for channel, pos in config['positions'].items():
        x, y = pos
        quadrant = atlas.crop((x, y, x + config['size'], y + config['size']))
        print(f"  {channel.upper()}: position {pos}, size {quadrant.size}")
        
        # Show sample values from corners
        arr = np.array(quadrant)
        if len(arr.shape) == 3:
            print(f"    TL: {arr[0, 0]}, TR: {arr[0, -1]}, BL: {arr[-1, 0]}, BR: {arr[-1, -1]}")
        else:
            print(f"    TL: {arr[0, 0]}, TR: {arr[0, -1]}, BL: {arr[-1, 0]}, BR: {arr[-1, -1]}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Bake emblem textures into quadrant atlases')
    parser.add_argument('file_list', type=Path, help='Text file with file paths (one per line, can be relative or absolute)')
    parser.add_argument('output', type=Path, nargs='?', default='ck3_assets/coa_emblems/atlases', help='Output directory for atlas PNGs (default: ck3_assets/coa_emblems/atlases)')
    parser.add_argument('--preview', type=Path, help='Preview atlas splitting (path to existing atlas)')
    
    args = parser.parse_args()
    
    if args.preview:
        preview_atlas_split(args.preview)
    else:
        batch_bake_emblems_from_list(args.file_list, None, args.output)
