"""Coordinate transformation utilities for canvas rendering.

Provides conversion between different coordinate systems:
- Layer space (0-1 range, Y-down)
- OpenGL NDC (-1 to +1, Y-up)
- Qt widget pixels (Y-down)
- Frame-adjusted space
"""

def layer_pos_to_opengl_coords(pos_x, pos_y):
	"""Convert layer position (0-1 range) to OpenGL normalized coordinates.
	
	CK3 uses Y-down (0=top, 1=bottom), OpenGL uses Y-up (positive=up).
	We invert Y when converting to OpenGL coordinates.
	
	Args:
		pos_x: Layer X position (0-1, where 0.5 is center)
		pos_y: Layer Y position (0-1, where 0.5 is center, 0=top in CK3)
		
	Returns:
		(gl_x, gl_y): OpenGL coordinates in normalized device coordinates (-1 to +1)
	"""
	gl_x = pos_x * 2.0 - 1.0  # Map [0,1] to [-1,+1]
	gl_y = -(pos_y * 2.0 - 1.0)  # Invert: CK3 Y-down to OpenGL Y-up
	return gl_x, gl_y


def layer_pos_to_qt_pixels(pos_x, pos_y, canvas_size, offset_x=0, offset_y=0, zoom_level=1.0, pan_x=0.0, pan_y=0.0, viewport_base_size=0.8, composite_scale=0.75):
	"""Convert layer position (0-1 range) to Qt widget pixel coordinates.
	
	Args:
		pos_x: Layer X position (0-1, where 0.5 is center)
		pos_y: Layer Y position (0-1, where 0.5 is center)
		canvas_size: Size of the canvas square in pixels (min of width/height)
		offset_x: X offset of canvas within parent widget
		offset_y: Y offset of canvas within parent widget
		zoom_level: Canvas zoom level (default 1.0)
		pan_x: Pan offset in pixels (horizontal)
		pan_y: Pan offset in pixels (vertical)
		viewport_base_size: Base size as fraction of viewport (default 0.8)
		composite_scale: Scale factor for CoA composite (default 0.75)
		
	Returns:
		(qt_x, qt_y): Qt pixel coordinates (Y-down)
	"""
	# First convert to OpenGL coords
	gl_x, gl_y = layer_pos_to_opengl_coords(pos_x, pos_y)
	
	# Convert OpenGL normalized (-1.0 to +1.0) to pixels
	pixel_x = gl_x * (canvas_size[1] / 2) * viewport_base_size * composite_scale * zoom_level
	pixel_y = gl_y * (canvas_size[1] / 2) * viewport_base_size * composite_scale * zoom_level
	
	# Qt Y-axis is inverted (down is positive)
	# Canvas center is at (offset + size/2, offset + size/2)
	qt_x = offset_x + canvas_size[1] / 2 + pixel_x + pan_x
	qt_y = offset_y + canvas_size[1] / 2 - pixel_y + pan_y  # Negate Y for Qt coords
	
	return qt_x, qt_y


def qt_pixels_to_layer_pos(qt_x, qt_y, canvas_size, offset_x=0, offset_y=0, zoom_level=1.0, pan_x=0.0, pan_y=0.0, viewport_base_size=0.8, composite_scale=0.75):
	"""Convert Qt widget pixel coordinates to layer position (0-1 range).
	
	Args:
		qt_x: Qt X pixel coordinate
		qt_y: Qt Y pixel coordinate
		canvas_size: Size of the canvas square in pixels
		offset_x: X offset of canvas within parent widget
		offset_y: Y offset of canvas within parent widget
		zoom_level: Canvas zoom level (default 1.0)
		pan_x: Pan offset in pixels (horizontal)
		pan_y: Pan offset in pixels (vertical)
		viewport_base_size: Base size as fraction of viewport (default 0.8)
		composite_scale: Scale factor for CoA composite (default 0.75)
		
	Returns:
		(pos_x, pos_y): Layer position (0-1 range, 0=top in CK3)
	"""
	# Remove pan offset first
	pixel_x = qt_x - offset_x - canvas_size[1] / 2 - pan_x
	pixel_y = qt_y - offset_y - canvas_size[1] / 2 - pan_y
	
	# Convert pixels to OpenGL normalized space
	gl_x = pixel_x / (canvas_size[1] / 2) / viewport_base_size / composite_scale / zoom_level
	gl_y = -pixel_y / (canvas_size[1] / 2) / viewport_base_size / composite_scale / zoom_level
	
	# Convert OpenGL coords back to layer position
	pos_x = (gl_x + 1.0) / 2.0
	pos_y = (-gl_y + 1.0) / 2.0
	
	return pos_x, pos_y


def coa_to_frame_space(pos_x, pos_y, frame_scale, frame_offset):
	"""Convert CoA space coordinates to frame-adjusted visual space.
	
	Args:
		pos_x, pos_y: Position in CoA space (0-1 range)
		frame_scale: Tuple (scale_x, scale_y) for frame
		frame_offset: Tuple (offset_x, offset_y) for frame
		
	Returns:
		tuple: (frame_x, frame_y) in visual frame space
	"""
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
	
	return (frame_x, frame_y)


def frame_to_coa_space(frame_x, frame_y, frame_scale, frame_offset):
	"""Convert frame-adjusted visual space to CoA space coordinates.
	
	Args:
		frame_x, frame_y: Position in frame visual space
		frame_scale: Tuple (scale_x, scale_y) for frame
		frame_offset: Tuple (offset_x, offset_y) for frame
		
	Returns:
		tuple: (pos_x, pos_y) in CoA space (0-1 range)
	"""
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
	
	return (pos_x, pos_y)
