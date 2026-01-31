"""
CK3 Coat of Arms Editor - Layer Data Model

Provides object-oriented interface to layer data with:
- Auto-migration from old format to instances format
- Method call tracking for debugging
- Instance-aware property access  
- Flat structure suitable for CK3 import/export
- UUID-based identification (stable across reordering)

This is part of the MODEL layer - pure data, no UI logic.

Usage:
    # Register your component
    LayerTracker.register('canvas_area')
    
    # Create layer
    layer = Layer(data, caller='canvas_area')
    
    # Access properties (automatically uses selected instance)
    x = layer.pos_x
    layer.pos_x = 0.6
    
    # UUID for stable identification
    uuid = layer.uuid
    
    # Export back to dict
    data = layer.to_dict()
"""

import logging
import uuid as uuid_module
from typing import Dict, List, Optional, Any
import sys
import os

# Add parent directory to path for constants import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from constants import (
    DEFAULT_POSITION_X, DEFAULT_POSITION_Y,
    DEFAULT_SCALE_X, DEFAULT_SCALE_Y,
    DEFAULT_ROTATION,
    DEFAULT_EMBLEM_COLOR1, DEFAULT_EMBLEM_COLOR2, DEFAULT_EMBLEM_COLOR3,
    CK3_NAMED_COLORS
)

from .instance import Instance


class LayerTracker:
    """Tracks method calls for debugging and accountability
    
    All components that manipulate layers must register a unique key.
    All layer operations are logged with caller information.
    """
    
    # Registered component keys (pre-register common internal callers)
    _registered_keys = {'CoA', 'Layer', 'Layers', 'query_mixin', 'CoA.merge'}
    
    # Call log (limited size to prevent memory issues)
    _call_log = []
    _max_log_size = 1000
    
    # Logger instance
    _logger = logging.getLogger('LayerTracker')
    
    @classmethod
    def register(cls, key: str) -> None:
        """Register a caller key (e.g., 'canvas_area', 'property_sidebar')
        
        Args:
            key: Unique identifier for the calling component
        """
        cls._registered_keys.add(key)
        cls._logger.info(f"Registered caller: {key}")
    
    @classmethod
    def log_call(cls, caller: str, layer_id: int, method: str, property_name: str = None, value: Any = None):
        """Log a method call
        
        Args:
            caller: The registered key of the caller
            layer_id: ID of the layer being modified
            method: Name of the method called
            property_name: Property being accessed (if applicable)
            value: New value being set (if applicable)
        """
        if caller not in cls._registered_keys:
            cls._logger.warning(f"Unregistered caller: {caller}")
        
        log_entry = {
            'caller': caller,
            'layer_id': layer_id,
            'method': method,
            'property': property_name,
            'value': value
        }
        
        cls._call_log.append(log_entry)
        
        # Trim log if too large
        if len(cls._call_log) > cls._max_log_size:
            cls._call_log = cls._call_log[-cls._max_log_size:]
        
        # Log at debug level
        if property_name:
            cls._logger.debug(f"{caller}.{method}(layer={layer_id}, {property_name}={value})")
        else:
            cls._logger.debug(f"{caller}.{method}(layer={layer_id})")
    
    @classmethod
    def get_log(cls, caller: str = None, layer_id: int = None) -> List[Dict]:
        """Get call log, optionally filtered
        
        Args:
            caller: Filter by caller key
            layer_id: Filter by layer ID
            
        Returns:
            List of log entries
        """
        log = cls._call_log
        
        if caller:
            log = [e for e in log if e['caller'] == caller]
        
        if layer_id is not None:
            log = [e for e in log if e['layer_id'] == layer_id]
        
        return log
    
    @classmethod
    def clear_log(cls):
        """Clear the call log"""
        cls._call_log.clear()
        cls._logger.info("Call log cleared")


class Layer:
    """Object-oriented wrapper for layer data with instance support
    
    Provides property-based access to layer data with:
    - Bounds checking and validation
    - Method call tracking
    - Flat structure (no parent/child hierarchy)
    - UUID-based identification (stable across reordering)
    
    Instance Properties (per-instance):
        pos_x, pos_y, scale_x, scale_y, rotation, depth
    
    Layer Properties (shared):
        filename, path, colors, color1, color2, color3,
        color1_name, color2_name, color3_name,
        flip_x, flip_y, mask, uuid
    """
    
    # Auto-incrementing ID for tracking (internal only, not persisted)
    _next_id = 0
    
    def __init__(self, data: Optional[Dict] = None, caller: str = 'unknown'):
        """Initialize layer from dictionary or create new
        
        Args:
            data: Existing layer dictionary, or None to create new
            caller: Registered key identifying the caller
        """
        # Internal tracking ID (not persisted)
        self._id = Layer._next_id
        Layer._next_id += 1
        
        # Initialize or copy data
        self._data = data if data is not None else self._create_default()
        
        # Ensure UUID exists (create if missing, preserve if present)
        if 'uuid' not in self._data:
            self._data['uuid'] = str(uuid_module.uuid4())
        
        # Convert instance dictionaries to Instance objects
        if 'instances' in self._data:
            instances = self._data['instances']
            if instances and isinstance(instances[0], dict):
                self._data['instances'] = [Instance(inst) if isinstance(inst, dict) else inst for inst in instances]
        
        LayerTracker.log_call(caller, self._id, '__init__')
    
    @property
    def id(self) -> int:
        """Get unique layer ID for tracking (internal, not persisted)"""
        return self._id
    
    @property
    def uuid(self) -> str:
        """Get UUID (stable identifier, persists across saves/loads)"""
        return self._data['uuid']
    
    # ========================================
    # Instance Properties (per-instance)
    # ========================================
    
    @property
    def pos_x(self) -> float:
        """Get X position of selected instance (0.0 to 1.0)"""
        return self._get_instance_property('pos_x', DEFAULT_POSITION_X)
    
    @pos_x.setter
    def pos_x(self, value: float):
        """Set X position of selected instance"""
        self._set_instance_property('pos_x', value)
    
    @property
    def pos_y(self) -> float:
        """Get Y position of selected instance (0.0 to 1.0)"""
        return self._get_instance_property('pos_y', DEFAULT_POSITION_Y)
    
    @pos_y.setter
    def pos_y(self, value: float):
        """Set Y position of selected instance"""
        self._set_instance_property('pos_y', value)
    
    @property
    def scale_x(self) -> float:
        """Get X scale of selected instance"""
        return self._get_instance_property('scale_x', DEFAULT_SCALE_X)
    
    @scale_x.setter
    def scale_x(self, value: float):
        """Set X scale of selected instance"""
        self._set_instance_property('scale_x', value)
    
    @property
    def scale_y(self) -> float:
        """Get Y scale of selected instance"""
        return self._get_instance_property('scale_y', DEFAULT_SCALE_Y)
    
    @scale_y.setter
    def scale_y(self, value: float):
        """Set Y scale of selected instance"""
        self._set_instance_property('scale_y', value)
    
    @property
    def rotation(self) -> float:
        """Get rotation of selected instance (degrees)"""
        return self._get_instance_property('rotation', DEFAULT_ROTATION)
    
    @rotation.setter
    def rotation(self, value: float):
        """Set rotation of selected instance (degrees)"""
        self._set_instance_property('rotation', value)
    
    @property
    def depth(self) -> float:
        """Get depth of selected instance"""
        return self._get_instance_property('depth', 0.0)
    
    @depth.setter
    def depth(self, value: float):
        """Set depth of selected instance"""
        self._set_instance_property('depth', value)
    
    # ========================================
    # Layer Properties (shared across instances)
    # ========================================
    
    @property
    def filename(self) -> str:
        """Get texture filename"""
        return self._data.get('filename', '')
    
    @filename.setter
    def filename(self, value: str):
        """Set texture filename"""
        self._data['filename'] = value
        self._data['path'] = value  # Keep path in sync
    
    @property
    def path(self) -> str:
        """Get texture path (alias for filename)"""
        return self._data.get('path', self._data.get('filename', ''))
    
    @path.setter
    def path(self, value: str):
        """Set texture path"""
        self._data['path'] = value
        self._data['filename'] = value  # Keep filename in sync
    
    @property
    def colors(self) -> int:
        """Get number of colors (1, 2, or 3)"""
        return self._data.get('colors', 3)
    
    @colors.setter
    def colors(self, value: int):
        """Set number of colors"""
        if value not in (1, 2, 3):
            raise ValueError(f"colors must be 1, 2, or 3, got {value}")
        self._data['colors'] = value
    
    @property
    def color1(self) -> List[int]:
        """Get color1 RGB values"""
        return self._data.get('color1', CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR1]['rgb'].copy())
    
    @color1.setter
    def color1(self, value: List[int]):
        """Set color1 RGB values"""
        self._data['color1'] = value
    
    @property
    def color2(self) -> List[int]:
        """Get color2 RGB values"""
        return self._data.get('color2', CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR2]['rgb'].copy())
    
    @color2.setter
    def color2(self, value: List[int]):
        """Set color2 RGB values"""
        self._data['color2'] = value
    
    @property
    def color3(self) -> List[int]:
        """Get color3 RGB values"""
        return self._data.get('color3', CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR3]['rgb'].copy())
    
    @color3.setter
    def color3(self, value: List[int]):
        """Set color3 RGB values"""
        self._data['color3'] = value
    
    @property
    def color1_name(self) -> str:
        """Get color1 name"""
        return self._data.get('color1_name', DEFAULT_EMBLEM_COLOR1)
    
    @color1_name.setter
    def color1_name(self, value: str):
        """Set color1 name"""
        self._data['color1_name'] = value
    
    @property
    def color2_name(self) -> str:
        """Get color2 name"""
        return self._data.get('color2_name', DEFAULT_EMBLEM_COLOR2)
    
    @color2_name.setter
    def color2_name(self, value: str):
        """Set color2 name"""
        self._data['color2_name'] = value
    
    @property
    def color3_name(self) -> str:
        """Get color3 name"""
        return self._data.get('color3_name', DEFAULT_EMBLEM_COLOR3)
    
    @color3_name.setter
    def color3_name(self, value: str):
        """Set color3 name"""
        self._data['color3_name'] = value
    
    @property
    def flip_x(self) -> bool:
        """Get horizontal flip state"""
        return self._data.get('flip_x', False)
    
    @flip_x.setter
    def flip_x(self, value: bool):
        """Set horizontal flip state"""
        self._data['flip_x'] = bool(value)
    
    @property
    def flip_y(self) -> bool:
        """Get vertical flip state"""
        return self._data.get('flip_y', False)
    
    @flip_y.setter
    def flip_y(self, value: bool):
        """Set vertical flip state"""
        self._data['flip_y'] = bool(value)
    
    @property
    def mask(self) -> Optional[List[int]]:
        """Get mask channels [r, g, b] or None"""
        return self._data.get('mask')
    
    @mask.setter
    def mask(self, value: Optional[List[int]]):
        """Set mask channels or None"""
        self._data['mask'] = value
    
    @property
    def visible(self) -> bool:
        """Get visibility state"""
        return self._data.get('visible', True)
    
    @visible.setter
    def visible(self, value: bool):
        """Set visibility state"""
        self._data['visible'] = bool(value)
    
    # ========================================
    # Instance Management
    # ========================================
    
    @property
    def selected_instance(self) -> int:
        """Get selected instance index"""
        return self._data.get('selected_instance', 0)
    
    @selected_instance.setter
    def selected_instance(self, value: int):
        """Set selected instance index"""
        instances = self._data.get('instances', [])
        if not (0 <= value < len(instances)):
            raise ValueError(f"Instance index {value} out of range [0, {len(instances)})")
        self._data['selected_instance'] = value
    
    @property
    def instance_count(self) -> int:
        """Get number of instances"""
        return len(self._data.get('instances', []))
    
    def get_instance(self, index: int, caller: str = 'unknown'):
        """Get instance by index
        
        Args:
            index: Instance index
            caller: Registered key identifying the caller
            
        Returns:
            Instance object
            
        Raises:
            IndexError: If index out of range
        """
        LayerTracker.log_call(caller, self._id, 'get_instance', property_name='index', value=index)
        
        instances = self._data.get('instances', [])
        if not (0 <= index < len(instances)):
            raise IndexError(f"Instance index {index} out of range [0, {len(instances)})")
        
        return instances[index]
    
    def add_instance(self, pos_x: float = None, pos_y: float = None, caller: str = 'unknown') -> int:
        """Add new instance to this layer
        
        Args:
            pos_x: X position (defaults to current selected instance)
            pos_y: Y position (defaults to current selected instance)
            caller: Registered key identifying the caller
            
        Returns:
            Index of the new instance
        """
        LayerTracker.log_call(caller, self._id, 'add_instance')
        
        # Get defaults from current instance
        if pos_x is None:
            pos_x = self.pos_x
        if pos_y is None:
            pos_y = self.pos_y
        
        new_instance = Instance({
            'pos_x': pos_x,
            'pos_y': pos_y,
            'scale_x': DEFAULT_SCALE_X,
            'scale_y': DEFAULT_SCALE_Y,
            'rotation': DEFAULT_ROTATION,
            'depth': 0.0
        })
        
        instances = self._data.setdefault('instances', [])
        instances.append(new_instance)
        
        return len(instances) - 1
    
    def remove_instance(self, index: int, caller: str = 'unknown'):
        """Remove instance by index
        
        Args:
            index: Instance index to remove
            caller: Registered key identifying the caller
            
        Raises:
            ValueError: If trying to remove last instance
            IndexError: If index out of range
        """
        LayerTracker.log_call(caller, self._id, 'remove_instance', property_name='index', value=index)
        
        instances = self._data.get('instances', [])
        
        if len(instances) <= 1:
            raise ValueError("Cannot remove last instance")
        
        if not (0 <= index < len(instances)):
            raise IndexError(f"Instance index {index} out of range [0, {len(instances)})")
        
        instances.pop(index)
        
        # Adjust selected_instance if needed
        if self.selected_instance >= len(instances):
            self._data['selected_instance'] = len(instances) - 1
    
    # ========================================
    # Internal Methods
    # ========================================
    
    def _get_instance_property(self, prop_name: str, default: Any) -> Any:
        """Get property from selected instance
        
        Args:
            prop_name: Property name
            default: Default value if not found
            
        Returns:
            Property value
        """
        instances = self._data.get('instances', [])
        selected = self._data.get('selected_instance', 0)
        
        if 0 <= selected < len(instances):
            inst = instances[selected]
            if isinstance(inst, Instance):
                return getattr(inst, prop_name, default)
            else:
                # Fallback for dict (shouldn't happen after __init__)
                return inst.get(prop_name, default)
        
        return default
    
    def _set_instance_property(self, prop_name: str, value: Any):
        """Set property on selected instance
        
        Args:
            prop_name: Property name
            value: New value
        """
        instances = self._data.setdefault('instances', [])
        selected = self._data.get('selected_instance', 0)
        
        # Ensure instances list exists and has enough entries
        if not instances:
            instances.append(Instance())
            self._data['instances'] = instances
        
        if 0 <= selected < len(instances):
            inst = instances[selected]
            if isinstance(inst, Instance):
                setattr(inst, prop_name, value)
            else:
                # Fallback for dict (shouldn't happen after __init__)
                inst[prop_name] = value
    
    def _create_default(self) -> Dict:
        """Create default layer data"""
        return {
            'uuid': str(uuid_module.uuid4()),
            'filename': '',
            'path': '',
            'colors': 3,
            'instances': [Instance()],  # Create Instance object instead of dict
            'selected_instance': 0,
            'flip_x': False,
            'flip_y': False,
            'color1': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR1]['rgb'],
            'color2': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR2]['rgb'],
            'color3': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR3]['rgb'],
            'color1_name': DEFAULT_EMBLEM_COLOR1,
            'color2_name': DEFAULT_EMBLEM_COLOR2,
            'color3_name': DEFAULT_EMBLEM_COLOR3,
            'mask': None
        }
    
    def _create_default_instance(self) -> Dict:
        """Create default instance data"""
        return {
            'pos_x': DEFAULT_POSITION_X,
            'pos_y': DEFAULT_POSITION_Y,
            'scale_x': DEFAULT_SCALE_X,
            'scale_y': DEFAULT_SCALE_Y,
            'rotation': DEFAULT_ROTATION,
            'depth': 0.0
        }
    
    def to_dict(self, caller: str = 'unknown') -> Dict:
        """Export to dictionary format
        
        Args:
            caller: Registered key identifying the caller
            
        Returns:
            Dictionary containing all layer data (including UUID)
        """
        LayerTracker.log_call(caller, self._id, 'to_dict')
        
        # Create a copy of the data
        import copy
        result = copy.copy(self._data)
        
        # Convert Instance objects back to dictionaries for serialization
        if 'instances' in result:
            instances = result['instances']
            result['instances'] = [
                inst.to_dict() if isinstance(inst, Instance) else inst 
                for inst in instances
            ]
        
        return result
    
    def serialize(self, caller: str = 'unknown') -> str:
        """Serialize layer to Clausewitz format
        
        Args:
            caller: Registered key identifying the caller
            
        Returns:
            Clausewitz-formatted colored_emblem block
        """
        LayerTracker.log_call(caller, self._id, 'serialize')
        
        from utils.color_utils import rgb_to_color_name
        
        # Helper to normalize RGB [0-255] to [0-1] range
        def normalize_rgb(rgb):
            if not rgb:
                return [1.0, 1.0, 1.0]
            return [rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0]
        
        # Helper to format color
        def format_color(rgb, color_name):
            normalized = normalize_rgb(rgb)
            color_str = rgb_to_color_name(normalized, color_name)
            if color_str.startswith('rgb'):
                return color_str  # Already formatted as "rgb { R G B }"
            else:
                return f'"{color_str}"'  # Named color, add quotes
        
        lines = []
        lines.append('\tcolored_emblem = {')
        lines.append(f'\t\ttexture = "{self.filename}"')
        
        # Add colors based on color count
        lines.append(f'\t\tcolor1 = {format_color(self.color1, self.color1_name)}')
        if self.colors >= 2:
            lines.append(f'\t\tcolor2 = {format_color(self.color2, self.color2_name)}')
        if self.colors >= 3:
            lines.append(f'\t\tcolor3 = {format_color(self.color3, self.color3_name)}')
        
        # Serialize mask if present
        if self.mask is not None:
            mask_str = ' '.join(map(str, self.mask))
            lines.append(f'\t\tmask = {{ {mask_str} }}')
        
        # Serialize all instances
        instances = self._data.get('instances', [])
        for inst in instances:
            if isinstance(inst, Instance):
                lines.append(inst.serialize(flip_x=self.flip_x, flip_y=self.flip_y))
        
        lines.append('\t}')
        return '\n'.join(lines)
    
    @classmethod
    def parse(cls, data: Dict[str, Any], caller: str = 'unknown') -> 'Layer':
        """Parse layer from Clausewitz parser output
        
        Args:
            data: Dict from parser with texture, colors, instances, etc
            caller: Registered key identifying the caller
            
        Returns:
            New Layer object
        """
        from utils.color_utils import color_name_to_rgb
        from utils.metadata_cache import get_texture_color_count
        
        filename = data.get('texture', '')
        
        # Get color names and RGB values
        color1_name = data.get('color1', 'yellow')
        color2_name = data.get('color2', 'red')
        color3_name = data.get('color3', 'red')
        
        # Look up actual color count from texture metadata
        color_count = get_texture_color_count(filename)
        
        # Parse instances
        instances_data = data.get('instance', [])
        if not instances_data:
            # No instance block means default values
            instances_data = [{'position': [0.5, 0.5], 'scale': [1.0, 1.0], 'rotation': 0}]
        
        # Parse first instance to detect flip from negative scale
        first_inst_data = instances_data[0]
        scale = first_inst_data.get('scale', [1.0, 1.0])
        scale_x_raw = scale[0] if isinstance(scale, list) else 1.0
        scale_y_raw = scale[1] if isinstance(scale, list) and len(scale) > 1 else 1.0
        flip_x = scale_x_raw < 0
        flip_y = scale_y_raw < 0
        
        # Convert all instances
        instances = [Instance.parse(inst_data) for inst_data in instances_data]
        
        # Parse mask if present
        mask = data.get('mask')
        if isinstance(mask, list):
            mask = [int(x) for x in mask]
        
        layer_data = {
            'uuid': str(uuid_module.uuid4()),
            'filename': filename,
            'path': filename,
            'colors': color_count,
            'instances': instances,
            'selected_instance': 0,
            'flip_x': flip_x,
            'flip_y': flip_y,
            'color1': color_name_to_rgb(color1_name),
            'color2': color_name_to_rgb(color2_name),
            'color3': color_name_to_rgb(color3_name),
            'color1_name': color1_name,
            'color2_name': color2_name,
            'color3_name': color3_name,
            'mask': mask,
            'visible': True
        }
        
        return Layer(layer_data, caller=caller)
    
    def duplicate(self, caller: str = 'unknown', offset_x: float = 0.0, offset_y: float = 0.0) -> 'Layer':
        """Create a duplicate of this layer with a new UUID
        
        Args:
            caller: Registered key identifying the caller
            offset_x: X position offset for all instances (default 0.0)
            offset_y: Y position offset for all instances (default 0.0)
            
        Returns:
            New Layer object with duplicated data and new UUID
        """
        LayerTracker.log_call(caller, self._id, 'duplicate', value=f"offset=({offset_x},{offset_y})")
        
        # Deep copy the data dict
        import copy
        duplicated = copy.deepcopy(self._data)
        
        # Generate new UUID
        duplicated['uuid'] = str(uuid_module.uuid4())
        
        # Apply offset to all instances if provided
        if offset_x != 0.0 or offset_y != 0.0:
            for inst in duplicated['instances']:
                # Instances in duplicated dict are still Instance objects after deepcopy
                if isinstance(inst, Instance):
                    inst.pos_x = inst.pos_x + offset_x  # setter handles clamping
                    inst.pos_y = inst.pos_y + offset_y  # setter handles clamping
        
        return Layer(duplicated, caller=caller)
    
    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"Layer(uuid='{self.uuid}', filename='{self.filename}', instances={self.instance_count})"


class Layers:
    """Collection of Layer objects with array-like access
    
    Provides container for multiple layers with:
    - List-like access (indexing, iteration, len)
    - Layer management (add, remove, move)
    - Batch operations
    - Export to dict list
    - UUID-based lookups
    """
    
    def __init__(self, data_list: Optional[List[Dict]] = None, caller: str = 'unknown'):
        """Initialize from list of dictionaries
        
        Args:
            data_list: List of layer dictionaries, or None for empty
            caller: Registered key identifying the caller
        """
        self._layers: List[Layer] = []
        
        if data_list:
            for data in data_list:
                self._layers.append(Layer(data, caller=caller))
        
        LayerTracker.log_call(caller, -1, 'Layers.__init__', value=f"{len(self._layers)} layers")
    
    def __len__(self) -> int:
        """Get number of layers"""
        return len(self._layers)
    
    def __getitem__(self, index: int) -> Layer:
        """Get layer by index"""
        return self._layers[index]
    
    def __setitem__(self, index: int, layer: Layer):
        """Set layer at index"""
        if not isinstance(layer, Layer):
            raise TypeError(f"Expected Layer, got {type(layer)}")
        self._layers[index] = layer
    
    def __iter__(self):
        """Iterate over layers"""
        return iter(self._layers)
    
    def __repr__(self) -> str:
        """String representation"""
        return f"Layers({len(self._layers)} layers)"
    
    def append(self, layer: Layer, caller: str = 'unknown'):
        """Add layer to end
        
        Args:
            layer: Layer to add
            caller: Registered key identifying the caller
        """
        if not isinstance(layer, Layer):
            raise TypeError(f"Expected Layer, got {type(layer)}")
        
        self._layers.append(layer)
        LayerTracker.log_call(caller, layer.id, 'Layers.append')
    
    def extend(self, layers: List[Layer], caller: str = 'unknown'):
        """Add multiple layers to end
        
        Args:
            layers: List of layers to add
            caller: Registered key identifying the caller
        """
        for layer in layers:
            if not isinstance(layer, Layer):
                raise TypeError(f"Expected Layer, got {type(layer)}")
        
        self._layers.extend(layers)
        LayerTracker.log_call(caller, -1, 'Layers.extend', value=f"{len(layers)} layers")
    
    def insert(self, index: int, layer: Layer, caller: str = 'unknown'):
        """Insert layer at index
        
        Args:
            index: Position to insert
            layer: Layer to insert
            caller: Registered key identifying the caller
        """
        if not isinstance(layer, Layer):
            raise TypeError(f"Expected Layer, got {type(layer)}")
        
        self._layers.insert(index, layer)
        LayerTracker.log_call(caller, layer.id, 'Layers.insert', property_name='index', value=index)
    
    def remove(self, layer: Layer, caller: str = 'unknown'):
        """Remove layer
        
        Args:
            layer: Layer to remove
            caller: Registered key identifying the caller
        """
        self._layers.remove(layer)
        LayerTracker.log_call(caller, layer.id, 'Layers.remove')
    
    def pop(self, index: int = -1, caller: str = 'unknown') -> Layer:
        """Remove and return layer at index
        
        Args:
            index: Index to pop (default: last)
            caller: Registered key identifying the caller
            
        Returns:
            Removed layer
        """
        layer = self._layers.pop(index)
        LayerTracker.log_call(caller, layer.id, 'Layers.pop', property_name='index', value=index)
        return layer
    
    def clear(self, caller: str = 'unknown'):
        """Remove all layers
        
        Args:
            caller: Registered key identifying the caller
        """
        self._layers.clear()
        LayerTracker.log_call(caller, -1, 'Layers.clear')
    
    def move(self, from_index: int, to_index: int, caller: str = 'unknown'):
        """Move layer from one index to another
        
        Args:
            from_index: Current index
            to_index: Target index
            caller: Registered key identifying the caller
        """
        layer = self._layers.pop(from_index)
        self._layers.insert(to_index, layer)
        LayerTracker.log_call(caller, layer.id, 'Layers.move', value=f"{from_index} -> {to_index}")
    
    def get_by_uuid(self, uuid: str) -> Optional[Layer]:
        """Find layer by UUID
        
        Args:
            uuid: Layer UUID to search for
            
        Returns:
            Layer with matching UUID, or None if not found
        """
        for layer in self._layers:
            if layer.uuid == uuid:
                return layer
        return None
    
    def get_index_by_uuid(self, uuid: str) -> int:
        """Get index of layer with given UUID
        
        Args:
            uuid: Layer UUID to search for
            
        Returns:
            Index of layer with matching UUID
            
        Raises:
            ValueError: If UUID not found
        """
        for i, layer in enumerate(self._layers):
            if layer.uuid == uuid:
                return i
        raise ValueError(f"Layer with UUID '{uuid}' not found")
    
    def to_dict_list(self, caller: str = 'unknown') -> List[Dict]:
        """Export all layers to list of dictionaries
        
        Args:
            caller: Registered key identifying the caller
            
        Returns:
            List of layer dictionaries (with UUIDs)
        """
        LayerTracker.log_call(caller, -1, 'Layers.to_dict_list')
        return [layer.to_dict(caller=caller) for layer in self._layers]
    
    @classmethod
    def from_dict_list(cls, data_list: List[Dict], caller: str = 'unknown') -> 'Layers':
        """Create Layers from list of dictionaries
        
        Args:
            data_list: List of layer dictionaries
            caller: Registered key identifying the caller
            
        Returns:
            New Layers instance
        """
        return cls(data_list, caller=caller)
