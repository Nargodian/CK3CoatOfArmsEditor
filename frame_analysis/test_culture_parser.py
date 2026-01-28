"""
Test script to parse CK3 culture files and extract frame scales.
This will be integrated into asset_converter.py later.
"""

import re
import os
import json
from collections import defaultdict

def parse_culture_frame_scales(culture_dir):
    """Parse all culture .txt files and extract frame → scale and offset mappings"""
    
    frame_scales = defaultdict(list)
    frame_offsets = defaultdict(list)
    culture_to_frame = {}  # Track which culture uses which frame
    
    for filename in os.listdir(culture_dir):
        if not filename.endswith('.txt'):
            continue
        
        filepath = os.path.join(culture_dir, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                lines = f.read().split('\n')
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            continue
        
        current_culture = None
        current_frame = None
        
        for line in lines:
            # Detect culture definition start
            culture_match = re.match(r'^(\w+)\s*=\s*\{', line)
            if culture_match:
                current_culture = culture_match.group(1)
                current_frame = None
                continue
            
            # Find house_coa_frame
            frame_match = re.search(r'house_coa_frame\s*=\s*(house_frame_\d+)', line)
            if frame_match and current_culture:
                current_frame = frame_match.group(1)
            
            # Find house_coa_mask_scale
            scale_match = re.search(r'house_coa_mask_scale\s*=\s*\{\s*([\d.]+)\s+([\d.]+)\s*\}', line)
            if scale_match and current_culture and current_frame:
                scale_x = float(scale_match.group(1))
                scale_y = float(scale_match.group(2))
                
                frame_scales[current_frame].append((scale_x, scale_y))
                culture_to_frame[current_culture] = {
                    'frame': current_frame,
                    'scale': [scale_x, scale_y]
                }
            
            # Find house_coa_mask_offset
            offset_match = re.search(r'house_coa_mask_offset\s*=\s*\{\s*([\d.-]+)\s+([\d.-]+)\s*\}', line)
            if offset_match and current_culture and current_frame:
                offset_x = float(offset_match.group(1))
                offset_y = float(offset_match.group(2))
                
                frame_offsets[current_frame].append((offset_x, offset_y))
                if current_culture in culture_to_frame:
                    culture_to_frame[current_culture]['offset'] = [offset_x, offset_y]
    
    # Build final dict with recommended scale per frame
    frame_scale_dict = {}
    frame_offset_dict = {}
    
    for frame_name, scales in frame_scales.items():
        unique_scales = sorted(set(scales))
        
        if len(unique_scales) == 1:
            # All cultures using this frame use same scale
            frame_scale_dict[frame_name] = list(unique_scales[0])
        else:
            # Multiple scales - pick most common
            from collections import Counter
            scale_counts = Counter(scales)
            most_common_scale = scale_counts.most_common(1)[0][0]
            frame_scale_dict[frame_name] = list(most_common_scale)
            print(f"WARNING: {frame_name} has multiple scales: {unique_scales}, using most common: {most_common_scale}")
    
    # Process offsets
    for frame_name, offsets in frame_offsets.items():
        unique_offsets = sorted(set(offsets))
        
        if len(unique_offsets) == 1:
            # All cultures using this frame use same offset
            frame_offset_dict[frame_name] = list(unique_offsets[0])
        else:
            # Multiple offsets - pick most common
            from collections import Counter
            offset_counts = Counter(offsets)
            most_common_offset = offset_counts.most_common(1)[0][0]
            frame_offset_dict[frame_name] = list(most_common_offset)
            print(f"WARNING: {frame_name} has multiple offsets: {unique_offsets}, using most common: {most_common_offset}")
    
    return frame_scale_dict, frame_offset_dict, culture_to_frame

if __name__ == "__main__":
    culture_dir = "E:/Program Files (x86)/Steam/steamapps/common/Crusader Kings III/game/common/culture/cultures"
    
    if not os.path.exists(culture_dir):
        print(f"ERROR: Culture directory not found: {culture_dir}")
        exit(1)
    
    print("Parsing CK3 culture files...")
    frame_scales, frame_offsets, culture_info = parse_culture_frame_scales(culture_dir)
    
    print(f"\nFound {len(frame_scales)} frames with scale data")
    print(f"Found {len(frame_offsets)} frames with offset data")
    print(f"Found {len(culture_info)} cultures\n")
    
    # Print results
    print("=== Frame Scales ===")
    for frame in sorted(frame_scales.keys()):
        scale = frame_scales[frame]
        offset = frame_offsets.get(frame, [0.0, 0.0])
        print(f"{frame:20s} -> scale: {scale}, offset: {offset}")
    
    # Test JSON output
    output_data = {
        'frame_scales': frame_scales,
        'frame_offsets': frame_offsets,
        'description': 'Auto-generated from CK3 culture files',
        'scale_values_used': sorted(list(set(tuple(v) for v in frame_scales.values())))
    }
    
    print("\n=== JSON Output ===")
    print(json.dumps(output_data, indent=2))
    
    # Save to file
    output_path = "e:/Projects/CK3CoatOfArmsEditor/ck3_assets/frame_scales.json"
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n✓ Saved to {output_path}")
