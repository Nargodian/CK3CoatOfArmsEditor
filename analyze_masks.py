"""Analyze mask files to understand their pixel values"""
from PIL import Image
import numpy as np
import os

mask_dir = "coa_frames"

# Get a few example masks
mask_files = [
    "house_mask.png",
    "house_china_mask.png",
    "house_japan_mask.png",
    "dynasty_mask.png"
]

for mask_file in mask_files:
    mask_path = os.path.join(mask_dir, mask_file)
    if not os.path.exists(mask_path):
        print(f"Skipping {mask_file} - not found")
        continue
    
    print(f"\n=== {mask_file} ===")
    img = Image.open(mask_path).convert('RGBA')
    data = np.array(img)
    
    height, width = data.shape[:2]
    center_y, center_x = height // 2, width // 2
    
    # Get center pixel
    center_pixel = data[center_y, center_x]
    print(f"Size: {width}x{height}")
    print(f"Center pixel ({center_x}, {center_y}): RGBA = {center_pixel}")
    
    # Get corner pixels
    print(f"Top-left (0, 0): RGBA = {data[0, 0]}")
    print(f"Top-right (0, {width-1}): RGBA = {data[0, width-1]}")
    print(f"Bottom-left ({height-1}, 0): RGBA = {data[height-1, 0]}")
    print(f"Bottom-right ({height-1}, {width-1}): RGBA = {data[height-1, width-1]}")
    
    # Get edge midpoints
    print(f"Top edge ({center_y}, 0): RGBA = {data[0, center_x]}")
    print(f"Bottom edge ({height-1}, {center_x}): RGBA = {data[height-1, center_x]}")
    print(f"Left edge ({center_y}, 0): RGBA = {data[center_y, 0]}")
    print(f"Right edge ({center_y}, {width-1}): RGBA = {data[center_y, width-1]}")
    
    # Statistics
    print(f"\nRGB Statistics:")
    print(f"  R: min={data[:,:,0].min()}, max={data[:,:,0].max()}, mean={data[:,:,0].mean():.1f}")
    print(f"  G: min={data[:,:,1].min()}, max={data[:,:,1].max()}, mean={data[:,:,1].mean():.1f}")
    print(f"  B: min={data[:,:,2].min()}, max={data[:,:,2].max()}, mean={data[:,:,2].mean():.1f}")
    print(f"  A: min={data[:,:,3].min()}, max={data[:,:,3].max()}, mean={data[:,:,3].mean():.1f}")
