"""
Test Phase 4: Container Operations

This test verifies Phase 4 implementation:
- Container selection (multi-selects all layers)
- Container duplication (new container_uuid, duplicate all layers)
- Create container from layers (regroups at highest position)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'editor', 'src'))

from models.coa import CoA


def test_container_selection():
	"""Test that getting container layers works (selection is UI only)"""
	print("\n=== Test: Container Selection ===")
	
	coa = CoA()
	
	# Create layers
	lion1 = coa.add_layer(emblem_path="ce_lion.dds")
	lion2 = coa.add_layer(emblem_path="ce_lion.dds")
	cross = coa.add_layer(emblem_path="ce_cross.dds")
	
	# Assign to container
	container_uuid = coa.generate_container_uuid("Animals")
	coa.set_layer_container(lion1, container_uuid)
	coa.set_layer_container(lion2, container_uuid)
	
	# Get container layers
	container_layers = set(coa.get_layers_by_container(container_uuid))
	
	print(f"Container has {len(container_layers)} layers")
	assert len(container_layers) == 2, f"Expected 2 layers, got {len(container_layers)}"
	assert lion1 in container_layers and lion2 in container_layers, "Wrong layers in container"
	print("✓ Container selection works")


def test_container_duplicate():
	"""Test duplicating an entire container"""
	print("\n=== Test: Container Duplicate ===")
	
	coa = CoA()
	
	# Create container with layers
	lion1 = coa.add_layer(emblem_path="ce_lion.dds")
	lion2 = coa.add_layer(emblem_path="ce_lion.dds")
	
	original_container = coa.generate_container_uuid("Lions")
	coa.set_layer_container(lion1, original_container)
	coa.set_layer_container(lion2, original_container)
	
	print(f"Original container: {original_container}")
	print(f"Original layers: {coa.get_layers_by_container(original_container)}")
	
	# Duplicate container
	new_container = coa.duplicate_container(original_container)
	
	print(f"New container: {new_container}")
	print(f"New layers: {coa.get_layers_by_container(new_container)}")
	
	# Verify new container exists
	assert new_container != original_container, "Container UUID should be different"
	
	# Verify new container has same name
	original_name = original_container.split('_', 2)[2]
	new_name = new_container.split('_', 2)[2]
	assert original_name == new_name, f"Names should match: {original_name} vs {new_name}"
	print(f"✓ Container name preserved: {new_name}")
	
	# Verify new container has same number of layers
	original_layers = coa.get_layers_by_container(original_container)
	new_layers = coa.get_layers_by_container(new_container)
	assert len(new_layers) == len(original_layers), \
		f"Expected {len(original_layers)} layers, got {len(new_layers)}"
	print(f"✓ Duplicated {len(new_layers)} layers")
	
	# Verify layer UUIDs are different
	for old_uuid, new_uuid in zip(original_layers, new_layers):
		assert old_uuid != new_uuid, "Layer UUIDs should be different"
	print("✓ All layer UUIDs are unique")
	
	# Verify total layers
	total_layers = len(coa.get_all_layer_uuids())
	assert total_layers == 4, f"Expected 4 total layers, got {total_layers}"
	print(f"✓ Total layers: {total_layers}")


def test_create_container_from_layers():
	"""Test creating container from selected layers"""
	print("\n=== Test: Create Container from Layers ===")
	
	coa = CoA()
	
	# Create layers at different positions
	layer1 = coa.add_layer(emblem_path="ce_lion.dds")  # index 0
	layer2 = coa.add_layer(emblem_path="ce_cross.dds")  # index 1
	layer3 = coa.add_layer(emblem_path="ce_star.dds")  # index 2
	layer4 = coa.add_layer(emblem_path="ce_circle.dds")  # index 3
	
	print("Initial layer order:")
	for i, uuid in enumerate(coa.get_all_layer_uuids()):
		print(f"  {i}: {uuid[:8]}... ({coa.get_layer_filename(uuid)})")
	
	# Group non-contiguous layers (0, 2)
	selected_layers = [layer1, layer3]
	new_container = coa.create_container_from_layers(selected_layers, name="Selected")
	
	print(f"\nCreated container: {new_container}")
	print("New layer order:")
	for i, uuid in enumerate(coa.get_all_layer_uuids()):
		container = coa.get_layer_container(uuid)
		container_str = container.split('_', 2)[2] if container else "root"
		print(f"  {i}: {uuid[:8]}... ({coa.get_layer_filename(uuid)}) - {container_str}")
	
	# Verify container created
	assert new_container is not None, "Container should be created"
	
	# Verify layers assigned to container
	container_layers = coa.get_layers_by_container(new_container)
	assert len(container_layers) == 2, f"Expected 2 layers, got {len(container_layers)}"
	assert set(container_layers) == set(selected_layers), "Wrong layers in container"
	print(f"✓ Container has {len(container_layers)} layers")
	
	# Verify layers are contiguous (next to each other)
	indices = []
	for uuid in container_layers:
		idx = coa.get_all_layer_uuids().index(uuid)
		indices.append(idx)
	indices.sort()
	
	for i in range(len(indices) - 1):
		assert indices[i+1] - indices[i] == 1, \
			f"Layers not contiguous: {indices}"
	print(f"✓ Container layers are contiguous at positions {indices}")


def test_roundtrip_with_operations():
	"""Test container operations with serialization roundtrip"""
	print("\n=== Test: Roundtrip with Container Operations ===")
	
	coa1 = CoA()
	
	# Create container
	lion1 = coa1.add_layer(emblem_path="ce_lion.dds")
	lion2 = coa1.add_layer(emblem_path="ce_lion.dds")
	container1 = coa1.generate_container_uuid("TestGroup")
	coa1.set_layer_container(lion1, container1)
	coa1.set_layer_container(lion2, container1)
	
	# Duplicate container
	container2 = coa1.duplicate_container(container1)
	
	# Serialize
	serialized = coa1.to_string()
	
	# Parse
	coa2 = CoA.from_string(serialized)
	
	# Verify both containers exist
	containers = coa2.get_all_containers()
	print(f"Containers after roundtrip: {len(containers)}")
	assert len(containers) == 2, f"Expected 2 containers, got {len(containers)}"
	
	# Verify each container has layers
	for container_uuid in containers:
		layers = coa2.get_layers_by_container(container_uuid)
		assert len(layers) == 2, f"Container should have 2 layers, got {len(layers)}"
	
	print("✓ Containers and operations preserved through roundtrip")


def run_all_tests():
	"""Run all Phase 4 tests"""
	print("=" * 60)
	print("PHASE 4 TESTS: Container Operations")
	print("=" * 60)
	
	try:
		test_container_selection()
		test_container_duplicate()
		test_create_container_from_layers()
		test_roundtrip_with_operations()
		
		print("\n" + "=" * 60)
		print("ALL PHASE 4 TESTS PASSED ✓")
		print("=" * 60)
		return True
		
	except Exception as e:
		print("\n" + "=" * 60)
		print(f"TEST FAILED ✗")
		print(f"Error: {e}")
		print("=" * 60)
		import traceback
		traceback.print_exc()
		return False


if __name__ == "__main__":
	success = run_all_tests()
	sys.exit(0 if success else 1)
