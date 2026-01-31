"""
CK3 Coat of Arms Editor - CoA Data Model

THE MODEL in the MVC architecture. Owns all CoA data and operations.

This class handles:
- Base pattern and colors
- Layers collection (with UUID-based identification)
- CK3 format serialization (from_string/to_string)
- Transform operations (single layer and multi-layer groups)
- Color operations
- Layer management (add, remove, move, duplicate, merge, split)
- Instance management (add, remove per layer)
- Query API (for UI to retrieve data)
- Snapshot API (for undo/redo support)
- Group transform math (AABB, ferris wheel rotation)

The CoA model is INDEPENDENT of UI:
- No Qt imports
- No rendering logic
- No selection state (that's EditorState)
- No undo stack (EditorState manages that with snapshots)

Controllers call methods on this model.
Views query this model for display data.

Usage:
    # Parse from CK3 format
    coa = CoA.from_string(ck3_text)
    
    # Modify layers
    layer_uuid = coa.add_layer(emblem_path="emblem_ordinary_cross.dds")
    coa.set_layer_position(layer_uuid, 0.5, 0.5)
    coa.rotate_layer(layer_uuid, 45.0)
    
    # Group operations
    coa.rotate_layers_group([uuid1, uuid2], 90.0)
    
    # Export back to CK3
    ck3_text = coa.to_string()
    
    # Undo support
    snapshot = coa.get_snapshot()
    coa.set_snapshot(snapshot)
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
import uuid as uuid_module
from copy import deepcopy
import math
import inspect

from ._coa_internal.layer import Layer, Layers, LayerTracker
from ._coa_internal.query_mixin import CoAQueryMixin
from constants import (
    DEFAULT_POSITION_X, DEFAULT_POSITION_Y,
    DEFAULT_SCALE_X, DEFAULT_SCALE_Y,
    DEFAULT_ROTATION,
    DEFAULT_PATTERN_TEXTURE,
    DEFAULT_BASE_COLOR1, DEFAULT_BASE_COLOR2, DEFAULT_BASE_COLOR3,
    DEFAULT_EMBLEM_COLOR1, DEFAULT_EMBLEM_COLOR2, DEFAULT_EMBLEM_COLOR3,
    CK3_NAMED_COLORS
)


class CoA(CoAQueryMixin):
    """Coat of Arms data model with full operation API
    
    Manages all CoA data and operations. This is THE MODEL in MVC.
    All data manipulation goes through this class.
    
    Active Instance Pattern:
        CoA.set_active(coa_instance) - Set the active CoA
        CoA.get_active() - Get the active CoA instance
        CoA.has_active() - Check if active instance exists
    
    Properties:
        pattern: Base pattern filename
        pattern_color1: RGB list for pattern color 1
        pattern_color2: RGB list for pattern color 2
        pattern_color1_name: CK3 color name for pattern color 1
        pattern_color2_name: CK3 color name for pattern color 2
        layers: Layers collection (UUID-based access)
    """
    
    _active_instance = None  # Class variable for active CoA instance
    
    @classmethod
    def set_active(cls, instance: 'CoA'):
        """Set the active CoA instance
        
        Args:
            instance: CoA instance to set as active
        """
        cls._active_instance = instance
    
    @classmethod
    def get_active(cls) -> 'CoA':
        """Get the active CoA instance
        
        Returns:
            Active CoA instance
            
        Raises:
            RuntimeError: If no active instance set
        """
        if cls._active_instance is None:
            raise RuntimeError("No active CoA instance set. Call CoA.set_active() first.")
        return cls._active_instance
    
    @classmethod
    def has_active(cls) -> bool:
        """Check if an active CoA instance exists
        
        Returns:
            True if active instance set, False otherwise
        """
        return cls._active_instance is not None
    
    def __init__(self):
        """Create new CoA with defaults"""
        self._logger = logging.getLogger('CoA')
        
        # Register as a LayerTracker caller
        from ._coa_internal.layer import LayerTracker
        LayerTracker.register('CoA')
        
        # Base pattern and colors
        self._pattern = DEFAULT_PATTERN_TEXTURE
        self._pattern_color1 = CK3_NAMED_COLORS[DEFAULT_BASE_COLOR1]['rgb'].copy()
        self._pattern_color2 = CK3_NAMED_COLORS[DEFAULT_BASE_COLOR2]['rgb'].copy()
        self._pattern_color3 = CK3_NAMED_COLORS[DEFAULT_BASE_COLOR3]['rgb'].copy()
        self._pattern_color1_name = DEFAULT_BASE_COLOR1
        self._pattern_color2_name = DEFAULT_BASE_COLOR2
        self._pattern_color3_name = DEFAULT_BASE_COLOR3
        
        # Layers collection - stored with name mangling to prevent external access
        # Access ONLY through the _layers property which validates the caller
        self.__layers = Layers(caller='CoA')
        
        # Transform cache for group operations (prevents cumulative error)
        self._transform_cache = None  # Dict: {uuid: {pos_x, pos_y, scale_x, scale_y, rotation}}
        
        # Track last added layer UUID for auto-selection
        self._last_added_uuid = None
        self._last_added_uuids = []  # List of UUIDs from last add operation (for multi-paste)
        
        self._logger.debug("Created new CoA")
    
    # ========================================
    # Properties
    # ========================================
    
    @property
    def _layers(self):
        """Protected layers access - only accessible from within CoA class
        
        Raises:
            AttributeError: If accessed from outside the CoA class
        """
        # Check caller - get the frame that's trying to access _layers
        frame = inspect.currentframe()
        try:
            caller_frame = frame.f_back
            # Get the caller's self object
            caller_self = caller_frame.f_locals.get('self')
            # Allow access if called from within a CoA instance method
            if caller_self is not None and isinstance(caller_self, CoA):
                return self.__layers
            else:
                # Get caller info for better error message
                caller_filename = caller_frame.f_code.co_filename
                caller_lineno = caller_frame.f_lineno
                caller_function = caller_frame.f_code.co_name
                raise AttributeError(
                    f"Direct access to CoA._layers is forbidden! "
                    f"Attempted from {caller_filename}:{caller_lineno} in {caller_function}(). "
                    f"Use CoA's public methods instead (get_layer_by_uuid, get_layer_count, etc.)"
                )
        finally:
            del frame  # Avoid reference cycles
    
    @_layers.setter
    def _layers(self, value):
        """Protected layers setter - only accessible from within CoA class
        
        Raises:
            AttributeError: If accessed from outside the CoA class
        """
        # Check caller - get the frame that's trying to set _layers
        frame = inspect.currentframe()
        try:
            caller_frame = frame.f_back
            # Get the caller's self object
            caller_self = caller_frame.f_locals.get('self')
            # Allow setting if called from within a CoA instance method
            if caller_self is not None and isinstance(caller_self, CoA):
                self.__layers = value
            else:
                # Get caller info for better error message
                caller_filename = caller_frame.f_code.co_filename
                caller_lineno = caller_frame.f_lineno
                caller_function = caller_frame.f_code.co_name
                raise AttributeError(
                    f"Direct modification of CoA._layers is forbidden! "
                    f"Attempted from {caller_filename}:{caller_lineno} in {caller_function}(). "
                    f"Use CoA's public methods instead"
                )
        finally:
            del frame  # Avoid reference cycles
    
    @property
    def pattern(self) -> str:
        """Get base pattern filename"""
        return self._pattern
    
    @pattern.setter
    def pattern(self, value: str):
        """Set base pattern filename"""
        self._pattern = value
        self._logger.debug(f"Set pattern: {value}")
    
    @property
    def pattern_color1(self) -> List[int]:
        """Get pattern color 1 RGB"""
        return self._pattern_color1.copy()
    
    @pattern_color1.setter
    def pattern_color1(self, value: List[int]):
        """Set pattern color 1 RGB"""
        if not isinstance(value, list) or len(value) != 3:
            raise ValueError(f"Color must be [R, G, B] list, got {value}")
        self._pattern_color1 = value.copy()
        self._logger.debug(f"Set pattern_color1: {value}")
    
    @property
    def pattern_color2(self) -> List[int]:
        """Get pattern color 2 RGB"""
        return self._pattern_color2.copy()
    
    @pattern_color2.setter
    def pattern_color2(self, value: List[int]):
        """Set pattern color 2 RGB"""
        if not isinstance(value, list) or len(value) != 3:
            raise ValueError(f"Color must be [R, G, B] list, got {value}")
        self._pattern_color2 = value.copy()
        self._logger.debug(f"Set pattern_color2: {value}")
    
    @property
    def pattern_color1_name(self) -> str:
        """Get pattern color 1 name"""
        return self._pattern_color1_name
    
    @pattern_color1_name.setter
    def pattern_color1_name(self, value: str):
        """Set pattern color 1 name"""
        self._pattern_color1_name = value
        self._logger.debug(f"Set pattern_color1_name: {value}")
    
    @property
    def pattern_color2_name(self) -> str:
        """Get pattern color 2 name"""
        return self._pattern_color2_name
    
    @pattern_color2_name.setter
    def pattern_color2_name(self, value: str):
        """Set pattern color 2 name"""
        self._pattern_color2_name = value
        self._logger.debug(f"Set pattern_color2_name: {value}")
    
    @property
    def pattern_color3(self) -> List[int]:
        """Get pattern color 3 RGB"""
        return self._pattern_color3.copy()
    
    @pattern_color3.setter
    def pattern_color3(self, value: List[int]):
        """Set pattern color 3 RGB"""
        if not isinstance(value, list) or len(value) != 3:
            raise ValueError(f"Color must be [R, G, B] list, got {value}")
        self._pattern_color3 = value.copy()
        self._logger.debug(f"Set pattern_color3: {value}")
    
    @property
    def pattern_color3_name(self) -> str:
        """Get pattern color 3 name"""
        return self._pattern_color3_name
    
    @pattern_color3_name.setter
    def pattern_color3_name(self, value: str):
        """Set pattern color 3 name"""
        self._pattern_color3_name = value
        self._logger.debug(f"Set pattern_color3_name: {value}")
    
    @property
    def layers(self) -> Layers:
        """Get layers collection (read-only access)"""
        return self._layers
    
    # ========================================
    # Serialization (CK3 Format)
    # ========================================
    
    @classmethod
    def from_string(cls, ck3_text: str) -> 'CoA':
        """Parse CoA from CK3 format string
        
        Uses the mature CoAParser from utils.coa_parser for parsing.
        Converts parsed structure into model format with UUIDs.
        
        Args:
            ck3_text: CK3 coat of arms definition
            
        Returns:
            New CoA instance
            
        Example CK3 format:
            {
                pattern = "pattern_solid.dds"
                color1 = rgb { 255 255 255 }
                color2 = "red"
                colored_emblem = {
                    texture = "emblem_cross.dds"
                    color1 = "blue"
                    color2 = "yellow"
                    mask = { 1 0 0 }
                    instance = {
                        position = { 0.5 0.5 }
                        scale = { 0.8 0.8 }
                        rotation = 45
                        depth = 1.0
                    }
                }
            }
        """
        # Import parser (lazy to avoid circular dependencies)
        from ._coa_internal.coa_parser import CoAParser
        from utils.color_utils import color_name_to_rgb
        
        coa = cls()
        
        # Parse CK3 text
        parser = CoAParser()
        try:
            parsed = parser.parse_string(ck3_text)
        except Exception as e:
            coa._logger.error(f"Failed to parse CoA: {e}")
            raise ValueError(f"Invalid CK3 format: {e}")
        
        # Extract CoA object (first key)
        if not parsed:
            coa._logger.warning("Empty CoA parsed")
            return coa
        
        coa_key = list(parsed.keys())[0]
        coa_obj = parsed[coa_key]
        
        # Extract base pattern and colors
        coa._pattern = coa_obj.get('pattern', DEFAULT_PATTERN_TEXTURE)
        
        # Parse color1
        color1_raw = coa_obj.get('color1', DEFAULT_BASE_COLOR1)
        if isinstance(color1_raw, str):
            if color1_raw.startswith('rgb'):
                # Parse "rgb { R G B }"
                rgb_match = re.search(r'(\d+)\s+(\d+)\s+(\d+)', color1_raw)
                if rgb_match:
                    coa._pattern_color1 = [int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))]
                    coa._pattern_color1_name = None
            else:
                # Named color
                coa._pattern_color1 = color_name_to_rgb(color1_raw)
                coa._pattern_color1_name = color1_raw
        
        # Parse color2
        color2_raw = coa_obj.get('color2', DEFAULT_BASE_COLOR2)
        if isinstance(color2_raw, str):
            if color2_raw.startswith('rgb'):
                rgb_match = re.search(r'(\d+)\s+(\d+)\s+(\d+)', color2_raw)
                if rgb_match:
                    coa._pattern_color2 = [int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))]
                    coa._pattern_color2_name = None
            else:
                coa._pattern_color2 = color_name_to_rgb(color2_raw)
                coa._pattern_color2_name = color2_raw
        
        # Parse color3
        color3_raw = coa_obj.get('color3', DEFAULT_BASE_COLOR3)
        if isinstance(color3_raw, str):
            if color3_raw.startswith('rgb'):
                rgb_match = re.search(r'(\d+)\s+(\d+)\s+(\d+)', color3_raw)
                if rgb_match:
                    coa._pattern_color3 = [int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))]
                    coa._pattern_color3_name = None
            else:
                coa._pattern_color3 = color_name_to_rgb(color3_raw)
                coa._pattern_color3_name = color3_raw
        
        # Parse colored_emblem blocks
        emblems = coa_obj.get('colored_emblem', [])
        
        # Collect all layers with depth for sorting
        layers_with_depth = []
        
        for emblem in emblems:
            filename = emblem.get('texture', '')
            
            # Parse colors
            color1_raw = emblem.get('color1', DEFAULT_EMBLEM_COLOR1)
            color2_raw = emblem.get('color2', DEFAULT_EMBLEM_COLOR2)
            color3_raw = emblem.get('color3', DEFAULT_EMBLEM_COLOR3)
            
            # Helper to parse color
            def parse_color(color_raw, default_name):
                if isinstance(color_raw, str):
                    if color_raw.startswith('rgb'):
                        rgb_match = re.search(r'(\d+)\s+(\d+)\s+(\d+)', color_raw)
                        if rgb_match:
                            return ([int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))], None)
                    return (color_name_to_rgb(color_raw), color_raw)
                return (color_name_to_rgb(default_name), default_name)
            
            color1, color1_name = parse_color(color1_raw, DEFAULT_EMBLEM_COLOR1)
            color2, color2_name = parse_color(color2_raw, DEFAULT_EMBLEM_COLOR2)
            color3, color3_name = parse_color(color3_raw, DEFAULT_EMBLEM_COLOR3)
            
            # Parse mask
            mask_raw = emblem.get('mask')
            mask = None
            if mask_raw:
                if isinstance(mask_raw, list) and len(mask_raw) == 3:
                    mask = mask_raw
            
            # Parse instances
            instances = emblem.get('instance', [])
            if not instances:
                # No instance block = default single instance
                instances = [{'position': [0.5, 0.5], 'scale': [1.0, 1.0], 'rotation': 0, 'depth': 0}]
            
            # Create layer data
            layer_data = {
                'filename': filename,
                'colors': 3,  # Will be auto-detected from texture
                'color1': color1,
                'color2': color2,
                'color3': color3,
                'color1_name': color1_name,
                'color2_name': color2_name,
                'color3_name': color3_name,
                'mask': mask,
                'instances': [],
                'selected_instance': 0,
                'flip_x': False,  # Will be set per-instance
                'flip_y': False,
                'uuid': str(uuid_module.uuid4())
            }
            
            # Parse instances and group by depth
            # If instances have different depths, split into separate layers
            instances_by_depth = {}
            for inst in instances:
                pos = inst.get('position', [0.5, 0.5])
                scale = inst.get('scale', [1.0, 1.0])
                rotation = inst.get('rotation', 0)
                depth = inst.get('depth', 0.0)
                
                # Extract flip from negative scale
                scale_x = abs(scale[0])
                scale_y = abs(scale[1])
                flip_x = scale[0] < 0
                flip_y = scale[1] < 0
                
                instance_data = {
                    'pos_x': pos[0],
                    'pos_y': pos[1],
                    'scale_x': scale_x,
                    'scale_y': scale_y,
                    'rotation': float(rotation),
                    'flip_x': flip_x,
                    'flip_y': flip_y
                }
                
                # Group instances by depth
                if depth not in instances_by_depth:
                    instances_by_depth[depth] = []
                instances_by_depth[depth].append(instance_data)
            
            # Create separate layers for each depth level
            for depth, depth_instances in instances_by_depth.items():
                split_layer_data = {
                    'filename': filename,
                    'colors': 3,
                    'color1': color1,
                    'color2': color2,
                    'color3': color3,
                    'color1_name': color1_name,
                    'color2_name': color2_name,
                    'color3_name': color3_name,
                    'mask': mask,
                    'instances': depth_instances,
                    'selected_instance': 0,
                    'flip_x': depth_instances[0]['flip_x'],
                    'flip_y': depth_instances[0]['flip_y'],
                    'uuid': str(uuid_module.uuid4())
                }
                
                layers_with_depth.append((depth, split_layer_data))
        
        # Sort by depth (higher depth = further back = first in list)
        layers_with_depth.sort(key=lambda x: x[0], reverse=True)
        
        # Add layers to model (back to front)
        # Higher depth goes to index 0 (bottom visual, back render)
        # Lower depth goes to end (top visual, front render)
        for _, layer_data in layers_with_depth:
            # Create Layer and add to collection
            layer = Layer(layer_data, caller='CoA')
            coa.add_layer_object(layer, at_front=False)  # Append to end (maintains sorted order)
        
        coa._logger.debug(f"Parsed CoA with {coa.get_layer_count()} layers")
        return coa
    
    @classmethod
    def from_layers_string(cls, ck3_text: str) -> 'CoA':
        """Parse colored_emblem blocks into a new CoA with default pattern/colors
        
        This is for clipboard operations where only layer data is copied,
        not the full CoA structure.
        
        Args:
            ck3_text: CK3 colored_emblem blocks
            
        Returns:
            New CoA instance with default pattern and parsed layers
        """
        from ._coa_internal.coa_parser import CoAParser
        from utils.color_utils import color_name_to_rgb
        import uuid as uuid_module
        
        coa = cls()
        
        # Quick validation: check if text looks like CoA data
        if not ck3_text or 'colored_emblem' not in ck3_text:
            coa._logger.debug(f"Text does not contain colored_emblem blocks, skipping parse")
            return coa  # Return empty CoA
        
        # Wrap the layers in a minimal CoA structure for parsing
        wrapped_text = f"coa_export = {{\n\tpattern = \"{DEFAULT_PATTERN_TEXTURE}\"\n\tcolor1 = \"{DEFAULT_BASE_COLOR1}\"\n\tcolor2 = \"{DEFAULT_BASE_COLOR2}\"\n\tcolor3 = \"{DEFAULT_BASE_COLOR3}\"\n\t{ck3_text}\n}}"
        
        # Parse using the standard parser
        parser = CoAParser()
        try:
            parsed = parser.parse_string(wrapped_text)
        except Exception as e:
            coa._logger.debug(f"Failed to parse layers: {e}")
            return coa  # Return empty CoA
        
        # Extract colored_emblem blocks
        if not parsed:
            return coa
        
        coa_key = list(parsed.keys())[0]
        coa_obj = parsed[coa_key]
        emblems = coa_obj.get('colored_emblem', [])
        
        # Collect all layers with depth for sorting
        layers_with_depth = []
        
        for emblem in emblems:
            filename = emblem.get('texture', '')
            
            # Parse colors
            color1_raw = emblem.get('color1', DEFAULT_EMBLEM_COLOR1)
            color2_raw = emblem.get('color2', DEFAULT_EMBLEM_COLOR2)
            color3_raw = emblem.get('color3', DEFAULT_EMBLEM_COLOR3)
            
            # Helper to parse color
            def parse_color(color_raw, default_name):
                if isinstance(color_raw, str):
                    if color_raw.startswith('rgb'):
                        rgb_match = re.search(r'(\d+)\s+(\d+)\s+(\d+)', color_raw)
                        if rgb_match:
                            return ([int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))], None)
                    return (color_name_to_rgb(color_raw), color_raw)
                return (color_name_to_rgb(default_name), default_name)
            
            color1, color1_name = parse_color(color1_raw, DEFAULT_EMBLEM_COLOR1)
            color2, color2_name = parse_color(color2_raw, DEFAULT_EMBLEM_COLOR2)
            color3, color3_name = parse_color(color3_raw, DEFAULT_EMBLEM_COLOR3)
            
            # Parse mask
            mask_raw = emblem.get('mask')
            mask = None
            if mask_raw:
                if isinstance(mask_raw, list) and len(mask_raw) == 3:
                    mask = mask_raw
            
            # Parse instances
            instances = emblem.get('instance', [])
            if not instances:
                instances = [{'position': [0.5, 0.5], 'scale': [1.0, 1.0], 'rotation': 0, 'depth': 0}]
            
            # Create layer data
            layer_data = {
                'filename': filename,
                'colors': 3,
                'color1': color1,
                'color2': color2,
                'color3': color3,
                'color1_name': color1_name,
                'color2_name': color2_name,
                'color3_name': color3_name,
                'mask': mask,
                'instances': [],
                'selected_instance': 0,
                'flip_x': False,
                'flip_y': False,
                'uuid': str(uuid_module.uuid4())
            }
            
            # Parse instances
            for inst in instances:
                position = inst.get('position', [0.5, 0.5])
                scale = inst.get('scale', [1.0, 1.0])
                rotation = inst.get('rotation', 0)
                depth = inst.get('depth', 0)
                
                pos_x = float(position[0]) if len(position) > 0 else 0.5
                pos_y = float(position[1]) if len(position) > 1 else 0.5
                scale_x = float(scale[0]) if len(scale) > 0 else 1.0
                scale_y = float(scale[1]) if len(scale) > 1 else 1.0
                
                instance_data = {
                    'pos_x': pos_x,
                    'pos_y': pos_y,
                    'scale_x': scale_x,
                    'scale_y': scale_y,
                    'rotation': float(rotation),
                    'depth': float(depth)
                }
                layer_data['instances'].append(instance_data)
            
            # Store layer with depth for sorting
            max_depth = max(inst['depth'] for inst in layer_data['instances'])
            layers_with_depth.append((max_depth, layer_data))
        
        # Sort by depth (higher depth = further back = first in list)
        layers_with_depth.sort(key=lambda x: x[0], reverse=True)
        
        # Add layers to model (back to front)
        for _, layer_data in layers_with_depth:
            # Remove depth from instances
            for inst in layer_data['instances']:
                del inst['depth']
            
            # Create Layer and add to collection
            layer = Layer(layer_data, caller='CoA')
            coa.insert_layer_at_index(0, layer)
        
        coa._logger.debug(f"Parsed {coa.get_layer_count()} layers from colored_emblem blocks")
        return coa
    
    def to_string(self) -> str:
        """Export CoA to CK3 format string
        
        Uses mature serialization matching the running application's format.
        Includes mask field support and proper depth ordering.
        
        Returns:
            CK3 coat of arms definition
        """
        from utils.color_utils import rgb_to_color_name
        
        # Helper to normalize RGB [0-255] to [0-1] range expected by rgb_to_color_name
        def normalize_rgb(rgb):
            """Convert [0-255] range to [0-1] range"""
            if not rgb:
                return [1.0, 1.0, 1.0]
            return [rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0]
        
        # Helper to format color (add quotes if it's a named color)
        def format_color(rgb, color_name):
            normalized = normalize_rgb(rgb)
            color_str = rgb_to_color_name(normalized, color_name)
            if color_str.startswith('rgb'):
                return color_str  # Already formatted as "rgb { R G B }"
            else:
                return f'"{color_str}"'  # Named color, add quotes
        
        lines = []
        lines.append("coa_export = {")
        
        # Pattern and colors
        lines.append(f'\tpattern = "{self._pattern}"')
        
        # Pattern color 1
        lines.append(f'\tcolor1 = {format_color(self._pattern_color1, self._pattern_color1_name)}')
        
        # Pattern color 2
        lines.append(f'\tcolor2 = {format_color(self._pattern_color2, self._pattern_color2_name)}')
        
        # Pattern color 3
        lines.append(f'\tcolor3 = {format_color(self._pattern_color3, self._pattern_color3_name)}')
        
        # Colored emblems (layers)
        for depth_index, layer in enumerate(self._layers):
            lines.append("\tcolored_emblem = {")
            lines.append(f'\t\ttexture = "{layer.filename}"')
            
            # Layer colors
            lines.append(f'\t\tcolor1 = {format_color(layer.color1, layer.color1_name)}')
            if layer.colors >= 2:
                lines.append(f'\t\tcolor2 = {format_color(layer.color2, layer.color2_name)}')
            if layer.colors >= 3:
                lines.append(f'\t\tcolor3 = {format_color(layer.color3, layer.color3_name)}')
            
            # Mask (only if set)
            if layer.mask is not None:
                mask_values = ' '.join(str(v) for v in layer.mask)
                lines.append(f'\t\tmask = {{ {mask_values} }}')
            
            # Instances
            for instance in range(layer.instance_count):
                inst = layer.get_instance(instance, caller='CoA')
                lines.append("\t\tinstance = {")
                
                # Position
                lines.append(f"\t\t\tposition = {{ {inst['pos_x']:.4f} {inst['pos_y']:.4f} }}")
                
                # Scale (combine with flip)
                scale_x = inst['scale_x']
                scale_y = inst['scale_y']
                if layer.flip_x:
                    scale_x = -scale_x
                if layer.flip_y:
                    scale_y = -scale_y
                lines.append(f"\t\t\tscale = {{ {scale_x:.4f} {scale_y:.4f} }}")
                
                # Rotation (only if non-zero)
                if inst['rotation'] != 0.0:
                    lines.append(f"\t\t\trotation = {inst['rotation']:.2f}")
                
                # Depth (higher = further back)
                # Calculate depth from position in list
                if depth_index < len(self._layers) - 1:
                    depth_from_back = len(self._layers) - 1 - depth_index
                    lines.append(f"\t\t\tdepth = {float(depth_from_back) + 0.01:.2f}")
                
                lines.append("\t\t}")
            
            lines.append("\t}")
        
        lines.append("}")
        return '\n'.join(lines)
    
    def serialize_layers_to_string(self, uuids: list) -> str:
        """Export specific layers to CK3 format string
        
        Serializes only the layers with the given UUIDs. Useful for clipboard operations.
        
        Args:
            uuids: List of layer UUIDs to serialize
            
        Returns:
            CK3 format string containing only the specified layers
        """
        from utils.color_utils import rgb_to_color_name
        
        # Helper to normalize RGB [0-255] to [0-1] range expected by rgb_to_color_name
        def normalize_rgb(rgb):
            """Convert [0-255] range to [0-1] range"""
            if not rgb:
                return [1.0, 1.0, 1.0]
            return [rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0]
        
        # Helper to format color (add quotes if it's a named color)
        def format_color(rgb, color_name):
            normalized = normalize_rgb(rgb)
            color_str = rgb_to_color_name(normalized, color_name)
            if color_str.startswith('rgb'):
                return color_str  # Already formatted as "rgb { R G B }"
            else:
                return f'"{color_str}"'  # Named color, add quotes
        
        lines = []
        lines.append("layers_export = {")
        
        # Filter and serialize only specified layers
        for layer_uuid in uuids:
            layer = self.get_layer_by_uuid(layer_uuid)
            if not layer:
                continue
                
            lines.append("\tcolored_emblem = {")
            lines.append(f'\t\ttexture = "{layer.filename}"')
            
            # Layer colors
            lines.append(f'\t\tcolor1 = {format_color(layer.color1, layer.color1_name)}')
            if layer.colors >= 2:
                lines.append(f'\t\tcolor2 = {format_color(layer.color2, layer.color2_name)}')
            if layer.colors >= 3:
                lines.append(f'\t\tcolor3 = {format_color(layer.color3, layer.color3_name)}')
            
            # Mask (only if set)
            if layer.mask is not None:
                mask_values = ' '.join(str(v) for v in layer.mask)
                lines.append(f'\t\tmask = {{ {mask_values} }}')
            
            # Instances
            for instance in range(layer.instance_count):
                inst = layer.get_instance(instance, caller='CoA')
                lines.append("\t\tinstance = {")
                
                # Position
                lines.append(f"\t\t\tposition = {{ {inst['pos_x']:.4f} {inst['pos_y']:.4f} }}")
                
                # Scale (combine with flip)
                scale_x = inst['scale_x']
                scale_y = inst['scale_y']
                if layer.flip_x:
                    scale_x = -scale_x
                if layer.flip_y:
                    scale_y = -scale_y
                lines.append(f"\t\t\tscale = {{ {scale_x:.4f} {scale_y:.4f} }}")
                
                # Rotation (only if non-zero)
                if inst['rotation'] != 0.0:
                    lines.append(f"\t\t\trotation = {inst['rotation']:.2f}")
                
                # Depth (preserve original depth value if present)
                if 'depth' in inst:
                    lines.append(f"\t\t\tdepth = {inst['depth']:.2f}")
                
                lines.append("\t\t}")
            
            lines.append("\t}")
        
        lines.append("}")
        return '\n'.join(lines)
    
    # ========================================
    # Layer Management
    # ========================================
    
    def add_layer(self, emblem_path: str = "", pos_x: float = DEFAULT_POSITION_X,
                  pos_y: float = DEFAULT_POSITION_Y, colors: int = 3, target_uuid: Optional[str] = None) -> str:
        """Add new layer
        
        Args:
            emblem_path: Path to emblem texture
            pos_x: Initial X position (0.0-1.0)
            pos_y: Initial Y position (0.0-1.0)
            colors: Number of colors (1, 2, or 3)
            target_uuid: If provided, insert layer below this target (in front of it, higher index)
            
        Returns:
            UUID of the new layer
        """
        data = {
            'uuid': str(uuid_module.uuid4()),
            'filename': emblem_path,
            'path': emblem_path,
            'colors': colors,
            'instances': [{
                'pos_x': pos_x,
                'pos_y': pos_y,
                'scale_x': DEFAULT_SCALE_X,
                'scale_y': DEFAULT_SCALE_Y,
                'rotation': DEFAULT_ROTATION,
                'depth': 0.0
            }],
            'selected_instance': 0,
            'flip_x': False,
            'flip_y': False,
            'color1': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR1]['rgb'].copy(),
            'color2': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR2]['rgb'].copy(),
            'color3': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR3]['rgb'].copy(),
            'color1_name': DEFAULT_EMBLEM_COLOR1,
            'color2_name': DEFAULT_EMBLEM_COLOR2,
            'color3_name': DEFAULT_EMBLEM_COLOR3,
            'mask': None
        }
        
        layer = Layer(data, caller='CoA')
        
        if target_uuid:
            # Insert below target (higher index = in front)
            target_index = self._layers.get_index_by_uuid(target_uuid)
            self._layers.insert(target_index + 1, layer, caller='CoA')
        else:
            self._layers.append(layer, caller='CoA')
        
        # Track for auto-selection
        self._last_added_uuid = layer.uuid
        self._last_added_uuids = [layer.uuid]
        
        self._logger.debug(f"Added layer: {layer.uuid}")
        return layer.uuid
    
    def remove_layer(self, uuid: str):
        """Remove layer by UUID
        
        Args:
            uuid: Layer UUID
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        self._layers.remove(layer, caller='CoA')
        self._logger.debug(f"Removed layer: {uuid}")
    
    def duplicate_layer(self, uuid: str) -> str:
        """Duplicate layer (creates new UUID)
        
        Args:
            uuid: Layer UUID to duplicate
            
        Returns:
            UUID of the new layer
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        # Deep copy layer data
        data = deepcopy(layer.to_dict(caller='CoA'))
        
        # Generate new UUID
        data['uuid'] = str(uuid_module.uuid4())
        
        # Create new layer
        new_layer = Layer(data, caller='CoA')
        
        # Insert after original
        index = self._layers.get_index_by_uuid(uuid)
        self._layers.insert(index + 1, new_layer, caller='CoA')
        
        self._logger.debug(f"Duplicated layer {uuid} -> {new_layer.uuid}")
        return new_layer.uuid
    
    def duplicate_layer_below(self, uuid: str, target_uuid: str) -> str:
        """Duplicate layer and place behind target in render order (lower index = renders behind)
        
        Args:
            uuid: Layer UUID to duplicate
            target_uuid: UUID of layer to place duplicate behind (in render order)
            
        Returns:
            UUID of the new layer
            
        Raises:
            ValueError: If either UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        # Get target layer position
        target_index = self._layers.get_index_by_uuid(target_uuid)
        
        # Deep copy layer data
        data = deepcopy(layer.to_dict(caller='CoA'))
        
        # Generate new UUID
        data['uuid'] = str(uuid_module.uuid4())
        
        # Create new layer
        new_layer = Layer(data, caller='CoA')
        
        # Insert at target index (pushes target forward, duplicate stays behind)
        self._layers.insert(target_index, new_layer, caller='CoA')
        
        self._logger.debug(f"Duplicated layer {uuid} -> {new_layer.uuid} behind {target_uuid}")
        return new_layer.uuid
    
    def duplicate_layer_above(self, uuid: str, target_uuid: str) -> str:
        """Duplicate layer and place above target in visual layer list (front of render order, higher index)
        
        Args:
            uuid: Layer UUID to duplicate
            target_uuid: UUID of layer to place duplicate above in the visual list (renders in front)
            
        Returns:
            UUID of the new layer
            
        Raises:
            ValueError: If either UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        # Get target layer position
        target_index = self._layers.get_index_by_uuid(target_uuid)
        
        # Deep copy layer data
        data = deepcopy(layer.to_dict(caller='CoA'))
        
        # Generate new UUID
        data['uuid'] = str(uuid_module.uuid4())
        
        # Create new layer
        new_layer = Layer(data, caller='CoA')
        
        # Insert above in visual list (lower index = renders behind)
        self._layers.insert(target_index, new_layer, caller='CoA')
        
        self._logger.debug(f"Duplicated layer {uuid} -> {new_layer.uuid} above (visual) {target_uuid}")
        return new_layer.uuid
    
    def merge_layers_into_first(self, uuids: List[str]) -> str:
        """Merge multiple layers into the first one by adding instances
        
        The first layer keeps its UUID and position. Instances from other layers
        are added to it, then the other layers are removed.
        
        Args:
            uuids: List of layer UUIDs to merge (first one is kept)
            
        Returns:
            UUID of the merged layer (same as first UUID in list)
            
        Raises:
            ValueError: If list empty, has only one UUID, or contains invalid UUIDs
        """
        if not uuids:
            raise ValueError("UUID list cannot be empty")
        if len(uuids) < 2:
            raise ValueError("Need at least 2 layers to merge")
        
        # Get all layer objects
        layers = []
        for uuid in uuids:
            layer = self._layers.get_by_uuid(uuid)
            if not layer:
                raise ValueError(f"Layer with UUID '{uuid}' not found")
            layers.append(layer)
        
        # First layer receives all instances
        first_uuid = uuids[0]
        first_layer = layers[0]
        
        # Add instances from other layers to the first layer
        for other_layer in layers[1:]:
            for instance_idx in range(other_layer.instance_count):
                instance = other_layer.get_instance(instance_idx, caller='CoA.merge')
                # Add instance with all its properties
                new_idx = self.add_instance(
                    first_uuid,
                    pos_x=instance['pos_x'],
                    pos_y=instance['pos_y']
                )
                # Copy remaining instance properties (if they exist)
                new_instance = first_layer.get_instance(new_idx, caller='CoA.merge')
                new_instance['scale_x'] = instance.get('scale_x', 1.0)
                new_instance['scale_y'] = instance.get('scale_y', 1.0)
                new_instance['rotation'] = instance.get('rotation', 0.0)
                if 'depth' in instance:
                    new_instance['depth'] = instance['depth']
        
        # Remove the other layers (not the first one)
        for uuid in uuids[1:]:
            self.remove_layer(uuid)
        
        self._logger.debug(f"Merged {len(uuids)} layers into {first_uuid} ({first_layer.instance_count} instances)")
        return first_uuid
    
    def copy_layers_from_coa(self, source_coa: 'CoA', at_front: bool = True, apply_offset: bool = False, target_uuid: Optional[str] = None) -> List[str]:
        """Copy all layers from another CoA into this one
        
        Args:
            source_coa: Source CoA to copy layers from
            at_front: If True, insert at front (highest index/top of render), else insert at back (index 0/bottom)
                     Ignored if target_uuid is provided.
            apply_offset: If True, apply paste offset to positions
            target_uuid: If provided, insert layers below this target (in front of it, higher index)
            
        Returns:
            List of new UUIDs for copied layers
        """
        new_uuids = []
        layer_count = source_coa.get_layer_count()
        
        # If target_uuid provided, get its position for insertion
        target_index = None
        if target_uuid:
            target_index = self._layers.get_index_by_uuid(target_uuid)
        
        for i in range(layer_count):
            source_uuid = source_coa.get_layer_uuid_by_index(i)
            source_layer = source_coa._layers.get_by_uuid(source_uuid)
            
            if not source_layer:
                continue
            
            # Deep copy layer data
            data = deepcopy(source_layer.to_dict(caller='CoA'))
            
            # Generate new UUID
            data['uuid'] = str(uuid_module.uuid4())
            
            # Apply offset if requested
            if apply_offset:
                for inst in data.get('instances', []):
                    inst['pos_x'] = inst.get('pos_x', 0.5) + PASTE_OFFSET_X
                    inst['pos_y'] = inst.get('pos_y', 0.5) + PASTE_OFFSET_Y
            
            # Create new layer
            new_layer = Layer(data, caller='CoA')
            
            # Insert at appropriate position
            if target_uuid and target_index is not None:
                # Insert below target (higher index = in front)
                self._layers.insert(target_index + 1 + i, new_layer, caller='CoA')
            elif at_front:
                self._layers.append(new_layer, caller='CoA')
            else:
                self._layers.insert(i, new_layer, caller='CoA')
            
            new_uuids.append(new_layer.uuid)
        
        self._logger.debug(f"Copied {len(new_uuids)} layers from source CoA")
        return new_uuids
    
    def move_layer_below(self, uuids: Union[str, List[str]], target_uuid: str):
        """Move layer(s) below target in visual layer list (back of render order, lower index)
        
        When moving multiple layers, they are moved as a contiguous group
        maintaining the order specified in the list.
        
        Args:
            uuids: Layer UUID to move, or list of UUIDs (list order = final stacking order)
            target_uuid: UUID of layer to move below in the visual list (renders behind)
            
        Raises:
            ValueError: If any UUID not found
        """
        # Normalize to list
        if isinstance(uuids, str):
            uuids = [uuids]
        
        if not uuids:
            return
        
        # Filter out target UUID if present
        uuids = [uuid for uuid in uuids if uuid != target_uuid]
        if not uuids:
            return  # Nothing to move
        
        # Get target position
        target_index = self._layers.get_index_by_uuid(target_uuid)
        
        # Remove all layers (collect them in order)
        layers_to_move = []
        for uuid in uuids:
            from_index = self._layers.get_index_by_uuid(uuid)
            layer = self._layers.pop(from_index, caller='CoA')
            layers_to_move.append(layer)
            
            # Adjust target index if we removed something before it
            if from_index < target_index:
                target_index -= 1
        
        # Insert below in visual list (higher index = renders in front)
        # Insert in order: first UUID in list goes at target+1, second at target+2, etc.
        for i, layer in enumerate(layers_to_move):
            self._layers.insert(target_index + 1 + i, layer, caller='CoA')
        
        self._logger.debug(f"Moved {len(layers_to_move)} layer(s) below (visual) {target_uuid}")
    
    def move_layer_above(self, uuids: Union[str, List[str]], target_uuid: str):
        """Move layer(s) above target in visual layer list (front of render order, higher index)
        
        When moving multiple layers, they are moved as a contiguous group
        maintaining the order specified in the list.
        
        Args:
            uuids: Layer UUID to move, or list of UUIDs (list order = final stacking order)
            target_uuid: UUID of layer to move above in the visual list (renders in front)
            
        Raises:
            ValueError: If any UUID not found
        """
        # Normalize to list
        if isinstance(uuids, str):
            uuids = [uuids]
        
        if not uuids:
            return
        
        # Filter out target UUID if present
        uuids = [uuid for uuid in uuids if uuid != target_uuid]
        if not uuids:
            return  # Nothing to move
        
        # Get target position
        target_index = self._layers.get_index_by_uuid(target_uuid)
        
        # Remove all layers (collect them in order)
        layers_to_move = []
        for uuid in uuids:
            from_index = self._layers.get_index_by_uuid(uuid)
            layer = self._layers.pop(from_index, caller='CoA')
            layers_to_move.append(layer)
            
            # Adjust target index if we removed something before it
            if from_index < target_index:
                target_index -= 1
        
        # Insert above in visual list (lower index = renders behind)
        # Insert in order: first UUID in list goes at target, second at target+1, etc.
        for i, layer in enumerate(layers_to_move):
            self._layers.insert(target_index + i, layer, caller='CoA')
        
        self._logger.debug(f"Moved {len(layers_to_move)} layer(s) above (visual) {target_uuid}")
    
    def move_layer_to_bottom(self, uuids: Union[str, List[str]]):
        """Move layer(s) to bottom of visual layer list (back of render order, lowest index)
        
        When moving multiple layers, they are moved as a contiguous group
        maintaining the order specified in the list.
        
        Args:
            uuids: Layer UUID to move, or list of UUIDs (list order = final stacking order)
            
        Raises:
            ValueError: If any UUID not found
        """
        # Normalize to list
        if isinstance(uuids, str):
            uuids = [uuids]
        
        if not uuids:
            return
        
        # Remove all layers (collect them in order)
        layers_to_move = []
        for uuid in uuids:
            from_index = self._layers.get_index_by_uuid(uuid)
            layer = self._layers.pop(from_index, caller='CoA')
            layers_to_move.append(layer)
        
        # Insert all layers at start (lowest index = bottom visual = back render)
        for i, layer in enumerate(layers_to_move):
            self._layers.insert(i, layer, caller='CoA')
        
        self._logger.debug(f"Moved {len(layers_to_move)} layer(s) to bottom (visual)")
    
    def move_layer_to_top(self, uuids: Union[str, List[str]]):
        """Move layer(s) to top of visual layer list (front of render order, highest index)
        
        When moving multiple layers, they are moved as a contiguous group
        maintaining the order specified in the list.
        
        Args:
            uuids: Layer UUID to move, or list of UUIDs (list order = final stacking order)
            
        Raises:
            ValueError: If any UUID not found
        """
        # Normalize to list
        if isinstance(uuids, str):
            uuids = [uuids]
        
        if not uuids:
            return
        
        # Remove all layers (collect them in order)
        layers_to_move = []
        for uuid in uuids:
            from_index = self._layers.get_index_by_uuid(uuid)
            layer = self._layers.pop(from_index, caller='CoA')
            layers_to_move.append(layer)
        
        # Append all layers to end (highest index = top visual = front render)
        for layer in layers_to_move:
            self._layers.append(layer, caller='CoA')
        
        self._logger.debug(f"Moved {len(layers_to_move)} layer(s) to top (visual)")
    
    def shift_layer_up(self, uuids: Union[str, List[str]]) -> bool:
        """Shift layer(s) up one position (toward index 0, visually toward top, renders more in back)
        
        Args:
            uuids: Layer UUID or list of UUIDs to shift up as a group
            
        Returns:
            True if shift was performed, False if already at top or blocked
            
        Raises:
            ValueError: If any UUID not found
        """
        # Normalize to list
        if isinstance(uuids, str):
            uuids = [uuids]
        
        if not uuids:
            return False
        
        # Get all indices, check if any at top (index 0)
        indices = []
        for uuid in uuids:
            idx = self._layers.get_index_by_uuid(uuid)
            if idx is None:
                raise ValueError(f"Layer with UUID '{uuid}' not found")
            indices.append(idx)
        
        # Can't shift up if any layer is at index 0
        if min(indices) == 0:
            return False
        
        # Get target UUID (layer immediately above the topmost selected layer)
        target_index = min(indices) - 1
        target_uuid = self.get_layer_uuid_by_index(target_index)
        
        # Move selected layers above target
        self.move_layer_above(uuids, target_uuid)
        return True
    
    def shift_layer_down(self, uuids: Union[str, List[str]]) -> bool:
        """Shift layer(s) down one position (toward higher index, visually toward bottom, renders more in front)
        
        Args:
            uuids: Layer UUID or list of UUIDs to shift down as a group
            
        Returns:
            True if shift was performed, False if already at bottom or blocked
            
        Raises:
            ValueError: If any UUID not found
        """
        # Normalize to list
        if isinstance(uuids, str):
            uuids = [uuids]
        
        if not uuids:
            return False
        
        # Get all indices, check if any at bottom (last index)
        indices = []
        for uuid in uuids:
            idx = self._layers.get_index_by_uuid(uuid)
            if idx is None:
                raise ValueError(f"Layer with UUID '{uuid}' not found")
            indices.append(idx)
        
        # Can't shift down if any layer is at last index
        if max(indices) >= len(self._layers) - 1:
            return False
        
        # Get target UUID (layer immediately below the bottommost selected layer)
        target_index = max(indices) + 1
        target_uuid = self.get_layer_uuid_by_index(target_index)
        
        # Move selected layers below target
        self.move_layer_below(uuids, target_uuid)
        return True
    
    def review_merge(self, uuids: List[str]) -> Dict[str, Any]:
        """Review merge operation before performing it (validation and warnings)
        
        Args:
            uuids: List of layer UUIDs to merge
            
        Returns:
            Dict with:
                'valid': bool - Whether merge can proceed
                'warnings': List[str] - Warning messages
                'info': Dict - Information about the merge
                    'total_instances': int
                    'textures': List[str] - Unique textures
                    'colors_match': bool
        """
        result = {
            'valid': True,
            'warnings': [],
            'info': {}
        }
        
        if len(uuids) < 2:
            result['valid'] = False
            result['warnings'].append("Need at least 2 layers to merge")
            return result
        
        # Get all layers
        layers = []
        for uuid in uuids:
            layer = self._layers.get_by_uuid(uuid)
            if not layer:
                result['valid'] = False
                result['warnings'].append(f"Layer UUID not found: {uuid}")
                return result
            layers.append(layer)
        
        # Check textures
        textures = set(layer.filename for layer in layers)
        result['info']['textures'] = list(textures)
        result['info']['total_instances'] = sum(layer.instance_count for layer in layers)
        
        if len(textures) > 1:
            result['valid'] = False
            result['warnings'].append(
                f"Cannot merge layers with different textures: {textures}. "
                "All layers must have the same emblem texture to merge."
            )
        
        # Check colors (warning only, not blocking)
        first_colors = (layers[0].color1, layers[0].color2, layers[0].color3)
        colors_match = all(
            (layer.color1, layer.color2, layer.color3) == first_colors
            for layer in layers[1:]
        )
        result['info']['colors_match'] = colors_match
        
        if not colors_match:
            result['warnings'].append(
                "Layers have different colors. After merge, all instances will use the first layer's colors."
            )
        
        return result
    
    def merge_layers(self, uuids: List[str]) -> str:
        """Merge multiple layers into one (keeps first UUID, combines instances)
        
        Note: All layers must have the same texture. Use review_merge() first to validate.
        
        Args:
            uuids: List of layer UUIDs to merge
            
        Returns:
            UUID of the merged layer (same as first UUID in list)
            
        Raises:
            ValueError: If any UUID not found, less than 2 UUIDs, or textures don't match
        """
        if len(uuids) < 2:
            raise ValueError("Need at least 2 layers to merge")
        
        # Validate merge
        review = self.review_merge(uuids)
        if not review['valid']:
            raise ValueError(f"Cannot merge: {'; '.join(review['warnings'])}")
        
        # Get all layers
        layers = [self._layers.get_by_uuid(uuid) for uuid in uuids]
        
        # Keep first layer, collect all instances
        first_layer = layers[0]
        first_uuid = uuids[0]
        
        # Add instances from other layers to first layer
        for layer in layers[1:]:
            for i in range(layer.instance_count):
                instance = layer.get_instance(i, caller='CoA')
                # Add to first layer
                idx = first_layer.add_instance(
                    pos_x=instance['pos_x'],
                    pos_y=instance['pos_y'],
                    caller='CoA'
                )
                # Copy other properties
                new_inst = first_layer.get_instance(idx, caller='CoA')
                new_inst['scale_x'] = instance['scale_x']
                new_inst['scale_y'] = instance['scale_y']
                new_inst['rotation'] = instance['rotation']
                new_inst['depth'] = instance['depth']
        
        # Remove other layers
        for uuid in uuids[1:]:
            self.remove_layer(uuid)
        
        self._logger.debug(f"Merged {len(uuids)} layers into {first_uuid}")
        return first_uuid
    
    def split_layer(self, uuid: str) -> List[str]:
        """Split layer instances into separate layers (one instance each)
        
        Args:
            uuid: Layer UUID to split
            
        Returns:
            List of UUIDs for the new layers (one per instance)
            
        Raises:
            ValueError: If UUID not found or layer has only 1 instance
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        if layer.instance_count <= 1:
            raise ValueError("Cannot split layer with only 1 instance")
        
        # Get original position
        original_index = self._layers.get_index_by_uuid(uuid)
        
        # Create new layer for each instance
        new_uuids = []
        for i in range(layer.instance_count):
            instance = layer.get_instance(i, caller='CoA')
            
            # Create new layer with this instance
            data = deepcopy(layer.to_dict(caller='CoA'))
            data['uuid'] = str(uuid_module.uuid4())
            data['instances'] = [instance.copy()]
            data['selected_instance'] = 0
            
            new_layer = Layer(data, caller='CoA')
            
            # Insert after previous
            insert_pos = original_index + i + 1
            self._layers.insert(insert_pos, new_layer, caller='CoA')
            
            new_uuids.append(new_layer.uuid)
        
        # Remove original layer
        self.remove_layer(uuid)
        
        self._logger.debug(f"Split layer {uuid} into {len(new_uuids)} layers")
        return new_uuids
    
    # ========================================
    # Instance Management (per layer)
    # ========================================
    
    def add_instance(self, uuid: str, pos_x: float = None, pos_y: float = None) -> int:
        """Add instance to layer
        
        Args:
            uuid: Layer UUID
            pos_x: X position (defaults to layer's current position)
            pos_y: Y position (defaults to layer's current position)
            
        Returns:
            Index of new instance
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        idx = layer.add_instance(pos_x=pos_x, pos_y=pos_y, caller='CoA')
        self._logger.debug(f"Added instance to layer {uuid}: index {idx}")
        return idx
    
    def remove_instance(self, uuid: str, instance_index: int):
        """Remove instance from layer
        
        Args:
            uuid: Layer UUID
            instance_index: Instance index to remove
            
        Raises:
            ValueError: If UUID not found or trying to remove last instance
            IndexError: If instance_index out of range
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        layer.remove_instance(instance_index, caller='CoA')
        self._logger.debug(f"Removed instance {instance_index} from layer {uuid}")
    
    def select_instance(self, uuid: str, instance_index: int):
        """Select instance on layer (affects property getters/setters)
        
        Args:
            uuid: Layer UUID
            instance_index: Instance index to select
            
        Raises:
            ValueError: If UUID not found or instance_index out of range
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        layer.selected_instance = instance_index
        self._logger.debug(f"Selected instance {instance_index} on layer {uuid}")
    
    # ========================================
    # Transform Operations (Single Layer)
    # ========================================
    
    def set_layer_position(self, uuid: str, x: float, y: float):
        """Set layer position (shallow - moves all instances as rigid unit)
        
        For single-instance layers, sets the instance position directly.
        For multi-instance layers, calculates AABB center and moves all instances
        maintaining their relative offsets from the center.
        
        Args:
            uuid: Layer UUID
            x: X position (0.0-1.0)
            y: Y position (0.0-1.0)
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        instances = layer._data.get('instances', [])
        
        if len(instances) == 1:
            # Single instance: set position directly (avoid accumulation errors)
            layer.pos_x = x
            layer.pos_y = y
            instances[0]['pos_x'] = x
            instances[0]['pos_y'] = y
        elif len(instances) > 1:
            # Multiple instances: calculate AABB center, maintain relative offsets
            # Get bounding box of all instances
            min_x = min(inst.get('pos_x', 0.5) for inst in instances)
            max_x = max(inst.get('pos_x', 0.5) for inst in instances)
            min_y = min(inst.get('pos_y', 0.5) for inst in instances)
            max_y = max(inst.get('pos_y', 0.5) for inst in instances)
            
            # Calculate AABB center
            aabb_center_x = (min_x + max_x) / 2.0
            aabb_center_y = (min_y + max_y) / 2.0
            
            # Calculate offset from AABB center to new position
            dx = x - aabb_center_x
            dy = y - aabb_center_y
            
            # Update layer position
            layer.pos_x = x
            layer.pos_y = y
            
            # Apply offset to all instances
            for inst in instances:
                inst['pos_x'] = max(0.0, min(1.0, inst['pos_x'] + dx))
                inst['pos_y'] = max(0.0, min(1.0, inst['pos_y'] + dy))
        else:
            # No instances: just set layer position
            layer.pos_x = x
            layer.pos_y = y
        
        self._logger.debug(f"Set position for layer {uuid} (shallow): ({x:.4f}, {y:.4f})")
    
    def translate_layer(self, uuid: str, dx: float, dy: float):
        """Translate layer by offset (shallow - moves all instances as rigid unit)
        
        Args:
            uuid: Layer UUID
            dx: X offset
            dy: Y offset
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        # Translate all instances by same offset (shallow transformation)
        instances = layer._data.get('instances', [])
        if instances:
            for inst in instances:
                inst['pos_x'] = max(0.0, min(1.0, inst['pos_x'] + dx))
                inst['pos_y'] = max(0.0, min(1.0, inst['pos_y'] + dy))
            
            # Update layer.pos_x/y to match first instance (for backward compatibility)
            # Use direct assignment to _data to avoid triggering property setter
            if instances:
                layer._data['pos_x'] = instances[0]['pos_x']
                layer._data['pos_y'] = instances[0]['pos_y']
        
        self._logger.debug(f"Translated layer {uuid} (shallow): ({dx:.4f}, {dy:.4f})")
    
    def adjust_layer_positions(self, uuids: List[str], dx: float, dy: float):
        """Adjust positions of multiple layers by offset
        
        Args:
            uuids: List of layer UUIDs to adjust
            dx: X offset to apply
            dy: Y offset to apply
            
        Raises:
            ValueError: If any UUID not found
        """
        for uuid in uuids:
            layer = self._layers.get_by_uuid(uuid)
            if not layer:
                raise ValueError(f"Layer with UUID '{uuid}' not found")
            
            layer.pos_x += dx
            layer.pos_y += dy
        
        self._logger.debug(f"Adjusted {len(uuids)} layer positions by ({dx:.4f}, {dy:.4f})")
    
    def get_layer_centroid(self, uuids: List[str]) -> tuple:
        """Calculate centroid (average position) of multiple layers
        
        Args:
            uuids: List of layer UUIDs
            
        Returns:
            Tuple of (x, y) representing centroid position
            
        Raises:
            ValueError: If list is empty or any UUID not found
        """
        if not uuids:
            raise ValueError("Need at least one layer UUID")
        
        total_x = 0.0
        total_y = 0.0
        
        for uuid in uuids:
            layer = self._layers.get_by_uuid(uuid)
            if not layer:
                raise ValueError(f"Layer with UUID '{uuid}' not found")
            
            total_x += layer.pos_x
            total_y += layer.pos_y
        
        centroid_x = total_x / len(uuids)
        centroid_y = total_y / len(uuids)
        
        return (centroid_x, centroid_y)
    
    def set_layer_scale(self, uuid: str, scale_x: float, scale_y: float):
        """Set layer scale (shallow - scales all instances as rigid unit)
        
        Args:
            uuid: Layer UUID
            scale_x: X scale factor
            scale_y: Y scale factor
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        # Apply scale to all instances (shallow transformation)
        instances = layer._data.get('instances', [])
        if len(instances) == 1:
            # Single instance: set directly to avoid flicker
            layer.scale_x = scale_x
            layer.scale_y = scale_y
            instances[0]['scale_x'] = scale_x
            instances[0]['scale_y'] = scale_y
        elif len(instances) > 1:
            # Multiple instances: calculate factor change before updating layer
            old_scale_x = layer.scale_x
            old_scale_y = layer.scale_y
            
            layer.scale_x = scale_x
            layer.scale_y = scale_y
            
            if old_scale_x != 0 and old_scale_y != 0:
                factor_x = scale_x / old_scale_x
                factor_y = scale_y / old_scale_y
                for inst in instances:
                    inst['scale_x'] = inst.get('scale_x', 1.0) * factor_x
                    inst['scale_y'] = inst.get('scale_y', 1.0) * factor_y
        else:
            # No instances: just set layer scale
            layer.scale_x = scale_x
            layer.scale_y = scale_y
        
        self._logger.debug(f"Set scale for layer {uuid} (shallow): ({scale_x:.4f}, {scale_y:.4f})")
    
    def scale_layer(self, uuid: str, factor_x: float, factor_y: float):
        """Scale layer by factor (shallow - scales all instances as rigid unit)
        
        Args:
            uuid: Layer UUID
            factor_x: X scale multiplier
            factor_y: Y scale multiplier
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        # Scale layer
        layer.scale_x *= factor_x
        layer.scale_y *= factor_y
        
        # Scale all instances (shallow transformation)
        instances = layer._data.get('instances', [])
        if instances:
            for inst in instances:
                inst['scale_x'] = inst.get('scale_x', 1.0) * factor_x
                inst['scale_y'] = inst.get('scale_y', 1.0) * factor_y
        
        self._logger.debug(f"Scaled layer {uuid} (shallow): ({factor_x:.4f}, {factor_y:.4f})")
    
    def set_layer_rotation(self, uuid: str, degrees: float):
        """Set layer rotation (shallow - rotates all instances around layer center)
        
        Args:
            uuid: Layer UUID
            degrees: Rotation in degrees
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        # Calculate rotation change
        delta_rotation = degrees - layer.rotation
        
        # Set layer rotation
        layer.rotation = degrees
        
        # Rotate all instances around layer center (shallow transformation)
        instances = layer._data.get('instances', [])
        if instances and delta_rotation != 0:
            import math
            rad = math.radians(delta_rotation)
            cos_r = math.cos(rad)
            sin_r = math.sin(rad)
            
            center_x = layer.pos_x
            center_y = layer.pos_y
            
            for inst in instances:
                # Get instance position
                ix = inst.get('pos_x', 0.5)
                iy = inst.get('pos_y', 0.5)
                
                # Rotate around layer center
                dx = ix - center_x
                dy = iy - center_y
                new_dx = dx * cos_r - dy * sin_r
                new_dy = dx * sin_r + dy * cos_r
                
                inst['pos_x'] = max(0.0, min(1.0, center_x + new_dx))
                inst['pos_y'] = max(0.0, min(1.0, center_y + new_dy))
                
                # Update instance rotation
                inst['rotation'] = inst.get('rotation', 0.0) + delta_rotation
        
        self._logger.debug(f"Set rotation for layer {uuid} (shallow): {degrees:.2f}°")
    
    def set_layer_visible(self, uuid: str, visible: bool):
        """Set layer visibility
        
        Args:
            uuid: Layer UUID
            visible: True to show, False to hide
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        layer.visible = visible
        self._logger.debug(f"Set layer {uuid} visibility: {visible}")
    
    def translate_all_instances(self, uuid: str, dx: float, dy: float):
        """Translate ALL instances of a layer by offset
        
        Args:
            uuid: Layer UUID
            dx: X offset
            dy: Y offset
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        instances = layer._data.get('instances', [])
        for inst in instances:
            inst['pos_x'] = max(0.0, min(1.0, inst['pos_x'] + dx))
            inst['pos_y'] = max(0.0, min(1.0, inst['pos_y'] + dy))
        
        self._logger.debug(f"Translated all {len(instances)} instances of layer {uuid}: ({dx:.4f}, {dy:.4f})")
    
    def scale_all_instances(self, uuid: str, scale_factor_x: float, scale_factor_y: float):
        """Scale ALL instances of a layer by factor
        
        Args:
            uuid: Layer UUID
            scale_factor_x: X scale multiplier
            scale_factor_y: Y scale multiplier
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        instances = layer._data.get('instances', [])
        for inst in instances:
            inst['scale_x'] *= scale_factor_x
            inst['scale_y'] *= scale_factor_y
        
        self._logger.debug(f"Scaled all {len(instances)} instances of layer {uuid}: ({scale_factor_x:.4f}, {scale_factor_y:.4f})")
    
    def rotate_all_instances(self, uuid: str, delta_degrees: float):
        """Rotate ALL instances of a layer by delta
        
        Args:
            uuid: Layer UUID
            delta_degrees: Rotation delta in degrees
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        instances = layer._data.get('instances', [])
        for inst in instances:
            inst['rotation'] = (inst['rotation'] + delta_degrees) % 360
        
        self._logger.debug(f"Rotated all {len(instances)} instances of layer {uuid}: +{delta_degrees:.2f}°")
    
    def begin_instance_group_transform(self, uuid: str):
        """Cache original instance positions for group transform
        
        Call this at the START of a transform operation, then call
        transform_instances_as_group repeatedly during the drag.
        
        Args:
            uuid: Layer UUID
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        # Cache original instance states
        instances = layer._data.get('instances', [])
        self._cached_instance_transforms = []
        for inst in instances:
            self._cached_instance_transforms.append({
                'pos_x': inst['pos_x'],
                'pos_y': inst['pos_y'],
                'scale_x': inst['scale_x'],
                'scale_y': inst['scale_y']
            })
        
        # Cache original AABB center
        bounds = self.get_layer_bounds(uuid)
        self._cached_instance_center = (bounds['center_x'], bounds['center_y'])
        
        self._logger.debug(f"Cached {len(instances)} instance transforms for layer {uuid}")
    
    def end_instance_group_transform(self):
        """Clear cached instance transform state"""
        self._cached_instance_transforms = None
        self._cached_instance_center = None
    
    def transform_instances_as_group(self, uuid: str, new_center_x: float, new_center_y: float, 
                                     scale_factor_x: float, scale_factor_y: float, rotation_delta: float = 0.0):
        """Transform all instances of a layer as a unified group (like multi-selection)
        
        IMPORTANT: Call begin_instance_group_transform() once at drag start, then call
        this method repeatedly during drag with updated transform values.
        
        This performs a group transform relative to the ORIGINAL AABB center:
        - Scales instance positions and scales relative to group center
        - Rotates instance positions around group center (ferris wheel)
        - Translates entire group
        
        Args:
            uuid: Layer UUID
            new_center_x: New X position for group center
            new_center_y: New Y position for group center
            scale_factor_x: X scale factor for group (affects positions and scales)
            scale_factor_y: Y scale factor for group (affects positions and scales)
            rotation_delta: Rotation delta in degrees (rotates positions, not individual rotations)
            
        Raises:
            ValueError: If UUID not found or begin_instance_group_transform not called
        """
        import math
        
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        if not hasattr(self, '_cached_instance_transforms') or self._cached_instance_transforms is None:
            raise ValueError("Must call begin_instance_group_transform() before transform_instances_as_group()")
        
        # Use CACHED original center (doesn't change during transform)
        original_center_x, original_center_y = self._cached_instance_center
        
        # Calculate position delta for group translation
        position_delta_x = new_center_x - original_center_x
        position_delta_y = new_center_y - original_center_y
        
        # Transform each instance using CACHED original values
        instances = layer._data.get('instances', [])
        for i, inst in enumerate(instances):
            cached = self._cached_instance_transforms[i]
            pos_x_orig = cached['pos_x']
            pos_y_orig = cached['pos_y']
            scale_x_orig = cached['scale_x']
            scale_y_orig = cached['scale_y']
            
            # Calculate offset from ORIGINAL group center
            offset_x = pos_x_orig - original_center_x
            offset_y = pos_y_orig - original_center_y
            
            # Apply rotation to offset if rotating
            if rotation_delta != 0:
                rotation_rad = math.radians(rotation_delta)
                cos_r = math.cos(rotation_rad)
                sin_r = math.sin(rotation_rad)
                new_offset_x = offset_x * cos_r - offset_y * sin_r
                new_offset_y = offset_x * sin_r + offset_y * cos_r
            else:
                new_offset_x = offset_x
                new_offset_y = offset_y
            
            # Apply scale to offset
            new_offset_x *= scale_factor_x
            new_offset_y *= scale_factor_y
            
            # Calculate new position with translation
            new_pos_x = original_center_x + new_offset_x + position_delta_x
            new_pos_y = original_center_y + new_offset_y + position_delta_y
            
            # Apply scale to ORIGINAL instance scale (not compounding)
            new_scale_x = scale_x_orig * scale_factor_x
            new_scale_y = scale_y_orig * scale_factor_y
            
            # Clamp positions to valid range
            inst['pos_x'] = max(0.0, min(1.0, new_pos_x))
            inst['pos_y'] = max(0.0, min(1.0, new_pos_y))
            
            # Clamp scales to valid range
            inst['scale_x'] = max(0.01, min(1.0, new_scale_x))
            inst['scale_y'] = max(0.01, min(1.0, new_scale_y))
    
    def begin_rotation_transform(self, uuids: List[str], rotation_mode: str = 'both_deep'):
        """Cache original rotation and position state before rotation operations
        
        Call this at START of rotation drag, then call apply_rotation_transform
        repeatedly during drag with TOTAL delta from start.
        
        Args:
            uuids: List of layer UUIDs to cache
            rotation_mode: Rotation mode (determines what state to cache)
        """
        self._rotation_cache = {
            'mode': rotation_mode,
            'layers': {}
        }
        
        for uuid in uuids:
            layer = self._layers.get_by_uuid(uuid)
            if not layer:
                continue
            
            layer_cache = {'instances': []}
            
            # Cache all instances for this layer
            instances = layer._data.get('instances', [])
            for inst in instances:
                layer_cache['instances'].append({
                    'pos_x': inst.get('pos_x', 0.5),
                    'pos_y': inst.get('pos_y', 0.5),
                    'rotation': inst.get('rotation', 0.0)
                })
            
            self._rotation_cache['layers'][uuid] = layer_cache
        
        self._logger.debug(f"Cached rotation state for {len(uuids)} layers in mode '{rotation_mode}'")
    
    def apply_rotation_transform(self, uuids: List[str], total_delta_degrees: float):
        """Apply rotation transform from cached original state
        
        This applies the TOTAL rotation delta from the original cached state,
        not an incremental delta. Prevents compounding during drag operations.
        
        Args:
            uuids: List of layer UUIDs to transform
            total_delta_degrees: Total rotation delta from original cached state
        """
        if not hasattr(self, '_rotation_cache') or not self._rotation_cache:
            self._logger.warning("No rotation cache found, call begin_rotation_transform first")
            return
        
        mode = self._rotation_cache['mode']
        cache = self._rotation_cache
        
        # Special handling for shallow orbit_only and both (layer-level operations)
        if mode == 'orbit_only':
            self._apply_orbit_only_shallow(uuids, total_delta_degrees, cache)
            return
        elif mode == 'both':
            self._apply_both_shallow(uuids, total_delta_degrees, cache)
            return
        
        # All other modes use unified approach
        # rotate_only: instances orbit around layer center + rotate
        # rotate_only_deep: instances rotate in place (no orbit)
        # orbit_only_deep: instances orbit around unified center (no rotation)
        should_orbit = mode in ['rotate_only', 'orbit_only_deep']
        should_rotate = mode in ['rotate_only', 'rotate_only_deep']
        
        # Get rotation groups based on mode
        rotation_groups = self._get_rotation_groups(uuids, mode, cache)
        
        # Apply rotation to all groups
        for center_x, center_y, instances_with_cache in rotation_groups:
            for inst, inst_cache in instances_with_cache:
                if should_orbit:
                    # Update position by orbiting around center
                    new_x, new_y = self._rotate_point_around(
                        inst_cache['pos_x'], inst_cache['pos_y'],
                        center_x, center_y,
                        total_delta_degrees
                    )
                    inst['pos_x'] = max(0.0, min(1.0, new_x))
                    inst['pos_y'] = max(0.0, min(1.0, new_y))
                
                if should_rotate:
                    # Update rotation value
                    inst['rotation'] = (inst_cache['rotation'] + total_delta_degrees) % 360
    
    def _apply_both_shallow(self, uuids: List[str], total_delta: float, cache: dict):
        """Apply both shallow mode - layers orbit group center AND instances rotate around layer center
        
        This is nested rotation:
        1. Instances orbit + rotate around their layer center (like rotate_only)
        2. Then the entire layer group orbits around the group center
        """
        # Calculate layer centers and apply layer-level rotation first
        layer_data = []
        for uuid in uuids:
            if uuid not in cache['layers']:
                continue
            
            layer = self._layers.get_by_uuid(uuid)
            if not layer:
                continue
            
            cached_instances = cache['layers'][uuid]['instances']
            instances = layer._data.get('instances', [])
            
            if not cached_instances:
                continue
            
            # Calculate layer center from cached positions
            layer_center_x = sum(inst['pos_x'] for inst in cached_instances) / len(cached_instances)
            layer_center_y = sum(inst['pos_y'] for inst in cached_instances) / len(cached_instances)
            
            # Step 1: Rotate instances around layer center (like rotate_only)
            temp_positions = []
            for inst_idx, inst in enumerate(instances):
                if inst_idx >= len(cached_instances):
                    continue
                
                inst_cache = cached_instances[inst_idx]
                
                # Orbit around layer center
                new_x, new_y = self._rotate_point_around(
                    inst_cache['pos_x'], inst_cache['pos_y'],
                    layer_center_x, layer_center_y,
                    total_delta
                )
                temp_positions.append((new_x, new_y))
                
                # Rotate
                inst['rotation'] = (inst_cache['rotation'] + total_delta) % 360
            
            layer_data.append((layer, cached_instances, instances, layer_center_x, layer_center_y, temp_positions))
        
        if not layer_data:
            return
        
        # Calculate group center from layer centers
        group_center_x = sum(ld[3] for ld in layer_data) / len(layer_data)
        group_center_y = sum(ld[4] for ld in layer_data) / len(layer_data)
        
        self._logger.debug(f"both_shallow: group_center=({group_center_x:.3f}, {group_center_y:.3f}), {len(layer_data)} layers")
        
        # Step 2: Orbit each layer's center around group center
        for layer, cached_instances, instances, layer_center_x, layer_center_y, temp_positions in layer_data:
            # Calculate where layer center orbits to
            new_layer_center_x, new_layer_center_y = self._rotate_point_around(
                layer_center_x, layer_center_y,
                group_center_x, group_center_y,
                total_delta
            )
            
            # Calculate translation offset for layer group
            offset_x = new_layer_center_x - layer_center_x
            offset_y = new_layer_center_y - layer_center_y
            
            self._logger.debug(f"  layer_center=({layer_center_x:.3f}, {layer_center_y:.3f}) -> ({new_layer_center_x:.3f}, {new_layer_center_y:.3f}), offset=({offset_x:.3f}, {offset_y:.3f})")
            
            # Apply offset to all instances (already rotated around layer center)
            for inst_idx, inst in enumerate(instances):
                if inst_idx >= len(temp_positions):
                    continue
                
                temp_x, temp_y = temp_positions[inst_idx]
                inst['pos_x'] = max(0.0, min(1.0, temp_x + offset_x))
                inst['pos_y'] = max(0.0, min(1.0, temp_y + offset_y))
    
    def _apply_orbit_only_shallow(self, uuids: List[str], total_delta: float, cache: dict):
        """Apply orbit_only shallow mode - layers translate as units
        
        This is special because instances don't orbit individually around a center,
        they translate together as the layer's center orbits the group center.
        """
        # Calculate layer centers from cached positions
        layer_data = []
        for uuid in uuids:
            if uuid not in cache['layers']:
                continue
            
            layer = self._layers.get_by_uuid(uuid)
            if not layer:
                continue
            
            cached_instances = cache['layers'][uuid]['instances']
            instances = layer._data.get('instances', [])
            
            if not cached_instances:
                continue
            
            # Calculate layer center from cached positions
            layer_center_x = sum(inst['pos_x'] for inst in cached_instances) / len(cached_instances)
            layer_center_y = sum(inst['pos_y'] for inst in cached_instances) / len(cached_instances)
            
            layer_data.append((layer, cached_instances, instances, layer_center_x, layer_center_y))
        
        if not layer_data:
            return
        
        # Calculate group center from layer centers
        group_center_x = sum(ld[3] for ld in layer_data) / len(layer_data)
        group_center_y = sum(ld[4] for ld in layer_data) / len(layer_data)
        
        # Apply orbit to each layer as a unit
        for layer, cached_instances, instances, layer_center_x, layer_center_y in layer_data:
            # Calculate where layer center orbits to
            new_layer_center_x, new_layer_center_y = self._rotate_point_around(
                layer_center_x, layer_center_y,
                group_center_x, group_center_y,
                total_delta
            )
            
            # Calculate translation offset
            offset_x = new_layer_center_x - layer_center_x
            offset_y = new_layer_center_y - layer_center_y
            
            # Apply offset to all instances (translate as unit, no rotation)
            for inst_idx, inst in enumerate(instances):
                if inst_idx >= len(cached_instances):
                    continue
                
                inst_cache = cached_instances[inst_idx]
                inst['pos_x'] = max(0.0, min(1.0, inst_cache['pos_x'] + offset_x))
                inst['pos_y'] = max(0.0, min(1.0, inst_cache['pos_y'] + offset_y))
    
    def end_rotation_transform(self):
        """Clear rotation transform cache"""
        if hasattr(self, '_rotation_cache'):
            self._rotation_cache = None
            self._logger.debug("Cleared rotation cache")
    
    def _get_rotation_groups(self, uuids: List[str], mode: str, cache: dict):
        """Determine rotation groups based on mode
        
        Returns groups: list of (center_x, center_y, [(inst, inst_cache), ...])
        
        Deep modes: ONE group with all instances from all layers
        Shallow modes: ONE group per layer
        
        Args:
            uuids: Layer UUIDs to group
            mode: Rotation mode
            cache: Rotation cache dict
            
        Returns:
            List of tuples: (center_x, center_y, [(inst_dict, inst_cache_dict), ...])
        """
        if 'deep' in mode:
            # Deep modes: all instances are one unified group
            all_instances = []
            all_positions = []
            
            for uuid in uuids:
                if uuid not in cache['layers']:
                    continue
                
                layer = self._layers.get_by_uuid(uuid)
                if not layer:
                    continue
                
                cached_instances = cache['layers'][uuid]['instances']
                instances = layer._data.get('instances', [])
                
                for inst_idx, inst in enumerate(instances):
                    if inst_idx >= len(cached_instances):
                        continue
                    
                    inst_cache = cached_instances[inst_idx]
                    all_instances.append((inst, inst_cache))
                    all_positions.append((inst_cache['pos_x'], inst_cache['pos_y']))
            
            if not all_positions:
                return []
            
            # Calculate unified center from all cached positions
            center_x = sum(p[0] for p in all_positions) / len(all_positions)
            center_y = sum(p[1] for p in all_positions) / len(all_positions)
            
            return [(center_x, center_y, all_instances)]
        
        else:
            # Shallow modes: each layer is its own group
            # For rotate_only: use layer center
            # For both: use layer center (instances orbit around their layer center AND rotate)
            layer_groups = []
            
            for uuid in uuids:
                if uuid not in cache['layers']:
                    continue
                
                layer = self._layers.get_by_uuid(uuid)
                if not layer:
                    continue
                
                cached_instances = cache['layers'][uuid]['instances']
                instances = layer._data.get('instances', [])
                
                layer_instances = []
                layer_positions = []
                
                for inst_idx, inst in enumerate(instances):
                    if inst_idx >= len(cached_instances):
                        continue
                    
                    inst_cache = cached_instances[inst_idx]
                    layer_instances.append((inst, inst_cache))
                    layer_positions.append((inst_cache['pos_x'], inst_cache['pos_y']))
                
                if not layer_positions:
                    continue
                
                # Calculate layer center from cached positions
                layer_center_x = sum(p[0] for p in layer_positions) / len(layer_positions)
                layer_center_y = sum(p[1] for p in layer_positions) / len(layer_positions)
                
                layer_groups.append((layer_center_x, layer_center_y, layer_instances))
            
            return layer_groups
    
    def _rotate_point_around(self, point_x: float, point_y: float, center_x: float, center_y: float, degrees: float) -> tuple:
        """Rotate a point around a center by degrees
        
        Args:
            point_x, point_y: Point to rotate
            center_x, center_y: Center of rotation
            degrees: Rotation angle in degrees
            
        Returns:
            Tuple of (new_x, new_y)
        """
        import math
        
        # Convert to radians
        radians = math.radians(degrees)
        
        # Translate to origin
        dx = point_x - center_x
        dy = point_y - center_y
        
        # Rotate
        cos_angle = math.cos(radians)
        sin_angle = math.sin(radians)
        
        new_dx = dx * cos_angle - dy * sin_angle
        new_dy = dx * sin_angle + dy * cos_angle
        
        # Translate back
        new_x = new_dx + center_x
        new_y = new_dy + center_y
        
        return (new_x, new_y)
    
    def rotate_layer(self, uuid: str, delta_degrees: float):
        """Rotate layer by delta
        
        If layer has multiple instances, performs ferris wheel rotation around
        their collective center (AABB group transform). If layer has single
        instance, rotates in place.
        
        Args:
            uuid: Layer UUID
            delta_degrees: Rotation delta in degrees
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        # Multi-instance layer: ferris wheel rotation
        if layer.instance_count > 1:
            # Calculate center of all instances
            total_x = 0.0
            total_y = 0.0
            for i in range(layer.instance_count):
                instance = layer.get_instance(i, caller='CoA')
                total_x += instance['pos_x']
                total_y += instance['pos_y']
            
            center_x = total_x / layer.instance_count
            center_y = total_y / layer.instance_count
            
            # Rotate each instance around center
            for i in range(layer.instance_count):
                instance = layer.get_instance(i, caller='CoA')
                
                # Rotate position around center
                new_x, new_y = self._rotate_point_around(
                    instance['pos_x'], instance['pos_y'],
                    center_x, center_y,
                    delta_degrees
                )
                instance['pos_x'] = new_x
                instance['pos_y'] = new_y
                
                # Rotate individual rotation
                instance['rotation'] += delta_degrees
            
            self._logger.debug(f"Rotated {layer.instance_count} instances of layer {uuid}: +{delta_degrees:.2f}°")
        else:
            # Single instance: rotate in place
            layer.rotation += delta_degrees
            self._logger.debug(f"Rotated layer {uuid}: +{delta_degrees:.2f}°")
    
    def flip_layer(self, uuid: str, flip_x: bool = None, flip_y: bool = None):
        """Flip layer horizontally and/or vertically
        
        Args:
            uuid: Layer UUID
            flip_x: Set horizontal flip (None = no change)
            flip_y: Set vertical flip (None = no change)
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        if flip_x is not None:
            layer.flip_x = flip_x
        if flip_y is not None:
            layer.flip_y = flip_y
        
        self._logger.debug(f"Flipped layer {uuid}: x={flip_x}, y={flip_y}")
    
    def align_layers(self, uuids: List[str], alignment: str):
        """Align multiple layers relative to each other (shallow - each layer moves as rigid unit)
        
        Args:
            uuids: List of layer UUIDs (must be 2 or more)
            alignment: One of 'left', 'center', 'right', 'top', 'middle', 'bottom'
            
        Raises:
            ValueError: If less than 2 layers, invalid alignment, or UUID not found
        """
        if len(uuids) < 2:
            raise ValueError("Must have at least 2 layers to align")
        
        valid_alignments = ['left', 'center', 'right', 'top', 'middle', 'bottom']
        if alignment not in valid_alignments:
            raise ValueError(f"alignment must be one of {valid_alignments}, got '{alignment}'")
        
        # Get all layers
        layers = []
        for uuid in uuids:
            layer = self._layers.get_by_uuid(uuid)
            if not layer:
                raise ValueError(f"Layer with UUID '{uuid}' not found")
            layers.append(layer)
        
        # Horizontal alignments
        if alignment in ['left', 'center', 'right']:
            positions = [layer.pos_x for layer in layers]
            
            if alignment == 'left':
                target = min(positions)
            elif alignment == 'right':
                target = max(positions)
            else:  # center
                target = sum(positions) / len(positions)
            
            # Apply to each layer (shallow - translate all instances together)
            for layer in layers:
                dx = target - layer.pos_x
                if dx != 0:
                    layer.pos_x = target
                    # Move all instances by same offset
                    instances = layer._data.get('instances', [])
                    if instances:
                        for inst in instances:
                            inst['pos_x'] = max(0.0, min(1.0, inst['pos_x'] + dx))
        
        # Vertical alignments
        else:
            positions = [layer.pos_y for layer in layers]
            
            if alignment == 'top':
                target = min(positions)
            elif alignment == 'bottom':
                target = max(positions)
            else:  # middle
                target = sum(positions) / len(positions)
            
            # Apply to each layer (shallow - translate all instances together)
            for layer in layers:
                dy = target - layer.pos_y
                if dy != 0:
                    layer.pos_y = target
                    # Move all instances by same offset
                    instances = layer._data.get('instances', [])
                    if instances:
                        for inst in instances:
                            inst['pos_y'] = max(0.0, min(1.0, inst['pos_y'] + dy))
        
        self._logger.debug(f"Aligned {len(uuids)} layers (shallow): {alignment}")
    
    def move_layers_to(self, uuids: List[str], position: str):
        """Move layers to fixed canvas positions (shallow - moves all instances as rigid units)
        
        Args:
            uuids: List of layer UUIDs
            position: One of 'left', 'center', 'right', 'top', 'middle', 'bottom'
            
        Raises:
            ValueError: If invalid position or UUID not found
        """
        valid_positions = ['left', 'center', 'right', 'top', 'middle', 'bottom']
        if position not in valid_positions:
            raise ValueError(f"position must be one of {valid_positions}, got '{position}'")
        
        # Define fixed positions (0.0 to 1.0 range)
        fixed_positions = {
            'left': 0.25,
            'center': 0.5,
            'right': 0.75,
            'top': 0.25,
            'middle': 0.5,
            'bottom': 0.75
        }
        
        target = fixed_positions[position]
        
        # For each layer: calculate AABB center, get offset to target, translate
        for uuid in uuids:
            layer = self.get_layer_by_uuid(uuid)
            if not layer:
                continue
            
            instances = layer._data.get('instances', [])
            if not instances:
                continue
            
            # Calculate current AABB center
            min_x = min(inst.get('pos_x', 0.5) for inst in instances)
            max_x = max(inst.get('pos_x', 0.5) for inst in instances)
            min_y = min(inst.get('pos_y', 0.5) for inst in instances)
            max_y = max(inst.get('pos_y', 0.5) for inst in instances)
            aabb_center_x = (min_x + max_x) / 2.0
            aabb_center_y = (min_y + max_y) / 2.0
            
            # Calculate offset: target - current, zero out axis we're not moving
            if position in ['left', 'center', 'right']:
                dx = target - aabb_center_x
                dy = 0.0  # Don't move vertically
            else:
                dx = 0.0  # Don't move horizontally
                dy = target - aabb_center_y
            
            # Translate by the offset (moves all instances together)
            self.translate_layer(uuid, dx, dy)
        
        self._logger.debug(f"Moved {len(uuids)} layers to {position}")
    
    # ========================================
    # Transform Operations (Multi-Layer Group)
    # ========================================
    
    def translate_layers_group(self, uuids: List[str], dx: float, dy: float):
        """Translate multiple layers as a group
        
        Args:
            uuids: List of layer UUIDs
            dx: X offset
            dy: Y offset
            
        Raises:
            ValueError: If any UUID not found
        """
        for uuid in uuids:
            self.translate_layer(uuid, dx, dy)
        
        self._logger.debug(f"Translated group of {len(uuids)} layers: ({dx:.4f}, {dy:.4f})")
    
    def scale_layers_group(self, uuids: List[str], factor: float, around_center: bool = True):
        """Scale multiple layers as a group around their collective center
        
        Args:
            uuids: List of layer UUIDs
            factor: Uniform scale factor
            around_center: If True, scale around AABB center; if False, scale in place
            
        Raises:
            ValueError: If any UUID not found
        """
        if not uuids:
            return
        
        if around_center:
            # Get group AABB center
            bounds = self.get_layers_bounds(uuids)
            center_x = (bounds['min_x'] + bounds['max_x']) / 2.0
            center_y = (bounds['min_y'] + bounds['max_y']) / 2.0
            
            # Scale each layer and adjust position relative to center
            for uuid in uuids:
                layer = self._layers.get_by_uuid(uuid)
                if not layer:
                    raise ValueError(f"Layer with UUID '{uuid}' not found")
                
                # Scale
                layer.scale_x *= factor
                layer.scale_y *= factor
                
                # Adjust position relative to center
                dx = layer.pos_x - center_x
                dy = layer.pos_y - center_y
                layer.pos_x = center_x + dx * factor
                layer.pos_y = center_y + dy * factor
        else:
            # Scale in place
            for uuid in uuids:
                self.scale_layer(uuid, factor, factor)
        
        self._logger.debug(f"Scaled group of {len(uuids)} layers: {factor:.4f}x")
    
    def rotate_selection(self, uuids: List[str], delta_degrees: float, rotation_mode: str = 'auto'):
        """Unified rotation with 6 manual modes plus auto-detection
        
        Rotation Modes:
        - 'auto': Intelligent routing (legacy behavior, default)
        - 'rotate_only': Rotate each layer around its own center (shallow)
        - 'orbit_only': Orbit layers around group center, no rotation (shallow)
        - 'both': Orbit AND rotate layers (shallow, combined ferris wheel)
        - 'rotate_only_deep': Rotate each instance in place, no position changes
        - 'orbit_only_deep': Orbit instances around group center, no rotation
        - 'both_deep': Orbit AND rotate all instances independently
        
        Shallow modes operate on layers as units (multi-instance layers stay grouped).
        Deep modes operate on individual instances (ignores layer boundaries).
        
        Args:
            uuids: List of layer UUIDs
            delta_degrees: Rotation delta in degrees
            rotation_mode: One of the 7 modes above
            
        Raises:
            ValueError: If any UUID not found, empty list, or invalid mode
        """
        if not uuids:
            raise ValueError("No layers selected")
        
        valid_modes = ['auto', 'rotate_only', 'orbit_only', 'both', 
                       'rotate_only_deep', 'orbit_only_deep', 'both_deep']
        if rotation_mode not in valid_modes:
            raise ValueError(f"rotation_mode must be one of {valid_modes}, got '{rotation_mode}'")
        
        # Get all layers
        layers = []
        for uuid in uuids:
            layer = self._layers.get_by_uuid(uuid)
            if not layer:
                raise ValueError(f"Layer with UUID '{uuid}' not found")
            layers.append(layer)
        
        # Route based on mode
        if rotation_mode == 'auto':
            self._rotate_auto(uuids, layers, delta_degrees)
        elif rotation_mode == 'rotate_only':
            self._rotate_only_shallow(uuids, layers, delta_degrees)
        elif rotation_mode == 'orbit_only':
            self._orbit_only_shallow(uuids, layers, delta_degrees)
        elif rotation_mode == 'both':
            self._both_shallow(uuids, layers, delta_degrees)
        elif rotation_mode == 'rotate_only_deep':
            self._rotate_only_deep(uuids, layers, delta_degrees)
        elif rotation_mode == 'orbit_only_deep':
            self._orbit_only_deep(uuids, layers, delta_degrees)
        elif rotation_mode == 'both_deep':
            self._both_deep(uuids, layers, delta_degrees)
    
    def _rotate_auto(self, uuids: List[str], layers: List, delta_degrees: float):
        """Auto-detection mode (legacy behavior)"""
        # Case 1: Single layer
        if len(uuids) == 1:
            self.rotate_layer(uuids[0], delta_degrees)
            return
        
        # Case 2: Multiple layers
        # Check if any have multiple instances
        has_multi_instance = any(layer.instance_count > 1 for layer in layers)
        
        if has_multi_instance:
            # Group of instance layers: reposition around group center,
            # but each layer's instances ferris wheel independently
            self._rotate_instance_layers_group(uuids, delta_degrees)
        else:
            # Regular group rotation: ferris wheel around group center
            self._rotate_regular_layers_group(uuids, delta_degrees)
    
    def _rotate_only_shallow(self, uuids: List[str], layers: List, delta_degrees: float):
        """Rotate each layer around its own center (shallow mode)"""
        for uuid in uuids:
            layer = self._layers.get_by_uuid(uuid)
            
            if layer.instance_count == 1:
                # Single instance: just rotate in place
                instance = layer.get_instance(0, caller='CoA')
                instance['rotation'] += delta_degrees
            else:
                # Multiple instances: ferris wheel around layer center
                # Calculate layer center
                center_x = 0.0
                center_y = 0.0
                for i in range(layer.instance_count):
                    inst = layer.get_instance(i, caller='CoA')
                    center_x += inst['pos_x']
                    center_y += inst['pos_y']
                center_x /= layer.instance_count
                center_y /= layer.instance_count
                
                # Rotate each instance around center
                for i in range(layer.instance_count):
                    instance = layer.get_instance(i, caller='CoA')
                    new_x, new_y = self._rotate_point_around(
                        instance['pos_x'], instance['pos_y'],
                        center_x, center_y,
                        delta_degrees
                    )
                    instance['pos_x'] = new_x
                    instance['pos_y'] = new_y
                    instance['rotation'] += delta_degrees
        
        self._logger.debug(f"Rotate only (shallow): {len(uuids)} layers, +{delta_degrees:.2f}°")
    
    def _orbit_only_shallow(self, uuids: List[str], layers: List, delta_degrees: float):
        """Orbit layers around group center, no rotation changes (shallow mode)"""
        # Get group center
        bounds = self.get_layers_bounds(uuids)
        center_x = bounds['center_x']
        center_y = bounds['center_y']
        
        for uuid in uuids:
            layer = self._layers.get_by_uuid(uuid)
            
            if layer.instance_count == 1:
                # Single instance: orbit position only
                instance = layer.get_instance(0, caller='CoA')
                new_x, new_y = self._rotate_point_around(
                    instance['pos_x'], instance['pos_y'],
                    center_x, center_y,
                    delta_degrees
                )
                instance['pos_x'] = new_x
                instance['pos_y'] = new_y
                # rotation unchanged
            else:
                # Multiple instances: move layer center, keep instances relative
                # Calculate current layer center
                layer_x = 0.0
                layer_y = 0.0
                for i in range(layer.instance_count):
                    inst = layer.get_instance(i, caller='CoA')
                    layer_x += inst['pos_x']
                    layer_y += inst['pos_y']
                layer_center_x = layer_x / layer.instance_count
                layer_center_y = layer_y / layer.instance_count
                
                # Orbit layer center around group center
                new_layer_center_x, new_layer_center_y = self._rotate_point_around(
                    layer_center_x, layer_center_y,
                    center_x, center_y,
                    delta_degrees
                )
                
                # Apply offset to all instances
                offset_x = new_layer_center_x - layer_center_x
                offset_y = new_layer_center_y - layer_center_y
                
                for i in range(layer.instance_count):
                    instance = layer.get_instance(i, caller='CoA')
                    instance['pos_x'] += offset_x
                    instance['pos_y'] += offset_y
                    # rotation unchanged
        
        self._logger.debug(f"Orbit only (shallow): {len(uuids)} layers, +{delta_degrees:.2f}°")
    
    def _both_shallow(self, uuids: List[str], layers: List, delta_degrees: float):
        """Orbit AND rotate layers (shallow mode) - auto mode for multi-layer"""
        # This is the same as _rotate_regular_layers_group for single-instance
        # and _rotate_instance_layers_group for multi-instance
        has_multi_instance = any(layer.instance_count > 1 for layer in layers)
        
        if has_multi_instance:
            self._rotate_instance_layers_group(uuids, delta_degrees)
        else:
            self._rotate_regular_layers_group(uuids, delta_degrees)
    
    def _rotate_only_deep(self, uuids: List[str], layers: List, delta_degrees: float):
        """Rotate each instance in place, no position changes (deep mode)"""
        for uuid in uuids:
            layer = self._layers.get_by_uuid(uuid)
            for i in range(layer.instance_count):
                instance = layer.get_instance(i, caller='CoA')
                instance['rotation'] += delta_degrees
                # position unchanged
        
        self._logger.debug(f"Rotate only (deep): {sum(l.instance_count for l in layers)} instances, +{delta_degrees:.2f}°")
    
    def _orbit_only_deep(self, uuids: List[str], layers: List, delta_degrees: float):
        """Orbit all instances around group center, no rotation changes (deep mode)"""
        # Collect all instances as flat list
        all_instances = []
        for uuid in uuids:
            layer = self._layers.get_by_uuid(uuid)
            for i in range(layer.instance_count):
                instance = layer.get_instance(i, caller='CoA')
                all_instances.append(instance)
        
        # Calculate center of all instances
        center_x = sum(inst['pos_x'] for inst in all_instances) / len(all_instances)
        center_y = sum(inst['pos_y'] for inst in all_instances) / len(all_instances)
        
        # Orbit each instance around center (no rotation change)
        for instance in all_instances:
            new_x, new_y = self._rotate_point_around(
                instance['pos_x'], instance['pos_y'],
                center_x, center_y,
                delta_degrees
            )
            instance['pos_x'] = new_x
            instance['pos_y'] = new_y
            # rotation unchanged
        
        self._logger.debug(f"Orbit only (deep): {len(all_instances)} instances, +{delta_degrees:.2f}°")
    
    def _both_deep(self, uuids: List[str], layers: List, delta_degrees: float):
        """Orbit AND rotate all instances independently (deep mode)"""
        # Collect all instances as flat list
        all_instances = []
        for uuid in uuids:
            layer = self._layers.get_by_uuid(uuid)
            for i in range(layer.instance_count):
                instance = layer.get_instance(i, caller='CoA')
                all_instances.append(instance)
        
        # Calculate center of all instances
        center_x = sum(inst['pos_x'] for inst in all_instances) / len(all_instances)
        center_y = sum(inst['pos_y'] for inst in all_instances) / len(all_instances)
        
        # Orbit AND rotate each instance
        for instance in all_instances:
            new_x, new_y = self._rotate_point_around(
                instance['pos_x'], instance['pos_y'],
                center_x, center_y,
                delta_degrees
            )
            instance['pos_x'] = new_x
            instance['pos_y'] = new_y
            instance['rotation'] += delta_degrees
        
        self._logger.debug(f"Both (deep): {len(all_instances)} instances, +{delta_degrees:.2f}°")
    
    def _rotate_regular_layers_group(self, uuids: List[str], delta_degrees: float):
        """Rotate multiple single-instance layers as group (ferris wheel)
        
        Args:
            uuids: List of layer UUIDs
            delta_degrees: Rotation delta in degrees
        """
        # Get group AABB center
        bounds = self.get_layers_bounds(uuids)
        center_x = bounds['center_x']
        center_y = bounds['center_y']
        
        # Rotate each layer around group center
        for uuid in uuids:
            layer = self._layers.get_by_uuid(uuid)
            
            # Rotate position around center
            new_x, new_y = self._rotate_point_around(
                layer.pos_x, layer.pos_y,
                center_x, center_y,
                delta_degrees
            )
            layer.pos_x = new_x
            layer.pos_y = new_y
            
            # Rotate individual rotation
            layer.rotation += delta_degrees
        
        self._logger.debug(f"Rotated group of {len(uuids)} layers: +{delta_degrees:.2f}°")
    
    def _rotate_instance_layers_group(self, uuids: List[str], delta_degrees: float):
        """Rotate group of instance layers (independent ferris wheels)
        
        Each layer's instances ferris wheel around their own layer center.
        The layers themselves reposition around group center but don't rotate.
        
        Args:
            uuids: List of layer UUIDs
            delta_degrees: Rotation delta in degrees
        """
        # Calculate group center based on all instances of all layers
        total_x = 0.0
        total_y = 0.0
        total_count = 0
        
        for uuid in uuids:
            layer = self._layers.get_by_uuid(uuid)
            for i in range(layer.instance_count):
                instance = layer.get_instance(i, caller='CoA')
                total_x += instance['pos_x']
                total_y += instance['pos_y']
                total_count += 1
        
        group_center_x = total_x / total_count
        group_center_y = total_y / total_count
        
        # For each layer
        for uuid in uuids:
            layer = self._layers.get_by_uuid(uuid)
            
            if layer.instance_count == 1:
                # Single instance: reposition around group center, add rotation
                instance = layer.get_instance(0, caller='CoA')
                new_x, new_y = self._rotate_point_around(
                    instance['pos_x'], instance['pos_y'],
                    group_center_x, group_center_y,
                    delta_degrees
                )
                instance['pos_x'] = new_x
                instance['pos_y'] = new_y
                instance['rotation'] += delta_degrees
            else:
                # Multiple instances: calculate this layer's center
                layer_x = 0.0
                layer_y = 0.0
                for i in range(layer.instance_count):
                    inst = layer.get_instance(i, caller='CoA')
                    layer_x += inst['pos_x']
                    layer_y += inst['pos_y']
                
                layer_center_x = layer_x / layer.instance_count
                layer_center_y = layer_y / layer.instance_count
                
                # Reposition layer center around group center
                new_layer_center_x, new_layer_center_y = self._rotate_point_around(
                    layer_center_x, layer_center_y,
                    group_center_x, group_center_y,
                    delta_degrees
                )
                
                # Calculate offset to apply to all instances
                offset_x = new_layer_center_x - layer_center_x
                offset_y = new_layer_center_y - layer_center_y
                
                # Ferris wheel instances around their own (new) center
                for i in range(layer.instance_count):
                    instance = layer.get_instance(i, caller='CoA')
                    
                    # First apply offset to move with layer center
                    instance['pos_x'] += offset_x
                    instance['pos_y'] += offset_y
                    
                    # Then ferris wheel around new layer center
                    rotated_x, rotated_y = self._rotate_point_around(
                        instance['pos_x'], instance['pos_y'],
                        new_layer_center_x, new_layer_center_y,
                        delta_degrees
                    )
                    instance['pos_x'] = rotated_x
                    instance['pos_y'] = rotated_y
                    
                    # Add rotation to instance
                    instance['rotation'] += delta_degrees
        
        self._logger.debug(f"Rotated instance group of {len(uuids)} layers: +{delta_degrees:.2f}°")
    
    def rotate_layers_group(self, uuids: List[str], delta_degrees: float):
        """Legacy method - use rotate_selection() instead
        
        Rotates multiple layers as a group around their collective center (ferris wheel).
        This is kept for backwards compatibility but rotate_selection() is preferred.
        
        Args:
            uuids: List of layer UUIDs
            delta_degrees: Rotation delta in degrees
            
        Raises:
            ValueError: If any UUID not found
        """
        self.rotate_selection(uuids, delta_degrees)
    
    # ========================================
    # Transform Cache (Group Operations)
    # ========================================
    
    def begin_transform_group(self, uuids: List[str]):
        """Cache current transform state for group operations
        
        Call this before starting a series of transform operations on a group
        to cache the original state. Use apply_transform_group() to apply
        transforms relative to the cached state.
        
        Args:
            uuids: List of layer UUIDs to cache
        """
        self._transform_cache = {}
        for uuid in uuids:
            layer = self._layers.get_by_uuid(uuid)
            if layer:
                self._transform_cache[uuid] = {
                    'pos_x': layer.pos_x,
                    'pos_y': layer.pos_y,
                    'scale_x': layer.scale_x,
                    'scale_y': layer.scale_y,
                    'rotation': layer.rotation
                }
    
    def end_transform_group(self):
        """Clear transform cache after group operation completes"""
        self._transform_cache = None
    
    def apply_transform_group(self, uuid: str, pos_x: float = None, pos_y: float = None, 
                             scale_x: float = None, scale_y: float = None, 
                             rotation: float = None):
        """Apply transform to a layer using cached baseline
        
        If transform cache exists, applies transform relative to cached state.
        Otherwise applies directly. This prevents cumulative error during drag operations.
        
        Args:
            uuid: Layer UUID
            pos_x: New position X (absolute, in 0-1 range)
            pos_y: New position Y (absolute, in 0-1 range)
            scale_x: New scale X (absolute)
            scale_y: New scale Y (absolute)
            rotation: New rotation (absolute, degrees)
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        # Apply transforms (use cached values if available as baseline)
        if pos_x is not None:
            layer.pos_x = pos_x
        if pos_y is not None:
            layer.pos_y = pos_y
        if scale_x is not None:
            layer.scale_x = scale_x
        if scale_y is not None:
            layer.scale_y = scale_y
        if rotation is not None:
            layer.rotation = rotation
    
    def get_cached_transform(self, uuid: str) -> Optional[Dict[str, float]]:
        """Get cached transform state for a layer
        
        Returns:
            Dict with pos_x, pos_y, scale_x, scale_y, rotation or None if not cached
        """
        if self._transform_cache is None:
            return None
        return self._transform_cache.get(uuid)
    
    # ========================================
    # Color Operations
    # ========================================
    
    def set_layer_color(self, uuid: str, color_index: int, rgb: List[int], name: str = None):
        """Set layer color
        
        Args:
            uuid: Layer UUID
            color_index: Color index (1, 2, or 3)
            rgb: RGB values [R, G, B]
            name: Optional color name
            
        Raises:
            ValueError: If UUID not found or color_index invalid
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        if color_index not in (1, 2, 3):
            raise ValueError(f"color_index must be 1, 2, or 3, got {color_index}")
        
        if color_index == 1:
            layer.color1 = rgb
            if name:
                layer.color1_name = name
        elif color_index == 2:
            layer.color2 = rgb
            if name:
                layer.color2_name = name
        elif color_index == 3:
            layer.color3 = rgb
            if name:
                layer.color3_name = name
        
        self._logger.debug(f"Set color{color_index} for layer {uuid}: {rgb}")
    
    def set_base_color(self, color_index: int, rgb: List[int], name: str = None):
        """Set base pattern color
        
        Args:
            color_index: Color index (1 or 2)
            rgb: RGB values [R, G, B]
            name: Optional color name
            
        Raises:
            ValueError: If color_index invalid
        """
        if color_index not in (1, 2):
            raise ValueError(f"color_index must be 1 or 2 for base, got {color_index}")
        
        if color_index == 1:
            self.pattern_color1 = rgb
            if name:
                self.pattern_color1_name = name
        elif color_index == 2:
            self.pattern_color2 = rgb
            if name:
                self.pattern_color2_name = name
        
        self._logger.debug(f"Set base color{color_index}: {rgb}")
    
    # ========================================
    # Query API (for UI to retrieve data)
    # ========================================
    
    def get_layer_property(self, uuid: str, property_name: str) -> Any:
        """Get layer property value
        
        Args:
            uuid: Layer UUID
            property_name: Property name (e.g., 'pos_x', 'filename', 'color1')
            
        Returns:
            Property value
            
        Raises:
            ValueError: If UUID not found
            AttributeError: If property doesn't exist
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        return getattr(layer, property_name)
    
    def get_layer_bounds(self, uuid: str) -> Dict[str, float]:
        """Calculate layer bounds (AABB) including all instances
        
        Args:
            uuid: Layer UUID
            
        Returns:
            Dict with 'min_x', 'max_x', 'min_y', 'max_y', 'width', 'height', 'center_x', 'center_y'
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        # Calculate bounds for all instances
        min_x = float('inf')
        max_x = float('-inf')
        min_y = float('inf')
        max_y = float('-inf')
        
        for i in range(layer.instance_count):
            instance = layer.get_instance(i, caller='CoA')
            
            # Get position and scale
            x = instance['pos_x']
            y = instance['pos_y']
            sx = instance['scale_x']
            sy = instance['scale_y']
            
            # Scale values represent the full width/height in normalized space
            # Use absolute values to handle negative scales (flips)
            half_w = abs(sx) / 2.0
            half_h = abs(sy) / 2.0
            
            # Update bounds
            min_x = min(min_x, x - half_w)
            max_x = max(max_x, x + half_w)
            min_y = min(min_y, y - half_h)
            max_y = max(max_y, y + half_h)
        
        return {
            'min_x': min_x,
            'max_x': max_x,
            'min_y': min_y,
            'max_y': max_y,
            'width': max_x - min_x,
            'height': max_y - min_y,
            'center_x': (min_x + max_x) / 2.0,
            'center_y': (min_y + max_y) / 2.0
        }
    
    def get_layers_bounds(self, uuids: List[str]) -> Dict[str, float]:
        """Calculate combined bounds of multiple layers (AABB)
        
        Args:
            uuids: List of layer UUIDs
            
        Returns:
            Dict with 'min_x', 'max_x', 'min_y', 'max_y', 'width', 'height', 'center_x', 'center_y'
            
        Raises:
            ValueError: If any UUID not found or list is empty
        """
        if not uuids:
            raise ValueError("Need at least one layer UUID")
        
        # Calculate individual bounds
        all_bounds = []
        for uuid in uuids:
            bounds = self.get_layer_bounds(uuid)
            all_bounds.append(bounds)
        
        # Combine
        min_x = min(b['min_x'] for b in all_bounds)
        max_x = max(b['max_x'] for b in all_bounds)
        min_y = min(b['min_y'] for b in all_bounds)
        max_y = max(b['max_y'] for b in all_bounds)
        
        return {
            'min_x': min_x,
            'max_x': max_x,
            'min_y': min_y,
            'max_y': max_y,
            'width': max_x - min_x,
            'height': max_y - min_y,
            'center_x': (min_x + max_x) / 2.0,
            'center_y': (min_y + max_y) / 2.0
        }
    
    def get_all_layer_uuids(self) -> List[str]:
        """Get list of all layer UUIDs (bottom to top order)
        
        Returns:
            List of UUID strings
        """
        return [layer.uuid for layer in self._layers]
    
    def get_top_layer_uuid(self) -> Optional[str]:
        """Get UUID of top layer (last in list)
        
        Returns:
            UUID string or None if no layers
        """
        if len(self._layers) == 0:
            return None
        return self._layers[-1].uuid
    
    def get_bottom_layer_uuid(self) -> Optional[str]:
        """Get UUID of bottom layer (first in list)
        
        Returns:
            UUID string or None if no layers
        """
        if len(self._layers) == 0:
            return None
        return self._layers[0].uuid
    
    def get_last_added_uuid(self) -> Optional[str]:
        """Get UUID of the last layer that was added
        
        Returns:
            UUID string or None if no layers have been added yet
        """
        return self._last_added_uuid
    
    def get_last_added_uuids(self) -> List[str]:
        """Get list of UUIDs from last add operation (useful for multi-paste)
        
        Returns:
            List of UUID strings
        """
        return self._last_added_uuids.copy()
    
    def set_last_added_uuids(self, uuids: List[str]):
        """Set the list of last added UUIDs (for batch operations like paste)
        
        Args:
            uuids: List of UUIDs that were just added
        """
        self._last_added_uuids = uuids.copy()
        if uuids:
            self._last_added_uuid = uuids[-1]  # Keep last one as single UUID
    
    def get_layer_above(self, uuid: str) -> Optional[str]:
        """Get UUID of layer above given layer
        
        Args:
            uuid: Reference layer UUID
            
        Returns:
            UUID of layer above, or None if at top or not found
        """
        try:
            index = self._layers.get_index_by_uuid(uuid)
            if index < len(self._layers) - 1:
                return self._layers[index + 1].uuid
        except ValueError:
            pass
        return None
    
    def get_layer_below(self, uuid: str) -> Optional[str]:
        """Get UUID of layer below given layer
        
        Args:
            uuid: Reference layer UUID
            
        Returns:
            UUID of layer below, or None if at bottom or not found
        """
        try:
            index = self._layers.get_index_by_uuid(uuid)
            if index > 0:
                return self._layers[index - 1].uuid
        except ValueError:
            pass
        return None
    
    def get_layer_count(self) -> int:
        """Get total number of layers
        
        Returns:
            Layer count
        """
        return len(self._layers)
    
    def get_all_layer_uuids(self) -> List[str]:
        """Get UUIDs of all layers in order (bottom to top)
        
        Returns:
            List of layer UUIDs (index 0 = bottom/back, last = top/front)
        """
        return [layer.uuid for layer in self._layers]
    
    def get_layer_by_uuid(self, uuid: str) -> Optional[Layer]:
        """Get layer object by UUID
        
        Args:
            uuid: Layer UUID
            
        Returns:
            Layer object or None if not found
        """
        return self._layers.get_by_uuid(uuid)
    
    def get_layer_by_index(self, index: int) -> Optional[Layer]:
        """Get layer object by index
        
        Args:
            index: Layer index (0 = bottom)
            
        Returns:
            Layer object or None if index out of range
        """
        if 0 <= index < len(self._layers):
            return self._layers[index]
        return None
    
    def get_layer_uuid_by_index(self, index: int) -> Optional[str]:
        """Get layer UUID by index
        
        Args:
            index: Layer index (0 = bottom)
            
        Returns:
            Layer UUID or None if index out of range
        """
        layer = self.get_layer_by_index(index)
        return layer.uuid if layer else None
    
    def add_layer_object(self, layer: Layer, at_front: bool = False, target_uuid: Optional[str] = None) -> str:
        """Add an existing Layer object to the CoA
        
        Args:
            layer: Layer object to add
            at_front: If True, insert at front (top) of layer stack
                     Ignored if target_uuid is provided.
            target_uuid: If provided, insert layer below this target (in front of it, higher index)
            
        Returns:
            UUID of the added layer
        """
        if target_uuid:
            # Insert below target (higher index = in front)
            target_index = self._layers.get_index_by_uuid(target_uuid)
            self._layers.insert(target_index + 1, layer, caller='CoA')
        elif at_front:
            self._layers.insert(len(self._layers), layer, caller='CoA')
        else:
            self._layers.append(layer, caller='CoA')
        
        # Track for auto-selection (single add)
        self._last_added_uuid = layer.uuid
        # Don't overwrite _last_added_uuids here - it's managed by batch operations
        
        return layer.uuid
    
    def insert_layer_at_index(self, index: int, layer: Layer):
        """Insert a layer at a specific index
        
        Args:
            index: Position to insert (0 = bottom)
            layer: Layer object to insert
        """
        self._layers.insert(index, layer, caller='CoA')
    
    def get_uuid_at_index(self, index: int) -> str:
        """Get UUID of layer at specific index
        
        Args:
            index: Layer index (0 = bottom/back, len-1 = top/front)
            
        Returns:
            Layer UUID
            
        Raises:
            IndexError: If index out of range
        """
        return self._layers[index].uuid
    
    def get_uuids_from_indices(self, indices: List[int]) -> List[str]:
        """Convert list of indices to list of UUIDs
        
        Args:
            indices: List of layer indices
            
        Returns:
            List of layer UUIDs in same order
            
        Raises:
            IndexError: If any index out of range
        """
        return [self._layers[i].uuid for i in indices]
    
    # ========================================
    # Snapshot API (for undo/redo)
    # ========================================
    
    def get_snapshot(self) -> Dict:
        """Get complete state snapshot (for undo)
        
        Returns:
            Serializable dictionary containing all CoA state
        """
        return {
            'pattern': self._pattern,
            'pattern_color1': self._pattern_color1.copy(),
            'pattern_color2': self._pattern_color2.copy(),
            'pattern_color1_name': self._pattern_color1_name,
            'pattern_color2_name': self._pattern_color2_name,
            'layers': self._layers.to_dict_list(caller='CoA')
        }
    
    def set_snapshot(self, snapshot: Dict):
        """Restore state from snapshot (for undo)
        
        Args:
            snapshot: Dictionary from get_snapshot()
        """
        self._pattern = snapshot['pattern']
        self._pattern_color1 = snapshot['pattern_color1'].copy()
        self._pattern_color2 = snapshot['pattern_color2'].copy()
        self._pattern_color1_name = snapshot['pattern_color1_name']
        self._pattern_color2_name = snapshot['pattern_color2_name']
        # Property setter validates caller is from within CoA
        self._layers = Layers.from_dict_list(snapshot['layers'], caller='CoA')
        
        self._logger.debug("Restored from snapshot")
    
    def check_merge_compatibility(self, uuids: List[str]) -> Tuple[bool, Dict[str, List[int]]]:
        """Check if layers can be merged as instances
        
        Layers can be merged if they share:
        - Same texture (filename)
        - Same mask
        - Same colors (color1, color2, color3)
        - Same flip settings
        
        Args:
            uuids: List of layer UUIDs to check
            
        Returns:
            Tuple of (compatible: bool, differences: dict)
            differences maps property name to list of layer indices that differ
            
        Raises:
            ValueError: If UUID list empty or contains invalid UUIDs
        """
        if not uuids:
            raise ValueError("UUID list cannot be empty")
        
        if len(uuids) < 2:
            return True, {}
        
        # Get all layer objects
        layer_objs = []
        for uuid in uuids:
            layer = self._layers.get_by_uuid(uuid)
            if not layer:
                raise ValueError(f"Layer with UUID '{uuid}' not found")
            layer_objs.append(layer)
        
        # Reference layer (first one)
        ref = layer_objs[0]
        ref_filename = ref.filename
        ref_mask = ref.mask
        ref_color1 = ref.color1
        ref_color2 = ref.color2
        ref_color3 = ref.color3
        ref_flip_x = ref.flip_x
        ref_flip_y = ref.flip_y
        
        # Track differences
        differences = {}
        
        # Check each layer against reference
        for idx, layer in enumerate(layer_objs[1:], start=1):
            if layer.filename != ref_filename:
                differences.setdefault('filename', []).append(idx)
            if layer.mask != ref_mask:
                differences.setdefault('mask', []).append(idx)
            # Compare colors as lists (element-wise)
            if list(layer.color1) != list(ref_color1):
                differences.setdefault('color1', []).append(idx)
            if list(layer.color2) != list(ref_color2):
                differences.setdefault('color2', []).append(idx)
            if list(layer.color3) != list(ref_color3):
                differences.setdefault('color3', []).append(idx)
            if layer.flip_x != ref_flip_x:
                differences.setdefault('flip_x', []).append(idx)
            if layer.flip_y != ref_flip_y:
                differences.setdefault('flip_y', []).append(idx)
        
        compatible = len(differences) == 0
        return compatible, differences
    
    # ========================================
    # Helper Methods (Internal)
    # ========================================
    
    def _calculate_bounds(self, layer: Layer) -> Dict[str, float]:
        """Calculate AABB for a layer (simplified - treats as point at center)
        
        In a full implementation, this would:
        1. Get texture dimensions
        2. Apply scale
        3. Rotate corners
        4. Find min/max X/Y
        
        For now, we approximate with a simple box around the position.
        
        Args:
            layer: Layer to calculate bounds for
            
        Returns:
            Dict with 'min_x', 'max_x', 'min_y', 'max_y', 'width', 'height'
        """
        # Get position and scale
        x = layer.pos_x
        y = layer.pos_y
        sx = layer.scale_x
        sy = layer.scale_y
        
        # Approximate half-extents (assume unit texture scaled)
        # In reality, we'd need actual texture dimensions
        half_w = sx * 0.1  # Placeholder
        half_h = sy * 0.1  # Placeholder
        
        return {
            'min_x': x - half_w,
            'max_x': x + half_w,
            'min_y': y - half_h,
            'max_y': y + half_h,
            'width': half_w * 2,
            'height': half_h * 2
        }
    
    def _get_bounds_center(self, bounds: Dict[str, float]) -> Tuple[float, float]:
        """Get center point of bounds
        
        Args:
            bounds: Bounds dict from _calculate_bounds()
            
        Returns:
            (center_x, center_y)
        """
        center_x = (bounds['min_x'] + bounds['max_x']) / 2.0
        center_y = (bounds['min_y'] + bounds['max_y']) / 2.0
        return center_x, center_y
    
    def _rotate_point_around(self, px: float, py: float,
                            cx: float, cy: float, degrees: float) -> Tuple[float, float]:
        """Rotate point around center
        
        Args:
            px, py: Point to rotate
            cx, cy: Center of rotation
            degrees: Rotation in degrees
            
        Returns:
            (new_x, new_y)
        """
        # Convert to radians
        radians = math.radians(degrees)
        
        # Translate to origin
        dx = px - cx
        dy = py - cy
        
        # Rotate
        cos_a = math.cos(radians)
        sin_a = math.sin(radians)
        
        new_dx = dx * cos_a - dy * sin_a
        new_dy = dx * sin_a + dy * cos_a
        
        # Translate back
        new_x = new_dx + cx
        new_y = new_dy + cy
        
        return new_x, new_y
    
    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"CoA(pattern='{self._pattern}', layers={len(self._layers)})"
