"""
Test what canvas_area.py actually receives during transforms
"""
import sys
sys.path.insert(0, 'editor/src')

from services.file_operations import load_coa_from_file
from utils.coa_parser import convert_to_internal_format

# Load and convert a real file
print("=== Loading real game file ===")
coa_data = load_coa_from_file('examples/game_samples/coa_sample_0.txt')
coa_key = list(coa_data.keys())[0]
coa = coa_data[coa_key]

print("=== Converting to internal format ===")
layers = convert_to_internal_format(coa)

print(f"\nNumber of layers: {len(layers)}")

import json
for i, layer in enumerate(layers):
    print(f"\n--- Layer {i} ---")
    print(f"Type: {layer.get('type')}")
    print(f"Asset ID: {layer.get('asset_id', 'N/A')}")
    
    # Check what format this layer is in
    has_pos_x = 'pos_x' in layer
    has_instances = 'instances' in layer
    
    print(f"Has 'pos_x' at root: {has_pos_x}")
    print(f"Has 'instances': {has_instances}")
    
    if has_pos_x:
        print(f"  OLD FORMAT: pos_x={layer['pos_x']}, pos_y={layer['pos_y']}, scale_x={layer['scale_x']}")
    
    if has_instances:
        print(f"  NEW FORMAT: {len(layer['instances'])} instance(s)")
        print(f"  Selected instance: {layer.get('selected_instance', 0)}")
        if layer['instances']:
            inst = layer['instances'][0]
            print(f"  Instance[0]: pos_x={inst.get('pos_x')}, pos_y={inst.get('pos_y')}, scale_x={inst.get('scale_x')}")
    
    if i >= 2:  # Just show first few layers
        print(f"\n... ({len(layers) - 3} more layers)")
        break

print("\n=== QUESTION: What does canvas_area.py receive? ===")
print("When transform_widget calls _on_transform_changed(), what format are the layers in?")
print("Answer: It receives self.property_sidebar.layers")
print("\nLet's simulate what property_sidebar would have after loading this file...")
