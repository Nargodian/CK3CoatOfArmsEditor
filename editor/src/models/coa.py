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
from typing import Dict, List, Optional, Tuple, Any
import uuid as uuid_module
from copy import deepcopy
import math

from models.layer import Layer, Layers
from constants import (
    DEFAULT_POSITION_X, DEFAULT_POSITION_Y,
    DEFAULT_SCALE_X, DEFAULT_SCALE_Y,
    DEFAULT_ROTATION,
    DEFAULT_PATTERN_TEXTURE,
    DEFAULT_BASE_COLOR1, DEFAULT_BASE_COLOR2,
    DEFAULT_EMBLEM_COLOR1, DEFAULT_EMBLEM_COLOR2, DEFAULT_EMBLEM_COLOR3,
    CK3_NAMED_COLORS
)


class CoA:
    """Coat of Arms data model with full operation API
    
    Manages all CoA data and operations. This is THE MODEL in MVC.
    All data manipulation goes through this class.
    
    Properties:
        pattern: Base pattern filename
        pattern_color1: RGB list for pattern color 1
        pattern_color2: RGB list for pattern color 2
        pattern_color1_name: CK3 color name for pattern color 1
        pattern_color2_name: CK3 color name for pattern color 2
        layers: Layers collection (UUID-based access)
    """
    
    def __init__(self):
        """Create new CoA with defaults"""
        self._logger = logging.getLogger('CoA')
        
        # Register as a LayerTracker caller
        from models.layer import LayerTracker
        LayerTracker.register('CoA')
        
        # Base pattern and colors
        self._pattern = DEFAULT_PATTERN_TEXTURE
        self._pattern_color1 = CK3_NAMED_COLORS[DEFAULT_BASE_COLOR1]['rgb'].copy()
        self._pattern_color2 = CK3_NAMED_COLORS[DEFAULT_BASE_COLOR2]['rgb'].copy()
        self._pattern_color1_name = DEFAULT_BASE_COLOR1
        self._pattern_color2_name = DEFAULT_BASE_COLOR2
        
        # Layers collection
        self._layers = Layers(caller='CoA')
        
        self._logger.debug("Created new CoA")
    
    # ========================================
    # Properties
    # ========================================
    
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
    def layers(self) -> Layers:
        """Get layers collection (read-only access)"""
        return self._layers
    
    # ========================================
    # Serialization (CK3 Format)
    # ========================================
    
    @classmethod
    def from_string(cls, ck3_text: str) -> 'CoA':
        """Parse CoA from CK3 format string
        
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
                    instance = {
                        position = { 0.5 0.5 }
                        scale = { 0.8 0.8 }
                        rotation = 45
                        depth = 1.0
                    }
                }
            }
        """
        coa = cls()
        
        # TODO: Implement full CK3 parser
        # For now, this is a placeholder that needs the parser from services/coa_parser.py
        # The parser should:
        # 1. Extract pattern and color1/color2
        # 2. Parse each colored_emblem block
        # 3. For each emblem, create Layer with:
        #    - filename from texture
        #    - colors from color1/color2/color3
        #    - instances from instance blocks
        # 4. Preserve or generate UUIDs for each layer
        
        coa._logger.warning("from_string() not fully implemented - using placeholder")
        return coa
    
    def to_string(self) -> str:
        """Export CoA to CK3 format string
        
        Returns:
            CK3 coat of arms definition
        """
        lines = []
        lines.append("{")
        
        # Pattern and colors
        lines.append(f'\tpattern = "{self._pattern}"')
        
        # Pattern colors (with names if available)
        if self._pattern_color1_name:
            lines.append(f'\tcolor1 = "{self._pattern_color1_name}"')
        else:
            r, g, b = self._pattern_color1
            lines.append(f'\tcolor1 = rgb {{ {r} {g} {b} }}')
        
        if self._pattern_color2_name:
            lines.append(f'\tcolor2 = "{self._pattern_color2_name}"')
        else:
            r, g, b = self._pattern_color2
            lines.append(f'\tcolor2 = rgb {{ {r} {g} {b} }}')
        
        # Layers (colored emblems)
        for layer in self._layers:
            lines.append(self._layer_to_ck3(layer))
        
        lines.append("}")
        
        return '\n'.join(lines)
    
    def _layer_to_ck3(self, layer: Layer) -> str:
        """Convert layer to CK3 colored_emblem block
        
        Args:
            layer: Layer to export
            
        Returns:
            CK3 colored_emblem text
        """
        lines = []
        lines.append("\tcolored_emblem = {")
        lines.append(f'\t\ttexture = "{layer.filename}"')
        
        # Colors (with names if available)
        if layer.color1_name:
            lines.append(f'\t\tcolor1 = "{layer.color1_name}"')
        else:
            r, g, b = layer.color1
            lines.append(f'\t\tcolor1 = rgb {{ {r} {g} {b} }}')
        
        if layer.colors >= 2:
            if layer.color2_name:
                lines.append(f'\t\tcolor2 = "{layer.color2_name}"')
            else:
                r, g, b = layer.color2
                lines.append(f'\t\tcolor2 = rgb {{ {r} {g} {b} }}')
        
        if layer.colors >= 3:
            if layer.color3_name:
                lines.append(f'\t\tcolor3 = "{layer.color3_name}"')
            else:
                r, g, b = layer.color3
                lines.append(f'\t\tcolor3 = rgb {{ {r} {g} {b} }}')
        
        # Instances
        for i in range(layer.instance_count):
            instance = layer.get_instance(i, caller='CoA')
            lines.append("\t\tinstance = {")
            lines.append(f"\t\t\tposition = {{ {instance['pos_x']:.4f} {instance['pos_y']:.4f} }}")
            lines.append(f"\t\t\tscale = {{ {instance['scale_x']:.4f} {instance['scale_y']:.4f} }}")
            if instance['rotation'] != 0.0:
                lines.append(f"\t\t\trotation = {instance['rotation']:.2f}")
            if instance['depth'] != 0.0:
                lines.append(f"\t\t\tdepth = {instance['depth']:.4f}")
            lines.append("\t\t}")
        
        lines.append("\t}")
        return '\n'.join(lines)
    
    # ========================================
    # Layer Management
    # ========================================
    
    def add_layer(self, emblem_path: str = "", pos_x: float = DEFAULT_POSITION_X,
                  pos_y: float = DEFAULT_POSITION_Y, colors: int = 3) -> str:
        """Add new layer
        
        Args:
            emblem_path: Path to emblem texture
            pos_x: Initial X position (0.0-1.0)
            pos_y: Initial Y position (0.0-1.0)
            colors: Number of colors (1, 2, or 3)
            
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
        self._layers.append(layer, caller='CoA')
        
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
    
    def move_layer(self, uuid: str, to_index: int):
        """Move layer to new position
        
        Args:
            uuid: Layer UUID
            to_index: Target index in layer stack
            
        Raises:
            ValueError: If UUID not found
            IndexError: If to_index out of range
        """
        from_index = self._layers.get_index_by_uuid(uuid)
        
        if not (0 <= to_index < len(self._layers)):
            raise IndexError(f"Index {to_index} out of range [0, {len(self._layers)})")
        
        self._layers.move(from_index, to_index, caller='CoA')
        self._logger.debug(f"Moved layer {uuid}: {from_index} -> {to_index}")
    
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
        """Set layer position (affects selected instance)
        
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
        
        layer.pos_x = x
        layer.pos_y = y
        self._logger.debug(f"Set position for layer {uuid}: ({x:.4f}, {y:.4f})")
    
    def translate_layer(self, uuid: str, dx: float, dy: float):
        """Translate layer by offset (affects selected instance)
        
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
        
        layer.pos_x += dx
        layer.pos_y += dy
        self._logger.debug(f"Translated layer {uuid}: ({dx:.4f}, {dy:.4f})")
    
    def set_layer_scale(self, uuid: str, scale_x: float, scale_y: float):
        """Set layer scale (affects selected instance)
        
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
        
        layer.scale_x = scale_x
        layer.scale_y = scale_y
        self._logger.debug(f"Set scale for layer {uuid}: ({scale_x:.4f}, {scale_y:.4f})")
    
    def scale_layer(self, uuid: str, factor_x: float, factor_y: float):
        """Scale layer by factor (affects selected instance)
        
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
        
        layer.scale_x *= factor_x
        layer.scale_y *= factor_y
        self._logger.debug(f"Scaled layer {uuid}: ({factor_x:.4f}, {factor_y:.4f})")
    
    def set_layer_rotation(self, uuid: str, degrees: float):
        """Set layer rotation (affects selected instance)
        
        Args:
            uuid: Layer UUID
            degrees: Rotation in degrees
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        layer.rotation = degrees
        self._logger.debug(f"Set rotation for layer {uuid}: {degrees:.2f}°")
    
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
            
            # Approximate half-extents (assume unit texture scaled)
            # In reality, we'd need actual texture dimensions
            half_w = sx * 0.1  # Placeholder
            half_h = sy * 0.1  # Placeholder
            
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
