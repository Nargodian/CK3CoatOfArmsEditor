"""
Unit tests for Layer, Layers, and LayerTracker classes

Tests cover:
- UUID generation and persistence
- Layer property access
- Instance management
- Auto-migration from old format
- Layers collection operations
- LayerTracker logging
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'editor', 'src'))

import unittest
from models.layer import Layer, Layers, LayerTracker


class TestLayerTracker(unittest.TestCase):
    """Tests for LayerTracker debugging system"""
    
    def setUp(self):
        LayerTracker.clear_log()
    
    def test_register(self):
        """Test caller registration"""
        LayerTracker.register('test_component')
        self.assertIn('test_component', LayerTracker._registered_keys)
    
    def test_log_call(self):
        """Test method call logging"""
        LayerTracker.register('test')
        LayerTracker.log_call('test', 123, 'test_method', 'prop', 'value')
        
        log = LayerTracker.get_log()
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]['caller'], 'test')
        self.assertEqual(log[0]['layer_id'], 123)
        self.assertEqual(log[0]['method'], 'test_method')
        self.assertEqual(log[0]['property'], 'prop')
        self.assertEqual(log[0]['value'], 'value')
    
    def test_filter_log(self):
        """Test log filtering"""
        LayerTracker.register('comp1')
        LayerTracker.register('comp2')
        
        LayerTracker.log_call('comp1', 1, 'method1')
        LayerTracker.log_call('comp2', 2, 'method2')
        LayerTracker.log_call('comp1', 1, 'method3')
        
        # Filter by caller
        comp1_log = LayerTracker.get_log(caller='comp1')
        self.assertEqual(len(comp1_log), 2)
        
        # Filter by layer ID
        layer1_log = LayerTracker.get_log(layer_id=1)
        self.assertEqual(len(layer1_log), 2)
        
        # Filter both
        specific_log = LayerTracker.get_log(caller='comp1', layer_id=1)
        self.assertEqual(len(specific_log), 2)


class TestLayer(unittest.TestCase):
    """Tests for Layer class"""
    
    def setUp(self):
        LayerTracker.register('test')
        LayerTracker.clear_log()
    
    def test_create_default(self):
        """Test creating default layer"""
        layer = Layer(caller='test')
        
        # Check defaults
        self.assertEqual(layer.filename, '')
        self.assertEqual(layer.colors, 3)
        self.assertEqual(layer.instance_count, 1)
        self.assertEqual(layer.selected_instance, 0)
        self.assertFalse(layer.flip_x)
        self.assertFalse(layer.flip_y)
        self.assertIsNone(layer.mask)
        
        # Check UUID was generated
        self.assertIsNotNone(layer.uuid)
        self.assertTrue(len(layer.uuid) > 0)
    
    def test_uuid_generation(self):
        """Test that each layer gets unique UUID"""
        layer1 = Layer(caller='test')
        layer2 = Layer(caller='test')
        
        self.assertNotEqual(layer1.uuid, layer2.uuid)
    
    def test_uuid_persistence(self):
        """Test that UUID is preserved through to_dict/from_dict"""
        layer1 = Layer(caller='test')
        uuid1 = layer1.uuid
        
        # Export to dict
        data = layer1.to_dict(caller='test')
        
        # Import from dict
        layer2 = Layer(data, caller='test')
        uuid2 = layer2.uuid
        
        # UUID should be preserved
        self.assertEqual(uuid1, uuid2)
    
    def test_create_from_data(self):
        """Test creating layer from dictionary"""
        data = {
            'uuid': 'test-uuid-123',
            'filename': 'emblem_cross.dds',
            'colors': 2,
            'instances': [{'pos_x': 0.3, 'pos_y': 0.7, 'scale_x': 1.5, 'scale_y': 1.5, 'rotation': 45.0, 'depth': 0.0}],
            'selected_instance': 0,
            'flip_x': True,
            'color1': [255, 0, 0],
            'color1_name': 'red'
        }
        
        layer = Layer(data, caller='test')
        
        self.assertEqual(layer.uuid, 'test-uuid-123')
        self.assertEqual(layer.filename, 'emblem_cross.dds')
        self.assertEqual(layer.colors, 2)
        self.assertEqual(layer.pos_x, 0.3)
        self.assertEqual(layer.pos_y, 0.7)
        self.assertEqual(layer.scale_x, 1.5)
        self.assertEqual(layer.rotation, 45.0)
        self.assertTrue(layer.flip_x)
        self.assertEqual(layer.color1, [255, 0, 0])
        self.assertEqual(layer.color1_name, 'red')
    
    def test_instance_properties(self):
        """Test instance property access"""
        layer = Layer(caller='test')
        
        # Set properties
        layer.pos_x = 0.6
        layer.pos_y = 0.4
        layer.scale_x = 1.2
        layer.scale_y = 0.8
        layer.rotation = 90.0
        layer.depth = 5.0
        
        # Verify
        self.assertEqual(layer.pos_x, 0.6)
        self.assertEqual(layer.pos_y, 0.4)
        self.assertEqual(layer.scale_x, 1.2)
        self.assertEqual(layer.scale_y, 0.8)
        self.assertEqual(layer.rotation, 90.0)
        self.assertEqual(layer.depth, 5.0)
    
    def test_layer_properties(self):
        """Test layer (shared) property access"""
        layer = Layer(caller='test')
        
        # Set properties
        layer.filename = 'test.dds'
        layer.colors = 2
        layer.flip_x = True
        layer.flip_y = False
        layer.color1 = [100, 150, 200]
        layer.color1_name = 'blue'
        
        # Verify
        self.assertEqual(layer.filename, 'test.dds')
        self.assertEqual(layer.path, 'test.dds')  # Should sync
        self.assertEqual(layer.colors, 2)
        self.assertTrue(layer.flip_x)
        self.assertFalse(layer.flip_y)
        self.assertEqual(layer.color1, [100, 150, 200])
        self.assertEqual(layer.color1_name, 'blue')
    
    def test_path_filename_sync(self):
        """Test that path and filename stay in sync"""
        layer = Layer(caller='test')
        
        layer.filename = 'emblem1.dds'
        self.assertEqual(layer.path, 'emblem1.dds')
        
        layer.path = 'emblem2.dds'
        self.assertEqual(layer.filename, 'emblem2.dds')
    
    def test_add_instance(self):
        """Test adding instances"""
        layer = Layer(caller='test')
        
        self.assertEqual(layer.instance_count, 1)
        
        # Add instance
        idx = layer.add_instance(pos_x=0.8, pos_y=0.2, caller='test')
        
        self.assertEqual(idx, 1)
        self.assertEqual(layer.instance_count, 2)
        
        # Switch to new instance
        layer.selected_instance = 1
        self.assertEqual(layer.pos_x, 0.8)
        self.assertEqual(layer.pos_y, 0.2)
    
    def test_remove_instance(self):
        """Test removing instances"""
        layer = Layer(caller='test')
        
        # Add instance
        layer.add_instance(caller='test')
        self.assertEqual(layer.instance_count, 2)
        
        # Remove it
        layer.remove_instance(1, caller='test')
        self.assertEqual(layer.instance_count, 1)
    
    def test_cannot_remove_last_instance(self):
        """Test that removing last instance raises error"""
        layer = Layer(caller='test')
        
        with self.assertRaises(ValueError):
            layer.remove_instance(0, caller='test')
    
    def test_get_instance(self):
        """Test getting instance data"""
        layer = Layer(caller='test')
        layer.pos_x = 0.3
        layer.pos_y = 0.7
        layer.scale_x = 1.5
        
        instance = layer.get_instance(0, caller='test')
        
        self.assertEqual(instance['pos_x'], 0.3)
        self.assertEqual(instance['pos_y'], 0.7)
        self.assertEqual(instance['scale_x'], 1.5)
    
    def test_select_instance(self):
        """Test selecting instances"""
        layer = Layer(caller='test')
        
        # Set properties on first instance
        layer.pos_x = 0.1
        layer.pos_y = 0.2
        
        # Add second instance
        layer.add_instance(pos_x=0.8, pos_y=0.9, caller='test')
        
        # Switch to second instance
        layer.selected_instance = 1
        
        # Verify properties changed
        self.assertEqual(layer.pos_x, 0.8)
        self.assertEqual(layer.pos_y, 0.9)
        
        # Switch back to first
        layer.selected_instance = 0
        self.assertEqual(layer.pos_x, 0.1)
        self.assertEqual(layer.pos_y, 0.2)
    
    def test_migration_from_old_format(self):
        """Test auto-migration from old format to instances"""
        # Old format data (no instances)
        old_data = {
            'uuid': 'test-uuid',
            'filename': 'emblem.dds',
            'pos_x': 0.4,
            'pos_y': 0.6,
            'scale_x': 1.2,
            'scale_y': 0.8,
            'rotation': 45.0,
            'depth': 2.0,
            'flip_x': True,
            'color1': [255, 0, 0]
        }
        
        layer = Layer(old_data, caller='test')
        
        # Should have migrated to instances format
        self.assertEqual(layer.instance_count, 1)
        self.assertEqual(layer.pos_x, 0.4)
        self.assertEqual(layer.pos_y, 0.6)
        self.assertEqual(layer.scale_x, 1.2)
        self.assertEqual(layer.scale_y, 0.8)
        self.assertEqual(layer.rotation, 45.0)
        self.assertEqual(layer.depth, 2.0)
        
        # Old format keys should be removed
        data = layer.to_dict(caller='test')
        self.assertNotIn('pos_x', data)  # Should only be in instances
        self.assertIn('instances', data)
        self.assertEqual(data['uuid'], 'test-uuid')  # UUID preserved
    
    def test_to_dict(self):
        """Test exporting to dictionary"""
        layer = Layer(caller='test')
        layer.filename = 'emblem.dds'
        layer.pos_x = 0.5
        layer.pos_y = 0.5
        
        data = layer.to_dict(caller='test')
        
        self.assertEqual(data['filename'], 'emblem.dds')
        self.assertIn('instances', data)
        self.assertEqual(data['instances'][0]['pos_x'], 0.5)
        self.assertIn('uuid', data)
    
    def test_repr(self):
        """Test string representation"""
        layer = Layer(caller='test')
        layer.filename = 'test.dds'
        
        repr_str = repr(layer)
        self.assertIn('Layer', repr_str)
        self.assertIn('test.dds', repr_str)
        self.assertIn('instances=1', repr_str)


class TestLayers(unittest.TestCase):
    """Tests for Layers collection"""
    
    def setUp(self):
        LayerTracker.register('test')
        LayerTracker.clear_log()
    
    def test_create_empty(self):
        """Test creating empty collection"""
        layers = Layers(caller='test')
        self.assertEqual(len(layers), 0)
    
    def test_create_from_list(self):
        """Test creating from data list"""
        data_list = [
            {'uuid': 'uuid1', 'filename': 'emblem1.dds', 'instances': [{'pos_x': 0.5, 'pos_y': 0.5, 'scale_x': 1.0, 'scale_y': 1.0, 'rotation': 0.0, 'depth': 0.0}]},
            {'uuid': 'uuid2', 'filename': 'emblem2.dds', 'instances': [{'pos_x': 0.3, 'pos_y': 0.7, 'scale_x': 1.0, 'scale_y': 1.0, 'rotation': 0.0, 'depth': 0.0}]}
        ]
        
        layers = Layers(data_list, caller='test')
        
        self.assertEqual(len(layers), 2)
        self.assertEqual(layers[0].filename, 'emblem1.dds')
        self.assertEqual(layers[1].filename, 'emblem2.dds')
    
    def test_append(self):
        """Test appending layers"""
        layers = Layers(caller='test')
        layer = Layer(caller='test')
        
        layers.append(layer, caller='test')
        
        self.assertEqual(len(layers), 1)
        self.assertEqual(layers[0], layer)
    
    def test_insert(self):
        """Test inserting layers"""
        layers = Layers(caller='test')
        
        layer1 = Layer(caller='test')
        layer2 = Layer(caller='test')
        layer3 = Layer(caller='test')
        
        layers.append(layer1, caller='test')
        layers.append(layer3, caller='test')
        layers.insert(1, layer2, caller='test')
        
        self.assertEqual(len(layers), 3)
        self.assertEqual(layers[0], layer1)
        self.assertEqual(layers[1], layer2)
        self.assertEqual(layers[2], layer3)
    
    def test_remove(self):
        """Test removing layers"""
        layers = Layers(caller='test')
        layer = Layer(caller='test')
        
        layers.append(layer, caller='test')
        layers.remove(layer, caller='test')
        
        self.assertEqual(len(layers), 0)
    
    def test_pop(self):
        """Test popping layers"""
        layers = Layers(caller='test')
        layer1 = Layer(caller='test')
        layer2 = Layer(caller='test')
        
        layers.append(layer1, caller='test')
        layers.append(layer2, caller='test')
        
        popped = layers.pop(caller='test')
        
        self.assertEqual(popped, layer2)
        self.assertEqual(len(layers), 1)
    
    def test_clear(self):
        """Test clearing collection"""
        layers = Layers(caller='test')
        layers.append(Layer(caller='test'), caller='test')
        layers.append(Layer(caller='test'), caller='test')
        
        layers.clear(caller='test')
        
        self.assertEqual(len(layers), 0)
    
    def test_move(self):
        """Test moving layers"""
        layers = Layers(caller='test')
        
        layer1 = Layer(caller='test')
        layer2 = Layer(caller='test')
        layer3 = Layer(caller='test')
        
        layer1.filename = 'layer1'
        layer2.filename = 'layer2'
        layer3.filename = 'layer3'
        
        layers.append(layer1, caller='test')
        layers.append(layer2, caller='test')
        layers.append(layer3, caller='test')
        
        # Move layer3 to position 0
        layers.move(2, 0, caller='test')
        
        self.assertEqual(layers[0].filename, 'layer3')
        self.assertEqual(layers[1].filename, 'layer1')
        self.assertEqual(layers[2].filename, 'layer2')
    
    def test_iteration(self):
        """Test iterating over layers"""
        layers = Layers(caller='test')
        layers.append(Layer(caller='test'), caller='test')
        layers.append(Layer(caller='test'), caller='test')
        
        count = 0
        for layer in layers:
            self.assertIsInstance(layer, Layer)
            count += 1
        
        self.assertEqual(count, 2)
    
    def test_get_by_uuid(self):
        """Test finding layer by UUID"""
        layers = Layers(caller='test')
        
        layer1 = Layer(caller='test')
        layer2 = Layer(caller='test')
        
        layers.append(layer1, caller='test')
        layers.append(layer2, caller='test')
        
        found = layers.get_by_uuid(layer2.uuid)
        self.assertEqual(found, layer2)
    
    def test_get_by_uuid_not_found(self):
        """Test that get_by_uuid returns None for missing UUID"""
        layers = Layers(caller='test')
        layers.append(Layer(caller='test'), caller='test')
        
        found = layers.get_by_uuid('nonexistent-uuid')
        self.assertIsNone(found)
    
    def test_get_index_by_uuid(self):
        """Test getting index by UUID"""
        layers = Layers(caller='test')
        
        layer1 = Layer(caller='test')
        layer2 = Layer(caller='test')
        
        layers.append(layer1, caller='test')
        layers.append(layer2, caller='test')
        
        index = layers.get_index_by_uuid(layer2.uuid)
        self.assertEqual(index, 1)
    
    def test_get_index_by_uuid_raises(self):
        """Test that get_index_by_uuid raises for missing UUID"""
        layers = Layers(caller='test')
        layers.append(Layer(caller='test'), caller='test')
        
        with self.assertRaises(ValueError):
            layers.get_index_by_uuid('nonexistent-uuid')
    
    def test_to_dict_list(self):
        """Test exporting to dict list"""
        data_list = [
            {'uuid': 'uuid1', 'filename': 'emblem1.dds', 'instances': [{'pos_x': 0.5, 'pos_y': 0.5, 'scale_x': 1.0, 'scale_y': 1.0, 'rotation': 0.0, 'depth': 0.0}]},
            {'uuid': 'uuid2', 'filename': 'emblem2.dds', 'instances': [{'pos_x': 0.3, 'pos_y': 0.7, 'scale_x': 1.0, 'scale_y': 1.0, 'rotation': 0.0, 'depth': 0.0}]}
        ]
        
        layers = Layers(data_list, caller='test')
        exported = layers.to_dict_list(caller='test')
        
        self.assertEqual(len(exported), 2)
        self.assertEqual(exported[0]['uuid'], 'uuid1')
        self.assertEqual(exported[1]['uuid'], 'uuid2')
    
    def test_from_dict_list(self):
        """Test creating from dict list (factory method)"""
        data_list = [
            {'uuid': 'uuid1', 'filename': 'emblem1.dds', 'instances': [{'pos_x': 0.5, 'pos_y': 0.5, 'scale_x': 1.0, 'scale_y': 1.0, 'rotation': 0.0, 'depth': 0.0}]},
        ]
        
        layers = Layers.from_dict_list(data_list, caller='test')
        
        self.assertEqual(len(layers), 1)
        self.assertEqual(layers[0].filename, 'emblem1.dds')
    
    def test_repr(self):
        """Test string representation"""
        layers = Layers(caller='test')
        layers.append(Layer(caller='test'), caller='test')
        
        repr_str = repr(layers)
        self.assertIn('Layers', repr_str)
        self.assertIn('1 layer', repr_str)


if __name__ == '__main__':
    unittest.main()
