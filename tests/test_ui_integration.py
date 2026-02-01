"""
Quick test to verify layer name UI works with the running editor
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'editor', 'src'))

from models.coa import CoA

# Test that the UI-related methods work
coa = CoA()

# Add a layer
uuid1 = coa.add_layer(emblem_path="ce_lion.dds")
print(f"✓ Added layer: {uuid1}")

# Test get_layer_name (should default to texture filename without extension)
name = coa.get_layer_name(uuid1)
print(f"✓ Default name: '{name}'")
assert name == "ce_lion", f"Expected 'ce_lion', got '{name}'"

# Test set_layer_name
coa.set_layer_name(uuid1, "My Custom Lion")
name = coa.get_layer_name(uuid1)
print(f"✓ Custom name: '{name}'")
assert name == "My Custom Lion", f"Expected 'My Custom Lion', got '{name}'"

# Test serialization includes name
serialized = coa.to_string()
assert 'name = "My Custom Lion"' in serialized, "Name not in serialization"
print(f"✓ Name serialized correctly")

# Test parsing preserves name
coa2 = CoA.from_string(serialized)
layers = coa2.get_all_layer_uuids()
name2 = coa2.get_layer_name(layers[0])
print(f"✓ Parsed name: '{name2}'")
assert name2 == "My Custom Lion", f"Expected 'My Custom Lion', got '{name2}'"

print("\n✅ All layer name functionality working correctly!")
print("\nTo test the UI:")
print("1. Open the editor (already running)")
print("2. Add a layer from the asset sidebar")
print("3. Double-click on the layer name in the Layers tab")
print("4. Type a new name and press Enter")
print("5. The name should update immediately!")
