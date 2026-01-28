"""
Compare the effective interior size of frame graphics vs their masks.
The mask defines the CoA clipping shape, but the frame graphic shows 
what's visually displayed. If the mask is larger/smaller than the visual
frame interior, CoA scale needs adjustment.
"""

from PIL import Image
import numpy as np
import os

def analyze_mask_vs_frame(frame_name, frame_path, mask_path):
    """Compare interior space: mask vs frame graphic"""
    
    frame_img = Image.open(frame_path).convert('RGBA')
    mask_img = Image.open(mask_path).convert('RGBA')
    
    frame_array = np.array(frame_img)
    mask_array = np.array(mask_img)
    
    # Mask interior: where alpha > 10
    mask_interior = mask_array[:, :, 3] > 10
    
    # Frame interior: where alpha < 250 (transparent/semi-transparent = interior)
    # The frame graphic draws the border, so low alpha = interior space
    frame_interior = frame_array[:, :, 3] < 250
    
    # Measure from center in 4 directions
    center_y, center_x = frame_array.shape[0] // 2, frame_array.shape[1] // 2
    
    # Mask measurements (how far CoA can extend)
    mask_up = mask_down = mask_left = mask_right = 0
    for dy in range(center_y):
        if mask_interior[center_y - dy, center_x]:
            mask_up = dy
        else:
            break
    for dy in range(center_y):
        if mask_interior[center_y + dy, center_x]:
            mask_down = dy
        else:
            break
    for dx in range(center_x):
        if mask_interior[center_y, center_x - dx]:
            mask_left = dx
        else:
            break
    for dx in range(center_x):
        if mask_interior[center_y, center_x + dx]:
            mask_right = dx
        else:
            break
    
    # Frame measurements (visual interior space)
    frame_up = frame_down = frame_left = frame_right = 0
    for dy in range(center_y):
        if frame_interior[center_y - dy, center_x]:
            frame_up = dy
        else:
            break
    for dy in range(center_y):
        if frame_interior[center_y + dy, center_x]:
            frame_down = dy
        else:
            break
    for dx in range(center_x):
        if frame_interior[center_y, center_x - dx]:
            frame_left = dx
        else:
            break
    for dx in range(center_x):
        if frame_interior[center_y, center_x + dx]:
            frame_right = dx
        else:
            break
    
    # Calculate inscribed square for both
    mask_inscribed = min(mask_up, mask_down, mask_left, mask_right)
    frame_inscribed = min(frame_up, frame_down, frame_left, frame_right)
    
    # The ratio tells us how much the mask differs from visual frame
    ratio = mask_inscribed / frame_inscribed if frame_inscribed > 0 else 0
    
    print(f"\n{frame_name}:")
    print(f"  Mask inscribed:  {mask_inscribed}px (up={mask_up}, down={mask_down}, left={mask_left}, right={mask_right})")
    print(f"  Frame inscribed: {frame_inscribed}px (up={frame_up}, down={frame_down}, left={frame_left}, right={frame_right})")
    print(f"  Mask/Frame ratio: {ratio:.4f}")
    print(f"  -> CoA scale should be: {1.0 / ratio:.4f}x" if ratio > 0 else "  -> ERROR")
    
    return ratio

if __name__ == "__main__":
    base_dir = "e:/Projects/CK3CoatOfArmsEditor/ck3_assets/coa_frames/source"
    
    frames_to_check = [
        'frame_02',  # User's baseline
        'frame_06',  # Needs 105.91% scale
        'frame_22',  # Needs 105% scale
    ]
    
    ratios = {}
    for frame_name in frames_to_check:
        frame_path = os.path.join(base_dir, f"{frame_name}.png")
        mask_path = os.path.join(base_dir, f"{frame_name}_mask.png")
        
        if os.path.exists(frame_path) and os.path.exists(mask_path):
            ratios[frame_name] = analyze_mask_vs_frame(frame_name, frame_path, mask_path)
    
    # Compare ratios
    if 'frame_02' in ratios:
        print(f"\n=== Comparison to frame_02 (baseline) ===")
        baseline = ratios['frame_02']
        for frame_name, ratio in ratios.items():
            if frame_name != 'frame_02':
                relative = ratio / baseline
                print(f"{frame_name}: {relative:.4f}x (needs {1.0/relative:.4f}x scale adjustment)")
