"""
Try different aggregation methods to find what correlates with observed scaling.
"""

from PIL import Image
import numpy as np
import os
from scipy import stats

def analyze_mask_radii(mask_path, num_directions=16):
    """Measure radii and try different aggregations"""
    
    mask_img = Image.open(mask_path).convert('RGBA')
    mask_array = np.array(mask_img)
    
    interior = mask_array[:, :, 3] > 10
    height, width = interior.shape
    center_y, center_x = height // 2, width // 2
    
    angles = [i * (360.0 / num_directions) for i in range(num_directions)]
    distances = []
    
    for angle in angles:
        rad = np.radians(angle)
        dx_step = np.cos(rad)
        dy_step = np.sin(rad)
        
        for dist in range(1, max(width, height)):
            x = int(center_x + dx_step * dist + 0.5)
            y = int(center_y - dy_step * dist + 0.5)
            
            if x < 0 or x >= width or y < 0 or y >= height or not interior[y, x]:
                distances.append(dist - 1)
                break
        else:
            distances.append(max(width, height))
    
    distances = np.array(distances)
    
    # Try different metrics
    return {
        'min': np.min(distances),
        'percentile_10': np.percentile(distances, 10),
        'percentile_25': np.percentile(distances, 25),
        'harmonic_mean': stats.hmean(distances),
        'geometric_mean': stats.gmean(distances),
        'median': np.median(distances),
        'mean': np.mean(distances),
    }

if __name__ == "__main__":
    base_dir = "e:/Projects/CK3CoatOfArmsEditor/ck3_assets/coa_frames"
    
    frames = [
        ('house_frame_02', '100.00%', 1.0000),
        ('house_frame_06', '105.91%', 1.0591),
        ('house_frame_22', '105.00%', 1.0500),
    ]
    
    results = {}
    
    print("=== Testing Different Aggregation Methods ===\n")
    
    for frame_name, note, observed_scale in frames:
        mask_path = os.path.join(base_dir, f"{frame_name}_mask.png")
        
        if os.path.exists(mask_path):
            metrics = analyze_mask_radii(mask_path, 16)
            results[frame_name] = metrics
            
            print(f"{frame_name} (observed: {note}):")
            for key, value in metrics.items():
                print(f"  {key:20s}: {value:.2f}px")
            print()
    
    # Compare each metric to observed scaling
    if 'house_frame_02' in results:
        baseline = results['house_frame_02']
        
        print("\n=== Which Metric Matches Observed Scaling? ===\n")
        
        metric_names = list(baseline.keys())
        
        for metric in metric_names:
            print(f"\n{metric}:")
            print(f"  {'Frame':<20s} {'Predicted Scale':<20s} {'Observed Scale':<20s} {'Error':<10s}")
            print(f"  {'-'*70}")
            
            for frame_name, note, observed_scale in frames:
                if frame_name in results:
                    # Inverse ratio: smaller radius = need bigger scale
                    predicted_scale = baseline[metric] / results[frame_name][metric]
                    error = abs(predicted_scale - observed_scale)
                    
                    print(f"  {frame_name:<20s} {predicted_scale:.4f} ({predicted_scale*100:.2f}%) {observed_scale:.4f} ({observed_scale*100:.2f}%) {error:.4f}")
