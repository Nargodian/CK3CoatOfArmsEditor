#!/usr/bin/env python3
"""Quick test to check Layer property values after parsing"""

import sys
sys.path.insert(0, 'editor/src')

from models.coa import CoA

# Load the sample file
with open('examples/game_samples/coa_sample_2.txt', 'r') as f:
    coa_text = f.read()

# Parse it
coa = CoA.from_string(coa_text)

print(f"Total layers: {coa.get_layer_count()}")
print()

# Check first layer (should be lowest depth - ce_kamon_sorrel)
if coa.get_layer_count() > 0:
    layer = coa._layers[0]
    print(f"Layer 0: {layer.filename}")
    print(f"  Instance count: {layer.instance_count}")
    print(f"  Selected instance: {layer.selected_instance}")
    print(f"  pos_x property: {layer.pos_x}")
    print(f"  pos_y property: {layer.pos_y}")
    print(f"  scale_x property: {layer.scale_x}")
    print(f"  scale_y property: {layer.scale_y}")
    print(f"  rotation property: {layer.rotation}")
    print()
    print("  Raw instances data:")
    for i, inst in enumerate(layer._data.get('instances', [])):
        print(f"    Instance {i}: {inst}")
    print()
    
    # Now simulate what main.py does - convert to dict
    layer_dict = {
        'uuid': layer.uuid,
        'filename': layer.filename,
        'pos_x': layer.pos_x,
        'pos_y': layer.pos_y,
        'scale_x': layer.scale_x,
        'scale_y': layer.scale_y,
        'rotation': layer.rotation,
        'depth': 0,
        'color1': layer.color1,
        'color2': layer.color2,
        'color3': layer.color3,
    }
    print("  Layer dict (as created by main.py):")
    print(f"    pos_x: {layer_dict['pos_x']}")
    print(f"    pos_y: {layer_dict['pos_y']}")
    print(f"    scale_x: {layer_dict['scale_x']}")
    print(f"    scale_y: {layer_dict['scale_y']}")
    print(f"    rotation: {layer_dict['rotation']}")
    print()
    
    # Simulate what canvas_area.py does - read from dict
    pos_x = layer_dict.get('pos_x', 0.5)
    pos_y = layer_dict.get('pos_y', 0.5)
    scale_x = layer_dict.get('scale_x', 0.5)
    scale_y = layer_dict.get('scale_y', 0.5)
    rotation = layer_dict.get('rotation', 0)
    print("  Values read by canvas_area.py:")
    print(f"    pos_x: {pos_x}")
    print(f"    pos_y: {pos_y}")
    print(f"    scale_x: {scale_x}")
    print(f"    scale_y: {scale_y}")
    print(f"    rotation: {rotation}")

