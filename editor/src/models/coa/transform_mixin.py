"""
CK3 Coat of Arms Editor - Transform Mixin

Contains all transform-related methods for CoA model:
- Position/scale operations
- Rotation operations (single and group)
- Flip operations
- Alignment and movement
- Group transform operations with caching

This mixin is pure domain logic - no UI dependencies.
"""

import math
import logging
from typing import Dict, List, Optional, Tuple, Any

from models.transform import Vec2


class CoATransformMixin:
    """Mixin containing transform operations for CoA model
    
    This mixin expects the parent class to have:
    - self._layers: Layers collection
    - self._logger: Logger instance
    - self.get_layer_bounds(uuid): Method to get layer bounds
    - self.get_layers_bounds(uuids): Method to get multi-layer bounds
    - self.get_layer_by_uuid(uuid): Method to get layer by UUID
    - self.get_layer_pos_x(uuid): Method to get layer X position
    - self.get_layer_pos_y(uuid): Method to get layer Y position
    """
    
    # ========================================
    # Position/Scale Operations
    # ========================================
    
    def get_layer_position(self, uuid: str) -> Tuple[float, float]:
        """Get layer position (AABB center for multi-instance, direct for single-instance)
        
        Args:
            uuid: Layer UUID
            
        Returns:
            Tuple of (x, y) position (0.0-1.0)
            
        Raises:
            ValueError: If UUID not found
        """
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        instances = layer._data.get('instances', [])
        
        if len(instances) == 1:
            # Single instance: return position directly
            pos = layer.pos
            return (pos.x, pos.y)
        elif len(instances) > 1:
            # Multiple instances: return AABB center
            min_x = min(inst.pos.x for inst in instances)
            max_x = max(inst.pos.x for inst in instances)
            min_y = min(inst.pos.y for inst in instances)
            max_y = max(inst.pos.y for inst in instances)
            
            center_x = (min_x + max_x) / 2.0
            center_y = (min_y + max_y) / 2.0
            
            return (center_x, center_y)
        else:
            # No instances - return layer default
            pos = layer.pos
            return (pos.x, pos.y)
    
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
        target_pos = Vec2(x, y)
        
        if len(instances) == 1:
            # Single instance: set position directly
            instances[0].pos = target_pos
        elif len(instances) > 1:
            # Multiple instances: calculate AABB center, maintain relative offsets
            # Get bounding box of all instances
            min_x = min(inst.pos.x for inst in instances)
            max_x = max(inst.pos.x for inst in instances)
            min_y = min(inst.pos.y for inst in instances)
            max_y = max(inst.pos.y for inst in instances)
            
            # Calculate AABB center
            aabb_center = Vec2((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)
            
            # Calculate offset from AABB center to new position
            offset = Vec2(target_pos.x - aabb_center.x, target_pos.y - aabb_center.y)
            
            # Apply offset to all instances
            for inst in instances:
                inst.pos = Vec2(inst.pos.x + offset.x, inst.pos.y + offset.y)  # setter handles clamping
        else:
            # No instances: just set layer position
            layer.pos = target_pos
        
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
        offset = Vec2(dx, dy)
        if instances:
            for inst in instances:
                inst.pos = Vec2(inst.pos.x + offset.x, inst.pos.y + offset.y)  # setter handles clamping
        
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
        offset = Vec2(dx, dy)
        for uuid in uuids:
            layer = self._layers.get_by_uuid(uuid)
            if not layer:
                raise ValueError(f"Layer with UUID '{uuid}' not found")
            
            layer.pos = Vec2(layer.pos.x + offset.x, layer.pos.y + offset.y)
        
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
        
        total = Vec2(0.0, 0.0)
        
        for uuid in uuids:
            layer = self._layers.get_by_uuid(uuid)
            if not layer:
                raise ValueError(f"Layer with UUID '{uuid}' not found")
            
            pos = layer.pos
            total = Vec2(total.x + pos.x, total.y + pos.y)
        
        centroid = Vec2(total.x / len(uuids), total.y / len(uuids))
        return (centroid.x, centroid.y)
    
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
        
        new_scale = Vec2(scale_x, scale_y)
        
        # Apply scale to all instances (shallow transformation)
        instances = layer._data.get('instances', [])
        if len(instances) == 1:
            # Single instance: set directly to avoid flicker
            layer.scale = new_scale
            instances[0].scale = new_scale
        elif len(instances) > 1:
            # Multiple instances: calculate factor change before updating layer
            old_scale = layer.scale
            layer.scale = new_scale
            
            if old_scale.x != 0 and old_scale.y != 0:
                factor = Vec2(new_scale.x / old_scale.x, new_scale.y / old_scale.y)
                for inst in instances:
                    inst.scale = Vec2(inst.scale.x * factor.x, inst.scale.y * factor.y)
        else:
            # No instances: just set layer scale
            layer.scale = new_scale
        
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
        
        factor = Vec2(factor_x, factor_y)
        
        # Scale layer
        layer.scale = Vec2(layer.scale.x * factor.x, layer.scale.y * factor.y)
        
        # Scale all instances (shallow transformation)
        instances = layer._data.get('instances', [])
        if instances:
            for inst in instances:
                inst.scale = Vec2(inst.scale.x * factor.x, inst.scale.y * factor.y)
        
        self._logger.debug(f"Scaled layer {uuid} (shallow): ({factor_x:.4f}, {factor_y:.4f})")
    
    # ========================================
    # Rotation Operations
    # ========================================
    
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
            rad = math.radians(delta_rotation)
            cos_r = math.cos(rad)
            sin_r = math.sin(rad)
            
            center = layer.pos
            
            for inst in instances:
                # Get instance position
                inst_pos = inst.pos
                
                # Rotate around layer center
                delta = Vec2(inst_pos.x - center.x, inst_pos.y - center.y)
                new_delta = Vec2(delta.x * cos_r - delta.y * sin_r, delta.x * sin_r + delta.y * cos_r)
                
                inst.pos = Vec2(center.x + new_delta.x, center.y + new_delta.y)  # setter handles clamping
                
                # Update instance rotation
                inst.rotation = inst.rotation + delta_rotation
        
        self._logger.debug(f"Set rotation for layer {uuid} (shallow): {degrees:.2f}°")
    
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
        
        offset = Vec2(dx, dy)
        instances = layer._data.get('instances', [])
        for inst in instances:
            inst.pos = Vec2(inst.pos.x + offset.x, inst.pos.y + offset.y)  # setter handles clamping
        
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
        
        factor = Vec2(scale_factor_x, scale_factor_y)
        instances = layer._data.get('instances', [])
        for inst in instances:
            inst.scale = Vec2(inst.scale.x * factor.x, inst.scale.y * factor.y)
        
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
            inst.rotation = (inst.rotation + delta_degrees) % 360
        
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
                'pos_x': inst.pos.x,
                'pos_y': inst.pos.y,
                'scale_x': inst.scale.x,
                'scale_y': inst.scale.y
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
        layer = self._layers.get_by_uuid(uuid)
        if not layer:
            raise ValueError(f"Layer with UUID '{uuid}' not found")
        
        if not hasattr(self, '_cached_instance_transforms') or self._cached_instance_transforms is None:
            raise ValueError("Must call begin_instance_group_transform() before transform_instances_as_group()")
        
        # Use CACHED original center (doesn't change during transform)
        original_center_x, original_center_y = self._cached_instance_center
        
        # Calculate position delta for group translation
        position_delta = Vec2(new_center_x - original_center_x, new_center_y - original_center_y)
        
        # Transform each instance using CACHED original values
        instances = layer._data.get('instances', [])
        for i, inst in enumerate(instances):
            cached = self._cached_instance_transforms[i]
            pos_orig = Vec2(cached['pos_x'], cached['pos_y'])
            scale_orig = Vec2(cached['scale_x'], cached['scale_y'])
            
            # Calculate offset from ORIGINAL group center
            offset = Vec2(pos_orig.x - original_center_x, pos_orig.y - original_center_y)
            
            # Apply rotation to offset if rotating
            if rotation_delta != 0:
                rotation_rad = math.radians(rotation_delta)
                cos_r = math.cos(rotation_rad)
                sin_r = math.sin(rotation_rad)
                new_offset = Vec2(offset.x * cos_r - offset.y * sin_r, offset.x * sin_r + offset.y * cos_r)
            else:
                new_offset = offset
            
            # Apply scale to offset
            new_offset = Vec2(new_offset.x * scale_factor_x, new_offset.y * scale_factor_y)
            
            # Calculate new position with translation
            new_pos = Vec2(original_center_x + new_offset.x + position_delta.x, original_center_y + new_offset.y + position_delta.y)
            
            # Apply scale to ORIGINAL instance scale (not compounding)
            new_scale = Vec2(scale_orig.x * scale_factor_x, scale_orig.y * scale_factor_y)
            
            # Set positions (setter handles clamping)
            inst.pos = new_pos
            
            # Set scales (with manual clamping)
            inst.scale = Vec2(max(0.01, min(1.0, new_scale.x)), max(0.01, min(1.0, new_scale.y)))
    
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
                    'pos_x': inst.pos.x,
                    'pos_y': inst.pos.y,
                    'rotation': inst.rotation
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
                    inst.pos = Vec2(new_x, new_y)  # setter handles clamping
                
                if should_rotate:
                    # Update rotation value
                    inst.rotation = (inst_cache['rotation'] + total_delta_degrees) % 360
    
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
                inst.rotation = (inst_cache['rotation'] + total_delta) % 360
            
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
                inst.pos = Vec2(temp_x + offset_x, temp_y + offset_y)  # setter handles clamping
    
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
                inst.pos = Vec2(inst_cache['pos_x'] + offset_x, inst_cache['pos_y'] + offset_y)  # setter handles clamping
    
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
                total_x += instance.pos.x
                total_y += instance.pos.y
            
            center_x = total_x / layer.instance_count
            center_y = total_y / layer.instance_count
            
            # Rotate each instance around center
            for i in range(layer.instance_count):
                instance = layer.get_instance(i, caller='CoA')
                
                # Rotate position around center
                new_x, new_y = self._rotate_point_around(
                    instance.pos.x, instance.pos.y,
                    center_x, center_y,
                    delta_degrees
                )
                instance.pos = Vec2(new_x, new_y)  # setter handles clamping
                
                # Rotate individual rotation
                instance.rotation += delta_degrees
            
            self._logger.debug(f"Rotated {layer.instance_count} instances of layer {uuid}: +{delta_degrees:.2f}°")
        else:
            # Single instance: rotate in place
            layer.rotation += delta_degrees
            self._logger.debug(f"Rotated layer {uuid}: +{delta_degrees:.2f}°")
    
    # ========================================
    # Flip Operations
    # ========================================
    
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
    
    def flip_selection(self, uuids: List[str], flip_x: bool = False, flip_y: bool = False):
        """Flip selected layers with automatic position mirroring for groups/multi-instance
        
        Single instance: Flips in place
        Multiple instances or multiple layers: Flips appearance AND mirrors positions around center
        
        Args:
            uuids: List of layer UUIDs
            flip_x: If True, toggle horizontal flip
            flip_y: If True, toggle vertical flip
            
        Raises:
            ValueError: If any UUID not found or empty list
        """
        if not uuids:
            raise ValueError("No layers selected")
        
        # Get all layers and validate
        layers = []
        for uuid in uuids:
            layer = self._layers.get_by_uuid(uuid)
            if not layer:
                raise ValueError(f"Layer with UUID '{uuid}' not found")
            layers.append(layer)
        
        # Check if we should orbit (mirror positions)
        # Orbit if: multiple layers OR single layer with multiple instances
        should_orbit = len(uuids) > 1 or (len(uuids) == 1 and layers[0].instance_count > 1)
        
        # Single instance of single layer: flip in place without position change
        if len(uuids) == 1 and layers[0].instance_count == 1:
            layer = layers[0]
            instance = layer.get_instance(0, caller='CoA.flip_selection')
            if flip_x:
                instance.flip_x = not instance.flip_x
            if flip_y:
                instance.flip_y = not instance.flip_y
        else:
            # Multiple layers or multi-instance: flip appearance AND mirror positions
            bounds = self.get_layers_bounds(uuids)
            center_x = (bounds['min_x'] + bounds['max_x']) / 2.0
            center_y = (bounds['min_y'] + bounds['max_y']) / 2.0
            
            for uuid, layer in zip(uuids, layers):
                # Toggle flip visual appearance for each instance individually
                for instance_idx in range(layer.instance_count):
                    instance = layer.get_instance(instance_idx, caller='CoA.flip_selection')
                    
                    # Toggle flip state
                    if flip_x:
                        instance.flip_x = not instance.flip_x
                    if flip_y:
                        instance.flip_y = not instance.flip_y
                    
                    # Mirror position around group center
                    current_x = instance.pos.x
                    current_y = instance.pos.y
                    
                    if flip_x:
                        offset_x = current_x - center_x
                        current_x = center_x - offset_x
                    
                    if flip_y:
                        offset_y = current_y - center_y
                        current_y = center_y - offset_y
                    
                    instance.pos = Vec2(current_x, current_y)
    
    # ========================================
    # Alignment/Movement Operations
    # ========================================
    
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
            positions = [self.get_layer_pos_x(uuid) for uuid in uuids]
            
            if alignment == 'left':
                target = min(positions)
            elif alignment == 'right':
                target = max(positions)
            else:  # center
                target = sum(positions) / len(positions)
            
            # Apply to each layer using set_layer_position (handles multi-instance correctly)
            for uuid in uuids:
                current_y = self.get_layer_pos_y(uuid)
                self.set_layer_position(uuid, target, current_y)
        
        # Vertical alignments
        else:
            positions = [self.get_layer_pos_y(uuid) for uuid in uuids]
            
            if alignment == 'top':
                target = min(positions)
            elif alignment == 'bottom':
                target = max(positions)
            else:  # middle
                target = sum(positions) / len(positions)
            
            # Apply to each layer using set_layer_position (handles multi-instance correctly)
            for uuid in uuids:
                current_x = self.get_layer_pos_x(uuid)
                self.set_layer_position(uuid, current_x, target)
    
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
            min_x = min(inst.pos.x for inst in instances)
            max_x = max(inst.pos.x for inst in instances)
            min_y = min(inst.pos.y for inst in instances)
            max_y = max(inst.pos.y for inst in instances)
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
    # Group Transform Operations
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
                layer.scale = Vec2(layer.scale.x * factor, layer.scale.y * factor)
                
                # Adjust position relative to center
                pos = layer.pos
                delta = Vec2(pos.x - center_x, pos.y - center_y)
                layer.pos = Vec2(center_x + delta.x * factor, center_y + delta.y * factor)
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
                instance.rotation += delta_degrees
            else:
                # Multiple instances: ferris wheel around layer center
                # Calculate layer center
                center_x = 0.0
                center_y = 0.0
                for i in range(layer.instance_count):
                    inst = layer.get_instance(i, caller='CoA')
                    center_x += inst.pos.x
                    center_y += inst.pos.y
                center_x /= layer.instance_count
                center_y /= layer.instance_count
                
                # Rotate each instance around center
                for i in range(layer.instance_count):
                    instance = layer.get_instance(i, caller='CoA')
                    new_x, new_y = self._rotate_point_around(
                        instance.pos.x, instance.pos.y,
                        center_x, center_y,
                        delta_degrees
                    )
                    instance.pos = Vec2(new_x, new_y)  # setter handles clamping
                    instance.rotation += delta_degrees
        
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
                    instance.pos.x, instance.pos.y,
                    center_x, center_y,
                    delta_degrees
                )
                instance.pos = Vec2(new_x, new_y)
                # rotation unchanged
            else:
                # Multiple instances: move layer center, keep instances relative
                # Calculate current layer center
                layer_x = 0.0
                layer_y = 0.0
                for i in range(layer.instance_count):
                    inst = layer.get_instance(i, caller='CoA')
                    layer_x += inst.pos.x
                    layer_y += inst.pos.y
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
                    instance.pos = Vec2(instance.pos.x + offset_x, instance.pos.y + offset_y)
                    # rotation unchanged
        
        self._logger.debug(f"Orbit only (shallow): {len(uuids)} layers, +{delta_degrees:.2f}°")
    
    def _both_shallow(self, uuids: List[str], layers: List, delta_degrees: float):
        """Both shallow mode: orbit AND rotate layers (shallow)"""
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
                instance.rotation += delta_degrees
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
        center_x = sum(inst.pos.x for inst in all_instances) / len(all_instances)
        center_y = sum(inst.pos.y for inst in all_instances) / len(all_instances)
        
        # Orbit each instance around center (no rotation change)
        for instance in all_instances:
            new_x, new_y = self._rotate_point_around(
                instance.pos.x, instance.pos.y,
                center_x, center_y,
                delta_degrees
            )
            instance.pos = Vec2(new_x, new_y)
        
        self._logger.debug(f"Orbit only (deep): {len(all_instances)} instances, +{delta_degrees:.2f}°")
    
    def _both_deep(self, uuids: List[str], layers: List, delta_degrees: float):
        """Both deep mode: orbit AND rotate all instances (deep mode)"""
        # Collect all instances as flat list
        all_instances = []
        for uuid in uuids:
            layer = self._layers.get_by_uuid(uuid)
            for i in range(layer.instance_count):
                instance = layer.get_instance(i, caller='CoA')
                all_instances.append(instance)
        
        # Calculate center of all instances
        center_x = sum(inst.pos.x for inst in all_instances) / len(all_instances)
        center_y = sum(inst.pos.y for inst in all_instances) / len(all_instances)
        
        # Orbit AND rotate each instance
        for instance in all_instances:
            new_x, new_y = self._rotate_point_around(
                instance.pos.x, instance.pos.y,
                center_x, center_y,
                delta_degrees
            )
            instance.pos = Vec2(new_x, new_y)
            instance.rotation += delta_degrees
        
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
            pos = layer.pos
            new_x, new_y = self._rotate_point_around(
                pos.x, pos.y,
                center_x, center_y,
                delta_degrees
            )
            layer.pos = Vec2(new_x, new_y)
            
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
                total_x += instance.pos.x
                total_y += instance.pos.y
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
                    instance.pos.x, instance.pos.y,
                    group_center_x, group_center_y,
                    delta_degrees
                )
                instance.pos = Vec2(new_x, new_y)
                instance.rotation += delta_degrees
            else:
                # Multiple instances: calculate this layer's center
                layer_x = 0.0
                layer_y = 0.0
                for i in range(layer.instance_count):
                    inst = layer.get_instance(i, caller='CoA')
                    layer_x += inst.pos.x
                    layer_y += inst.pos.y
                
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
                    instance.pos = Vec2(instance.pos.x + offset_x, instance.pos.y + offset_y)
                    
                    # Then ferris wheel around new layer center
                    rotated_x, rotated_y = self._rotate_point_around(
                        instance.pos.x, instance.pos.y,
                        new_layer_center_x, new_layer_center_y,
                        delta_degrees
                    )
                    instance.pos = Vec2(rotated_x, rotated_y)
                    instance.rotation += delta_degrees
    
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
                    'pos_x': layer.pos.x,
                    'pos_y': layer.pos.y,
                    'scale_x': layer.scale.x,
                    'scale_y': layer.scale.y,
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
            layer.pos = Vec2(pos_x, layer.pos.y if pos_y is None else pos_y)
        elif pos_y is not None:
            layer.pos = Vec2(layer.pos.x, pos_y)
            
        if scale_x is not None:
            layer.scale = Vec2(scale_x, layer.scale.y if scale_y is None else scale_y)
        elif scale_y is not None:
            layer.scale = Vec2(layer.scale.x, scale_y)
            
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
