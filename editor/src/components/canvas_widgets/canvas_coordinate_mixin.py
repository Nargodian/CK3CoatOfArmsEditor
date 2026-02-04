"""Coordinate transformation mixin for canvas widget.

Provides atomic and composite coordinate transformation methods:
- Atomic: Single-step conversions between coordinate spaces
- Composite: Chained conversions for convenience

Coordinate spaces:
- CoA: 0-1 normalized space (0.5 is center)
- Frame: CoA space with frame scale/offset applied
- Canvas: Qt pixel coordinates with zoom/pan applied
"""


class CanvasCoordinateMixin:
	"""Mixin providing coordinate transformation methods.
	
	Requires the following from the parent class:
	- self.get_frame_transform() -> (scale_tuple, offset_tuple)
	- self.zoom_level (float)
	- self.pan_x, self.pan_y (float)
	- self.width(), self.height() (methods returning int)
	"""
	
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
