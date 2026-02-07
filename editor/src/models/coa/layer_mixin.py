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
from models.color import Color
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
            'color1': Color.from_name(DEFAULT_EMBLEM_COLOR1),
            'color2': Color.from_name(DEFAULT_EMBLEM_COLOR2),
            'color3': Color.from_name(DEFAULT_EMBLEM_COLOR3),
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
        
        # Check textures (warning only - first layer's texture will be used)
        textures = set(layer.filename for layer in layers)
        result['info']['textures'] = list(textures)
        result['info']['total_instances'] = sum(layer.instance_count for layer in layers)
        
        if len(textures) > 1:
            result['warnings'].append(
                f"Layers have different textures: {textures}. "
                "After merge, all instances will use the first layer's texture."
            )
        
        # Check colors (warning only, respecting color count)
        first_layer = layers[0]
        first_color_count = first_layer.colors
        colors_match = True
        
        for layer in layers[1:]:
            # Compare only the colors that the first layer actually uses
            if first_color_count >= 1 and tuple(layer.color1) != tuple(first_layer.color1):
                colors_match = False
                break
            if first_color_count >= 2 and tuple(layer.color2) != tuple(first_layer.color2):
                colors_match = False
                break
            if first_color_count >= 3 and tuple(layer.color3) != tuple(first_layer.color3):
                colors_match = False
                break
        
        result['info']['colors_match'] = colors_match
        
        if not colors_match:
            # Build detailed message showing which colors differ (only active colors)
            color_details = []
            for i, layer in enumerate(layers):
                color_count = first_color_count  # Show first layer's color count
                if color_count >= 1:
                    c1 = layer.color1.to_rgb255()
                    details = f"Layer {i+1}: c1={layer.color1.name}{c1}"
                if color_count >= 2:
                    c2 = layer.color2.to_rgb255()
                    details += f", c2={layer.color2.name}{c2}"
                if color_count >= 3:
                    c3 = layer.color3.to_rgb255()
                    details += f", c3={layer.color3.name}{c3}"
                color_details.append(details)
            
            result['warnings'].append(
                f"Layers have different colors. After merge, all instances will use the first layer's colors "
                f"(comparing {first_color_count} color{'s' if first_color_count != 1 else ''}).\n\n" +
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
        
        # Check if all layers have same symmetry settings
        has_mixed_symmetry = False
        first_symmetry_type = first_layer.symmetry_type
        first_symmetry_props = first_layer.symmetry_properties
        
        for layer in layers[1:]:
            if (layer.symmetry_type != first_symmetry_type or 
                layer.symmetry_properties != first_symmetry_props):
                has_mixed_symmetry = True
                break
        
        # Reset symmetry if mixed (warn user)
        if has_mixed_symmetry:
            self._logger.warning("Merging layers with different symmetry settings - resetting to none")
            first_layer.symmetry_type = 'none'
            first_layer.symmetry_properties = []
        
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
            # Invalid merge (e.g., <2 layers, UUID not found)
            return False, {}
        
        # Check for differences (warnings don't block, but we report them)
        differences = {}
        
        # Check texture differences
        if review['info'].get('textures') and len(review['info']['textures']) > 1:
            differences['filename'] = list(range(1, len(uuids)))
        
        # Check color differences (respecting color count)
        if not review['info'].get('colors_match', True):
            layers = [self._layers.get_by_uuid(uuid) for uuid in uuids]
            ref = layers[0]
            color_count = ref.colors
            
            for idx, layer in enumerate(layers[1:], start=1):
                if color_count >= 1 and list(layer.color1) != list(ref.color1):
                    differences.setdefault('color1', []).append(idx)
                if color_count >= 2 and list(layer.color2) != list(ref.color2):
                    differences.setdefault('color2', []).append(idx)
                if color_count >= 3 and list(layer.color3) != list(ref.color3):
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
    
    # ========================================
    # Layer Symmetry Operations
    # ========================================
    
    def get_layer_symmetry_type(self, uuid: str) -> str:
        """Get layer symmetry type
        
        Args:
            uuid: Layer UUID
            
        Returns:
            Symmetry type: 'none', 'bisector', 'rotational', or 'grid'
        """
        layer = self._layers.get_by_uuid(uuid)
        return layer.symmetry_type if layer else 'none'
    
    def set_layer_symmetry_type(self, uuid: str, symmetry_type: str):
        """Set layer symmetry type
        
        Args:
            uuid: Layer UUID
            symmetry_type: 'none', 'bisector', 'rotational', or 'grid'
            
        Raises:
            ValueError: If UUID not found or invalid symmetry_type
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        layer.symmetry_type = symmetry_type
        self._logger.debug(f"Set layer {uuid} symmetry type to '{symmetry_type}'")
    
    def get_layer_symmetry_properties(self, uuid: str) -> List[float]:
        """Get layer symmetry properties
        
        Args:
            uuid: Layer UUID
            
        Returns:
            List of floats (type-specific parameters)
        """
        layer = self._layers.get_by_uuid(uuid)
        return layer.symmetry_properties if layer else []
    
    def set_layer_symmetry_properties(self, uuid: str, properties: List[float]):
        """Set layer symmetry properties
        
        Args:
            uuid: Layer UUID
            properties: List of floats (type-specific parameters)
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        layer.symmetry_properties = properties
        self._logger.debug(f"Set layer {uuid} symmetry properties: {properties}")
    
    def get_symmetry_transforms(self, uuid: str, instance_idx: int = 0) -> List:
        """Calculate all transforms (seed + mirrors) for symmetry rendering
        
        Args:
            uuid: Layer UUID
            instance_idx: Instance index (default 0 for selected instance)
            
        Returns:
            List of Transform objects: mirrors only (seed NOT included)
        """
        from services.symmetry_transforms import get_transform
        from models.transform import Transform
        
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            return []
        
        # Get seed instance
        try:
            if instance_idx < 0:
                # Use selected instance
                instance = layer.get_instance(layer.selected_instance, caller='CoA')
            else:
                instance = layer.get_instance(instance_idx, caller='CoA')
        except (IndexError, ValueError):
            return []
        
        # Create seed transform
        seed_transform = Transform(instance.pos, instance.scale, instance.rotation)
        
        # Get transform plugin and calculate mirrors
        symmetry_type = layer.symmetry_type
        if symmetry_type == 'none':
            return []
        
        transform_plugin = get_transform(symmetry_type)
        if not transform_plugin:
            return []
        
        # Load properties
        symmetry_properties = layer.symmetry_properties
        if symmetry_properties:
            transform_plugin.set_properties(symmetry_properties)
        
        # Calculate and return mirror transforms
        return transform_plugin.calculate_transforms(seed_transform)
