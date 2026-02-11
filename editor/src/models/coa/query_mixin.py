"""
Query Mixin for CoA Model

Provides read-only query methods for UI components to retrieve CoA state.
These methods are separated into a mixin to keep the main CoA class focused
on core operations and make the query API easier to maintain.

All query methods follow these conventions:
- Prefix with get_ for retrieving data
- Accept uuid parameter for layer-specific queries
- Raise ValueError if UUID not found
- Return copies of mutable data (no direct access to internal state)
"""

from typing import Dict, List, Optional, Any
from ._internal.layer import Layer
from models.transform import Vec2


class CoAQueryMixin:
    """Mixin providing query API for CoA model
    
    This mixin assumes the class has:
    - self._layers: Layers collection
    - self._last_added_uuid: str tracking last added layer
    - self._last_added_uuids: List[str] tracking batch additions
    """
    
    # ========================================
    # Layer Bounds Queries
    # ========================================
    
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
            x = instance.pos.x
            y = instance.pos.y
            sx = instance.scale.x
            sy = instance.scale.y
            half_w = abs(sx) / 2.0
            half_h = abs(sy) / 2.0
            
            # Update bounds (AABB is axis-aligned, ignores rotation)
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
    
    # ========================================
    # Layer Collection Queries
    # ========================================
    
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
    
    def has_layer_uuid(self, uuid: str) -> bool:
        """Check if a layer with given UUID exists
        
        Args:
            uuid: Layer UUID to check
            
        Returns:
            True if layer exists, False otherwise
        """
        return self._layers.get_by_uuid(uuid) is not None
    
    def get_layer_by_uuid(self, uuid: str) -> Optional['Layer']:
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
    
    def get_layer_index_by_uuid(self, uuid: str) -> Optional[int]:
        """Get layer index by UUID
        
        Args:
            uuid: Layer UUID
            
        Returns:
            Layer index (0 = bottom) or None if UUID not found
        """
        return self._layers.get_index_by_uuid(uuid)
    
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
    # Layer Instance Queries
    # ========================================
    
    def get_layer_instance_count(self, uuid: str) -> int:
        """Get number of instances for a layer
        
        Args:
            uuid: Layer UUID
            
        Returns:
            Number of instances (at least 1)
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        return layer.instance_count
    
    def get_layer_instance(self, uuid: str, instance_index: int) -> Dict:
        """Get instance data for a layer by index
        
        Args:
            uuid: Layer UUID
            instance_index: Instance index
            
        Returns:
            Dictionary containing instance properties:
                - pos_x, pos_y: Position
                - scale_x, scale_y: Scale
                - rotation: Rotation in degrees
                - depth: Depth value
            
        Raises:
            ValueError: If UUID not found
            IndexError: If instance_index out of range
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        return layer.get_instance(instance_index, caller='query_mixin')
    
    # ========================================
    # Layer Basic Property Queries
    # ========================================
    
    def get_layer_filename(self, uuid: str) -> str:
        """Get texture filename for a layer
        
        Args:
            uuid: Layer UUID
            
        Returns:
            Texture filename
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        return layer.filename
    
    def get_layer_colors(self, uuid: str) -> int:
        """Get number of colors for a layer
        
        Args:
            uuid: Layer UUID
            
        Returns:
            Number of colors (1, 2, or 3)
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        return layer.colors
    
    def get_layer_visible(self, uuid: str) -> bool:
        """Get visibility state for a layer
        
        Args:
            uuid: Layer UUID
            
        Returns:
            True if visible, False otherwise
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        return layer.visible
    
    def get_layer_mask(self, uuid: str) -> Optional[List[int]]:
        """Get mask channels for a layer
        
        Args:
            uuid: Layer UUID
            
        Returns:
            Mask channels [r, g, b] or None
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        return layer.mask
    
    # ========================================
    # Layer Transform Queries
    # ========================================
    
    def get_layer_pos(self, uuid: str) -> Vec2:
        """Get position for a layer (AABB center for multi-instance)
        
        Args:
            uuid: Layer UUID
            
        Returns:
            Position as Vec2 (0.0 to 1.0)
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        instances = layer._data.get('instances', [])
        if len(instances) > 1:
            # Multi-instance: return AABB center
            min_x = min(inst.pos.x for inst in instances)
            max_x = max(inst.pos.x for inst in instances)
            min_y = min(inst.pos.y for inst in instances)
            max_y = max(inst.pos.y for inst in instances)
            return Vec2((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)
        else:
            # Single instance or fallback
            return layer.pos
    
    def get_layer_pos_x(self, uuid: str) -> float:
        """Get X position for a layer (AABB center for multi-instance)
        
        Returns:
            X position (0.0 to 1.0)
        """
        return self.get_layer_pos(uuid).x
    
    def get_layer_pos_y(self, uuid: str) -> float:
        """Get Y position for a layer (AABB center for multi-instance)
        
        Returns:
            Y position (0.0 to 1.0)
        """
        return self.get_layer_pos(uuid).y
    
    def get_layer_scale(self, uuid: str) -> Vec2:
        """Get scale for a layer
        
        Args:
            uuid: Layer UUID
            
        Returns:
            Scale as Vec2
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        return layer.scale
    
    def get_layer_scale_x(self, uuid: str) -> float:
        """Get X scale for a layer
        
        Returns:
            X scale
        """
        return self.get_layer_scale(uuid).x
    
    def get_layer_scale_y(self, uuid: str) -> float:
        """Get Y scale for a layer
        
        Returns:
            Y scale
        """
        return self.get_layer_scale(uuid).y
    
    def get_layer_rotation(self, uuid: str) -> float:
        """Get rotation for a layer
        
        Args:
            uuid: Layer UUID
            
        Returns:
            Rotation in degrees
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        return layer.rotation
    
    def get_layer_flip_x(self, uuid: str) -> bool:
        """Get horizontal flip state for a layer
        
        Args:
            uuid: Layer UUID
            
        Returns:
            True if horizontally flipped, False otherwise
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        return layer.flip_x
    
    def get_layer_flip_y(self, uuid: str) -> bool:
        """Get vertical flip state for a layer
        
        Args:
            uuid: Layer UUID
            
        Returns:
            True if vertically flipped, False otherwise
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        return layer.flip_y
    
    # ========================================
    # Layer Color Queries
    # ========================================
    
    def get_layer_color(self, uuid: str, color_index: int):
        """Get color for a layer as Color object
        
        Args:
            uuid: Layer UUID
            color_index: Color index (1, 2, or 3)
            
        Returns:
            Color object
            
        Raises:
            ValueError: If UUID not found or color_index invalid
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        if color_index == 1:
            return layer.color1
        elif color_index == 2:
            return layer.color2
        elif color_index == 3:
            return layer.color3
        else:
            raise ValueError(f"color_index must be 1, 2, or 3, got {color_index}")