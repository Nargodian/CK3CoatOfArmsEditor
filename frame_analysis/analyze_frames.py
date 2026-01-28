"""
Frame Graphics Analysis Script

Analyzes CK3 frame graphics to understand their boundaries and determine
optimal CoA fitting parameters.

For each frame (160x160 within 960x160 strip):
- Bounding box of actual content
- Expanding cross crawl from center to find edges
- Symmetry analysis
- Mask correlation
- Optimal square fitting calculations
"""

import os
import sys
from pathlib import Path
from PIL import Image
import numpy as np

# Path to frame assets
FRAME_DIR = Path("../ck3_assets/coa_frames")
OUTPUT_FILE = "frame_analysis_results.txt"


def analyze_frame_slice(img_data, slice_idx, width=160, height=160):
    """
    Analyze a single 160x160 frame slice from the 6x1 strip.
    
    Args:
        img_data: Full image numpy array (RGBA)
        slice_idx: Index 0-5 for which frame in the strip
        width: Width of each frame slice (160)
        height: Height of frame (160)
    
    Returns:
        Dictionary with analysis results
    """
    # Extract the slice
    x_start = slice_idx * width
    x_end = x_start + width
    frame_slice = img_data[0:height, x_start:x_end, :]
    
    # Get alpha channel
    alpha = frame_slice[:, :, 3]
    
    # Find all pixels with non-zero alpha (actual content)
    content_mask = alpha > 0
    
    # If no content, return empty results
    if not np.any(content_mask):
        return {
            'has_content': False,
            'slice_idx': slice_idx
        }
    
    # Bounding box analysis
    rows = np.any(content_mask, axis=1)
    cols = np.any(content_mask, axis=0)
    y_min, y_max = np.where(rows)[0][[0, -1]]
    x_min, x_max = np.where(cols)[0][[0, -1]]
    
    bbox_width = x_max - x_min + 1
    bbox_height = y_max - y_min + 1
    
    # Center point
    center_x, center_y = width // 2, height // 2
    
    # Interior flood fill: Fill the empty space INSIDE the frame
    # Strategy: Flood fill from center where alpha == 0 (transparent)
    # This gives us the actual usable interior area
    
    # Create a mask for flood filling (1 = can fill, 0 = frame/blocked)
    # Threshold: alpha <= 10 is considered "empty" (allows for slight anti-aliasing)
    empty_mask = alpha <= 10
    
    # Flood fill from center
    from scipy import ndimage
    
    # Create binary structure for 4-connectivity (no diagonals)
    structure = np.array([[0, 1, 0],
                          [1, 1, 1],
                          [0, 1, 0]], dtype=bool)
    
    # Start from center - mark it as seed
    seed_mask = np.zeros_like(empty_mask, dtype=bool)
    seed_mask[center_y, center_x] = True
    
    # Flood fill: find all connected empty pixels from center
    filled_interior = ndimage.binary_dilation(seed_mask, structure=structure, mask=empty_mask, iterations=-1)
    
    # Get bounding box of the filled interior
    if np.any(filled_interior):
        rows = np.any(filled_interior, axis=1)
        cols = np.any(filled_interior, axis=0)
        
        if np.any(rows) and np.any(cols):
            interior_y_min, interior_y_max = np.where(rows)[0][[0, -1]]
            interior_x_min, interior_x_max = np.where(cols)[0][[0, -1]]
            
            interior_width = interior_x_max - interior_x_min + 1
            interior_height = interior_y_max - interior_y_min + 1
            interior_center_x = (interior_x_min + interior_x_max) / 2
            interior_center_y = (interior_y_min + interior_y_max) / 2
            
            # Calculate maximum square that fits in interior
            # Distance from interior center to edges
            interior_radius_x = min(interior_center_x - interior_x_min, interior_x_max - interior_center_x)
            interior_radius_y = min(interior_center_y - interior_y_min, interior_y_max - interior_center_y)
            interior_square_radius = min(interior_radius_x, interior_radius_y)
            interior_square_size = int(interior_square_radius * 2)
        else:
            interior_width = 0
            interior_height = 0
            interior_square_size = 0
            interior_center_x = center_x
            interior_center_y = center_y
    else:
        interior_width = 0
        interior_height = 0
        interior_square_size = 0
        interior_center_x = center_x
        interior_center_y = center_y
    
    # Also calculate inscribed square (for comparison)
    # Expanding cross crawl from center
    crawl_right = 0
    for x in range(center_x, width):
        if alpha[center_y, x] > 10:  # Hit frame
            crawl_right = x - center_x
            break
    if crawl_right == 0:
        crawl_right = width - center_x
    
    crawl_left = 0
    for x in range(center_x, -1, -1):
        if alpha[center_y, x] > 10:  # Hit frame
            crawl_left = center_x - x
            break
    if crawl_left == 0:
        crawl_left = center_x
    
    crawl_down = 0
    for y in range(center_y, height):
        if alpha[y, center_x] > 10:  # Hit frame
            crawl_down = y - center_y
            break
    if crawl_down == 0:
        crawl_down = height - center_y
    
    crawl_up = 0
    for y in range(center_y, -1, -1):
        if alpha[y, center_x] > 10:  # Hit frame
            crawl_up = center_y - y
            break
    if crawl_up == 0:
        crawl_up = center_y
    
    inscribed_radius = min(crawl_right, crawl_left, crawl_down, crawl_up)
    inscribed_size = inscribed_radius * 2
    
    # Calculate ratios
    interior_ratio = interior_square_size / width if width > 0 else 0
    inscribed_ratio = inscribed_size / width if width > 0 else 0
    
    # Symmetry check (horizontal)
    left_half = frame_slice[:, :width//2, :]
    right_half = np.flip(frame_slice[:, width//2:, :], axis=1)
    symmetry_score = np.mean(np.abs(left_half[:, :, 3].astype(float) - right_half[:, :, 3].astype(float)))
    is_symmetric = symmetry_score < 10
    
    # Content density
    total_pixels = width * height
    content_pixels = np.sum(content_mask)
    content_density = content_pixels / total_pixels
    
    # Average alpha of content
    avg_alpha = np.mean(alpha[content_mask])
    
    # Center of mass
    y_coords, x_coords = np.where(content_mask)
    if len(y_coords) > 0:
        center_of_mass_x = np.mean(x_coords)
        center_of_mass_y = np.mean(y_coords)
    else:
        center_of_mass_x = center_x
        center_of_mass_y = center_y
    
    return {
        'has_content': True,
        'slice_idx': slice_idx,
        'bbox': {
            'x_min': int(x_min),
            'x_max': int(x_max),
            'y_min': int(y_min),
            'y_max': int(y_max),
            'width': int(bbox_width),
            'height': int(bbox_height)
        },
        'crawl': {
            'right': int(crawl_right),
            'left': int(crawl_left),
            'down': int(crawl_down),
            'up': int(crawl_up)
        },
        'inscribed_square': {
            'radius': int(inscribed_radius),
            'size': int(inscribed_size),
            'ratio': float(inscribed_ratio)
        },
        'interior_flood_fill': {
            'bbox_width': int(interior_width),
            'bbox_height': int(interior_height),
            'square_size': int(interior_square_size),
            'ratio': float(interior_ratio),
            'center_x': float(interior_center_x),
            'center_y': float(interior_center_y)
        },
        'symmetry': {
            'score': float(symmetry_score),
            'is_symmetric': bool(is_symmetric)
        },
        'content': {
            'density': float(content_density),
            'avg_alpha': float(avg_alpha)
        },
        'center_of_mass': {
            'x': float(center_of_mass_x),
            'y': float(center_of_mass_y),
            'offset_from_center_x': float(center_of_mass_x - center_x),
            'offset_from_center_y': float(center_of_mass_y - center_y)
        }
    }


def analyze_mask(mask_path):
    """
    Analyze the frame mask to understand its properties.
    
    Returns:
        Dictionary with mask analysis
    """
    if not mask_path.exists():
        return None
    
    mask_img = Image.open(mask_path).convert('RGBA')
    mask_data = np.array(mask_img)
    
    alpha = mask_data[:, :, 3]
    rgb_max = max(mask_data[:,:,0].max(), mask_data[:,:,1].max(), mask_data[:,:,2].max())
    
    # Alpha statistics
    alpha_min = alpha.min()
    alpha_max = alpha.max()
    alpha_mean = alpha.mean()
    alpha_std = alpha.std()
    
    # Count different alpha levels (for gradient analysis)
    unique_alphas = len(np.unique(alpha))
    
    # Is it a "doggy mask" (full alpha everywhere)?
    is_full_alpha = alpha_min >= 250
    
    # Find content area
    content_mask = alpha > 0
    if np.any(content_mask):
        rows = np.any(content_mask, axis=1)
        cols = np.any(content_mask, axis=0)
        y_min, y_max = np.where(rows)[0][[0, -1]]
        x_min, x_max = np.where(cols)[0][[0, -1]]
        
        mask_bbox = {
            'x_min': int(x_min),
            'x_max': int(x_max),
            'y_min': int(y_min),
            'y_max': int(y_max),
            'width': int(x_max - x_min + 1),
            'height': int(y_max - y_min + 1)
        }
    else:
        mask_bbox = None
    
    return {
        'exists': True,
        'alpha': {
            'min': int(alpha_min),
            'max': int(alpha_max),
            'mean': float(alpha_mean),
            'std': float(alpha_std),
            'unique_levels': int(unique_alphas)
        },
        'rgb_max': int(rgb_max),
        'is_full_alpha': bool(is_full_alpha),
        'type': 'full_alpha' if is_full_alpha else 'gradient_alpha',
        'bbox': mask_bbox
    }


def analyze_all_frames():
    """
    Analyze all frame files and generate report.
    """
    results = {}
    
    frame_files = {
        "dynasty": "dynasty.png",
        "house": "house.png",
        "house_china": "house_china.png",
        "house_japan": "house_japan.png"
    }
    
    # Add house frames 02-30
    for i in range(2, 31):
        frame_files[f"house_frame_{i:02d}"] = f"house_frame_{i:02d}.png"
    
    for frame_name, filename in sorted(frame_files.items()):
        frame_path = FRAME_DIR / filename
        mask_path = FRAME_DIR / filename.replace('.png', '_mask.png')
        
        if not frame_path.exists():
            results[frame_name] = {'exists': False}
            continue
        
        print(f"Analyzing {frame_name}...")
        
        # Load frame image
        img = Image.open(frame_path).convert('RGBA')
        img_data = np.array(img)
        
        # Analyze each of the 6 slices (splendor levels)
        slices = []
        for i in range(6):
            slice_result = analyze_frame_slice(img_data, i)
            slices.append(slice_result)
        
        # Analyze mask
        mask_result = analyze_mask(mask_path)
        
        results[frame_name] = {
            'exists': True,
            'filename': filename,
            'dimensions': f"{img.width}x{img.height}",
            'slices': slices,
            'mask': mask_result
        }
    
    return results


def write_report(results, output_path):
    """
    Write analysis results to a text file.
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("CK3 FRAME GRAPHICS ANALYSIS\n")
        f.write("=" * 80 + "\n\n")
        
        # Summary statistics
        f.write("SUMMARY\n")
        f.write("-" * 80 + "\n")
        total_frames = sum(1 for r in results.values() if r.get('exists'))
        full_alpha_frames = []
        gradient_alpha_frames = []
        
        for name, data in results.items():
            if data.get('exists') and data.get('mask'):
                if data['mask']['is_full_alpha']:
                    full_alpha_frames.append(name)
                else:
                    gradient_alpha_frames.append(name)
        
        f.write(f"Total frames analyzed: {total_frames}\n")
        f.write(f"Full alpha masks (doggy masks): {len(full_alpha_frames)}\n")
        f.write(f"Gradient alpha masks: {len(gradient_alpha_frames)}\n\n")
        
        f.write("Full alpha mask frames:\n")
        for name in full_alpha_frames:
            f.write(f"  - {name}\n")
        f.write("\n")
        
        # Detailed per-frame analysis
        f.write("\n" + "=" * 80 + "\n")
        f.write("DETAILED FRAME ANALYSIS\n")
        f.write("=" * 80 + "\n\n")
        
        for frame_name, data in sorted(results.items()):
            if not data.get('exists'):
                continue
            
            f.write(f"\n{'=' * 80}\n")
            f.write(f"FRAME: {frame_name}\n")
            f.write(f"{'=' * 80}\n")
            f.write(f"File: {data['filename']}\n")
            f.write(f"Dimensions: {data['dimensions']}\n\n")
            
            # Mask analysis
            if data.get('mask'):
                mask = data['mask']
                f.write("MASK ANALYSIS:\n")
                f.write(f"  Type: {mask['type']}\n")
                f.write(f"  Alpha range: {mask['alpha']['min']} - {mask['alpha']['max']}\n")
                f.write(f"  Alpha mean: {mask['alpha']['mean']:.1f}\n")
                f.write(f"  Alpha std dev: {mask['alpha']['std']:.1f}\n")
                f.write(f"  Unique alpha levels: {mask['alpha']['unique_levels']}\n")
                f.write(f"  RGB max: {mask['rgb_max']}\n")
                if mask['bbox']:
                    f.write(f"  Bounding box: {mask['bbox']['width']}x{mask['bbox']['height']} ")
                    f.write(f"at ({mask['bbox']['x_min']}, {mask['bbox']['y_min']})\n")
                f.write("\n")
            else:
                f.write("MASK: Not found\n\n")
            
            # Slice analysis
            f.write("SPLENDOR LEVEL ANALYSIS (6 slices):\n")
            f.write("-" * 80 + "\n")
            
            for slice_data in data['slices']:
                if not slice_data['has_content']:
                    f.write(f"  Slice {slice_data['slice_idx']}: No content\n")
                    continue
                
                f.write(f"\n  Slice {slice_data['slice_idx']}:\n")
                
                bbox = slice_data['bbox']
                f.write(f"    Bounding box: {bbox['width']}x{bbox['height']} ")
                f.write(f"at ({bbox['x_min']}, {bbox['y_min']})\n")
                
                crawl = slice_data['crawl']
                f.write(f"    Crawl from center (80,80):\n")
                f.write(f"      Right: {crawl['right']}px, Left: {crawl['left']}px\n")
                f.write(f"      Down: {crawl['down']}px, Up: {crawl['up']}px\n")
                
                inscribed = slice_data['inscribed_square']
                f.write(f"    Inscribed square (cross crawl):\n")
                f.write(f"      Radius: {inscribed['radius']}px\n")
                f.write(f"      Size: {inscribed['size']}x{inscribed['size']}px\n")
                f.write(f"      Ratio: {inscribed['ratio']:.3f} ({inscribed['ratio']*100:.1f}%)\n")
                
                interior = slice_data['interior_flood_fill']
                f.write(f"    Interior flood fill bbox:\n")
                f.write(f"      Interior size: {interior['bbox_width']}x{interior['bbox_height']}px\n")
                f.write(f"      Max square: {interior['square_size']}x{interior['square_size']}px\n")
                f.write(f"      Ratio: {interior['ratio']:.3f} ({interior['ratio']*100:.1f}%)\n")
                f.write(f"      Interior center: ({interior['center_x']:.1f}, {interior['center_y']:.1f})\n")
                
                sym = slice_data['symmetry']
                f.write(f"    Symmetry: {'Yes' if sym['is_symmetric'] else 'No'} ")
                f.write(f"(score: {sym['score']:.2f})\n")
                
                content = slice_data['content']
                f.write(f"    Content density: {content['density']:.3f} ({content['density']*100:.1f}%)\n")
                f.write(f"    Average alpha: {content['avg_alpha']:.1f}\n")
                
                com = slice_data['center_of_mass']
                f.write(f"    Center of mass: ({com['x']:.1f}, {com['y']:.1f})\n")
                f.write(f"    Offset from center: ({com['offset_from_center_x']:.1f}, {com['offset_from_center_y']:.1f})\n")
            
            f.write("\n")
        
        # Analysis of patterns
        f.write("\n" + "=" * 80 + "\n")
        f.write("PATTERN ANALYSIS\n")
        f.write("=" * 80 + "\n\n")
        
        # Collect safe square ratios for comparison
        f.write("INSCRIBED vs INTERIOR FLOOD FILL RATIOS:\n")
        f.write("-" * 80 + "\n")
        f.write("Format: frame_name [mask_type] inscribed / flood_fill\n\n")
        
        for frame_name, data in sorted(results.items()):
            if not data.get('exists'):
                continue
            
            mask_type = data.get('mask', {}).get('type', 'unknown')
            
            # Get average ratios across all slices
            inscribed_ratios = []
            interior_ratios = []
            for slice_data in data['slices']:
                if slice_data['has_content']:
                    inscribed_ratios.append(slice_data['inscribed_square']['ratio'])
                    interior_ratios.append(slice_data['interior_flood_fill']['ratio'])
            
            if inscribed_ratios and interior_ratios:
                avg_inscribed = np.mean(inscribed_ratios)
                avg_interior = np.mean(interior_ratios)
                f.write(f"{frame_name:25s} [{mask_type:14s}] ")
                f.write(f"{avg_inscribed:.3f} / {avg_interior:.3f}\n")
        
        f.write("\n")
        
        # Recommendations
        f.write("\n" + "=" * 80 + "\n")
        f.write("RECOMMENDATIONS\n")
        f.write("=" * 80 + "\n\n")
        
        # Calculate average safe ratios for each mask type
        full_alpha_inscribed = []
        full_alpha_interior = []
        gradient_alpha_inscribed = []
        gradient_alpha_interior = []
        
        for frame_name, data in results.items():
            if not data.get('exists'):
                continue
            
            if data.get('mask'):
                inscribed_ratios = [s['inscribed_square']['ratio'] for s in data['slices'] if s['has_content']]
                interior_ratios = [s['interior_flood_fill']['ratio'] for s in data['slices'] if s['has_content']]
                
                if inscribed_ratios and interior_ratios:
                    avg_inscribed = np.mean(inscribed_ratios)
                    avg_interior = np.mean(interior_ratios)
                    
                    if data['mask']['is_full_alpha']:
                        full_alpha_inscribed.append(avg_inscribed)
                        full_alpha_interior.append(avg_interior)
                    else:
                        gradient_alpha_inscribed.append(avg_inscribed)
                        gradient_alpha_interior.append(avg_interior)
        
        if full_alpha_interior:
            f.write(f"Full alpha masks (doggy masks):\n")
            f.write(f"  Inscribed (cross crawl): {np.mean(full_alpha_inscribed):.3f}\n")
            f.write(f"  Interior flood fill: {np.mean(full_alpha_interior):.3f}\n")
            f.write(f"  Recommended scale: {np.mean(full_alpha_interior):.2f}\n\n")
        
        if gradient_alpha_interior:
            f.write(f"Gradient alpha masks:\n")
            f.write(f"  Inscribed (cross crawl): {np.mean(gradient_alpha_inscribed):.3f}\n")
            f.write(f"  Interior flood fill: {np.mean(gradient_alpha_interior):.3f}\n")
            f.write(f"  Recommended scale: {np.mean(gradient_alpha_interior):.2f}\n\n")
        
        f.write(f"Current implementation:\n")
        f.write(f"  Full alpha frames: scale=1.0\n")
        f.write(f"  Gradient frames: scale=0.9\n\n")
        
        f.write(f"NOTE: Interior flood fill measures the actual usable space inside the\n")
        f.write(f"      frame by filling from center until hitting frame content.\n")


if __name__ == '__main__':
    print("Starting frame analysis...")
    results = analyze_all_frames()
    
    print(f"\nWriting report to {OUTPUT_FILE}...")
    write_report(results, OUTPUT_FILE)
    
    print("Analysis complete!")
