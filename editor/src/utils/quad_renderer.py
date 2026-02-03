"""OpenGL quad rendering utilities.

Provides helper functions for rendering textured quads with various transformations.
"""

import OpenGL.GL as gl
import numpy as np
import math
from PyQt5.QtGui import QOpenGLVertexArrayObject, QOpenGLBuffer


class QuadRenderer:
	"""Utility for rendering textured quads in OpenGL."""
	
	@stacreate_unit_quad():
		"""Create a static unit quad geometry (-0.5 to 0.5, size = 1).
		
		Returns:
			tuple: (vao, vbo, ebo) - OpenGL objects for the quad
		"""
		# Static unit quad vertices (never changes - GPU transforms it)
		vertices = np.array([
			-0.5, -0.5, 0.0,  0.0, 0.0,  # bottom-left
			 0.5, -0.5, 0.0,  1.0, 0.0,  # bottom-right
			 0.5,  0.5, 0.0,  1.0, 1.0,  # top-right
			-0.5,  0.5, 0.0,  0.0, 1.0,  # top-left
		], dtype=np.float32)
		
		indices = np.array([0, 1, 2, 2, 3, 0], dtype=np.uint32)
		
		# Create VAO
		vao = QOpenGLVertexArrayObject()
		vao.create()
		vao.bind()
		
		# Create VBO
		vbo = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
		vbo.create()
		vbo.bind()
		vbo.allocate(vertices.tobytes(), vertices.nbytes)
		
		# Create EBO
		ebo = QOpenGLBuffer(QOpenGLBuffer.IndexBuffer)
		ebo.create()
		ebo.bind()
		ebo.allocate(indices.tobytes(), indices.nbytes)
		
		# Set vertex attributes (position + UV)
		stride = 5 * 4  # 5 floats * 4 bytes
		gl.glEnableVertexAttribArray(0)
		gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, stride, None)
		gl.glEnableVertexAttribArray(1)
		gl.glVertexAttribPointer(1, 2, gl.GL_FLOAT, gl.GL_FALSE, stride, gl.ctypes.c_void_p(3 * 4))
		
		vao.release()
		
		return vao, vbo, ebo
	
	@staticmethod
	def ticmethod
	def render_textured_quad(vbo, bounds, uv_coords, flip_v=False):
		"""Render a simple textured quad.
		
		Args:
			vbo: OpenGL VBO to write vertices to
			bounds: Tuple (left, bottom, right, top) in NDC coordinates
			uv_coords: Tuple (u0, v0, u1, v1) for texture coordinates
			flip_v: Whether to flip V coordinates vertically
			
		Note: Assumes VAO is already bound and will call glDrawElements
		"""
		left, bottom, right, top = bounds
		u0, v0, u1, v1 = uv_coords
		
		if flip_v:
			v0, v1 = v1, v0
		
		vertices = np.array([
			left, bottom, 0.0,  u0, v1,
			right, bottom, 0.0,  u1, v1,
			right, top, 0.0,  u1, v0,
			left, top, 0.0,  u0, v0,
		], dtype=np.float32)
		
		vbo.write(0, vertices.tobytes(), vertices.nbytes)
		gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
	
	@staticmethod
	def build_quad_vertices(bounds, uv_coords, flip_v=False):
		"""Build vertex array for a textured quad without rendering.
		
		Args:
			bounds: Tuple (left, bottom, right, top) in NDC coordinates
			uv_coords: Tuple (u0, v0, u1, v1) for texture coordinates
			flip_v: Whether to flip V coordinates vertically
			
		Returns:
			numpy.ndarray: Vertex array ready for VBO upload
		"""
		left, bottom, right, top = bounds
		u0, v0, u1, v1 = uv_coords
		
		if flip_v:
			v0, v1 = v1, v0
		
		return np.array([
			left, bottom, 0.0,  u0, v1,
			right, bottom, 0.0,  u1, v1,
			right, top, 0.0,  u1, v0,
			left, top, 0.0,  u0, v0,
		], dtype=np.float32)
	
	@staticmethod
	def render_transformed_quad(vbo, center, size, rotation_deg, uv_coords, flip_x=False, flip_y=False):
		"""Render a textured quad with rotation and flipping.
		
		Args:
			vbo: OpenGL VBO to write vertices to
			center: Tuple (center_x, center_y) in NDC coordinates
			size: Tuple (half_width, half_height) in NDC units
			rotation_deg: Rotation angle in degrees (positive = counterclockwise)
			uv_coords: Tuple (u0, v0, u1, v1) for texture coordinates
			flip_x: Whether to flip horizontally
			flip_y: Whether to flip vertically
			
		Note: Assumes VAO is already bound and will call glDrawElements
		"""
		center_x, center_y = center
		half_width, half_height = size
		u0, v0, u1, v1 = uv_coords
		
		# Convert rotation to radians (negate for OpenGL coordinate system)
		angle_rad = math.radians(-rotation_deg)
		cos_a = math.cos(angle_rad)
		sin_a = math.sin(angle_rad)
		
		# Unit quad corners
		unit_corners = [
			(-1.0, -1.0),
			( 1.0, -1.0),
			( 1.0,  1.0),
			(-1.0,  1.0),
		]
		
		# Apply flip
		scale_sign_x = -1 if flip_x else 1
		scale_sign_y = -1 if flip_y else 1
		
		# Transform corners
		transformed = []
		for ux, uy in unit_corners:
			# Flip
			fx = ux * scale_sign_x
			fy = uy * scale_sign_y
			# Rotate
			rx = fx * cos_a - fy * sin_a
			ry = fx * sin_a + fy * cos_a
			# Scale
			sx = rx * half_width
			sy = ry * half_height
			# Translate
			transformed.append((sx + center_x, sy + center_y))
		
		vertices = np.array([
			transformed[0][0], transformed[0][1], 0.0,  u0, v1,
			transformed[1][0], transformed[1][1], 0.0,  u1, v1,
			transformed[2][0], transformed[2][1], 0.0,  u1, v0,
			transformed[3][0], transformed[3][1], 0.0,  u0, v0,
		], dtype=np.float32)
		
		vbo.write(0, vertices.tobytes(), vertices.nbytes)
		gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
	
	@staticmethod
	def calculate_ndc_size(pixel_size, viewport_size):
		"""Convert pixel size to NDC size.
		
		Args:
			pixel_size: Size in pixels (width, height) or single value
			viewport_size: Viewport dimensions (width, height)
			
		Returns:
			tuple: (ndc_width, ndc_height)
		"""
		if isinstance(pixel_size, (int, float)):
			pixel_size = (pixel_size, pixel_size)
		
		ndc_width = pixel_size[0] / viewport_size[0] * 2.0
		ndc_height = pixel_size[1] / viewport_size[1] * 2.0
		
		return ndc_width, ndc_height
	
	@staticmethod
	def calculate_corner_position(corner, padding_px, size_px, viewport_size):
		"""Calculate NDC position for a corner-anchored quad.
		
		Args:
			corner: One of 'top-left', 'top-right', 'bottom-left', 'bottom-right'
			padding_px: Padding from edge in pixels (x, y) or single value
			size_px: Quad size in pixels (width, height) or single value
			viewport_size: Viewport dimensions (width, height)
			
		Returns:
			tuple: (left, bottom, right, top) in NDC coordinates
		"""
		if isinstance(padding_px, (int, float)):
			padding_px = (padding_px, padding_px)
		if isinstance(size_px, (int, float)):
			size_px = (size_px, size_px)
		
		# Convert to NDC
		size_ndc = QuadRenderer.calculate_ndc_size(size_px, viewport_size)
		padding_ndc = QuadRenderer.calculate_ndc_size(padding_px, viewport_size)
		
		if corner == 'top-left':
			left = -1.0 + padding_ndc[0]
			top = 1.0 - padding_ndc[1]
			right = left + size_ndc[0]
			bottom = top - size_ndc[1]
		elif corner == 'top-right':
			right = 1.0 - padding_ndc[0]
			top = 1.0 - padding_ndc[1]
			left = right - size_ndc[0]
			bottom = top - size_ndc[1]
		elif corner == 'bottom-left':
			left = -1.0 + padding_ndc[0]
			bottom = -1.0 + padding_ndc[1]
			right = left + size_ndc[0]
			top = bottom + size_ndc[1]
		elif corner == 'bottom-right':
			right = 1.0 - padding_ndc[0]
			bottom = -1.0 + padding_ndc[1]
			left = right - size_ndc[0]
			top = bottom + size_ndc[1]
		else:
			raise ValueError(f"Invalid corner: {corner}")
		
		return (left, bottom, right, top)
