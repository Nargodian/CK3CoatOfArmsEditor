"""Transform handling mixin for CanvasArea - thin coordinator that delegates to CoA model"""
from models.transform import Transform, Vec2


class CanvasAreaTransformMixin:
    """Handles transform widget interactions and coordinate conversions"""
    
    def _convert_widget_to_coa_coords(self, widget_transform, is_aabb_dimension=False):
        """Convert transform widget coordinates to CoA space.
        
        Args:
            widget_transform: Transform in widget pixel space (center-origin)
            is_aabb_dimension: If True, scale represents AABB dimensions (no frame compensation)
            
        Returns:
            Transform in CoA space (0-1 normalized)
        """
        # Convert origin (transform widget uses center, canvas_to_coa expects top-left)
        topleft_pos = self.canvas_widget.center_origin_to_topleft(widget_transform.pos)
        
        # Convert pixels to CoA space
        coa_pos = self.canvas_widget.canvas_to_coa(topleft_pos)
        
        if is_aabb_dimension:
            # AABB dimensions: convert pixels directly to CoA space dimensions
            # without frame compensation (matches coa_to_transform_widget AABB path)
            from components.canvas_widget import COA_BASE_SIZE_PX
            zoom = self.canvas_widget.zoom_level
            scale_x = (widget_transform.scale.x * 2.0) / (COA_BASE_SIZE_PX * zoom)
            scale_y = (widget_transform.scale.y * 2.0) / (COA_BASE_SIZE_PX * zoom)
        else:
            # Instance scale multipliers: apply frame compensation
            scale_x, scale_y = self.canvas_widget.pixels_to_coa_scale(
                widget_transform.scale.x, widget_transform.scale.y
            )
        
        return Transform(Vec2(coa_pos.x, coa_pos.y), Vec2(scale_x, scale_y), widget_transform.rotation)
    
    def _handle_rotation_transform(self, selected_uuids, rotation):
        """Handle rotation-only transforms (rotation handle dragged).
        
        Args:
            selected_uuids: List of selected layer UUIDs
            rotation: Current rotation angle in degrees
        """
        # First rotation frame - cache state
        if not hasattr(self, '_rotation_start') or self._rotation_start is None:
            self._rotation_start = rotation
            rotation_mode = self.get_rotation_mode()
            self.main_window.coa.begin_rotation_transform(list(selected_uuids), rotation_mode)
        
        # Calculate TOTAL delta from start
        total_delta = rotation - self._rotation_start
        
        # Apply rotation from cached state (prevents compounding)
        self.main_window.coa.apply_rotation_transform(list(selected_uuids), total_delta)
        
        # Update canvas for live preview
        self.canvas_widget.update()
    
    def _handle_single_instance_transform(self, uuid, coa_transform):
        """Handle direct transform for single-instance layer.
        
        Args:
            uuid: Layer UUID
            coa_transform: Transform in CoA space (0-1 normalized)
        """
        self.main_window.coa.set_layer_position(uuid, coa_transform.pos.x, coa_transform.pos.y)
        self.main_window.coa.set_layer_scale(uuid, coa_transform.scale.x, coa_transform.scale.y)
        self.main_window.coa.set_layer_rotation(uuid, coa_transform.rotation)
        self.canvas_widget.update()
    
    def _handle_multi_instance_transform(self, uuid, coa_transform):
        """Handle group transform for multi-instance layer (AABB-based).
        
        Args:
            uuid: Layer UUID
            coa_transform: Transform in CoA space (pos/scale are AABB center/size)
        """
        # Cache initial AABB at drag start
        if not hasattr(self, '_single_layer_aabb') or self._single_layer_aabb is None:
            # Begin caching in CoA
            self.main_window.coa.begin_instance_group_transform(uuid)
            
            bounds = self.main_window.coa.get_layer_bounds(uuid)
            self._single_layer_aabb = {
                'center_x': bounds['center_x'],
                'center_y': bounds['center_y'],
                'width': bounds['width'],
                'height': bounds['height']
            }
            self._initial_instance_rotation = 0  # Widget starts at 0 for group
        
        # Calculate transform relative to CACHED original AABB
        original_center_x = self._single_layer_aabb['center_x']
        original_center_y = self._single_layer_aabb['center_y']
        original_width = self._single_layer_aabb['width']
        original_height = self._single_layer_aabb['height']
        
        # Calculate scale factors
        scale_factor_x = coa_transform.scale.x / original_width if original_width > 0.001 else 1.0
        scale_factor_y = coa_transform.scale.y / original_height if original_height > 0.001 else 1.0
        
        # Calculate rotation delta
        rotation_delta = coa_transform.rotation - self._initial_instance_rotation
        
        # Apply group transform using CoA method (uses cached original positions)
        self.main_window.coa.transform_instances_as_group(
            uuid, coa_transform.pos.x, coa_transform.pos.y, scale_factor_x, scale_factor_y, rotation_delta
        )
        self.canvas_widget.update()
    
    def _init_multi_selection_cache(self, selected_uuids):
        """Initialize cache for multi-selection group transform.
        
        Args:
            selected_uuids: List of selected layer UUIDs
        """
        # Begin transform group in CoA (caches original states)
        self.main_window.coa.begin_transform_group(selected_uuids)
        
        self._drag_start_layers = []
        self._aabb_synced = False
        
        for uuid in selected_uuids:
            # For multi-instance layers, use AABB bounds instead of first instance
            instance_count = self.main_window.coa.get_layer_instance_count(uuid)
            if instance_count > 1:
                # Multi-instance: use layer's AABB
                bounds = self.main_window.coa.get_layer_bounds(uuid)
                self._drag_start_layers.append({
                    'uuid': uuid,
                    'pos_x': bounds['center_x'],
                    'pos_y': bounds['center_y'],
                    'scale_x': bounds['width'],
                    'scale_y': bounds['height'],
                    'is_multi_instance': True
                })
            else:
                # Single instance: use cached transform (AABB ignores rotation)
                cached = self.main_window.coa.get_cached_transform(uuid)
                if cached:
                    self._drag_start_layers.append({
                        'uuid': uuid,
                        'pos_x': cached['pos_x'],
                        'pos_y': cached['pos_y'],
                        'scale_x': cached['scale_x'],
                        'scale_y': cached['scale_y'],
                        'is_multi_instance': False
                    })
        
        # Calculate and cache the original group AABB
        self._drag_start_aabb = self._calculate_group_aabb(self._drag_start_layers)
    
    def _calculate_group_aabb(self, layer_states):
        """Calculate AABB for a group of layers.
        
        Args:
            layer_states: List of dicts with pos_x, pos_y, scale_x, scale_y
            
        Returns:
            Dict with center_x, center_y, scale_x, scale_y
        """
        min_x = float('inf')
        max_x = float('-inf')
        min_y = float('inf')
        max_y = float('-inf')
        
        for state in layer_states:
            pos_x = state['pos_x']
            pos_y = state['pos_y']
            scale_x = state['scale_x']
            scale_y = state['scale_y']
            
            # Scales are always positive (flip is separate)
            layer_min_x = pos_x - scale_x / 2
            layer_max_x = pos_x + scale_x / 2
            layer_min_y = pos_y - scale_y / 2
            layer_max_y = pos_y + scale_y / 2
            
            min_x = min(min_x, layer_min_x)
            max_x = max(max_x, layer_max_x)
            min_y = min(min_y, layer_min_y)
            max_y = max(max_y, layer_max_y)
        
        return {
            'center_x': (min_x + max_x) / 2,
            'center_y': (min_y + max_y) / 2,
            'scale_x': max_x - min_x,
            'scale_y': max_y - min_y
        }
    
    def _apply_multi_selection_transform(self, coa_transform):
        """Apply group transform to all selected layers.
        
        Delegates all geometric math to CoA - mixin only does coordinate conversion.
        
        Args:
            coa_transform: Transform in CoA space (group AABB)
        """
        selected_uuids = list(self._drag_start_aabb.keys()) if hasattr(self, '_drag_start_aabb') and isinstance(self._drag_start_aabb, dict) else [layer['uuid'] for layer in self._drag_start_layers]
        
        # Get original AABB
        original_center_x = self._drag_start_aabb['center_x']
        original_center_y = self._drag_start_aabb['center_y']
        original_scale_x = self._drag_start_aabb['scale_x']
        original_scale_y = self._drag_start_aabb['scale_y']
        
        # Calculate scale factors
        scale_factor_x = coa_transform.scale.x / original_scale_x if original_scale_x > 0.001 else 1.0
        scale_factor_y = coa_transform.scale.y / original_scale_y if original_scale_y > 0.001 else 1.0
        
        # Calculate position delta
        position_delta_x = coa_transform.pos.x - original_center_x
        position_delta_y = coa_transform.pos.y - original_center_y
        
        # Apply transforms per layer using CoA methods with cached state
        for layer_state in self._drag_start_layers:
            uuid = layer_state['uuid']
            cached = self.main_window.coa.get_cached_transform(uuid)
            if not cached:
                continue
            
            # Calculate ferris wheel transform: offset from center, scale it, translate it
            offset_x = cached['pos_x'] - original_center_x
            offset_y = cached['pos_y'] - original_center_y
            
            new_offset_x = offset_x * scale_factor_x
            new_offset_y = offset_y * scale_factor_y
            
            new_pos_x = original_center_x + new_offset_x + position_delta_x
            new_pos_y = original_center_y + new_offset_y + position_delta_y
            new_scale_x = cached['scale_x'] * scale_factor_x
            new_scale_y = cached['scale_y'] * scale_factor_y
            
            # Conditional widget-level clamping: only for single layer + single instance
            # (Model always enforces clamping, this is UI convenience)
            if len(self._drag_start_layers) == 1 and not layer_state.get('is_multi_instance', False):
                new_pos_x = max(0.0, min(1.0, new_pos_x))
                new_pos_y = max(0.0, min(1.0, new_pos_y))
                new_scale_x = max(0.01, min(1.0, new_scale_x))
                new_scale_y = max(0.01, min(1.0, new_scale_y))
            
            # Apply using CoA method
            if layer_state.get('is_multi_instance', False):
                # Multi-instance: use instance group transform
                bounds = self.main_window.coa.get_layer_bounds(uuid)
                orig_scale_x = bounds['width']
                orig_scale_y = bounds['height']
                inst_scale_factor_x = new_scale_x / orig_scale_x if orig_scale_x > 0.001 else 1.0
                inst_scale_factor_y = new_scale_y / orig_scale_y if orig_scale_y > 0.001 else 1.0
                
                if uuid not in self._instance_transforms:
                    self.main_window.coa.begin_instance_group_transform(uuid)
                    self._instance_transforms.add(uuid)
                
                self.main_window.coa.transform_instances_as_group(
                    uuid, new_pos_x, new_pos_y, inst_scale_factor_x, inst_scale_factor_y, 0.0
                )
            else:
                # Single instance: direct set
                self.main_window.coa.apply_transform_group(uuid, new_pos_x, new_pos_y, new_scale_x, new_scale_y, None)
        
        # Update canvas
        self.canvas_widget.update()
    
    def _handle_multi_selection_transform(self, coa_transform, selected_uuids):
        """Handle group transform for multiple selected layers.
        
        Args:
            coa_transform: Transform in CoA space (group AABB)
            selected_uuids: List of selected layer UUIDs
        """
        # Initialize cache on first call
        if self._drag_start_layers is None:
            self._init_multi_selection_cache(list(selected_uuids))
        
        # Apply transform to all layers
        self._apply_multi_selection_transform(coa_transform)
