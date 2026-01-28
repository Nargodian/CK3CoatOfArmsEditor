"""
Parse CK3 culture files to extract frame → scale mappings.
"""

import re
import os
from collections import defaultdict

culture_dir = "E:/Program Files (x86)/Steam/steamapps/common/Crusader Kings III/game/common/culture/cultures"

# Pattern to match culture blocks
# culture_name = {
#     ...
#     coa_gfx = { house_frame_XX }
#     house_coa_mask_scale = { X.XX X.XX }
#     ...
# }

frame_scales = defaultdict(list)  # frame_name -> [scales]

for filename in os.listdir(culture_dir):
    if not filename.endswith('.txt'):
        continue
    
    filepath = os.path.join(culture_dir, filename)
    
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    
    # Look for patterns like:
    # house_coa_frame = house_frame_29
    # house_coa_mask_scale = { 0.95 0.95 }
    
    # Find all culture blocks - match culture_name = { ... }
    # Use a simpler approach: find house_coa_frame and house_coa_mask_scale on nearby lines
    
    lines = content.split('\n')
    
    current_culture = None
    current_frame = None
    
    for i, line in enumerate(lines):
        # Detect culture start (name at start of line followed by = {)
        culture_start = re.match(r'^(\w+)\s*=\s*\{', line)
        if culture_start:
            current_culture = culture_start.group(1)
            current_frame = None
            continue
        
        # Look for house_coa_frame
        frame_match = re.search(r'house_coa_frame\s*=\s*(house_frame_\d+)', line)
        if frame_match and current_culture:
            current_frame = frame_match.group(1)
        
        # Look for house_coa_mask_scale
        scale_match = re.search(r'house_coa_mask_scale\s*=\s*\{\s*([\d.]+)\s+([\d.]+)\s*\}', line)
        if scale_match and current_culture and current_frame:
            scale_x = float(scale_match.group(1))
            scale_y = float(scale_match.group(2))
            frame_scales[current_frame].append((current_culture, scale_x, scale_y))

# Print results
print("=== Frame → Scale Mappings from Culture Files ===\n")

for frame_name in sorted(frame_scales.keys()):
    scales = frame_scales[frame_name]
    
    # Get unique scale values
    unique_scales = sorted(set((s[1], s[2]) for s in scales))
    
    print(f"{frame_name}:")
    print(f"  Used by {len(scales)} cultures")
    print(f"  Scale values: {unique_scales}")
    
    if len(unique_scales) == 1:
        print(f"  → Recommended: {unique_scales[0]}")
    else:
        # Find most common
        scale_counts = defaultdict(int)
        for _, sx, sy in scales:
            scale_counts[(sx, sy)] += 1
        
        most_common = max(scale_counts.items(), key=lambda x: x[1])
        print(f"  → Most common: {most_common[0]} ({most_common[1]} cultures)")
    
    print()

# Summary
print("\n=== Summary ===")
all_scales = set()
for scales in frame_scales.values():
    for _, sx, sy in scales:
        all_scales.add((sx, sy))

print(f"Total unique frames: {len(frame_scales)}")
print(f"Scale values used: {sorted(all_scales)}")
