"""
Test Phase 1: Layer Name Property & Visibility API

This test verifies Phase 1 implementation:
- Layer name property with default from texture filename
- get_layer_name() and set_layer_name() CoA methods  
- get_layer_visible() and set_layer_visible() CoA methods
- Serialization includes name property
- Import/parse preserves name property
"""

import sys
import os

# Add editor src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'editor', 'src'))

from models.coa import CoA


def test_layer_name_default():
    """Test that layer name defaults to texture filename without extension"""
    print("\n=== Test: Layer Name Default ===")
    
    coa = CoA()
    layer_uuid = coa.add_layer(emblem_path="ce_lion.dds")
    
    name = coa.get_layer_name(layer_uuid)
    print(f"Added layer with texture 'ce_lion.dds'")
    print(f"Default name: '{name}'")
    
    assert name == "ce_lion", f"Expected 'ce_lion', got '{name}'"
    print("✓ Name defaults to texture filename without extension")


def test_layer_name_custom():
    """Test setting custom layer name"""
    print("\n=== Test: Custom Layer Name ===")
    
    coa = CoA()
    layer_uuid = coa.add_layer(emblem_path="ce_cross.dds")
    
    print(f"Layer UUID: {layer_uuid}")
    print(f"Initial name: '{coa.get_layer_name(layer_uuid)}'")
    
    coa.set_layer_name(layer_uuid, "My Custom Cross")
    name = coa.get_layer_name(layer_uuid)
    print(f"After rename: '{name}'")
    
    assert name == "My Custom Cross", f"Expected 'My Custom Cross', got '{name}'"
    print("✓ Custom name set successfully")


def test_layer_name_empty_texture():
    """Test layer name with empty texture filename"""
    print("\n=== Test: Layer Name with Empty Texture ===")
    
    coa = CoA()
    layer_uuid = coa.add_layer(emblem_path="")
    
    name = coa.get_layer_name(layer_uuid)
    print(f"Added layer with empty texture")
    print(f"Default name: '{name}'")
    
    assert name == "empty", f"Expected 'empty', got '{name}'"
    print("✓ Empty texture defaults to 'empty' name")


def test_visibility_api():
    """Test layer visibility getter/setter"""
    print("\n=== Test: Visibility API ===")
    
    coa = CoA()
    layer_uuid = coa.add_layer(emblem_path="ce_star.dds")
    
    # Test initial visibility (should be True)
    visible = coa.get_layer_visible(layer_uuid)
    print(f"Initial visibility: {visible}")
    assert visible == True, f"Expected True, got {visible}"
    
    # Test hiding layer
    coa.set_layer_visible(layer_uuid, False)
    visible = coa.get_layer_visible(layer_uuid)
    print(f"After hiding: {visible}")
    assert visible == False, f"Expected False, got {visible}"
    
    # Test showing layer
    coa.set_layer_visible(layer_uuid, True)
    visible = coa.get_layer_visible(layer_uuid)
    print(f"After showing: {visible}")
    assert visible == True, f"Expected True, got {visible}"
    
    print("✓ Visibility API works correctly")


def test_serialization():
    """Test that serialization includes name property"""
    print("\n=== Test: Serialization with Name ===")
    
    coa = CoA()
    layer_uuid = coa.add_layer(emblem_path="ce_lion.dds")
    coa.set_layer_name(layer_uuid, "Lion Layer")
    
    serialized = coa.to_string()
    print("Serialized CoA:")
    print(serialized)
    
    assert 'name = "Lion Layer"' in serialized, "Name property not found in serialization"
    assert 'uuid = "' in serialized, "UUID not found in serialization"
    print("✓ Serialization includes name property")


def test_parse_with_name():
    """Test parsing CoA with name property"""
    print("\n=== Test: Parse with Name Property ===")
    
    coa_text = """coa_export = {
    pattern = "pattern__solid.dds"
    color1 = "yellow"
    color2 = "red"
    color3 = "black"
    colored_emblem = {
        uuid = "test-uuid-123"
        name = "Parsed Lion"
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
    name = coa.get_layer_name(layer_uuid)
    uuid = layer_uuid
    
    print(f"Parsed layer UUID: {uuid}")
    print(f"Parsed layer name: '{name}'")
    
    # UUID should be preserved (though may be regenerated on parse)
    assert name == "Parsed Lion", f"Expected 'Parsed Lion', got '{name}'"
    print("✓ Name property preserved during parse")


def test_parse_without_name():
    """Test parsing CoA without name property (legacy format)"""
    print("\n=== Test: Parse without Name Property ===")
    
    coa_text = """coa_export = {
    pattern = "pattern__solid.dds"
    color1 = "yellow"
    color2 = "red"
    color3 = "black"
    colored_emblem = {
        texture = "ce_cross.dds"
        color1 = "yellow"
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
    name = coa.get_layer_name(layer_uuid)
    
    print(f"Parsed layer without name property")
    print(f"Default name: '{name}'")
    
    assert name == "ce_cross", f"Expected 'ce_cross', got '{name}'"
    print("✓ Legacy CoA without name defaults to texture filename")


def test_roundtrip():
    """Test complete roundtrip: create, serialize, parse"""
    print("\n=== Test: Complete Roundtrip ===")
    
    # Create CoA with custom names
    coa1 = CoA()
    uuid1 = coa1.add_layer(emblem_path="ce_lion.dds")
    uuid2 = coa1.add_layer(emblem_path="ce_cross.dds")
    
    coa1.set_layer_name(uuid1, "First Lion")
    coa1.set_layer_name(uuid2, "Second Cross")
    
    # Serialize
    serialized = coa1.to_string()
    print("Serialized with custom names")
    
    # Parse back
    coa2 = CoA.from_string(serialized)
    layers = coa2.get_all_layer_uuids()
    
    assert len(layers) == 2, f"Expected 2 layers, got {len(layers)}"
    
    # Check names are preserved
    names = [coa2.get_layer_name(uuid) for uuid in layers]
    print(f"Parsed names: {names}")
    
    # Note: layers are stored back-to-front, so order might be reversed
    assert "First Lion" in names, "First Lion not found"
    assert "Second Cross" in names, "Second Cross not found"
    
    print("✓ Names preserved through complete roundtrip")


def run_all_tests():
    """Run all Phase 1 tests"""
    print("=" * 60)
    print("PHASE 1 TESTS: Layer Name Property & Visibility API")
    print("=" * 60)
    
    try:
        test_layer_name_default()
        test_layer_name_custom()
        test_layer_name_empty_texture()
        test_visibility_api()
        test_serialization()
        test_parse_with_name()
        test_parse_without_name()
        test_roundtrip()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
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
