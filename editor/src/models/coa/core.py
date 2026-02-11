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

from models.color import Color
from copy import deepcopy
import math
import inspect

from ._internal.layer import Layer, Layers, LayerTracker
from ._internal.instance import Instance
from .query_mixin import CoAQueryMixin
from .transform_mixin import CoATransformMixin
from .layer_mixin import CoALayerMixin
from .serialization_mixin import CoASerializationMixin
from .container_mixin import CoAContainerMixin
from models.transform import Vec2
from constants import (
    DEFAULT_POSITION_X, DEFAULT_POSITION_Y,
    DEFAULT_SCALE_X, DEFAULT_SCALE_Y,
    DEFAULT_ROTATION,
    DEFAULT_PATTERN_TEXTURE,
    DEFAULT_BASE_COLOR1, DEFAULT_BASE_COLOR2, DEFAULT_BASE_COLOR3,
    DEFAULT_EMBLEM_COLOR1, DEFAULT_EMBLEM_COLOR2, DEFAULT_EMBLEM_COLOR3,
    CK3_NAMED_COLORS,
    PASTE_OFFSET_X, PASTE_OFFSET_Y
)


class CoA(CoATransformMixin, CoALayerMixin, CoASerializationMixin, CoAContainerMixin, CoAQueryMixin):
    """Coat of Arms data model with full operation API
    
    Manages all CoA data and operations. This is THE MODEL in MVC.
    All data manipulation goes through this class.
    
    Active Instance Pattern:
        CoA.set_active(coa_instance) - Set the active CoA
        CoA.get_active() - Get the active CoA instance
        CoA.has_active() - Check if active instance exists
    
    Properties:
        pattern: Base pattern filename
        pattern_color1: Color object for pattern color 1
        pattern_color2: Color object for pattern color 2
        pattern_color3: Color object for pattern color 3
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
        
        # LayerTracker already imported at top
        LayerTracker.register('CoA')
        
        # Base pattern and colors
        self._pattern = DEFAULT_PATTERN_TEXTURE
        # Store pattern colors as Color objects
        self._pattern_color1 = Color.from_name(DEFAULT_BASE_COLOR1)
        self._pattern_color2 = Color.from_name(DEFAULT_BASE_COLOR2)
        self._pattern_color3 = Color.from_name(DEFAULT_BASE_COLOR3)
        
        # Layers collection - stored with name mangling to prevent external access
        # Access ONLY through the _layers property which validates the caller
        self.__layers = Layers(caller='CoA')
        
        # Transform cache for group operations (prevents cumulative error)
        self._transform_cache = None  # Dict: {uuid: {pos_x, pos_y, scale_x, scale_y, rotation}}
        
        # Track last added layer UUID for auto-selection
        self._last_added_uuid = None
        self._last_added_uuids = []  # List of UUIDs from last add operation (for multi-paste)
        
        self._logger.debug("Created new CoA")
    
    def clear(self):
        """Reset CoA to defaults (empty layers, default pattern/colors)"""
        # Reset pattern and colors
        self._pattern = DEFAULT_PATTERN_TEXTURE
        # Reset pattern colors to defaults (Color objects)
        self._pattern_color1 = Color.from_name(DEFAULT_BASE_COLOR1)
        self._pattern_color2 = Color.from_name(DEFAULT_BASE_COLOR2)
        self._pattern_color3 = Color.from_name(DEFAULT_BASE_COLOR3)
        
        # Clear layers
        self._layers.clear()
        
        # Reset transform cache
        self._transform_cache = None
        
        # Reset tracking
        self._last_added_uuid = None
        self._last_added_uuids = []
        
        self._logger.debug("Cleared CoA to defaults")
    
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
    def pattern_color1(self) -> Color:
        """Get pattern color 1 as Color object"""
        return self._pattern_color1
    
    @pattern_color1.setter
    def pattern_color1(self, value: Color):
        """Set pattern color 1 from Color object"""
        if not isinstance(value, Color):
            raise TypeError("pattern_color1 must be a Color object")
        self._pattern_color1 = value
        self._logger.debug(f"Set pattern_color1: {value}")
    
    @property
    def pattern_color2(self) -> Color:
        """Get pattern color 2 as Color object"""
        return self._pattern_color2
    
    @pattern_color2.setter
    def pattern_color2(self, value: Color):
        """Set pattern color 2 from Color object"""
        if not isinstance(value, Color):
            raise TypeError("pattern_color2 must be a Color object")
        self._pattern_color2 = value
        self._logger.debug(f"Set pattern_color2: {value}")
    
    @property
    def pattern_color3(self) -> Color:
        """Get pattern color 3 as Color object"""
        return self._pattern_color3
    
    @pattern_color3.setter
    def pattern_color3(self, value: Color):
        """Set pattern color 3 from Color object"""
        if not isinstance(value, Color):
            raise TypeError("pattern_color3 must be a Color object")
        self._pattern_color3 = value
        self._logger.debug(f"Set pattern_color3: {value}")
    
    @property
    def layers(self) -> Layers:
        """Get layers collection (read-only access)"""
        return self._layers
    
    # ========================================
    # Color Operations
    # ========================================
    
    def set_layer_color(self, uuid: str, color_index: int, color: Color):
        """Set layer color
        
        Args:
            uuid: Layer UUID
            color_index: Color index (1, 2, or 3)
            color: Color object to set
            
        Raises:
            ValueError: If UUID not found or color_index invalid
            TypeError: If color is not a Color object
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        if color_index not in (1, 2, 3):
            raise ValueError(f"color_index must be 1, 2, or 3, got {color_index}")
        
        if not isinstance(color, Color):
            raise TypeError("color must be a Color object")
        
        if color_index == 1:
            layer.color1 = color
        elif color_index == 2:
            layer.color2 = color
        elif color_index == 3:
            layer.color3 = color
        
        self._logger.debug(f"Set color{color_index} for layer {uuid}: {color}")
    
    def set_base_color(self, color_index: int, color: Color):
        """Set base pattern color
        
        Args:
            color_index: Color index (1, 2, or 3)
            color: Color object to set
            
        Raises:
            ValueError: If color_index invalid
            TypeError: If color is not a Color object
        """
        if color_index not in (1, 2, 3):
            raise ValueError(f"color_index must be 1, 2, or 3 for base, got {color_index}")
        
        if not isinstance(color, Color):
            raise TypeError("color must be a Color object")
        
        if color_index == 1:
            self.pattern_color1 = color
        elif color_index == 2:
            self.pattern_color2 = color
        elif color_index == 3:
            self.pattern_color3 = color
        
        self._logger.debug(f"Set base color{color_index}: {color}")
    
    # ========================================
    # Query/Getter Methods
    # ========================================
    
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
        self._logger.debug(f"Set layer {uuid} visible: {visible}")
    
    def get_layer_visible(self, uuid: str) -> bool:
        """Get layer visibility
        
        Args:
            uuid: Layer UUID
            
        Returns:
            True if visible, False if hidden
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        return layer.visible
    
    def set_layer_mask(self, uuid: str, mask: List[int]):
        """Set layer mask
        
        Args:
            uuid: Layer UUID
            mask: Mask values [1, 2, 3] or None
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        layer.mask = mask
        self._logger.debug(f"Set layer {uuid} mask: {mask}")
    
    def set_layer_name(self, uuid: str, name: str):
        """Set layer name (editor-only metadata)
        
        The layer name is purely for editor organization and display.
        It does not affect the layer's UUID or identity.
        
        Args:
            uuid: Layer UUID
            name: New display name for the layer
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        layer.name = name
        self._logger.debug(f"Set layer {uuid} name: {name}")
    
    def get_layer_name(self, uuid: str) -> str:
        """Get layer name (editor-only metadata)
        
        Returns the layer's display name, which defaults to the texture filename
        without extension if no custom name has been set.
        
        Args:
            uuid: Layer UUID
            
        Returns:
            Layer name string
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        return layer.name
    
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
            'pattern_color1': self._pattern_color1,
            'pattern_color2': self._pattern_color2,
            'pattern_color3': self._pattern_color3,
            'layers': self._layers.to_dict_list(caller='CoA')
        }
    
    def set_snapshot(self, snapshot: Dict):
        """Restore state from snapshot (for undo)
        
        Args:
            snapshot: Dictionary from get_snapshot()
        """
        self._pattern = snapshot['pattern']
        self._pattern_color1 = snapshot['pattern_color1']
        self._pattern_color2 = snapshot['pattern_color2']
        self._pattern_color3 = snapshot.get('pattern_color3', Color.from_name(DEFAULT_BASE_COLOR3))
        # Property setter validates caller is from within CoA
        self._layers = Layers.from_dict_list(snapshot['layers'], caller='CoA')
        
        self._logger.debug("Restored from snapshot")
    
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
        pos = layer.pos
        scale = layer.scale
        x = pos.x
        y = pos.y
        sx = scale.x
        sy = scale.y
        
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
