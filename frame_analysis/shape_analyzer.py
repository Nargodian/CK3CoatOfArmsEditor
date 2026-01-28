"""
Frame Shape Semantic Analysis

Analyzes frame shapes to understand their geometric characteristics:
- Contour extraction and simplification
- Shape descriptors (circularity, aspect ratio, etc.)
- Width/height profiles showing how the frame narrows/widens
- Shape classification (shield, circle, rectangle, ornate)
"""

import os
import sys
from pathlib import Path
from PIL import Image
import numpy as np
import cv2

FRAME_DIR = Path("../ck3_assets/coa_frames")
OUTPUT_FILE = "frame_shape_analysis.txt"


def analyze_frame_shape(img_data, slice_idx, width=160, height=160):
    """
    Analyze the semantic shape characteristics of a frame slice.
    """
    # Extract the slice
    x_start = slice_idx * width
    x_end = x_start + width
    frame_slice = img_data[0:height, x_start:x_end, :]
    
    # Get alpha channel
    alpha = frame_slice[:, :, 3]
    
    # Threshold to get frame mask (alpha > 10)
    _, binary = cv2.threshold(alpha, 10, 255, cv2.THRESH_BINARY)
    
    # Find contours of the frame
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None
    
    # Get the largest contour (the frame outline)
    main_contour = max(contours, key=cv2.contourArea)
    
    # Basic shape descriptors
    area = cv2.contourArea(main_contour)
    perimeter = cv2.arcLength(main_contour, True)
    
    # Circularity: 4π * area / perimeter²
    # Circle = 1.0, square ≈ 0.785, elongated shapes < 0.5
    circularity = (4 * np.pi * area) / (perimeter ** 2) if perimeter > 0 else 0
    
    # Bounding rectangle
    x, y, w, h = cv2.boundingRect(main_contour)
    aspect_ratio = w / h if h > 0 else 0
    
    # Extent: ratio of contour area to bounding rectangle area
    extent = area / (w * h) if (w * h) > 0 else 0
    
    # Convexity: ratio of contour area to convex hull area
    hull = cv2.convexHull(main_contour)
    hull_area = cv2.contourArea(hull)
    convexity = area / hull_area if hull_area > 0 else 0
    
    # Solidity: how "solid" vs "hollow" the shape is
    solidity = area / hull_area if hull_area > 0 else 0
    
    # Approximate the contour to simpler polygon
    epsilon = 0.02 * perimeter
    approx = cv2.approxPolyDP(main_contour, epsilon, True)
    num_vertices = len(approx)
    
    # Width profile: measure width at different heights
    width_profile = []
    for scan_y in range(0, height, 5):
        row = binary[scan_y, :]
        transitions = np.diff(row.astype(int))
        # Find left and right edges
        left_edges = np.where(transitions > 0)[0]
        right_edges = np.where(transitions < 0)[0]
        
        if len(left_edges) > 0 and len(right_edges) > 0:
            # Take outermost edges
            left = left_edges[0]
            right = right_edges[-1]
            width_at_y = right - left
            width_profile.append((scan_y, width_at_y))
    
    # Height profile: measure height at different widths
    height_profile = []
    for scan_x in range(0, width, 5):
        col = binary[:, scan_x]
        transitions = np.diff(col.astype(int))
        top_edges = np.where(transitions > 0)[0]
        bottom_edges = np.where(transitions < 0)[0]
        
        if len(top_edges) > 0 and len(bottom_edges) > 0:
            top = top_edges[0]
            bottom = bottom_edges[-1]
            height_at_x = bottom - top
            height_profile.append((scan_x, height_at_x))
    
    # Analyze width profile for shape characteristics
    if width_profile:
        widths = [w for _, w in width_profile]
        width_min = min(widths)
        width_max = max(widths)
        width_mean = np.mean(widths)
        width_std = np.std(widths)
        width_variation = (width_max - width_min) / width_mean if width_mean > 0 else 0
        
        # Find where width is minimum (bottleneck)
        min_idx = widths.index(width_min)
        bottleneck_y = width_profile[min_idx][0]
        bottleneck_position = bottleneck_y / height  # Normalized position (0=top, 1=bottom)
    else:
        width_min = width_max = width_mean = width_std = width_variation = 0
        bottleneck_y = bottleneck_position = 0
    
    # Analyze height profile
    if height_profile:
        heights = [h for _, h in height_profile]
        height_min = min(heights)
        height_max = max(heights)
        height_mean = np.mean(heights)
        height_std = np.std(heights)
        height_variation = (height_max - height_min) / height_mean if height_mean > 0 else 0
        
        min_idx = heights.index(height_min)
        bottleneck_x = height_profile[min_idx][0]
        bottleneck_horizontal = bottleneck_x / width
    else:
        height_min = height_max = height_mean = height_std = height_variation = 0
        bottleneck_x = bottleneck_horizontal = 0
    
    # Shape classification based on features
    shape_type = classify_shape(
        circularity, aspect_ratio, convexity, 
        width_variation, height_variation,
        bottleneck_position, bottleneck_horizontal
    )
    
    return {
        'slice_idx': slice_idx,
        'descriptors': {
            'circularity': float(circularity),
            'aspect_ratio': float(aspect_ratio),
            'extent': float(extent),
            'convexity': float(convexity),
            'solidity': float(solidity),
            'vertices': int(num_vertices)
        },
        'width_profile': {
            'min': int(width_min),
            'max': int(width_max),
            'mean': float(width_mean),
            'std': float(width_std),
            'variation': float(width_variation),
            'bottleneck_y': int(bottleneck_y),
            'bottleneck_pos': float(bottleneck_position)
        },
        'height_profile': {
            'min': int(height_min),
            'max': int(height_max),
            'mean': float(height_mean),
            'std': float(height_std),
            'variation': float(height_variation),
            'bottleneck_x': int(bottleneck_x),
            'bottleneck_pos': float(bottleneck_horizontal)
        },
        'classification': shape_type
    }


def classify_shape(circularity, aspect_ratio, convexity, 
                   width_var, height_var, bottleneck_y, bottleneck_x):
    """
    Classify the frame shape based on geometric features.
    """
    shapes = []
    
    # High circularity = round
    if circularity > 0.8:
        shapes.append("circular")
    elif circularity > 0.6:
        shapes.append("oval")
    
    # Low circularity + low convexity = ornate/complex
    if circularity < 0.5 and convexity < 0.8:
        shapes.append("ornate")
    
    # Aspect ratio
    if 0.95 < aspect_ratio < 1.05:
        shapes.append("square")
    elif aspect_ratio > 1.2:
        shapes.append("wide")
    elif aspect_ratio < 0.8:
        shapes.append("tall")
    
    # Width variation = tapered/shield shape
    if width_var > 0.3:
        if bottleneck_y > 0.6:
            shapes.append("shield_pointed_bottom")
        elif bottleneck_y < 0.4:
            shapes.append("shield_pointed_top")
        else:
            shapes.append("tapered")
    
    # Height variation = side constraints
    if height_var > 0.3:
        if bottleneck_x < 0.4:
            shapes.append("constrained_left")
        elif bottleneck_x > 0.6:
            shapes.append("constrained_right")
        else:
            shapes.append("constrained_sides")
    
    # High convexity = simple shape
    if convexity > 0.95:
        shapes.append("simple")
    
    # Default
    if not shapes:
        shapes.append("standard")
    
    return ", ".join(shapes)


def analyze_all_frames():
    """
    Analyze shapes of all frame files.
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
        
        if not frame_path.exists():
            continue
        
        print(f"Analyzing shape of {frame_name}...")
        
        # Load frame image
        img = Image.open(frame_path).convert('RGBA')
        img_data = np.array(img)
        
        # Analyze first slice (usually representative)
        shape_result = analyze_frame_shape(img_data, 0)
        
        if shape_result:
            results[frame_name] = shape_result
    
    return results


def write_report(results, output_path):
    """
    Write shape analysis results.
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("FRAME SHAPE SEMANTIC ANALYSIS\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("SHAPE CLASSIFICATIONS:\n")
        f.write("-" * 80 + "\n")
        for name, data in sorted(results.items()):
            f.write(f"{name:25s} {data['classification']}\n")
        f.write("\n")
        
        # Detailed analysis
        f.write("\n" + "=" * 80 + "\n")
        f.write("DETAILED SHAPE ANALYSIS\n")
        f.write("=" * 80 + "\n\n")
        
        for name, data in sorted(results.items()):
            f.write(f"\n{'=' * 80}\n")
            f.write(f"{name}\n")
            f.write(f"{'=' * 80}\n")
            f.write(f"Classification: {data['classification']}\n\n")
            
            desc = data['descriptors']
            f.write("Shape Descriptors:\n")
            f.write(f"  Circularity: {desc['circularity']:.3f} ")
            if desc['circularity'] > 0.8:
                f.write("(very round)\n")
            elif desc['circularity'] > 0.6:
                f.write("(somewhat round)\n")
            else:
                f.write("(angular/complex)\n")
            
            f.write(f"  Aspect ratio: {desc['aspect_ratio']:.3f} ")
            if 0.95 < desc['aspect_ratio'] < 1.05:
                f.write("(square-ish)\n")
            elif desc['aspect_ratio'] > 1.2:
                f.write("(wide)\n")
            else:
                f.write("(tall)\n")
            
            f.write(f"  Convexity: {desc['convexity']:.3f} ")
            if desc['convexity'] > 0.95:
                f.write("(simple/smooth)\n")
            else:
                f.write("(complex/detailed)\n")
            
            f.write(f"  Extent: {desc['extent']:.3f}\n")
            f.write(f"  Vertices: {desc['vertices']}\n\n")
            
            wp = data['width_profile']
            f.write("Width Profile (how width changes vertically):\n")
            f.write(f"  Range: {wp['min']}px to {wp['max']}px\n")
            f.write(f"  Mean: {wp['mean']:.1f}px (±{wp['std']:.1f})\n")
            f.write(f"  Variation: {wp['variation']:.2f} ")
            if wp['variation'] > 0.3:
                f.write("(highly variable - tapered shape)\n")
            elif wp['variation'] > 0.15:
                f.write("(somewhat variable)\n")
            else:
                f.write("(uniform width)\n")
            
            if wp['variation'] > 0.2:
                f.write(f"  Bottleneck at Y={wp['bottleneck_y']}px ")
                f.write(f"({wp['bottleneck_pos']:.1%} from top)\n")
            f.write("\n")
            
            hp = data['height_profile']
            f.write("Height Profile (how height changes horizontally):\n")
            f.write(f"  Range: {hp['min']}px to {hp['max']}px\n")
            f.write(f"  Mean: {hp['mean']:.1f}px (±{hp['std']:.1f})\n")
            f.write(f"  Variation: {hp['variation']:.2f} ")
            if hp['variation'] > 0.3:
                f.write("(highly variable - side constraints)\n")
            elif hp['variation'] > 0.15:
                f.write("(somewhat variable)\n")
            else:
                f.write("(uniform height)\n")
            
            if hp['variation'] > 0.2:
                f.write(f"  Bottleneck at X={hp['bottleneck_x']}px ")
                f.write(f"({hp['bottleneck_pos']:.1%} from left)\n")
            f.write("\n")


if __name__ == '__main__':
    print("Starting frame shape analysis...")
    results = analyze_all_frames()
    
    print(f"\nWriting report to {OUTPUT_FILE}...")
    write_report(results, OUTPUT_FILE)
    
    print("Shape analysis complete!")
