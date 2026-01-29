"""
Diagnostic script to understand transform data structure issues
"""
import sys
import json

# Test what the layer data actually looks like
def test_layer_structure():
    """Test both old and new layer formats"""
    
    # Old format (pre-Phase 2)
    old_layer = {
        'type': 'emblem',
        'asset_id': 'eagle',
        'pos_x': 0.5,
        'pos_y': 0.5,
        'scale_x': 0.3,
        'scale_y': 0.3,
        'rotation': 0
    }
    
    # New format (Phase 2 multi-instance)
    new_layer = {
        'type': 'emblem',
        'asset_id': 'eagle',
        'selected_instance': 0,
        'instances': [
            {
                'pos_x': 0.5,
                'pos_y': 0.5,
                'scale_x': 0.3,
                'scale_y': 0.3,
                'rotation': 0,
                'depth': 0
            }
        ]
    }
    
    print("=== OLD FORMAT (Pre-Phase 2) ===")
    print(json.dumps(old_layer, indent=2))
    print(f"\nAccess pos_x: layer['pos_x'] = {old_layer['pos_x']}")
    
    print("\n=== NEW FORMAT (Phase 2 Multi-Instance) ===")
    print(json.dumps(new_layer, indent=2))
    print(f"\nAccess pos_x: layer['instances'][0]['pos_x'] = {new_layer['instances'][0]['pos_x']}")
    print(f"Selected instance: {new_layer['selected_instance']}")
    print(f"Access via selected: layer['instances'][layer['selected_instance']]['pos_x'] = {new_layer['instances'][new_layer['selected_instance']]['pos_x']}")
    
    # Test what happens with the old accessor on new format
    print("\n=== TESTING OLD ACCESSOR ON NEW FORMAT ===")
    try:
        pos_x = new_layer['pos_x']
        print(f"SUCCESS: layer['pos_x'] = {pos_x}")
    except KeyError as e:
        print(f"ERROR: KeyError - {e}")
        print("This is EXPECTED - new format doesn't have 'pos_x' at root level")
    
    # Test what happens with new accessor on old format
    print("\n=== TESTING NEW ACCESSOR ON OLD FORMAT ===")
    try:
        instances = old_layer.get('instances', [])
        selected = old_layer.get('selected_instance', 0)
        print(f"instances = {instances}")
        print(f"selected_instance = {selected}")
        
        if instances and 0 <= selected < len(instances):
            pos_x = instances[selected]['pos_x']
            print(f"SUCCESS: Got pos_x = {pos_x}")
        else:
            print("FALLBACK: No instances, would need migration or default value")
    except Exception as e:
        print(f"ERROR: {type(e).__name__} - {e}")

if __name__ == '__main__':
    test_layer_structure()
