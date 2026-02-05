"""Coordinate transformation mixin for canvas widget.

Provides atomic and composite coordinate transformation methods:
- Atomic: Single-step conversions between coordinate spaces
- Composite: Chained conversions for convenience

Coordinate spaces:
- CoA: 0-1 normalized space (0.5 is center)
- Frame: CoA space with frame scale/offset applied
- Canvas: Qt pixel coordinates with zoom/pan applied
"""
from models.transform import Transform


class CanvasCoordinateMixin:
	"""Mixin providing coordinate transformation methods.
	
	Requires the following from the parent class:
	- self.get_frame_transform() -> (scale_tuple, offset_tuple)
	- self.zoom_level (float)
	- self.pan_x, self.pan_y (float)
	- self.width(), self.height() (methods returning int)
	"""
	
	# ========================================
	# Origin conversions (geometric helpers)
	# ========================================
	
	def center_origin_to_topleft(self, center_x, center_y):
		"""Convert center-origin coordinates to top-left origin.
		
		Args:
			center_x: X in center-origin space (0 at center)
			center_y: Y in center-origin space (0 at center)
			
		Returns:
			(topleft_x, topleft_y): Top-left pixel coordinates
		"""
		half_width = self.width() / 2
		half_height = self.height() / 2
		topleft_x = center_x + half_width
		topleft_y = center_y + half_height
		return topleft_x, topleft_y
	
	def topleft_to_center_origin(self, topleft_x, topleft_y):
		"""Convert top-left origin to center-origin coordinates.
		
		Args:
			topleft_x: X in top-left origin space
			topleft_y: Y in top-left origin space
			
		Returns:
			(center_x, center_y): Center-origin coordinates (0 at center)
		"""
		half_width = self.width() / 2
		half_height = self.height() / 2
		center_x = topleft_x - half_width
		center_y = topleft_y - half_height
		return center_x, center_y
	
	# ========================================
	# Atomic transformations (single-step conversions)
	# ========================================
	
	def coa_to_frame(self, pos_x, pos_y):
		"""Convert CoA space to frame-adjusted space.
		
		Applies frame scale and offset only.
		
		Args:
			pos_x: CoA X position (0-1)
			pos_y: CoA Y position (0-1)
			
		Returns:
			(frame_x, frame_y): Frame-adjusted position
		"""
		frame_scale, frame_offset = self.get_frame_transform()
		
		# Center position (move to origin)
		centered_x = pos_x - 0.5
		centered_y = pos_y - 0.5
		
		# Apply frame scale
		scaled_x = centered_x * frame_scale[0]
		scaled_y = centered_y * frame_scale[1]
		
		# Move back from origin
		uncentered_x = scaled_x + 0.5
		uncentered_y = scaled_y + 0.5
		
		# Apply frame offset
		frame_x = uncentered_x - frame_offset[0] * frame_scale[0]
		frame_y = uncentered_y - frame_offset[1] * frame_scale[1]
		
		return frame_x, frame_y
	
	def frame_to_coa(self, frame_x, frame_y):
		"""Convert frame-adjusted space to CoA space.
		
		Removes frame scale and offset.
		
		Args:
			frame_x: Frame-adjusted X position
			frame_y: Frame-adjusted Y position
			
		Returns:
			(pos_x, pos_y): CoA position (0-1)
		"""
		frame_scale, frame_offset = self.get_frame_transform()
		
		# Remove frame offset
		no_offset_x = frame_x + frame_offset[0] * frame_scale[0]
		no_offset_y = frame_y + frame_offset[1] * frame_scale[1]
		
		# Center position (move to origin)
		centered_x = no_offset_x - 0.5
		centered_y = no_offset_y - 0.5
		
		# Remove frame scale
		unscaled_x = centered_x / frame_scale[0]
		unscaled_y = centered_y / frame_scale[1]
		
		# Move back from origin
		pos_x = unscaled_x + 0.5
		pos_y = unscaled_y + 0.5
		
		return pos_x, pos_y
	
	def frame_to_canvas(self, frame_x, frame_y, clamp=False):
		"""Convert frame space to canvas pixel coordinates.
		
		Applies zoom, pan, and viewport scaling.
		
		Args:
			frame_x: Frame-adjusted X position
			frame_y: Frame-adjusted Y position
			clamp: If True, clamp result to canvas bounds
			
		Returns:
			(x, y): Canvas pixel coordinates
		"""
		# Convert to OpenGL coords
		gl_x = frame_x * 2.0 - 1.0
		gl_y = -(frame_y * 2.0 - 1.0)  # Invert Y
		
		# Get current canvas size
		width, height = self.width(), self.height()
		canvas_size = min(width, height)
		
		# Convert to canvas pixels with zoom (pure pixel-based)
		pixel_x = gl_x * (canvas_size / 2) * self.zoom_level
		pixel_y = gl_y * (canvas_size / 2) * self.zoom_level
		
		# Canvas center + pan
		x = width / 2 + pixel_x + self.pan_x
		y = height / 2 - pixel_y + self.pan_y  # Qt Y-down
		
		if clamp:
			x = max(0, min(width, x))
			y = max(0, min(height, y))
		
		return x, y
	
	def canvas_to_frame(self, x, y):
		"""Convert canvas pixel coordinates to frame space.
		
		Removes zoom, pan, and viewport scaling.
		
		Args:
			x: Canvas pixel X coordinate
			y: Canvas pixel Y coordinate
			
		Returns:
			(frame_x, frame_y): Frame-adjusted position
		"""
		# Get current canvas size
		width, height = self.width(), self.height()
		canvas_size = min(width, height)
		
		# Remove pan and center offset
		pixel_x = x - width / 2 - self.pan_x
		pixel_y = y - height / 2 - self.pan_y
		
		# Convert to OpenGL normalized space (pure pixel-based)
		gl_x = pixel_x / (canvas_size / 2) / self.zoom_level
		gl_y = -pixel_y / (canvas_size / 2) / self.zoom_level
		
		# Convert to frame space
		frame_x = (gl_x + 1.0) / 2.0
		frame_y = (-gl_y + 1.0) / 2.0
		
		return frame_x, frame_y
	
	# ========================================
	# Composite transformations (chained conversions)
	# ========================================
	
	def coa_to_canvas(self, pos_x, pos_y, clamp=False):
		"""Convert CoA space (0-1) to canvas pixel coordinates.
		
		Applies frame transforms, zoom, pan, and viewport scaling.
		Fetches all state (zoom, pan, size, frame) from self.
		
		Args:
			pos_x: CoA X position (0-1, where 0.5 is center)
			pos_y: CoA Y position (0-1, where 0.5 is center)
			clamp: If True, clamp result to canvas bounds
			
		Returns:
			(x, y): Canvas pixel coordinates
		"""
		frame_x, frame_y = self.coa_to_frame(pos_x, pos_y)
		return self.frame_to_canvas(frame_x, frame_y, clamp)
	
	def canvas_to_coa(self, x, y, clamp=False):
		"""Convert canvas pixel coordinates to CoA space (0-1).
		
		Reverses zoom, pan, viewport scaling, and frame transforms.
		Fetches all state from self.
		
		Args:
			x: Canvas pixel X coordinate
			y: Canvas pixel Y coordinate
			clamp: If True, clamp result to 0-1 range
			
		Returns:
			(pos_x, pos_y): CoA position (0-1 range)
		"""
		frame_x, frame_y = self.canvas_to_frame(x, y)
		pos_x, pos_y = self.frame_to_coa(frame_x, frame_y)
		
		if clamp:
			pos_x = max(0.0, min(1.0, pos_x))
			pos_y = max(0.0, min(1.0, pos_y))
		
		return pos_x, pos_y
	
	# ========================================
	# Scale transformations (atomic + composite)
	# ========================================
	
	def coa_scale_to_frame_scale(self, scale_x, scale_y):
		"""Convert CoA scale to frame-adjusted scale.
		
		Args:
			scale_x: CoA scale multiplier (1.0 = normal size)
			scale_y: CoA scale multiplier (1.0 = normal size)
			
		Returns:
			(frame_scale_x, frame_scale_y): Frame-adjusted scale multipliers
		"""
		frame_scales, _ = self.get_frame_transform()
		return scale_x * frame_scales[0], scale_y * frame_scales[1]
	
	def frame_scale_to_pixels(self, frame_scale_x, frame_scale_y):
		"""Convert frame-adjusted scale to pixel AABB half-dimensions.
		
		Args:
			frame_scale_x: Frame-adjusted scale multiplier
			frame_scale_y: Frame-adjusted scale multiplier
			
		Returns:
			(half_w, half_h): Pixel radius of AABB (half width, half height)
		"""
		from components.canvas_widget_NEW import COA_BASE_SIZE_PX
		
		half_w = abs(frame_scale_x) * COA_BASE_SIZE_PX * self.zoom_level / 2.0
		half_h = abs(frame_scale_y) * COA_BASE_SIZE_PX * self.zoom_level / 2.0
		
		return half_w, half_h
	
	def coa_scale_to_pixels(self, scale_x, scale_y):
		"""Convert CoA scale to pixel AABB half-dimensions (composite).
		
		Chains coa_scale_to_frame_scale() → frame_scale_to_pixels()
		
		Args:
			scale_x: CoA scale multiplier (1.0 = normal size)
			scale_y: CoA scale multiplier (1.0 = normal size)
			
		Returns:
			(half_w, half_h): Pixel radius of AABB
		"""
		frame_scale_x, frame_scale_y = self.coa_scale_to_frame_scale(scale_x, scale_y)
		return self.frame_scale_to_pixels(frame_scale_x, frame_scale_y)
	
	def coa_to_transform_widget(self, coa_transform):
		"""Convert CoA space to transform widget center-origin coordinates.
		
		Combines position + scale conversion and applies center-origin shift
		for transform widget (which uses center=0,0 coordinate system).
		
		Args:
			coa_transform: Transform in CoA space (0-1 normalized)
			
		Returns:
			Transform in widget pixel space (center-origin)
		"""
		# Convert to canvas top-left pixels
		canvas_x, canvas_y = self.coa_to_canvas(coa_transform.pos_x, coa_transform.pos_y)
		half_w, half_h = self.coa_scale_to_pixels(coa_transform.scale_x, coa_transform.scale_y)
		
		# Shift to center-origin (transform widget coordinate system)
		center_x = canvas_x - self.width() / 2
		center_y = canvas_y - self.height() / 2
		
		return Transform(center_x, center_y, half_w, half_h, coa_transform.rotation)
	
	def pixels_to_frame_scale(self, half_w, half_h):
		"""Convert pixel AABB half-dimensions to frame-adjusted scale.
		
		Args:
			half_w: Pixel AABB half-width
			half_h: Pixel AABB half-height
			
		Returns:
			(frame_scale_x, frame_scale_y): Frame-adjusted scale multipliers
		"""
		from components.canvas_widget_NEW import COA_BASE_SIZE_PX
		
		frame_scale_x = (half_w * 2.0) / (COA_BASE_SIZE_PX * self.zoom_level)
		frame_scale_y = (half_h * 2.0) / (COA_BASE_SIZE_PX * self.zoom_level)
		
		return frame_scale_x, frame_scale_y
	
	def frame_scale_to_coa_scale(self, frame_scale_x, frame_scale_y):
		"""Convert frame-adjusted scale back to CoA scale.
		
		Args:
			frame_scale_x: Frame-adjusted scale multiplier
			frame_scale_y: Frame-adjusted scale multiplier
			
		Returns:
			(scale_x, scale_y): CoA scale multipliers (1.0 = normal)
		"""
		frame_scales, _ = self.get_frame_transform()
		return frame_scale_x / frame_scales[0], frame_scale_y / frame_scales[1]
	
	def pixels_to_coa_scale(self, half_w, half_h):
		"""Convert pixel AABB half-dimensions to CoA scale (composite).
		
		Chains pixels_to_frame_scale() → frame_scale_to_coa_scale()
		
		Args:
			half_w: Pixel AABB half-width
			half_h: Pixel AABB half-height
			
		Returns:
			(scale_x, scale_y): CoA scale multipliers (1.0 = normal)
		"""
		frame_scale_x, frame_scale_y = self.pixels_to_frame_scale(half_w, half_h)
		return self.frame_scale_to_coa_scale(frame_scale_x, frame_scale_y)
