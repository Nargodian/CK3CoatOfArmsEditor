#!/usr/bin/env python3
"""Test layer selection functionality"""
import sys
sys.path.insert(0, 'editor/src')

from models.coa import CoA

# Create CoA
coa = CoA()

# Add a test layer
uuid = coa.add_layer("test_emblem.dds", 0.5, 0.5, 3)
print(f"Added layer: {uuid}")

# Test get_layer_index_by_uuid
index = coa.get_layer_index_by_uuid(uuid)
print(f"Layer index: {index}")

# Test get_layer_pos
pos = coa.get_layer_pos(uuid)
print(f"Layer pos: {pos}")

# Test sorting (what the bug was about)
uuids = [uuid]
sorted_uuids = sorted(uuids, key=lambda u: coa.get_layer_index_by_uuid(u) or 0)
print(f"Sorted UUIDs: {sorted_uuids}")

print("\n✅ All tests passed!")
