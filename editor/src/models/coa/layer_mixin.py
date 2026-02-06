"""
CoA Layer Management Mixin

This mixin provides all layer CRUD and instance management operations for the CoA model.
Extracted from CoA to improve code organization and maintainability.

Methods:
    Layer CRUD:
        - add_layer
        - remove_layer
        - duplicate_layer
        - duplicate_layer_below
        - duplicate_layer_above
        - merge_layers_into_first
        - move_layer_below
        - move_layer_above
        - move_layer_to_bottom
        - move_layer_to_top
        - shift_layer_up
        - shift_layer_down
        - review_merge
        - merge_layers
        - split_layer
        - add_layer_object
        - insert_layer_at_index
        - check_merge_compatibility
    
    Instance Management:
        - add_instance
        - remove_instance
        - select_instance
"""

import logging
import uuid as uuid_module
from copy import deepcopy
from typing import Dict, List, Optional, Any, Union, Tuple

from ._internal.layer import Layer
from ._internal.instance import Instance
from models.transform import Vec2
from constants import (
    DEFAULT_POSITION_X, DEFAULT_POSITION_Y,
    DEFAULT_SCALE_X, DEFAULT_SCALE_Y,
    DEFAULT_ROTATION,
    DEFAULT_EMBLEM_COLOR1, DEFAULT_EMBLEM_COLOR2, DEFAULT_EMBLEM_COLOR3,
    CK3_NAMED_COLORS
)


class CoALayerMixin:
    """Mixin providing layer management operations for CoA
    
    This mixin assumes the parent class has:
        - self._layers: Layers collection
        - self._logger: logging.Logger instance
    """
    
    # ========================================
    # Layer CRUD Operations
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
            'instances': [Instance({
                'pos_x': pos_x,
                'pos_y': pos_y,
                'scale_x': DEFAULT_SCALE_X,
                'scale_y': DEFAULT_SCALE_Y,
                'rotation': DEFAULT_ROTATION,
                'depth': 0.0
            })],
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
                    pos_x=instance.pos.x,
                    pos_y=instance.pos.y
                )
                # Copy remaining instance properties (if they exist)
                new_instance = first_layer.get_instance(new_idx, caller='CoA.merge')
                new_instance.scale = instance.scale
                new_instance.rotation = instance.rotation
                new_instance.flip_x = instance.flip_x
                new_instance.flip_y = instance.flip_y
                if instance.depth is not None:
                    new_instance.depth = instance.depth
        
        # Remove the other layers (not the first one)
        for uuid in uuids[1:]:
            self.remove_layer(uuid)
        
        self._logger.debug(f"Merged {len(uuids)} layers into {first_uuid} ({first_layer.instance_count} instances)")
        return first_uuid
    
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
        """Shift layer(s) up one position (higher index = toward front/top of visual list)
        
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
        
        # Get all indices, check if any at top (highest index)
        indices = []
        for uuid in uuids:
            idx = self._layers.get_index_by_uuid(uuid)
            if idx is None:
                raise ValueError(f"Layer with UUID '{uuid}' not found")
            indices.append(idx)
        
        # Can't shift up if any layer is at highest index (top)
        if max(indices) >= len(self._layers) - 1:
            return False
        
        # Get target UUID (layer immediately above - higher index than topmost selected)
        target_index = max(indices) + 1
        target_uuid = self.get_layer_uuid_by_index(target_index)
        
        # Move selected layers below target (puts them AFTER target at higher index)
        self.move_layer_below(uuids, target_uuid)
        return True
    
    def shift_layer_down(self, uuids: Union[str, List[str]]) -> bool:
        """Shift layer(s) down one position (lower index = toward back/bottom of visual list)
        
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
        
        # Get all indices, check if any at bottom (index 0)
        indices = []
        for uuid in uuids:
            idx = self._layers.get_index_by_uuid(uuid)
            if idx is None:
                raise ValueError(f"Layer with UUID '{uuid}' not found")
            indices.append(idx)
        
        # Can't shift down if any layer is at index 0 (bottom)
        if min(indices) == 0:
            return False
        
        # Get target UUID (layer immediately below - lower index than bottommost selected)
        target_index = min(indices) - 1
        target_uuid = self.get_layer_uuid_by_index(target_index)
        
        # Move selected layers above target (puts them BEFORE target at lower index)
        self.move_layer_above(uuids, target_uuid)
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
        first_colors = (tuple(layers[0].color1), tuple(layers[0].color2), tuple(layers[0].color3))
        colors_match = all(
            (tuple(layer.color1), tuple(layer.color2), tuple(layer.color3)) == first_colors
            for layer in layers[1:]
        )
        result['info']['colors_match'] = colors_match
        
        if not colors_match:
            # Build detailed message showing which colors differ
            color_details = []
            for i, layer in enumerate(layers):
                c1 = tuple(layer.color1)
                c2 = tuple(layer.color2)
                c3 = tuple(layer.color3)
                color_details.append(
                    f"Layer {i+1}: c1={layer.color1_name}{c1}, c2={layer.color2_name}{c2}, c3={layer.color3_name}{c3}"
                )
            
            result['warnings'].append(
                f"Layers have different colors. After merge, all instances will use the first layer's colors.\n\n" +
                "\n".join(color_details)
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
                    pos_x=instance.pos.x,
                    pos_y=instance.pos.y,
                    caller='CoA'
                )
                # Copy other properties
                new_inst = first_layer.get_instance(idx, caller='CoA')
                new_inst.scale = instance.scale
                new_inst.rotation = instance.rotation
                new_inst.flip_x = instance.flip_x
                new_inst.flip_y = instance.flip_y
                new_inst.depth = instance.depth
        
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
    
    def check_merge_compatibility(self, uuids: List[str]) -> Tuple[bool, Dict[str, List[int]]]:
        """Check if layers can be merged as instances
        
        This is a wrapper around review_merge() that provides tuple return format.
        
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
        
        # Use review_merge as single source of truth
        review = self.review_merge(uuids)
        
        # Transform to tuple format
        if not review['valid']:
            # If not valid due to texture mismatch, mark as texture difference
            differences = {}
            if review['info'].get('textures') and len(review['info']['textures']) > 1:
                # All non-first layers have different textures
                differences['filename'] = list(range(1, len(uuids)))
            return False, differences
        
        # Check for color differences (warnings don't block, but we report them)
        differences = {}
        if not review['info'].get('colors_match', True):
            # Get layers to check which specific colors differ
            layers = [self._layers.get_by_uuid(uuid) for uuid in uuids]
            ref = layers[0]
            for idx, layer in enumerate(layers[1:], start=1):
                if list(layer.color1) != list(ref.color1):
                    differences.setdefault('color1', []).append(idx)
                if list(layer.color2) != list(ref.color2):
                    differences.setdefault('color2', []).append(idx)
                if list(layer.color3) != list(ref.color3):
                    differences.setdefault('color3', []).append(idx)
        
        compatible = len(differences) == 0
        return compatible, differences
    
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
