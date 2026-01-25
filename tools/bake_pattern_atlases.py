"""
Bake pattern/background textures into 2-tile atlases.

Each atlas contains 2 tiles (256x256 each) in a 512x256 image:
┌─────────┬─────────┐
│ G (L)   │ B (R)   │  Left:  White (111) with green channel as alpha
│ 256x256 │ 256x256 │  Right: White (111) with blue channel as alpha
└─────────┴─────────┘

This allows runtime color composition for 2-color backgrounds/patterns.
"""

import os
from pathlib import Path
from typing import Callable, Dict, Tuple
from PIL import Image
import numpy as np

# Tile configuration
TILE_CONFIG = {
    'tile_width': 256,
    'tile_height': 256,
    'atlas_width': 512,
    'atlas_height': 256,
    'positions': {
        'green': (0, 0),     # Left
        'blue': (256, 0)     # Right
    }
}


def extract_green_tile(img_array: np.ndarray) -> np.ndarray:
    """White image (1,1,1) with green channel as alpha"""
    if len(img_array.shape) == 3:
        green = img_array[:, :, 1].astype(np.float32)
        alpha = img_array[:, :, 3].astype(np.float32) if img_array.shape[2] == 4 else np.full(green.shape, 255.0, dtype=np.float32)
    else:
        green = img_array.astype(np.float32)
        alpha = np.full(green.shape, 255.0, dtype=np.float32)
    
    # Create RGBA: white RGB (255,255,255) with green as alpha
    h, w = green.shape
    result = np.ones((h, w, 4), dtype=np.uint8) * 255
    result[:, :, 3] = green.astype(np.uint8)  # Alpha = green channel
    return result


def extract_blue_tile(img_array: np.ndarray) -> np.ndarray:
    """White image (1,1,1) with blue channel as alpha"""
    if len(img_array.shape) == 3:
        blue = img_array[:, :, 2].astype(np.float32)
        alpha = img_array[:, :, 3].astype(np.float32) if img_array.shape[2] == 4 else np.full(blue.shape, 255.0, dtype=np.float32)
    else:
        blue = img_array.astype(np.float32)
        alpha = np.full(blue.shape, 255.0, dtype=np.float32)
    
    # Create RGBA: white RGB (255,255,255) with blue as alpha
    h, w = blue.shape
    result = np.ones((h, w, 4), dtype=np.uint8) * 255
    result[:, :, 3] = blue.astype(np.uint8)  # Alpha = blue channel
    return result


# Extraction functions for each tile
TILE_EXTRACTORS: Dict[str, Callable[[np.ndarray], np.ndarray]] = {
    'green': extract_green_tile,
    'blue': extract_blue_tile
}


def load_pattern_texture(path: Path) -> np.ndarray:
    """Load pattern texture from PNG file."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    img = Image.open(path).convert('RGBA')
    return np.array(img)


def create_tile_atlas(
    img_array: np.ndarray,
    extractors: Dict[str, Callable] = None,
    config: Dict = None
) -> Image.Image:
    """
    Create 512x256 atlas with 2 tiles from pattern texture.
    
    Args:
        img_array: Source RGBA image as numpy array
        extractors: Dictionary of extraction functions (optional, uses defaults)
        config: Tile configuration (optional, uses defaults)
    
    Returns:
        PIL Image of the atlas
    """
    if extractors is None:
        extractors = TILE_EXTRACTORS
    if config is None:
        config = TILE_CONFIG
    
    # Create blank RGBA atlas
    atlas = Image.new('RGBA', (config['atlas_width'], config['atlas_height']), (0, 0, 0, 0))
    
    # Resize source image to tile size if needed
    h, w = img_array.shape[:2]
    if h != config['tile_height'] or w != config['tile_width']:
        img = Image.fromarray(img_array)
        img = img.resize((config['tile_width'], config['tile_height']), Image.Resampling.LANCZOS)
        img_array = np.array(img)
    
    # Extract and place each tile
    for channel, extractor in extractors.items():
        if channel not in config['positions']:
            continue
        
        # Extract tile as RGBA (white with channel as alpha)
        rgba_tile = extractor(img_array)
        tile_img = Image.fromarray(rgba_tile, mode='RGBA')
        
        # Paste into atlas at configured position
        pos = config['positions'][channel]
        atlas.paste(tile_img, pos)
    
    return atlas


def batch_bake_patterns_from_list(
    file_list_path: Path,
    source_dir: Path,
    output_dir: Path,
    extractors: Dict[str, Callable] = None,
    config: Dict = None
):
    """
    Batch process pattern textures from a text file list.
    
    Args:
        file_list_path: Path to .txt file containing full or relative paths (one per line)
        source_dir: Base directory (unused if paths in file are absolute/relative to working dir)
        output_dir: Directory to save atlas PNGs
        extractors: Custom extraction functions (optional)
        config: Custom tile configuration (optional)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Read file list - support comments starting with #
    with open(file_list_path, 'r') as f:
        filenames = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    
    total = len(filenames)
    
    print(f"Found {total} files in list: {file_list_path.name}")
    print(f"Output: {output_dir}")
    print(f"Tile config: {config or TILE_CONFIG}")
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
            img_array = load_pattern_texture(file_path)
            
            # Create atlas
            atlas = create_tile_atlas(img_array, extractors, config)
            
            # Save atlas
            output_name = file_path.stem + '_atlas.png'
            output_path = output_dir / output_name
            atlas.save(output_path, 'PNG', optimize=True)
            
            processed += 1
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
    Preview how an atlas will be split into tiles.
    Useful for debugging extraction order.
    """
    if config is None:
        config = TILE_CONFIG
    
    atlas = Image.open(atlas_path)
    
    print(f"Atlas: {atlas_path.name}")
    print(f"Size: {atlas.size}")
    print("\nTile layout:")
    
    for channel, pos in config['positions'].items():
        x, y = pos
        tile = atlas.crop((x, y, x + config['tile_width'], y + config['tile_height']))
        print(f"  {channel.upper()}: position {pos}, size {tile.size}")
        
        # Show sample values from corners
        arr = np.array(tile)
        if len(arr.shape) == 3:
            print(f"    TL: {arr[0, 0]}, TR: {arr[0, -1]}, BL: {arr[-1, 0]}, BR: {arr[-1, -1]}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Bake pattern textures into 2-tile atlases')
    parser.add_argument('file_list', type=Path, help='Text file with file paths (one per line, can be relative or absolute)')
    parser.add_argument('output', type=Path, nargs='?', default='ck3_assets/coa_patterns/atlases', help='Output directory for atlas PNGs (default: ck3_assets/coa_patterns/atlases)')
    parser.add_argument('--preview', type=Path, help='Preview atlas splitting (path to existing atlas)')
    
    args = parser.parse_args()
    
    if args.preview:
        preview_atlas_split(args.preview)
    else:
        batch_bake_patterns_from_list(args.file_list, None, args.output)
