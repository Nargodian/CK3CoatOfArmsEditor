"""Transform handling mixin for CanvasArea - refactored from 243-line monolith"""
import math


class CanvasAreaTransformMixin:
	"""Handles transform widget interactions and coordinate conversions"""
	
	def _convert_widget_to_coa_coords(self, center_x, center_y, half_w, half_h):
		"""Convert transform widget coordinates to CoA space.
		
		Args:
			center_x: X in widget center-origin space
			center_y: Y in widget center-origin space
			half_w: Half-width in pixels
			half_h: Half-height in pixels
			
		Returns:
			(pos_x, pos_y, scale_x, scale_y) in CoA space
		"""
		# Convert from center-origin to top-left coordinates
		center_x_topleft = center_x + self.canvas_widget.width() / 2
		center_y_topleft = center_y + self.canvas_widget.height() / 2
		
		# Convert canvas pixels to CoA space
		pos_x, pos_y = self.canvas_widget.canvas_to_coa(center_x_topleft, center_y_topleft)
		scale_x, scale_y = self.canvas_widget.pixels_to_coa_scale(half_w, half_h)
		
		return pos_x, pos_y, scale_x, scale_y
	
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
	
	def _handle_single_instance_transform(self, uuid, pos_x, pos_y, scale_x, scale_y, rotation):
		"""Handle direct transform for single-instance layer.
		
		Args:
			uuid: Layer UUID
			pos_x, pos_y: Position in CoA space
			scale_x, scale_y: Scale in CoA space
			rotation: Rotation angle in degrees
		"""
		self.main_window.coa.set_layer_position(uuid, pos_x, pos_y)
		self.main_window.coa.set_layer_scale(uuid, scale_x, scale_y)
		self.main_window.coa.set_layer_rotation(uuid, rotation)
		self.canvas_widget.update()
	
	def _handle_multi_instance_transform(self, uuid, pos_x, pos_y, scale_x, scale_y, rotation):
		"""Handle group transform for multi-instance layer (AABB-based).
		
		Args:
			uuid: Layer UUID
			pos_x, pos_y: New AABB center in CoA space
			scale_x, scale_y: New AABB size in CoA space
			rotation: Rotation delta in degrees
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
		scale_factor_x = scale_x / original_width if original_width > 0.001 else 1.0
		scale_factor_y = scale_y / original_height if original_height > 0.001 else 1.0
		
		# Calculate rotation delta
		rotation_delta = rotation - self._initial_instance_rotation
		
		# Apply group transform using CoA method (uses cached original positions)
		self.main_window.coa.transform_instances_as_group(
			uuid, pos_x, pos_y, scale_factor_x, scale_factor_y, rotation_delta
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
				# Single instance: use cached transform
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
	
	def _apply_multi_selection_transform(self, pos_x, pos_y, scale_x, scale_y, rotation):
		"""Apply group transform to all selected layers.
		
		Args:
			pos_x, pos_y: New group center in CoA space
			scale_x, scale_y: New group size in CoA space
			rotation: Rotation angle in degrees
		"""
		# Use cached original AABB
		original_center_x = self._drag_start_aabb['center_x']
		original_center_y = self._drag_start_aabb['center_y']
		original_scale_x = self._drag_start_aabb['scale_x']
		original_scale_y = self._drag_start_aabb['scale_y']
		
		# Calculate transform deltas
		position_delta_x = pos_x - original_center_x
		position_delta_y = pos_y - original_center_y
		rotation_delta = rotation - getattr(self, '_initial_group_rotation', 0)
		
		# Apply transforms to all selected layers
		for layer_state in self._drag_start_layers:
			uuid = layer_state['uuid']
			
			# Get original positions from cache
			pos_x_orig = layer_state['pos_x']
			pos_y_orig = layer_state['pos_y']
			scale_x_orig = layer_state['scale_x']
			scale_y_orig = layer_state['scale_y']
			
			# Calculate offset from original group center
			offset_x = pos_x_orig - original_center_x
			offset_y = pos_y_orig - original_center_y
			
			# Calculate new position and scale based on transform type
			if self.transform_widget.is_rotating:
				new_pos_x, new_pos_y, new_scale_x, new_scale_y = self._apply_rotation_to_layer(
					offset_x, offset_y, scale_x_orig, scale_y_orig,
					rotation_delta, original_center_x, original_center_y, position_delta_x, position_delta_y
				)
			else:
				new_pos_x, new_pos_y, new_scale_x, new_scale_y = self._apply_scale_to_layer(
					offset_x, offset_y, scale_x_orig, scale_y_orig,
					original_scale_x, original_scale_y, scale_x, scale_y,
					original_center_x, original_center_y, position_delta_x, position_delta_y
				)
			
			# Clamp positions to valid range
			new_pos_x = max(0.0, min(1.0, new_pos_x))
			new_pos_y = max(0.0, min(1.0, new_pos_y))
			
			# Clamp scales (but not during rotation)
			if not self.transform_widget.is_rotating:
				new_scale_x = max(0.01, min(1.0, new_scale_x))
				new_scale_y = max(0.01, min(1.0, new_scale_y))
			
			# Update layer
			self._update_layer_transform(
				uuid, new_pos_x, new_pos_y, new_scale_x, new_scale_y,
				scale_x_orig, scale_y_orig, layer_state.get('is_multi_instance', False)
			)
		
		# Update canvas for live preview
		self.canvas_widget.update()
	
	def _apply_rotation_to_layer(self, offset_x, offset_y, scale_x, scale_y,
	                              rotation_delta, center_x, center_y, delta_x, delta_y):
		"""Apply rotation to a layer's offset (ferris wheel behavior).
		
		Returns:
			(new_pos_x, new_pos_y, new_scale_x, new_scale_y)
		"""
		# Rotate offset around group center
		rotation_rad = math.radians(rotation_delta)
		cos_r = math.cos(rotation_rad)
		sin_r = math.sin(rotation_rad)
		new_offset_x = offset_x * cos_r - offset_y * sin_r
		new_offset_y = offset_x * sin_r + offset_y * cos_r
		
		# Apply position delta
		new_pos_x = center_x + new_offset_x + delta_x
		new_pos_y = center_y + new_offset_y + delta_y
		
		# Keep scales unchanged during rotation
		return new_pos_x, new_pos_y, scale_x, scale_y
	
	def _apply_scale_to_layer(self, offset_x, offset_y, scale_x, scale_y,
	                           orig_group_scale_x, orig_group_scale_y,
	                           new_group_scale_x, new_group_scale_y,
	                           center_x, center_y, delta_x, delta_y):
		"""Apply scale/position transform to a layer.
		
		Returns:
			(new_pos_x, new_pos_y, new_scale_x, new_scale_y)
		"""
		# Calculate scale factors
		scale_factor_x = new_group_scale_x / orig_group_scale_x if orig_group_scale_x > 0.001 else 1.0
		scale_factor_y = new_group_scale_y / orig_group_scale_y if orig_group_scale_y > 0.001 else 1.0
		
		# Scale offset
		new_offset_x = offset_x * scale_factor_x
		new_offset_y = offset_y * scale_factor_y
		
		# Apply position delta
		new_pos_x = center_x + new_offset_x + delta_x
		new_pos_y = center_y + new_offset_y + delta_y
		
		# Scale layer size
		new_scale_x = scale_x * scale_factor_x
		new_scale_y = scale_y * scale_factor_y
		
		return new_pos_x, new_pos_y, new_scale_x, new_scale_y
	
	def _update_layer_transform(self, uuid, pos_x, pos_y, scale_x, scale_y,
	                             orig_scale_x, orig_scale_y, is_multi_instance):
		"""Update a single layer's transform in the CoA model.
		
		Args:
			uuid: Layer UUID
			pos_x, pos_y: New position
			scale_x, scale_y: New scale
			orig_scale_x, orig_scale_y: Original scale (for multi-instance)
			is_multi_instance: Whether this is a multi-instance layer
		"""
		if is_multi_instance:
			# Multi-instance layer: transform all instances as a group
			scale_factor_x = scale_x / orig_scale_x if orig_scale_x > 0.001 else 1.0
			scale_factor_y = scale_y / orig_scale_y if orig_scale_y > 0.001 else 1.0
			
			# Begin instance transform if not already begun
			if uuid not in self._instance_transforms:
				self.main_window.coa.begin_instance_group_transform(uuid)
				self._instance_transforms.add(uuid)
			
			self.main_window.coa.transform_instances_as_group(
				uuid, pos_x, pos_y, scale_factor_x, scale_factor_y, 0.0
			)
		else:
			# Single instance layer: direct transform
			self.main_window.coa.set_layer_position(uuid, pos_x, pos_y)
			self.main_window.coa.set_layer_scale(uuid, scale_x, scale_y)
	
	def _handle_multi_selection_transform(self, pos_x, pos_y, scale_x, scale_y, rotation, selected_uuids):
		"""Handle group transform for multiple selected layers.
		
		Args:
			pos_x, pos_y: New group center in CoA space
			scale_x, scale_y: New group size in CoA space
			rotation: Rotation angle in degrees
			selected_uuids: List of selected layer UUIDs
		"""
		# Initialize cache on first call
		if self._drag_start_layers is None:
			self._init_multi_selection_cache(list(selected_uuids))
		
		# Apply transform to all layers
		self._apply_multi_selection_transform(pos_x, pos_y, scale_x, scale_y, rotation)
