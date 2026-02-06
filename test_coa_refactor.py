"""Test CoA mixin refactoring - verify all operations work"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'editor', 'src'))

from models.coa import CoA

def test_coa_operations():
    print("Testing CoA Mixin Architecture...")
    
    # Test 1: Create CoA
    print("\n1. Creating CoA...")
    coa = CoA()
    assert coa is not None
    print("   ✓ CoA created")
    
    # Test 2: Add layer
    print("\n2. Adding layer...")
    uuid1 = coa.add_layer(emblem_path="emblem_ordinary_cross.dds", pos_x=0.5, pos_y=0.5)
    assert uuid1 is not None
    assert coa.get_layer_count() == 1
    print(f"   ✓ Layer added: {uuid1}")
    
    # Test 3: Set layer properties (transform operations)
    print("\n3. Testing transform operations...")
    coa.set_layer_position(uuid1, 0.6, 0.4)
    pos = coa.get_layer_position(uuid1)
    assert pos == (0.6, 0.4)
    print(f"   ✓ Position set: {pos}")
    
    coa.set_layer_scale(uuid1, 1.5, 1.5)
    print("   ✓ Scale set")
    
    coa.set_layer_rotation(uuid1, 45.0)
    print("   ✓ Rotation set")
    
    # Test 4: Duplicate layer (layer operations)
    print("\n4. Testing layer operations...")
    uuid2 = coa.duplicate_layer(uuid1)
    assert coa.get_layer_count() == 2
    print(f"   ✓ Layer duplicated: {uuid2}")
    
    # Test 5: Add instance
    print("\n5. Testing instance operations...")
    instance_idx = coa.add_instance(uuid1, 0.3, 0.3)
    assert instance_idx is not None
    print(f"   ✓ Instance added: {instance_idx}")
    
    # Test 6: Group transform
    print("\n6. Testing group transform...")
    coa.rotate_layers_group([uuid1, uuid2], 90.0)
    print("   ✓ Group rotation applied")
    
    # Test 7: Serialization
    print("\n7. Testing serialization...")
    ck3_text = coa.to_string()
    assert "pattern =" in ck3_text
    assert "colored_emblem" in ck3_text
    print(f"   ✓ Serialized ({len(ck3_text)} chars)")
    
    # Test 8: Parsing
    print("\n8. Testing parsing...")
    coa2 = CoA.from_string(ck3_text)
    assert coa2.get_layer_count() == 2
    print(f"   ✓ Parsed CoA with {coa2.get_layer_count()} layers")
    
    # Test 9: Container operations
    print("\n9. Testing container operations...")
    container_uuid = coa.create_container_from_layers([uuid1, uuid2], "Test Container")
    containers = coa.get_all_containers()
    assert len(containers) > 0
    print(f"   ✓ Container created: {container_uuid}")
    
    # Test 10: Snapshot (undo/redo support)
    print("\n10. Testing snapshot...")
    snapshot = coa.get_snapshot()
    assert snapshot is not None
    assert 'pattern' in snapshot
    assert 'layers' in snapshot
    print("   ✓ Snapshot captured")
    
    coa.remove_layer(uuid2)
    assert coa.get_layer_count() == 1
    
    coa.set_snapshot(snapshot)
    assert coa.get_layer_count() == 2
    print("   ✓ Snapshot restored")
    
    # Test 11: Query operations
    print("\n11. Testing query operations...")
    all_uuids = coa.get_all_layer_uuids()
    assert len(all_uuids) == 2
    print(f"   ✓ Query: {len(all_uuids)} layers")
    
    bounds = coa.get_layer_bounds(uuid1)
    assert 'min_x' in bounds
    print(f"   ✓ Bounds calculated: {bounds}")
    
    # Test 12: Color operations
    print("\n12. Testing color operations...")
    coa.set_layer_color(uuid1, 1, [255, 0, 0], "red")
    print("   ✓ Layer color set")
    
    coa.set_base_color(1, [0, 255, 0], "green")
    print("   ✓ Base color set")
    
    # Test 13: Alignment/movement
    print("\n13. Testing alignment...")
    coa.align_layers([uuid1, uuid2], "center")
    print("   ✓ Layers aligned")
    
    # Test 14: Flip operations
    print("\n14. Testing flip...")
    coa.flip_layer(uuid1, flip_x=True, flip_y=False)
    print("   ✓ Layer flipped")
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED - CoA mixin refactoring works correctly!")
    print("="*60)

if __name__ == '__main__':
    try:
        test_coa_operations()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
