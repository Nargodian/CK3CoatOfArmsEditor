"""
Test Phase 2: Container Model Support

This test verifies Phase 2 implementation:
- Layer container_uuid property with getter/setter
- CoA methods: get_layer_container(), set_layer_container()
- CoA methods: get_layers_by_container(), get_all_containers()
- Serialization includes container_uuid
- Parsing preserves container_uuid
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'editor', 'src'))

from models.coa import CoA


def test_container_uuid_property():
    """Test that layer container_uuid property works"""
    print("\n=== Test: Container UUID Property ===")
    
    coa = CoA()
    layer_uuid = coa.add_layer(emblem_path="ce_lion.dds")
    
    # Default should be None (root level)
    container = coa.get_layer_container(layer_uuid)
    print(f"Default container_uuid: {container}")
    assert container is None, f"Expected None, got {container}"
    print("✓ Default container_uuid is None")
    
    # Set container UUID
    test_container = "container_test-123_MyContainer"
    coa.set_layer_container(layer_uuid, test_container)
    container = coa.get_layer_container(layer_uuid)
    print(f"After setting: {container}")
    assert container == test_container, f"Expected {test_container}, got {container}"
    print("✓ Container UUID can be set")
    
    # Set back to None
    coa.set_layer_container(layer_uuid, None)
    container = coa.get_layer_container(layer_uuid)
    assert container is None, f"Expected None, got {container}"
    print("✓ Container UUID can be cleared")


def test_get_layers_by_container():
    """Test getting layers by container UUID"""
    print("\n=== Test: Get Layers By Container ===")
    
    coa = CoA()
    
    # Create multiple layers
    layer1 = coa.add_layer(emblem_path="ce_lion.dds")
    layer2 = coa.add_layer(emblem_path="ce_cross.dds")
    layer3 = coa.add_layer(emblem_path="ce_star.dds")
    layer4 = coa.add_layer(emblem_path="ce_circle.dds")
    
    # Assign some to containers
    container_a = "container_abc-123_ContainerA"
    container_b = "container_def-456_ContainerB"
    
    coa.set_layer_container(layer1, container_a)
    coa.set_layer_container(layer2, container_a)
    coa.set_layer_container(layer3, container_b)
    # layer4 stays at root (None)
    
    # Query by container A
    layers_a = coa.get_layers_by_container(container_a)
    print(f"Container A layers: {len(layers_a)}")
    assert len(layers_a) == 2, f"Expected 2 layers, got {len(layers_a)}"
    assert layer1 in layers_a and layer2 in layers_a, "Wrong layers in container A"
    print("✓ Container A has correct layers")
    
    # Query by container B
    layers_b = coa.get_layers_by_container(container_b)
    print(f"Container B layers: {len(layers_b)}")
    assert len(layers_b) == 1, f"Expected 1 layer, got {len(layers_b)}"
    assert layer3 in layers_b, "Wrong layer in container B"
    print("✓ Container B has correct layers")
    
    # Query root level (None)
    root_layers = coa.get_layers_by_container(None)
    print(f"Root level layers: {len(root_layers)}")
    assert len(root_layers) == 1, f"Expected 1 root layer, got {len(root_layers)}"
    assert layer4 in root_layers, "Wrong layer at root"
    print("✓ Root level has correct layers")


def test_get_all_containers():
    """Test getting all unique container UUIDs"""
    print("\n=== Test: Get All Containers ===")
    
    coa = CoA()
    
    # Initially should be empty
    containers = coa.get_all_containers()
    print(f"Initial containers: {containers}")
    assert len(containers) == 0, f"Expected 0 containers, got {len(containers)}"
    print("✓ No containers initially")
    
    # Create layers in different containers
    layer1 = coa.add_layer(emblem_path="ce_lion.dds")
    layer2 = coa.add_layer(emblem_path="ce_cross.dds")
    layer3 = coa.add_layer(emblem_path="ce_star.dds")
    
    container_a = "container_abc-123_ContainerA"
    container_b = "container_def-456_ContainerB"
    
    coa.set_layer_container(layer1, container_a)
    coa.set_layer_container(layer2, container_b)
    # layer3 at root
    
    # Should return both containers
    containers = coa.get_all_containers()
    print(f"Containers after assignment: {containers}")
    assert len(containers) == 2, f"Expected 2 containers, got {len(containers)}"
    assert container_a in containers and container_b in containers, "Missing containers"
    print("✓ All containers returned correctly")
    
    # Remove a layer from container
    coa.set_layer_container(layer1, None)
    containers = coa.get_all_containers()
    print(f"After removing one layer: {containers}")
    assert len(containers) == 1, f"Expected 1 container, got {len(containers)}"
    assert container_b in containers, "Wrong container remaining"
    print("✓ Container list updates correctly")


def test_serialization_with_container():
    """Test that serialization includes container_uuid"""
    print("\n=== Test: Serialization with Container ===")
    
    coa = CoA()
    layer_uuid = coa.add_layer(emblem_path="ce_lion.dds")
    
    # Set container
    container = "container_test-123_TestContainer"
    coa.set_layer_container(layer_uuid, container)
    
    # Serialize
    serialized = coa.to_string()
    print("Serialized CoA:")
    print(serialized[:500])  # First 500 chars
    
    assert 'container_uuid = "container_test-123_TestContainer"' in serialized, \
        "Container UUID not found in serialization"
    print("✓ Container UUID included in serialization")


def test_parsing_with_container():
    """Test parsing CoA with container_uuid"""
    print("\n=== Test: Parse with Container UUID ===")
    
    coa_text = """coa_export = {
    pattern = "pattern__solid.dds"
    color1 = "yellow"
    color2 = "red"
    color3 = "black"
    colored_emblem = {
        uuid = "test-uuid-123"
        container_uuid = "container_abc-456_TestContainer"
        name = "Test Lion"
        texture = "ce_lion.dds"
        color1 = "red"
        instance = {
            position = { 0.5 0.5 }
            scale = { 1.0 1.0 }
            rotation = 0
        }
    }
}"""
    
    coa = CoA.from_string(coa_text)
    layers = coa.get_all_layer_uuids()
    
    assert len(layers) == 1, f"Expected 1 layer, got {len(layers)}"
    
    layer_uuid = layers[0]
    container = coa.get_layer_container(layer_uuid)
    
    print(f"Parsed container_uuid: {container}")
    assert container == "container_abc-456_TestContainer", \
        f"Expected 'container_abc-456_TestContainer', got '{container}'"
    print("✓ Container UUID preserved during parse")


def test_roundtrip_with_containers():
    """Test complete roundtrip with containers"""
    print("\n=== Test: Complete Roundtrip with Containers ===")
    
    # Create CoA with layers in containers
    coa1 = CoA()
    uuid1 = coa1.add_layer(emblem_path="ce_lion.dds")
    uuid2 = coa1.add_layer(emblem_path="ce_cross.dds")
    uuid3 = coa1.add_layer(emblem_path="ce_star.dds")
    
    container_a = "container_test-123_Animals"
    container_b = "container_test-456_Symbols"
    
    coa1.set_layer_container(uuid1, container_a)
    coa1.set_layer_container(uuid2, container_b)
    # uuid3 at root
    
    # Serialize
    serialized = coa1.to_string()
    print("Serialized with containers")
    
    # Parse back
    coa2 = CoA.from_string(serialized)
    
    # Check containers preserved
    containers = coa2.get_all_containers()
    print(f"Parsed containers: {containers}")
    assert len(containers) == 2, f"Expected 2 containers, got {len(containers)}"
    
    # Check layer groupings
    layers_a = coa2.get_layers_by_container(container_a)
    layers_b = coa2.get_layers_by_container(container_b)
    root_layers = coa2.get_layers_by_container(None)
    
    print(f"Container A: {len(layers_a)} layers")
    print(f"Container B: {len(layers_b)} layers")
    print(f"Root: {len(root_layers)} layers")
    
    assert len(layers_a) == 1, f"Expected 1 layer in container A"
    assert len(layers_b) == 1, f"Expected 1 layer in container B"
    assert len(root_layers) == 1, f"Expected 1 layer at root"
    
    print("✓ Container organization preserved through roundtrip")


def run_all_tests():
    """Run all Phase 2 tests"""
    print("=" * 60)
    print("PHASE 2 TESTS: Container Model Support")
    print("=" * 60)
    
    try:
        test_container_uuid_property()
        test_get_layers_by_container()
        test_get_all_containers()
        test_serialization_with_container()
        test_parsing_with_container()
        test_roundtrip_with_containers()
        
        print("\n" + "=" * 60)
        print("ALL PHASE 2 TESTS PASSED ✓")
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
