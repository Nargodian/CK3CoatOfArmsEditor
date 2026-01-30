"""Test the _layers protection mechanism"""

import sys
sys.path.insert(0, 'editor/src')

from models.coa import CoA

# Create a CoA instance
coa = CoA()

# This should work - calling public method
print("Testing public method (should work):")
layer_uuid = coa.add_layer("test.dds")
print(f"✓ Successfully added layer via public method: {layer_uuid}")

# This should FAIL with AttributeError
print("\nTesting direct _layers access (should fail):")
try:
    layers = coa._layers
    print("✗ ERROR: Direct access was allowed!")
except AttributeError as e:
    print(f"✓ Successfully blocked: {e}")

print("\nTest complete!")
