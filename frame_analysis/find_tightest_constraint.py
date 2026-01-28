"""
Find the tightest constraint (minimum radius) in each mask.
Theory: CK3 scales CoA to fit the narrowest point, everything else gets clamped.
"""

from PIL import Image
import numpy as np
import os

def find_minimum_radius(mask_path, num_directions=16):
    """Find the smallest distance to mask edge from center"""
    
    mask_img = Image.open(mask_path).convert('RGBA')
    mask_array = np.array(mask_img)
    
    # Interior: where alpha > 10
    interior = mask_array[:, :, 3] > 10
    
    height, width = interior.shape
    center_y, center_x = height // 2, width // 2
    
    # Cast rays in multiple directions
    angles = [i * (360.0 / num_directions) for i in range(num_directions)]
    distances = []
    
    for angle in angles:
        rad = np.radians(angle)
        dx_step = np.cos(rad)
        dy_step = np.sin(rad)
        
        # March outward until we hit the edge
        for dist in range(1, max(width, height)):
            x = int(center_x + dx_step * dist + 0.5)
            y = int(center_y - dy_step * dist + 0.5)  # -dy because image Y is down
            
            # Out of bounds or hit mask edge
            if x < 0 or x >= width or y < 0 or y >= height or not interior[y, x]:
                distances.append(dist - 1)
                break
        else:
            # Never hit edge (shouldn't happen)
            distances.append(max(width, height))
    
    return {
        'min': min(distances),
        'max': max(distances),
        'avg': np.mean(distances),
        'angles': angles,
        'distances': distances
    }

if __name__ == "__main__":
    base_dir = "e:/Projects/CK3CoatOfArmsEditor/ck3_assets/coa_frames"
    
    frames = [
        ('house_frame_02', 'baseline'),
        ('house_frame_06', 'needs 105.91%'),
        ('house_frame_13', 'full mask'),
        ('house_frame_22', 'needs 105.00%'),
    ]
    
    results = {}
    
    print("=== Finding Tightest Constraint (16 directions) ===\n")
    
    for frame_name, note in frames:
        mask_path = os.path.join(base_dir, f"{frame_name}_mask.png")
        
        if os.path.exists(mask_path):
            metrics = find_minimum_radius(mask_path, 16)
            results[frame_name] = metrics
            
            # Find which angle has the minimum
            min_idx = metrics['distances'].index(metrics['min'])
            min_angle = metrics['angles'][min_idx]
            
            print(f"{frame_name} ({note}):")
            print(f"  Min radius: {metrics['min']}px at {min_angle:.1f}°")
            print(f"  Max radius: {metrics['max']}px")
            print(f"  Avg radius: {metrics['avg']:.1f}px")
            print(f"  Max/Min ratio: {metrics['max']/metrics['min']:.3f}")
            print()
    
    # Compare to baseline
    if 'house_frame_02' in results:
        baseline_min = results['house_frame_02']['min']
        print("\n=== Scale Relative to frame_02 (based on minimum radius) ===")
        print("(CoA scaled to fit tightest constraint)\n")
        
        for frame_name, note in frames:
            if frame_name in results:
                frame_min = results[frame_name]['min']
                # Smaller min = tighter constraint = need larger CoA scale
                scale_needed = baseline_min / frame_min
                
                print(f"{frame_name}: {scale_needed:.4f}x ({scale_needed*100:.2f}%)")
