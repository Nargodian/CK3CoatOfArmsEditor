"""
Measure the effective size of masks using various metrics.
Theory: CK3 measures something simple about the mask geometry 
to determine CoA scale, independent of the frame graphic.
"""

from PIL import Image
import numpy as np
from scipy import ndimage
import os

def measure_mask_effective_size(mask_path):
    """Measure mask interior using multiple methods"""
    
    mask_img = Image.open(mask_path).convert('RGBA')
    mask_array = np.array(mask_img)
    
    # Interior: where alpha > 10
    interior = mask_array[:, :, 3] > 10
    
    height, width = interior.shape
    center_y, center_x = height // 2, width // 2
    
    # Method 1: 4-direction cross (what we already have)
    distances_4 = []
    for dy in range(1, center_y + 1):
        if not interior[center_y - dy, center_x]:
            distances_4.append(dy - 1)
            break
    else:
        distances_4.append(center_y)
    for dy in range(1, height - center_y):
        if not interior[center_y + dy, center_x]:
            distances_4.append(dy - 1)
            break
    else:
        distances_4.append(height - center_y - 1)
    for dx in range(1, center_x + 1):
        if not interior[center_y, center_x - dx]:
            distances_4.append(dx - 1)
            break
    else:
        distances_4.append(center_x)
    for dx in range(1, width - center_x):
        if not interior[center_y, center_x + dx]:
            distances_4.append(dx - 1)
            break
    else:
        distances_4.append(width - center_x - 1)
    
    cross_4_min = min(distances_4) if distances_4 else 0
    cross_4_avg = np.mean(distances_4) if distances_4 else 0
    
    # Method 2: 8-direction star
    distances_8 = []
    angles_8 = [0, 45, 90, 135, 180, 225, 270, 315]
    for angle in angles_8:
        rad = np.radians(angle)
        dx_step = np.cos(rad)
        dy_step = np.sin(rad)
        
        for dist in range(1, max(width, height)):
            x = int(center_x + dx_step * dist)
            y = int(center_y - dy_step * dist)  # -dy because image Y is down
            
            if x < 0 or x >= width or y < 0 or y >= height:
                distances_8.append(dist - 1)
                break
            if not interior[y, x]:
                distances_8.append(dist - 1)
                break
    
    star_8_min = min(distances_8) if distances_8 else 0
    star_8_avg = np.mean(distances_8) if distances_8 else 0
    
    # Method 3: 16-direction star
    distances_16 = []
    angles_16 = [i * 22.5 for i in range(16)]
    for angle in angles_16:
        rad = np.radians(angle)
        dx_step = np.cos(rad)
        dy_step = np.sin(rad)
        
        for dist in range(1, max(width, height)):
            x = int(center_x + dx_step * dist)
            y = int(center_y - dy_step * dist)
            
            if x < 0 or x >= width or y < 0 or y >= height:
                distances_16.append(dist - 1)
                break
            if not interior[y, x]:
                distances_16.append(dist - 1)
                break
    
    star_16_min = min(distances_16) if distances_16 else 0
    star_16_avg = np.mean(distances_16) if distances_16 else 0
    
    # Method 4: Harmonic mean (emphasizes smaller values)
    harmonic_8 = len(distances_8) / sum(1/d if d > 0 else 0 for d in distances_8) if distances_8 else 0
    harmonic_16 = len(distances_16) / sum(1/d if d > 0 else 0 for d in distances_16) if distances_16 else 0
    
    return {
        'cross_4_min': cross_4_min,
        'cross_4_avg': cross_4_avg,
        'star_8_min': star_8_min,
        'star_8_avg': star_8_avg,
        'star_16_min': star_16_min,
        'star_16_avg': star_16_avg,
        'harmonic_8': harmonic_8,
        'harmonic_16': harmonic_16,
    }

if __name__ == "__main__":
    base_dir = "e:/Projects/CK3CoatOfArmsEditor/ck3_assets/coa_frames"
    
    frames = [
        ('house_frame_02', 'baseline - 100%'),
        ('house_frame_06', 'needs 105.91% scale'),
        ('house_frame_22', 'needs 105.00% scale'),
    ]
    
    results = {}
    
    print("=== Mask Effective Size Analysis ===\n")
    
    for frame_name, note in frames:
        mask_path = os.path.join(base_dir, f"{frame_name}_mask.png")
        
        if os.path.exists(mask_path):
            metrics = measure_mask_effective_size(mask_path)
            results[frame_name] = metrics
            
            print(f"{frame_name} ({note}):")
            print(f"  4-dir cross min: {metrics['cross_4_min']:.1f}px")
            print(f"  4-dir cross avg: {metrics['cross_4_avg']:.1f}px")
            print(f"  8-dir star min:  {metrics['star_8_min']:.1f}px")
            print(f"  8-dir star avg:  {metrics['star_8_avg']:.1f}px")
            print(f"  16-dir star min: {metrics['star_16_min']:.1f}px")
            print(f"  16-dir star avg: {metrics['star_16_avg']:.1f}px")
            print(f"  8-dir harmonic:  {metrics['harmonic_8']:.1f}px")
            print(f"  16-dir harmonic: {metrics['harmonic_16']:.1f}px")
            print()
    
    # Compare to baseline
    if 'frame_02' in results:
        baseline = results['frame_02']
        print("\n=== Ratios relative to frame_02 ===")
        print("(Smaller ratio = needs larger CoA scale)\n")
        
        for frame_name, _ in frames:
            if frame_name != 'frame_02' and frame_name in results:
                metrics = results[frame_name]
                
                print(f"{frame_name}:")
                for key in baseline.keys():
                    if baseline[key] > 0:
                        ratio = metrics[key] / baseline[key]
                        scale_needed = 1.0 / ratio
                        print(f"  {key:20s}: {ratio:.4f}  -> scale {scale_needed:.4f}x ({scale_needed*100:.2f}%)")
                print()
