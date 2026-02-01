"""
Test Phase 5: Drag and Drop for Containers

This test verifies Phase 5 implementation:
- Layer drag to root zone (sets container_uuid=None)
- Layer drag to sub zone (sets container_uuid to target)
- Container drag to root zone (repositions all layers)
- Container drag logic (no nesting)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'editor', 'src'))

from models.coa import CoA


def test_layer_move_between_containers():
	"""Test moving layers between containers"""
	print("\n=== Test: Layer Move Between Containers ===")
	
	coa = CoA()
	
	# Create two containers
	lion1 = coa.add_layer(emblem_path="ce_lion.dds")
	lion2 = coa.add_layer(emblem_path="ce_lion.dds")
	cross1 = coa.add_layer(emblem_path="ce_cross.dds")
	cross2 = coa.add_layer(emblem_path="ce_cross.dds")
	
	container_a = coa.generate_container_uuid("Animals")
	container_b = coa.generate_container_uuid("Symbols")
	
	coa.set_layer_container(lion1, container_a)
	coa.set_layer_container(lion2, container_a)
	coa.set_layer_container(cross1, container_b)
	coa.set_layer_container(cross2, container_b)
	
	print(f"Initial state:")
	print(f"  Container A: {len(coa.get_layers_by_container(container_a))} layers")
	print(f"  Container B: {len(coa.get_layers_by_container(container_b))} layers")
	
	# Simulate drag: move lion1 from container A to container B
	coa.set_layer_container(lion1, container_b)
	
	print(f"After moving lion1 to Container B:")
	print(f"  Container A: {len(coa.get_layers_by_container(container_a))} layers")
	print(f"  Container B: {len(coa.get_layers_by_container(container_b))} layers")
	
	assert len(coa.get_layers_by_container(container_a)) == 1, "Container A should have 1 layer"
	assert len(coa.get_layers_by_container(container_b)) == 3, "Container B should have 3 layers"
	assert coa.get_layer_container(lion1) == container_b, "Lion1 should be in Container B"
	
	print("✓ Layer moved between containers")


def test_layer_move_to_root():
	"""Test moving layer from container to root"""
	print("\n=== Test: Layer Move to Root ===")
	
	coa = CoA()
	
	# Create container with layers
	lion1 = coa.add_layer(emblem_path="ce_lion.dds")
	lion2 = coa.add_layer(emblem_path="ce_lion.dds")
	
	container = coa.generate_container_uuid("Animals")
	coa.set_layer_container(lion1, container)
	coa.set_layer_container(lion2, container)
	
	print(f"Initial container: {len(coa.get_layers_by_container(container))} layers")
	print(f"Initial root: {len(coa.get_layers_by_container(None))} layers")
	
	# Simulate drag to root zone (sets container_uuid=None)
	coa.set_layer_container(lion1, None)
	
	print(f"After moving lion1 to root:")
	print(f"  Container: {len(coa.get_layers_by_container(container))} layers")
	print(f"  Root: {len(coa.get_layers_by_container(None))} layers")
	
	assert len(coa.get_layers_by_container(container)) == 1, "Container should have 1 layer"
	assert len(coa.get_layers_by_container(None)) == 1, "Root should have 1 layer"
	assert coa.get_layer_container(lion1) is None, "Lion1 should be at root"
	
	print("✓ Layer moved to root")


def test_container_reposition():
	"""Test repositioning entire container"""
	print("\n=== Test: Container Reposition ===")
	
	coa = CoA()
	
	# Create layers and container
	layer1 = coa.add_layer(emblem_path="ce_lion.dds")  # index 0
	layer2 = coa.add_layer(emblem_path="ce_cross.dds")  # index 1
	layer3 = coa.add_layer(emblem_path="ce_star.dds")  # index 2
	layer4 = coa.add_layer(emblem_path="ce_circle.dds")  # index 3
	
	# Put layers 2 and 3 in a container
	container = coa.generate_container_uuid("Middle")
	coa.set_layer_container(layer2, container)
	coa.set_layer_container(layer3, container)
	
	print("Initial order:")
	for i, uuid in enumerate(coa.get_all_layer_uuids()):
		container_name = "Container" if coa.get_layer_container(uuid) else "root"
		print(f"  {i}: {coa.get_layer_filename(uuid)} - {container_name}")
	
	# Simulate container drag: move all container layers to top
	container_layers = coa.get_layers_by_container(container)
	coa.move_layer_to_top(container_layers)
	
	print("\nAfter moving container to top:")
	for i, uuid in enumerate(coa.get_all_layer_uuids()):
		container_name = "Container" if coa.get_layer_container(uuid) else "root"
		print(f"  {i}: {coa.get_layer_filename(uuid)} - {container_name}")
	
	# Verify container layers are at top (highest indices)
	all_uuids = coa.get_all_layer_uuids()
	container_indices = [all_uuids.index(uuid) for uuid in container_layers]
	
	assert all(idx >= 2 for idx in container_indices), \
		f"Container layers should be at indices 2-3, got {container_indices}"
	
	print("✓ Container repositioned as unit")


def test_container_stays_contiguous():
	"""Test that container layers stay contiguous after operations"""
	print("\n=== Test: Container Contiguity ===")
	
	coa = CoA()
	
	# Create container
	layer1 = coa.add_layer(emblem_path="ce_lion.dds")
	layer2 = coa.add_layer(emblem_path="ce_cross.dds")
	layer3 = coa.add_layer(emblem_path="ce_star.dds")
	
	container = coa.generate_container_uuid("Group")
	coa.set_layer_container(layer1, container)
	coa.set_layer_container(layer2, container)
	coa.set_layer_container(layer3, container)
	
	# Get container layer indices
	all_uuids = coa.get_all_layer_uuids()
	container_layers = coa.get_layers_by_container(container)
	indices = sorted([all_uuids.index(uuid) for uuid in container_layers])
	
	print(f"Container layer indices: {indices}")
	
	# Check contiguity
	for i in range(len(indices) - 1):
		diff = indices[i+1] - indices[i]
		assert diff == 1, f"Layers not contiguous: gap of {diff} between {indices[i]} and {indices[i+1]}"
	
	print("✓ Container layers are contiguous")


def test_mixed_drag_drop():
	"""Test complex drag-drop scenario"""
	print("\n=== Test: Mixed Drag-Drop Scenario ===")
	
	coa = CoA()
	
	# Create complex structure
	root1 = coa.add_layer(emblem_path="ce_lion.dds")
	
	container_a = coa.generate_container_uuid("ContainerA")
	layer_a1 = coa.add_layer(emblem_path="ce_cross.dds")
	layer_a2 = coa.add_layer(emblem_path="ce_star.dds")
	coa.set_layer_container(layer_a1, container_a)
	coa.set_layer_container(layer_a2, container_a)
	
	root2 = coa.add_layer(emblem_path="ce_circle.dds")
	
	container_b = coa.generate_container_uuid("ContainerB")
	layer_b1 = coa.add_layer(emblem_path="ce_eagle.dds")
	layer_b2 = coa.add_layer(emblem_path="ce_dragon.dds")
	coa.set_layer_container(layer_b1, container_b)
	coa.set_layer_container(layer_b2, container_b)
	
	print("Initial structure:")
	print(f"  Root layers: {len(coa.get_layers_by_container(None))}")
	print(f"  Container A: {len(coa.get_layers_by_container(container_a))}")
	print(f"  Container B: {len(coa.get_layers_by_container(container_b))}")
	
	# Simulate drag: move layer from container A to container B
	coa.set_layer_container(layer_a1, container_b)
	
	print("\nAfter moving layer_a1 to Container B:")
	print(f"  Container A: {len(coa.get_layers_by_container(container_a))}")
	print(f"  Container B: {len(coa.get_layers_by_container(container_b))}")
	
	assert len(coa.get_layers_by_container(container_a)) == 1
	assert len(coa.get_layers_by_container(container_b)) == 3
	
	# Simulate drag: move root layer into container
	coa.set_layer_container(root1, container_a)
	
	print("\nAfter moving root1 to Container A:")
	print(f"  Root layers: {len(coa.get_layers_by_container(None))}")
	print(f"  Container A: {len(coa.get_layers_by_container(container_a))}")
	
	assert len(coa.get_layers_by_container(None)) == 1  # Only root2 left
	assert len(coa.get_layers_by_container(container_a)) == 2
	
	print("✓ Mixed drag-drop operations work correctly")


def run_all_tests():
	"""Run all Phase 5 tests"""
	print("=" * 60)
	print("PHASE 5 TESTS: Drag and Drop")
	print("=" * 60)
	
	try:
		test_layer_move_between_containers()
		test_layer_move_to_root()
		test_container_reposition()
		test_container_stays_contiguous()
		test_mixed_drag_drop()
		
		print("\n" + "=" * 60)
		print("ALL PHASE 5 TESTS PASSED ✓")
		print("=" * 60)
		print("\nUI Testing Notes:")
		print("- Drag layers to indented zones to move into containers")
		print("- Drag layers to root zones to remove from containers")
		print("- Drag container markers to reposition entire container")
		print("- Container drops on indented zones are rejected (no nesting)")
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
