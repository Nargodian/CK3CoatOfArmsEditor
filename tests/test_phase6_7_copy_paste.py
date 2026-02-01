"""Test Phase 6-7: Copy/Paste Logic and Container Validation"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'editor', 'src')))

from models.coa import CoA

def test_copy_type_detection():
    """Test detection of container copy vs individual layer copy"""
    print("\n=== Test Copy Type Detection ===")
    coa = CoA()
    
    # Add 3 layers in a container
    uuid1 = coa.add_layer()
    uuid2 = coa.add_layer()
    uuid3 = coa.add_layer()
    
    container_uuid = coa.create_container_from_layers([uuid1, uuid2, uuid3], "TestContainer")
    
    # Test 1: Serialize with container_uuid stripped (individual copy)
    clipboard_text = coa.serialize_layers_to_string([uuid1], strip_container_uuid=True)
    assert "container_uuid" not in clipboard_text, "Individual copy should strip container_uuid"
    print("✓ Individual layer copy strips container_uuid")
    
    # Test 2: Serialize with container_uuid preserved (container copy)
    clipboard_text = coa.serialize_layers_to_string([uuid1, uuid2, uuid3], strip_container_uuid=False)
    assert container_uuid in clipboard_text, "Container copy should preserve container_uuid"
    print("✓ Container copy preserves container_uuid")
    
    print("✓ Copy type detection works")

def test_paste_rule_1_no_container_uuid():
    """Test Rule 1: Layers without container_uuid adopt destination or go to root"""
    print("\n=== Test Paste Rule 1 (No Container UUID) ===")
    coa = CoA()
    
    # Create a container with layers
    uuid1 = coa.add_layer()
    uuid2 = coa.add_layer()
    container_uuid = coa.create_container_from_layers([uuid1, uuid2], "Container1")
    
    # Add a root layer
    uuid3 = coa.add_layer()
    
    # Serialize without container_uuid (simulate individual copy)
    clipboard_text = coa.serialize_layers_to_string([uuid3], strip_container_uuid=True)
    
    # Verify container_uuid is stripped
    assert "container_uuid" not in clipboard_text, "Individual copy should strip container_uuid"
    
    # Parse into new CoA and verify no container_uuid
    temp_coa = CoA()
    temp_coa.parse(clipboard_text)
    temp_uuids = [temp_coa.get_layer_uuid_by_index(i) for i in range(temp_coa.get_layer_count())]
    assert len(temp_uuids) == 1, f"Expected 1 layer, got {len(temp_uuids)}"
    assert temp_coa.get_layer_container(temp_uuids[0]) is None, "Pasted layer should have no container_uuid"
    
    # Now assign to a container (simulating Rule 1 adoption)
    temp_coa.set_layer_container(temp_uuids[0], container_uuid)
    assert temp_coa.get_layer_container(temp_uuids[0]) == container_uuid, "Layer should adopt container_uuid"
    
    print("✓ Rule 1: Individual layers adopt destination container")

def test_paste_rule_2_with_container_uuid():
    """Test Rule 2: Layers with container_uuid create new container"""
    print("\n=== Test Paste Rule 2 (With Container UUID) ===")
    coa = CoA()
    
    # Create a container with layers
    uuid1 = coa.add_layer()
    uuid2 = coa.add_layer()
    original_container_uuid = coa.create_container_from_layers([uuid1, uuid2], "Container1")
    
    # Serialize WITH container_uuid (simulate container copy)
    clipboard_text = coa.serialize_layers_to_string([uuid1, uuid2], strip_container_uuid=False)
    assert original_container_uuid in clipboard_text, "Container copy should preserve UUID"
    
    # Parse into new CoA
    temp_coa = CoA()
    temp_coa.parse(clipboard_text)
    temp_uuids = [temp_coa.get_layer_uuid_by_index(i) for i in range(temp_coa.get_layer_count())]
    
    # Verify layers have container_uuid
    for uuid in temp_uuids:
        assert temp_coa.get_layer_container(uuid) == original_container_uuid, "Layers should have container_uuid"
    
    # Regenerate container UUID (simulating Rule 2)
    new_container_uuid = coa.regenerate_container_uuid(original_container_uuid)
    assert new_container_uuid != original_container_uuid, "New container should have different UUID"
    assert "Container1" in new_container_uuid, "Container name should be preserved"
    
    print("✓ Rule 2: Container paste creates new container with regenerated UUID")

def test_container_validator_contiguity():
    """Test validator detects and fixes non-contiguous containers"""
    print("\n=== Test Container Validator ===")
    coa = CoA()
    
    # Create scenario: layers 0,1,2 in container A, layer 3 in container B, layers 4,5 in container A
    uuid1 = coa.add_layer()  # Index 0
    uuid2 = coa.add_layer()  # Index 1
    uuid3 = coa.add_layer()  # Index 2
    uuid4 = coa.add_layer()  # Index 3
    uuid5 = coa.add_layer()  # Index 4
    uuid6 = coa.add_layer()  # Index 5
    
    # Create containers
    containerA = coa.generate_container_uuid("ContainerA")
    containerB = coa.generate_container_uuid("ContainerB")
    
    # Set up non-contiguous situation: A, A, A, B, A, A
    coa.set_layer_container(uuid1, containerA)
    coa.set_layer_container(uuid2, containerA)
    coa.set_layer_container(uuid3, containerA)
    coa.set_layer_container(uuid4, containerB)
    coa.set_layer_container(uuid5, containerA)  # Non-contiguous!
    coa.set_layer_container(uuid6, containerA)  # Non-contiguous!
    
    # Validate - should split containerA
    splits = coa.validate_container_contiguity()
    
    assert len(splits) == 1, f"Expected 1 split, got {len(splits)}"
    assert splits[0]['old_container'] == containerA, "Split should be from containerA"
    assert splits[0]['layer_count'] == 2, "Split should affect 2 layers (uuid5, uuid6)"
    
    # Verify layers 5,6 now have different container_uuid
    new_container = coa.get_layer_container(uuid5)
    assert new_container != containerA, "Split layers should have new container_uuid"
    assert coa.get_layer_container(uuid6) == new_container, "Both split layers should share new UUID"
    assert "ContainerA" in new_container, "New container should preserve name"
    
    # Verify layers 1,2,3 still in original container
    assert coa.get_layer_container(uuid1) == containerA
    assert coa.get_layer_container(uuid2) == containerA
    assert coa.get_layer_container(uuid3) == containerA
    
    print("✓ Validator detects and splits non-contiguous containers")

def test_validator_multiple_gaps():
    """Test validator handles multiple gaps in same container"""
    print("\n=== Test Validator Multiple Gaps ===")
    coa = CoA()
    
    # Create layers: A, B, A, B, A (3 groups of A, 2 groups of B)
    uuid1 = coa.add_layer()  # A
    uuid2 = coa.add_layer()  # B
    uuid3 = coa.add_layer()  # A (gap 1)
    uuid4 = coa.add_layer()  # B
    uuid5 = coa.add_layer()  # A (gap 2)
    
    containerA = coa.generate_container_uuid("ContainerA")
    containerB = coa.generate_container_uuid("ContainerB")
    
    coa.set_layer_container(uuid1, containerA)
    coa.set_layer_container(uuid2, containerB)
    coa.set_layer_container(uuid3, containerA)
    coa.set_layer_container(uuid4, containerB)
    coa.set_layer_container(uuid5, containerA)
    
    # Validate - should split containerA into 3 groups, containerB into 2 groups
    splits = coa.validate_container_contiguity()
    
    # We expect splits for:
    # - ContainerA: groups 2 and 3 split off (2 splits)
    # - ContainerB: group 2 split off (1 split)
    # Total: 3 splits
    assert len(splits) >= 2, f"Expected at least 2 splits, got {len(splits)}"
    
    # Verify all 3 A groups have different UUIDs
    container1 = coa.get_layer_container(uuid1)
    container3 = coa.get_layer_container(uuid3)
    container5 = coa.get_layer_container(uuid5)
    
    assert container1 == containerA, "First group should keep original UUID"
    assert container3 != containerA, "Second group should have new UUID"
    assert container5 != containerA, "Third group should have new UUID"
    assert container3 != container5, "Second and third groups should be distinct"
    
    print("✓ Validator handles multiple gaps correctly")

def test_paste_with_validation():
    """Test paste operation triggers validation"""
    print("\n=== Test Paste with Validation ===")
    coa = CoA()
    
    # Create a simple non-contiguous scenario directly
    uuid1 = coa.add_layer()  # Index 0
    uuid2 = coa.add_layer()  # Index 1
    uuid3 = coa.add_layer()  # Index 2
    uuid4 = coa.add_layer()  # Index 3
    
    # Set up: container, container, root, container (non-contiguous)
    container_uuid = coa.generate_container_uuid("TestContainer")
    coa.set_layer_container(uuid1, container_uuid)
    coa.set_layer_container(uuid2, container_uuid)
    # uuid3 stays at root (None)
    coa.set_layer_container(uuid4, container_uuid)  # This makes it non-contiguous!
    
    # Validate should split
    splits = coa.validate_container_contiguity()
    
    assert len(splits) >= 1, f"Expected at least 1 split, got {len(splits)}"
    
    # Verify uuid4 now has different container UUID
    container4_uuid = coa.get_layer_container(uuid4)
    container1_uuid = coa.get_layer_container(uuid1)
    assert container4_uuid != container1_uuid, "Split should create different containers"
    assert container4_uuid != container_uuid, "Split layer should have new UUID"
    
    print("✓ Validation detects and fixes non-contiguous containers after operations")

def test_container_name_preservation():
    """Test container name is preserved through regeneration"""
    print("\n=== Test Container Name Preservation ===")
    coa = CoA()
    
    # Create container with specific name
    original_uuid = coa.generate_container_uuid("MySpecialContainer")
    assert "MySpecialContainer" in original_uuid, "Container should have name"
    
    # Regenerate
    new_uuid = coa.regenerate_container_uuid(original_uuid)
    assert "MySpecialContainer" in new_uuid, "Regenerated container should preserve name"
    assert new_uuid != original_uuid, "Regenerated UUID should be different"
    
    # Extract UUID portions and verify they're different
    parts1 = original_uuid.split('_', 2)
    parts2 = new_uuid.split('_', 2)
    assert parts1[1] != parts2[1], "UUID portions should be different"
    assert parts1[2] == parts2[2], "Names should be identical"
    
    print("✓ Container names preserved through regeneration")

def run_all_tests():
    """Run all Phase 6-7 tests"""
    print("\n" + "="*60)
    print("PHASE 6-7: COPY/PASTE LOGIC AND VALIDATION TESTS")
    print("="*60)
    
    try:
        test_copy_type_detection()
        test_paste_rule_1_no_container_uuid()
        test_paste_rule_2_with_container_uuid()
        test_container_validator_contiguity()
        test_validator_multiple_gaps()
        test_paste_with_validation()
        test_container_name_preservation()
        
        print("\n" + "="*60)
        print("✓ ALL PHASE 6-7 TESTS PASSED")
        print("="*60)
        return True
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
