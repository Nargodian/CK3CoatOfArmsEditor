# PyQt5 imports
from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QOpenGLShaderProgram, QOpenGLShader, QOpenGLVertexArrayObject, QOpenGLBuffer, QVector2D, QVector3D, QVector4D
from models.coa import CoA

#COA INTEGRATION ACTION: Step 5 - Import Layer and CoA models for type hints and future use
from models.coa import CoA, Layer

# External library imports
import OpenGL.GL as gl
import numpy as np
import os
import json
import logging
from constants import (
	DEFAULT_FRAME,
	DEFAULT_BASE_COLOR1, DEFAULT_BASE_COLOR2, DEFAULT_BASE_COLOR3,
	CK3_NAMED_COLORS
)
from PIL import Image
from pathlib import Path

# Local imports
from components.canvas_widgets.shader_manager import ShaderManager
from services.framebuffer_rtt import FramebufferRTT
from utils.path_resolver import (get_pattern_metadata_path, get_emblem_metadata_path, 
                                  get_pattern_source_dir, get_emblem_source_dir, get_frames_dir)


# ========================================
# Constants
# ========================================

# Composite quad base size as fraction of viewport (NDC coordinates)
# This determines how much of the viewport the design occupies at zoom=1.0
# e.g., 0.8 means the design occupies 80% of the viewport width/height
VIEWPORT_BASE_SIZE = 0.8

# Scale factor for CoA composite to fit under frame
# CK3 default: 0.9 (90% of shield area) from data_binding/tgp_data_bindings.txt
COMPOSITE_SCALE = 0.75

# Vertical offset for CoA within frame (CK3 default: 0.04 = 4% upward)
COMPOSITE_OFFSET_Y = 0.00

# ========================================
# Coordinate Conversion Functions
# ========================================

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


def layer_pos_to_qt_pixels(pos_x, pos_y, canvas_size, offset_x=0, offset_y=0, zoom_level=1.0):
	"""Convert layer position (0-1 range) to Qt widget pixel coordinates.
	
	Args:
		pos_x: Layer X position (0-1, where 0.5 is center)
		pos_y: Layer Y position (0-1, where 0.5 is center)
		canvas_size: Size of the canvas square in pixels
		offset_x: X offset of canvas within parent widget
		offset_y: Y offset of canvas within parent widget
		zoom_level: Canvas zoom level (default 1.0)
		
	Returns:
		(qt_x, qt_y): Qt pixel coordinates (Y-down)
	"""
	# First convert to OpenGL coords
	gl_x, gl_y = layer_pos_to_opengl_coords(pos_x, pos_y)
	
	# Convert OpenGL normalized (-1.0 to +1.0) to pixels
	# Must account for composite quad base_size factor (quad only occupies VIEWPORT_BASE_SIZE of viewport)
	# and COMPOSITE_SCALE (shrinks CoA to fit under frame) and zoom_level
	pixel_x = gl_x * (canvas_size / 2) * VIEWPORT_BASE_SIZE * COMPOSITE_SCALE * zoom_level
	pixel_y = gl_y * (canvas_size / 2) * VIEWPORT_BASE_SIZE * COMPOSITE_SCALE * zoom_level
	
	# Qt Y-axis is inverted (down is positive)
	# Canvas center is at (offset + size/2, offset + size/2)
	qt_x = offset_x + canvas_size / 2 + pixel_x
	qt_y = offset_y + canvas_size / 2 - pixel_y  # Negate Y for Qt coords
	
	return qt_x, qt_y


def qt_pixels_to_layer_pos(qt_x, qt_y, canvas_size, offset_x=0, offset_y=0, zoom_level=1.0):
	"""Convert Qt widget pixel coordinates to layer position (0-1 range).
	
	Args:
		qt_x: Qt X pixel coordinate
		qt_y: Qt Y pixel coordinate
		canvas_size: Size of the canvas square in pixels
		offset_x: X offset of canvas within parent widget
		offset_y: Y offset of canvas within parent widget
		zoom_level: Canvas zoom level (default 1.0)
		
	Returns:
		(pos_x, pos_y): Layer position (0-1 range, 0=top in CK3)
	"""
	# Convert Qt pixels to canvas-relative pixels
	pixel_x = qt_x - offset_x - canvas_size / 2
	pixel_y = qt_y - offset_y - canvas_size / 2
	
	# Convert pixels to OpenGL normalized space
	# Qt Y-down to OpenGL Y-up: negate pixel_y
	# Must account for composite quad base_size factor, COMPOSITE_SCALE and zoom_level
	gl_x = pixel_x / (canvas_size / 2) / VIEWPORT_BASE_SIZE / COMPOSITE_SCALE / zoom_level
	gl_y = -pixel_y / (canvas_size / 2) / VIEWPORT_BASE_SIZE / COMPOSITE_SCALE / zoom_level
	
	# Convert OpenGL coords back to layer position
	# layer_pos_to_opengl_coords: gl_x = pos_x * 2.0 - 1.0
	# Reversing: pos_x = (gl_x + 1.0) / 2.0
	# layer_pos_to_opengl_coords: gl_y = -(pos_y * 2.0 - 1.0)
	# Reversing: pos_y = (-gl_y + 1.0) / 2.0
	pos_x = (gl_x + 1.0) / 2.0
	pos_y = (-gl_y + 1.0) / 2.0
	
	return pos_x, pos_y


class CoatOfArmsCanvas(QOpenGLWidget):
	"""OpenGL canvas for rendering coat of arms with shaders"""
	
	def __init__(self, parent=None):
		super().__init__(parent)
		#COA INTEGRATION ACTION: Step 5 - Add CoA model reference (set by CanvasArea/MainWindow)
		# Note: CoA is accessed via CoA.get_active() in paintGL, not stored as instance variable
		self.canvas_area = None  # Reference to CanvasArea (set after init)
		self.base_shader = None  # Shader for base layer
		self.design_shader = None  # Shader for emblem layers
		self.basic_shader = None  # Shader for frame rendering
		self.composite_shader = None  # Shader for RTT compositing
		self.framebuffer_rtt = None  # Offscreen framebuffer for RTT
		self.vao = None
		self.vbo = None
		self.texture_atlases = []  # List of OpenGL texture IDs
		self.texture_uv_map = {}  # filename -> (atlas_index, u0, v0, u1, v1)
		self.base_texture = None  # Base pattern texture
		self.base_colors = [
			CK3_NAMED_COLORS[DEFAULT_BASE_COLOR1]['rgb'],
			CK3_NAMED_COLORS[DEFAULT_BASE_COLOR2]['rgb'],
			CK3_NAMED_COLORS[DEFAULT_BASE_COLOR3]['rgb']
		]  # Default base colors from constants
		self.frameTexture = None  # Current frame texture
		self.frameTextures = {}  # Frame name -> texture ID
		self.frame_masks = {}  # Frame name -> frameMask texture ID
		self.frame_scales = {}  # Frame name -> (scale_x, scale_y) tuple
		self.frame_offsets = {}  # Frame name -> (offset_x, offset_y) tuple
		self.official_frame_scales = {}  # Official scales from CK3 culture files
		self.official_frame_offsets = {}  # Official offsets from CK3 culture files
		self._load_official_frame_transforms()
		self.patternMask = None  # Current pattern mask (shield shape, changes with frame)
		self.default_mask_texture = None  # Default white mask (fallback)
		self.texturedMask = None  # CK3 material texture (dirt/fabric/paint) - coa_mask_texture.png
		self.noiseMask = None  # Noise texture for grain effect - noise.png
		self.current_frame_name = DEFAULT_FRAME  # Track current frame name
		self.prestige_level = 0  # Current prestige level (0-5)
		
		# Zoom and grid properties
		self.zoom_level = 1.0  # Current zoom level (1.0 = 100%)
		self.show_grid = False  # Whether to show alignment grid
		self.grid_divisions = 4  # Grid size (2, 4, 8, or 16)
		
		# Store clear color for restoration after export
		self.clear_color = (0.95, 0.95, 0.95, 0.0)  # Default, updated in initializeGL
	
	# ========================================
	# Qt OpenGL Widget Overrides
	# ========================================
	
	def resizeEvent(self, event):
		"""Override resize to maintain square aspect"""
		super().resizeEvent(event)
		# Force square dimensions
		size = min(self.width(), self.height())
		if self.width() != size or self.height() != size:
			self.setFixedSize(size, size)
	
	def sizeHint(self):
		"""Suggest square aspect ratio"""
		return QSize(600, 600)
	
	# ========================================
	# OpenGL Initialization and Rendering
	# ========================================
		
	def initializeGL(self):
		"""Initialize OpenGL context and shaders"""
		# Use grandparent's background color (parent is dark canvas_container)
		from PyQt5.QtGui import QPalette
		widget = self.parent().parent() if self.parent() and self.parent().parent() else self.parent()
		if widget:
			bg_color = widget.palette().color(QPalette.Window)
			self.clear_color = (0.05, 0.05, 0.05, 1.0)
		else:
			self.clear_color = (0.95, 0.95, 0.95, 0.0)  # Light gray fallback
		
		gl.glClearColor(*self.clear_color)
		gl.glEnable(gl.GL_BLEND)
		gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
		
		# Create shaders using ShaderManager
		shader_manager = ShaderManager()
		self.base_shader = shader_manager.create_base_shader(self)
		self.design_shader = shader_manager.create_design_shader(self)
		self.basic_shader = shader_manager.create_basic_shader(self)
		self.composite_shader = shader_manager.create_composite_shader(self)
		
		# Create RTT framebuffer
		self.framebuffer_rtt = FramebufferRTT()
		
		self.base_shader.bind()
		
		# Create quad vertices (position + UV)
		vertices = np.array([
			# Position (x, y, z)    UV (u, v)
			-0.8, -0.8, 0.0,        0.0, 0.0,  # Bottom-left
			 0.8, -0.8, 0.0,        1.0, 0.0,  # Bottom-right
			 0.8,  0.8, 0.0,        1.0, 1.0,  # Top-right
			-0.8,  0.8, 0.0,        0.0, 1.0,  # Top-left
		], dtype=np.float32)
		
		indices = np.array([
			0, 1, 2,  # First triangle
			2, 3, 0   # Second triangle
		], dtype=np.uint32)
		
		# Create VAO
		self.vao = QOpenGLVertexArrayObject()
		self.vao.create()
		self.vao.bind()
		
		# Create VBO
		self.vbo = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
		self.vbo.create()
		self.vbo.bind()
		self.vbo.allocate(vertices.tobytes(), vertices.nbytes)
		
		# Create EBO (Element Buffer Object)
		self.ebo = QOpenGLBuffer(QOpenGLBuffer.IndexBuffer)
		self.ebo.create()
		self.ebo.bind()
		self.ebo.allocate(indices.tobytes(), indices.nbytes)
		
		# Set vertex attributes
		stride = 5 * 4  # 5 floats per vertex * 4 bytes per float
		
		# Position attribute (location 0)
		gl.glEnableVertexAttribArray(0)
		gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, stride, None)
		
		# UV attribute (location 1)
		gl.glEnableVertexAttribArray(1)
		gl.glVertexAttribPointer(1, 2, gl.GL_FLOAT, gl.GL_FALSE, stride, gl.ctypes.c_void_p(3 * 4))
		
		self.vao.release()
		self.base_shader.release()
		
		# Load texture atlases
		self._load_texture_atlases()
		
		# Load frame textures
		self._load_frame_textures()
		
		# Load mask texture
		self._load_mask_texture()
		
		# Load material mask texture (CK3 coa_mask_texture)
		self._load_material_mask_texture()
		
		# Load noise texture for grain effect
		self._load_noise_texture()
		
		# Initialize RTT framebuffer
		self.framebuffer_rtt.initialize()
		
		# Set defaults after initialization
		self.set_frame(DEFAULT_FRAME)
		self.set_prestige(3)
		# Set default base pattern
		if "pattern__solid_designer.dds" in self.texture_uv_map:
			self.set_base_texture("pattern__solid_designer.dds")
		
		# Force initial render after event loop starts
		from PyQt5.QtCore import QTimer
		QTimer.singleShot(0, self.update)
	
	def paintGL(self):
		"""Render the scene using RTT pipeline"""
		gl.glClearColor(*self.clear_color)
		gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
		
		if not self.vao:
			return
		
		# Render CoA to framebuffer (512x512 canonical space)
		self._render_coa_to_framebuffer()
		
		# Restore viewport to widget size (RTT sets it to 512x512)
		size = min(self.width(), self.height())
		x = (self.width() - size) // 2
		y = (self.height() - size) // 2
		gl.glViewport(x, y, size, size)
		
		# Composite framebuffer to viewport with frame mask
		self._composite_to_viewport()
		
		# Render frame graphic on top
		self._render_frame()
	
	def _render_coa_to_framebuffer(self):
		"""Render pattern and emblems to RTT framebuffer in canonical 512x512 space"""
		import math
		
		# Bind RTT framebuffer
		self.framebuffer_rtt.bind()
		self.framebuffer_rtt.clear(0.0, 0.0, 0.0, 0.0)  # Transparent background
		
		gl.glEnable(gl.GL_BLEND)
		gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
		
		# Render base pattern
		if self.base_shader and self.default_mask_texture:
			base_size = 1.0  # Fill entire framebuffer
			
			# Get pattern texture UV coordinates from atlas
			u0, v0, u1, v1 = 0.0, 0.0, 1.0, 1.0
			pattern_texture_id = self.default_mask_texture
			if self.base_texture and self.base_texture in self.texture_uv_map:
				atlas_index, u0, v0, u1, v1 = self.texture_uv_map[self.base_texture]
				if 0 <= atlas_index < len(self.texture_atlases):
					pattern_texture_id = self.texture_atlases[atlas_index]
			
			vertices = np.array([
				-base_size, -base_size, 0.0,  u0, v1,
				 base_size, -base_size, 0.0,  u1, v1,
				 base_size,  base_size, 0.0,  u1, v0,
				-base_size,  base_size, 0.0,  u0, v0,
			], dtype=np.float32)
			
			self.vao.bind()
			self.vbo.write(0, vertices.tobytes(), vertices.nbytes)
			
			self.base_shader.bind()
			
			# Bind pattern texture
			gl.glActiveTexture(gl.GL_TEXTURE0)
			gl.glBindTexture(gl.GL_TEXTURE_2D, pattern_texture_id)
			self.base_shader.setUniformValue("patternMaskSampler", 0)
			
			# Colors from base_colors attribute
			self.base_shader.setUniformValue("color1", QVector3D(*self.base_colors[0]))
			self.base_shader.setUniformValue("color2", QVector3D(*self.base_colors[1]))
			self.base_shader.setUniformValue("color3", QVector3D(*self.base_colors[2]))
			
			gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
			
			self.base_shader.release()
			self.vao.release()
		
		# Render emblem layers
		coa = CoA.get_active() if CoA.has_active() else None
		if coa and self.design_shader and coa.get_layer_count() > 0:
			self.vao.bind()  # Bind VAO once for all emblem layers
			self.design_shader.bind()
			
			# Bind pattern texture for mask channels (once, before layer loop)
			if self.base_texture and self.base_texture in self.texture_uv_map:
				pattern_atlas_idx, p_u0, p_v0, p_u1, p_v1 = self.texture_uv_map[self.base_texture]
				if pattern_atlas_idx < len(self.texture_atlases):
					gl.glActiveTexture(gl.GL_TEXTURE2)
					gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_atlases[pattern_atlas_idx])
					if self.design_shader.uniformLocation("patternMaskSampler") != -1:
						self.design_shader.setUniformValue("patternMaskSampler", 2)
					if self.design_shader.uniformLocation("patternUV") != -1:
						self.design_shader.setUniformValue("patternUV", QVector4D(p_u0, p_v0, p_u1, p_v1))
			
			# Iterate through layers using UUIDs
			for layer_uuid in coa.get_all_layer_uuids():
				# Get layer properties via UUID-based queries
				visible = coa.get_layer_visible(layer_uuid)
				if not visible:
					continue
				
				filename = coa.get_layer_filename(layer_uuid)
				if not filename or filename not in self.texture_uv_map:
					continue
				
				atlas_idx, u0, v0, u1, v1 = self.texture_uv_map[filename]
				if atlas_idx >= len(self.texture_atlases):
					continue
				
				# Bind emblem texture
				gl.glActiveTexture(gl.GL_TEXTURE0)
				gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_atlases[atlas_idx])
				self.design_shader.setUniformValue("emblemMaskSampler", 0)
				
				# Set emblem colors via CoA queries (shared by all instances)
				color1 = coa.get_layer_color(layer_uuid, 1)
				color2 = coa.get_layer_color(layer_uuid, 2)
				color3 = coa.get_layer_color(layer_uuid, 3)
				self.design_shader.setUniformValue("primaryColor", color1[0], color1[1], color1[2])
				self.design_shader.setUniformValue("secondaryColor", color2[0], color2[1], color2[2])
				self.design_shader.setUniformValue("tertiaryColor", color3[0], color3[1], color3[2])
				
				# Set pattern mask flag (shared by all instances)
				mask = coa.get_layer_mask(layer_uuid)
				if mask is None:
					pattern_flag = 0
				else:
					pattern_flag = 0
					if len(mask) > 0 and mask[0] != 0:
						pattern_flag |= 1
					if len(mask) > 1 and mask[1] != 0:
						pattern_flag |= 2
					if len(mask) > 2 and mask[2] != 0:
						pattern_flag |= 4
				self.design_shader.setUniformValue("patternFlag", pattern_flag)
				
				# Get shared flip properties (shared by all instances)
				flip_x = coa.get_layer_flip_x(layer_uuid)
				flip_y = coa.get_layer_flip_y(layer_uuid)
				scale_sign_x = -1 if flip_x else 1
				scale_sign_y = -1 if flip_y else 1
				
				# Render all instances of this layer
				instance_count = coa.get_layer_instance_count(layer_uuid)
				for instance_idx in range(instance_count):
					# Get instance-specific transform data
					instance = coa.get_layer_instance(layer_uuid, instance_idx)
					pos_x = instance.pos_x
					pos_y = instance.pos_y
					scale_x = instance.scale_x
					scale_y = instance.scale_y
					rotation = instance.rotation
					
					# Convert layer position to OpenGL coordinates
					center_x, center_y = layer_pos_to_opengl_coords(pos_x, pos_y)
					
					angle_rad = math.radians(-rotation)
					cos_a = math.cos(angle_rad)
					sin_a = math.sin(angle_rad)
					
					half_width = scale_x
					half_height = scale_y
					
					unit_corners = [
						(-1.0, -1.0),
						( 1.0, -1.0),
						( 1.0,  1.0),
						(-1.0,  1.0),
					]
					
					transformed = []
					for ux, uy in unit_corners:
						fx = ux * scale_sign_x
						fy = uy * scale_sign_y
						rx = fx * cos_a - fy * sin_a
						ry = fx * sin_a + fy * cos_a
						sx = rx * half_width
						sy = ry * half_height
						transformed.append((sx + center_x, sy + center_y))
					
					vertices = np.array([
						transformed[0][0], transformed[0][1], 0.0,  u0, v1,
						transformed[1][0], transformed[1][1], 0.0,  u1, v1,
						transformed[2][0], transformed[2][1], 0.0,  u1, v0,
						transformed[3][0], transformed[3][1], 0.0,  u0, v0,
					], dtype=np.float32)
					
					# Update VBO (VAO already bound)
					self.vbo.write(0, vertices.tobytes(), vertices.nbytes)
					
					gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
			
			self.design_shader.release()
			self.vao.release()
		
		gl.glFlush()
		self.framebuffer_rtt.unbind(self.defaultFramebufferObject())
	
	def _composite_to_viewport(self):
		"""Composite RTT texture to viewport with zoom and frame"""
		gl.glEnable(gl.GL_BLEND)
		gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
		
		if not self.composite_shader or not self.vao:
			return
		
		self.vao.bind()
		self.composite_shader.bind()
		
		# Bind RTT texture
		gl.glActiveTexture(gl.GL_TEXTURE0)
		gl.glBindTexture(gl.GL_TEXTURE_2D, self.framebuffer_rtt.get_texture())
		self.composite_shader.setUniformValue("coaTextureSampler", 0)
		
		# Bind frame mask texture
		if self.current_frame_name in self.frame_masks:
			gl.glActiveTexture(gl.GL_TEXTURE1)
			gl.glBindTexture(gl.GL_TEXTURE_2D, self.frame_masks[self.current_frame_name])
			self.composite_shader.setUniformValue("frameMaskSampler", 1)
		elif self.default_mask_texture:
			# Use default white mask if no frame-specific mask exists
			gl.glActiveTexture(gl.GL_TEXTURE1)
			gl.glBindTexture(gl.GL_TEXTURE_2D, self.default_mask_texture)
			self.composite_shader.setUniformValue("frameMaskSampler", 1)
		
		# Bind material texture
		if self.texturedMask:
			gl.glActiveTexture(gl.GL_TEXTURE2)
			gl.glBindTexture(gl.GL_TEXTURE_2D, self.texturedMask)
			self.composite_shader.setUniformValue("texturedMaskSampler", 2)
		
		# Bind noise texture
		if self.noiseMask:
			gl.glActiveTexture(gl.GL_TEXTURE3)
			gl.glBindTexture(gl.GL_TEXTURE_2D, self.noiseMask)
			self.composite_shader.setUniformValue("noiseMaskSampler", 3)
		
		# Set per-frame scale and offset uniforms
		safeMargin = 1.0
		if self.current_frame_name == "None":
			# No frame: render at full scale with no offset, no bleed margin
			self.composite_shader.setUniformValue("coaScale", QVector2D(1.0, 1.0))
			self.composite_shader.setUniformValue("coaOffset", QVector2D(0.0, 0.0))
			self.composite_shader.setUniformValue("bleedMargin", 1.0)
		elif self.current_frame_name in self.frame_scales:
			# Listed frame: apply bleed margin (larger viewport, smaller CoA = edge bleed)
			safeMargin = 1.05
			scale = self.frame_scales[self.current_frame_name]
			self.composite_shader.setUniformValue("coaScale", QVector2D(scale[0], scale[1]))
			self.composite_shader.setUniformValue("bleedMargin", safeMargin)
			if self.current_frame_name in self.frame_offsets:
				offset = self.frame_offsets[self.current_frame_name]
				self.composite_shader.setUniformValue("coaOffset", QVector2D(offset[0], offset[1]))
			else:
				# Default CK3 offset for this frame
				self.composite_shader.setUniformValue("coaOffset", QVector2D(0.0, 0.04))
		else:
			# Unlisted frame: apply bleed margin with default CK3 scale and offset
			safeMargin = 1.05
			self.composite_shader.setUniformValue("coaScale", QVector2D(0.9, 0.9))
			self.composite_shader.setUniformValue("bleedMargin", safeMargin)
			self.composite_shader.setUniformValue("coaOffset", QVector2D(0.0, 0.04))
		
		# Composite quad always at fixed size (scaling/offset done in shader)
		base_size = VIEWPORT_BASE_SIZE * self.zoom_level * COMPOSITE_SCALE * safeMargin
		# Texture coords: RTT renders Y-up (OpenGL standard), texture V=0 at bottom, V=1 at top
		# Position Y=-1 (bottom) → V=0, Position Y=+1 (top) → V=1
		vertices = np.array([
			-base_size, -base_size, 0.0,  0.0, 0.0,  # bottom-left
			 base_size, -base_size, 0.0,  1.0, 0.0,  # bottom-right
			 base_size,  base_size, 0.0,  1.0, 1.0,  # top-right
			-base_size,  base_size, 0.0,  0.0, 1.0,  # top-left
		], dtype=np.float32)
		
		self.vbo.write(0, vertices.tobytes(), vertices.nbytes)
		
		gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
		
		self.composite_shader.release()
		self.vao.release()
	
	def _composite_to_fbo(self, fbo_handle):
		"""Composite RTT texture to arbitrary FBO (for export) with frame mask
		
		Args:
			fbo_handle: OpenGL framebuffer ID to render to
		"""
		# Bind target framebuffer
		gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, fbo_handle)
		
		gl.glEnable(gl.GL_BLEND)
		gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
		
		if not self.composite_shader or not self.vao:
			return
		
		self.vao.bind()
		self.composite_shader.bind()
		
		# Bind RTT texture
		gl.glActiveTexture(gl.GL_TEXTURE0)
		gl.glBindTexture(gl.GL_TEXTURE_2D, self.framebuffer_rtt.get_texture())
		self.composite_shader.setUniformValue("coaTextureSampler", 0)
		
		# Bind frame mask texture
		if self.current_frame_name in self.frame_masks:
			gl.glActiveTexture(gl.GL_TEXTURE1)
			gl.glBindTexture(gl.GL_TEXTURE_2D, self.frame_masks[self.current_frame_name])
			self.composite_shader.setUniformValue("frameMaskSampler", 1)
		elif self.default_mask_texture:
			# Use default white mask if no frame-specific mask exists
			gl.glActiveTexture(gl.GL_TEXTURE1)
			gl.glBindTexture(gl.GL_TEXTURE_2D, self.default_mask_texture)
			self.composite_shader.setUniformValue("frameMaskSampler", 1)
		
		# Bind material texture
		if self.texturedMask:
			gl.glActiveTexture(gl.GL_TEXTURE2)
			gl.glBindTexture(gl.GL_TEXTURE_2D, self.texturedMask)
			self.composite_shader.setUniformValue("texturedMaskSampler", 2)
		
		# Bind noise texture
		if self.noiseMask:
			gl.glActiveTexture(gl.GL_TEXTURE3)
			gl.glBindTexture(gl.GL_TEXTURE_2D, self.noiseMask)
			self.composite_shader.setUniformValue("noiseMaskSampler", 3)
		
		# For export: use frame-specific scaling but no zoom or UI transforms
		safeMargin = 1.0
		if self.current_frame_name == "None":
			self.composite_shader.setUniformValue("coaScale", QVector2D(1.0, 1.0))
			self.composite_shader.setUniformValue("coaOffset", QVector2D(0.0, 0.0))
			self.composite_shader.setUniformValue("bleedMargin", 1.0)
		elif self.current_frame_name in self.frame_scales:
			safeMargin = 1.05
			scale = self.frame_scales[self.current_frame_name]
			self.composite_shader.setUniformValue("coaScale", QVector2D(scale[0], scale[1]))
			self.composite_shader.setUniformValue("bleedMargin", safeMargin)
			if self.current_frame_name in self.frame_offsets:
				offset = self.frame_offsets[self.current_frame_name]
				self.composite_shader.setUniformValue("coaOffset", QVector2D(offset[0], offset[1]))
			else:
				self.composite_shader.setUniformValue("coaOffset", QVector2D(0.0, 0.04))
		else:
			safeMargin = 1.05
			self.composite_shader.setUniformValue("coaScale", QVector2D(0.9, 0.9))
			self.composite_shader.setUniformValue("bleedMargin", safeMargin)
			self.composite_shader.setUniformValue("coaOffset", QVector2D(0.0, 0.04))
		
		# Composite quad at fixed size (no zoom for export)
		base_size = VIEWPORT_BASE_SIZE * COMPOSITE_SCALE * safeMargin
		vertices = np.array([
			-base_size, -base_size, 0.0,  0.0, 0.0,  # bottom-left
			 base_size, -base_size, 0.0,  1.0, 0.0,  # bottom-right
			 base_size,  base_size, 0.0,  1.0, 1.0,  # top-right
			-base_size,  base_size, 0.0,  0.0, 1.0,  # top-left
		], dtype=np.float32)
		
		self.vbo.write(0, vertices.tobytes(), vertices.nbytes)
		
		gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
		
		self.composite_shader.release()
		self.vao.release()
	
	def _render_frame(self):
		"""Render frame graphic on top of CoA"""
		if self.current_frame_name not in self.frameTextures:
			return
		
		if not self.basic_shader or not self.vao:
			return
		
		self.vao.bind()
		self.basic_shader.bind()
		
		# Bind frame texture
		gl.glActiveTexture(gl.GL_TEXTURE0)
		gl.glBindTexture(gl.GL_TEXTURE_2D, self.frameTextures[self.current_frame_name])
		self.basic_shader.setUniformValue("textureSampler", 0)
		
		# Frame textures are 6x1 grids (6 splendor levels horizontally)
		# Calculate UV coordinates for the current prestige/splendor level (0-5)
		frame_index = max(0, min(5, self.prestige_level))  # Clamp to 0-5
		u0 = frame_index / 6.0
		u1 = (frame_index + 1) / 6.0
		
		# Render frame at same size as composite
		base_size = VIEWPORT_BASE_SIZE * self.zoom_level
		vertices = np.array([
			-base_size, -base_size, 0.0,  u0, 1.0,
			 base_size, -base_size, 0.0,  u1, 1.0,
			 base_size,  base_size, 0.0,  u1, 0.0,
			-base_size,  base_size, 0.0,  u0, 0.0,
		], dtype=np.float32)
		
		self.vbo.write(0, vertices.tobytes(), vertices.nbytes)
		
		gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
		
		self.basic_shader.release()
		self.vao.release()
	
	def _render_grid(self):
		"""Render a grid overlay for alignment"""
		# Enable line rendering
		gl.glDisable(gl.GL_TEXTURE_2D)
		gl.glLineWidth(1.0)
		
		# Set grid color (light gray)
		gl.glColor4f(0.5, 0.5, 0.5, 0.5)
		
		# Draw vertical and horizontal lines
		grid_size = VIEWPORT_BASE_SIZE * self.zoom_level
		grid_step = (VIEWPORT_BASE_SIZE * 2.0 * self.zoom_level) / self.grid_divisions  # Divide into grid_divisions
		
		gl.glBegin(gl.GL_LINES)
		
		# Vertical lines
		x = -grid_size
		while x <= grid_size:
			gl.glVertex2f(x, -grid_size)
			gl.glVertex2f(x, grid_size)
			x += grid_step
		
		# Horizontal lines
		y = -grid_size
		while y <= grid_size:
			gl.glVertex2f(-grid_size, y)
			gl.glVertex2f(grid_size, y)
			y += grid_step
		
		gl.glEnd()
		
		# Reset color and re-enable textures
		gl.glColor4f(1.0, 1.0, 1.0, 1.0)
		gl.glEnable(gl.GL_TEXTURE_2D)
	
	# ========================================
	# Texture Loading and Atlas Management
	# ========================================
			
	def _load_texture_atlases(self):
		"""Load texture atlases from emblem files and patterns, create UV mappings"""
		try:
			from utils.path_resolver import get_pattern_metadata_path, get_emblem_metadata_path, get_pattern_source_dir, get_emblem_source_dir
			# Collect all valid files (patterns + emblems)
			emblem_files = []

			# Load patterns first
			pattern_json_path = get_pattern_metadata_path()
			if pattern_json_path.exists():
				with open(pattern_json_path, 'r', encoding='utf-8') as f:
					pattern_data = json.load(f)

				for filename, props in pattern_data.items():
					if props is None or filename == "\ufeff" or filename == "":
						continue
					# Load all patterns (even invisible) - asset sidebar will filter display
					png_filename = filename.replace('.dds', '.png')
					image_path = get_pattern_source_dir() / png_filename
					if image_path.exists():
						emblem_files.append((filename, str(image_path)))  # Store .dds name as key

			# Load emblems
			emblem_json_path = get_emblem_metadata_path()
			if emblem_json_path.exists():
				with open(emblem_json_path, 'r', encoding='utf-8') as f:
					emblem_data = json.load(f)

				for filename, props in emblem_data.items():
					if props is None or filename == "\ufeff":
						continue
					# Load all emblems (even invisible) - asset sidebar will filter display
					png_filename = filename.replace('.dds', '.png')
					image_path = get_emblem_source_dir() / png_filename
					if image_path.exists():
						emblem_files.append((filename, str(image_path)))  # Store .dds name as key

			# Build texture atlas (32x32 grid of 256x256 images = 8192x8192)
			atlas_size = 8192
			tile_size = 256
			tiles_per_row = atlas_size // tile_size  # 32
			tiles_per_atlas = tiles_per_row * tiles_per_row  # 1024

			num_atlases = (len(emblem_files) + tiles_per_atlas - 1) // tiles_per_atlas

			for atlas_idx in range(num_atlases):
				# Create atlas texture
				atlas_data = np.zeros((atlas_size, atlas_size, 4), dtype=np.uint8)

				start_idx = atlas_idx * tiles_per_atlas
				end_idx = min((atlas_idx + 1) * tiles_per_atlas, len(emblem_files))

				# Pack textures into atlas
				for i in range(start_idx, end_idx):
					filename, image_path = emblem_files[i]
					local_idx = i - start_idx

					# Calculate position in atlas
					row = local_idx // tiles_per_row
					col = local_idx % tiles_per_row
					x = col * tile_size
					y = row * tile_size

					# Load and resize image
					img = Image.open(image_path).convert('RGBA')
					img = img.resize((tile_size, tile_size), Image.Resampling.LANCZOS)
					img_array = np.array(img)

					# Place in atlas
					atlas_data[y:y+tile_size, x:x+tile_size, :] = img_array

					# Calculate UV coordinates (normalized)
					u0 = x / atlas_size
					v0 = y / atlas_size
					u1 = (x + tile_size) / atlas_size
					v1 = (y + tile_size) / atlas_size

					# Store UV mapping
					self.texture_uv_map[filename] = (atlas_idx, u0, v0, u1, v1)

				# Create OpenGL texture
				texture_id = gl.glGenTextures(1)
				gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)

				# Set texture parameters
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)

				# Upload texture data
				gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, atlas_size, atlas_size,
				               0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, atlas_data.tobytes())

				self.texture_atlases.append(texture_id)

		except Exception as e:
			print(f"Error loading texture atlases: {e}")
			import traceback
			traceback.print_exc()
			self.update()  # Trigger repaint
	
	def _load_frame_textures(self):
		"""Load frame textures from coa_frames directory"""
		try:
			frame_dir = get_frames_dir()
			if not frame_dir.exists():
				return
			
			frame_files = {
				"dynasty": "dynasty.png",
				"house": "house.png",
				"house_china": "house_china.png",
				"house_japan": "house_japan.png"
			}
			
			# Add house frames 02-30
			for i in range(2, 31):
				frame_files[f"house_frame_{i:02d}"] = f"house_frame_{i:02d}.png"
			
			for name, filename in frame_files.items():
				path = frame_dir / filename
				if path.exists():
					img = Image.open(path).convert('RGBA')
					img_data = np.array(img)
					
					# Create OpenGL texture for frame
					texture_id = gl.glGenTextures(1)
					gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
					
					gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
					gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
					gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
					gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
					
					gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, img.width, img.height,
					               0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, img_data.tobytes())
					
					self.frameTextures[name] = texture_id
					
					# Load corresponding mask file
					mask_filename = filename.replace('.png', '_mask.png')
					mask_path = os.path.join(frame_dir, mask_filename)
					if os.path.exists(mask_path):
						mask_img = Image.open(mask_path).convert('RGBA')
						
						# Analyze mask properties
						mask_data = np.array(mask_img)
						max_alpha = mask_data[:,:,3].max()
						
						# Skip only if completely invalid (no alpha data at all)
						if max_alpha > 0:
							# Resize mask to match expected canvas size (800x800)
							target_size = 800
							if mask_img.size != (target_size, target_size):
								mask_img = mask_img.resize((target_size, target_size), Image.Resampling.LANCZOS)
								mask_data = np.array(mask_img)
							
							# Create OpenGL texture for mask
							mask_id = gl.glGenTextures(1)
							gl.glBindTexture(gl.GL_TEXTURE_2D, mask_id)
							
							# Use CLAMP_TO_BORDER to respect transparent edges
							gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_BORDER)
							gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_BORDER)
							# Set border color to transparent black
							gl.glTexParameterfv(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_BORDER_COLOR, [0.0, 0.0, 0.0, 0.0])
							gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
							gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
							
							gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, mask_img.width, mask_img.height,
							               0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, mask_data.tobytes())
							
							self.frame_masks[name] = mask_id
							
							# Use official frame scales and offsets from CK3 culture files
							if name in self.official_frame_scales:
								scale_data = self.official_frame_scales[name]
								self.frame_scales[name] = (scale_data[0]/1.05, scale_data[1]/1.05)
								# Use official offset if available, otherwise default to (0, 0)
								if name in self.official_frame_offsets:
									offset_data = self.official_frame_offsets[name]
									self.frame_offsets[name] = (offset_data[0], offset_data[1])
								else:
									self.frame_offsets[name] = (0.0, 0.0)
							else:
								# Fallback: unlisted frames default to 1.0 scale, no offset
								self.frame_scales[name] = (1.0, 1.0)
								self.frame_offsets[name] = (0.0, 0.0)
		except Exception as e:
			print(f"Error loading frame textures: {e}")
	
	def _load_official_frame_transforms(self):
		"""Load official frame scales and offsets from CK3 culture files"""
		try:
			transform_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ck3_assets', 'frame_transforms.json')
			transform_path = os.path.normpath(transform_path)
			
			if os.path.exists(transform_path):
				with open(transform_path, 'r') as f:
					data = json.load(f)
					self.official_frame_scales = data.get('frame_scales', {})
					self.official_frame_offsets = data.get('frame_offsets', {})
		except Exception as e:
			print(f"Error loading official frame transforms: {e}")
	
	def _load_mask_texture(self):
		"""Create a default white square mask texture matching real frame masks"""
		try:
			# Simple white square mask with transparent edges (size doesn't matter for sampler)
			size = 128
			mask_data = np.zeros((size, size, 4), dtype=np.uint8)
			
			# Create white square in center with transparent border (like house_mask.png)
			# Border is roughly 10% on each side
			border = int(size * 0.01)
			
			# Set center square to white
			mask_data[border:size-border, border:size-border] = [255, 255, 255, 255]
			
			# Edges remain transparent black [0, 0, 0, 0]
			
			self.default_mask_texture = gl.glGenTextures(1)
			gl.glBindTexture(gl.GL_TEXTURE_2D, self.default_mask_texture)
			
			# Match the settings used for loaded masks
			gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_BORDER)
			gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_BORDER)
			gl.glTexParameterfv(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_BORDER_COLOR, [0.0, 0.0, 0.0, 0.0])
			gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
			gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
			
			gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, size, size,
			               0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, mask_data.tobytes())
		except Exception as e:
			print(f"Error creating default mask texture: {e}")
	
	def _load_material_mask_texture(self):
		"""Load CK3 material mask texture (coa_mask_texture.png) for dirt/fabric/paint effects"""
		try:
			from utils.path_resolver import get_assets_dir
			material_mask_path = get_assets_dir() / 'coa_mask_texture.png'
			if os.path.exists(material_mask_path):
				img = Image.open(material_mask_path).convert('RGBA')
				# Resize to 128x128 to reduce compression artifacts
				img = img.resize((128, 128), Image.Resampling.LANCZOS)
				img_data = np.array(img)
				
				self.texturedMask = gl.glGenTextures(1)
				gl.glBindTexture(gl.GL_TEXTURE_2D, self.texturedMask)
				
				# Use REPEAT to tile the texture
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
				# Use trilinear filtering with mipmaps for smooth sampling
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR_MIPMAP_LINEAR)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
				
				gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, img.width, img.height,
				               0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, img_data.tobytes())
				gl.glGenerateMipmap(gl.GL_TEXTURE_2D)
			else:
				# Create a white fallback texture
				size = 256
				mask_data = np.full((size, size, 4), 255, dtype=np.uint8)
				
				self.texturedMask = gl.glGenTextures(1)
				gl.glBindTexture(gl.GL_TEXTURE_2D, self.texturedMask)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
				gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, size, size,
				               0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, mask_data.tobytes())
		except Exception as e:
			print(f"Error loading material mask texture: {e}")
	
	def _load_noise_texture(self):
		"""Load noise texture for grain effect"""
		try:
			from utils.path_resolver import get_resource_path
			# Use get_resource_path to handle both dev and frozen (bundled) modes
			noise_path = get_resource_path('assets', 'noise.png')
			
			if os.path.exists(noise_path):
				img = Image.open(noise_path).convert('RGBA')
				img_data = np.array(img)
				
				self.noiseMask = gl.glGenTextures(1)
				gl.glBindTexture(gl.GL_TEXTURE_2D, self.noiseMask)
				
				# Use REPEAT to tile the texture
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
				
				gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, img.width, img.height,
				               0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, img_data.tobytes())
			else:
				# Create a white fallback texture
				# Create a white fallback (no grain effect)
				size = 64
				noise_data = np.full((size, size, 4), 255, dtype=np.uint8)
				
				self.noiseMask = gl.glGenTextures(1)
				gl.glBindTexture(gl.GL_TEXTURE_2D, self.noiseMask)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
				gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, size, size,
				               0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, noise_data.tobytes())
		except Exception as e:
			print(f"Error loading noise texture: {e}")
	
	# ========================================
	# Texture and Frame Management
	# ========================================
	
	def set_frame(self, frame_name):
		"""Set the frame by name and update mask accordingly"""
		# Get old frame scale before changing
		old_scale, old_offset = self.get_frame_transform()
		
		if frame_name in self.frameTextures:
			self.frameTexture = self.frameTextures[frame_name]
			self.current_frame_name = frame_name
			# Update mask texture to match frame, or use default white mask
			if frame_name in self.frame_masks:
				self.patternMask = self.frame_masks[frame_name]
			else:
				self.patternMask = self.default_mask_texture
			self.update()
		elif frame_name == "None":
			self.frameTexture = None
			self.current_frame_name = "None"
			self.patternMask = self.default_mask_texture
			self.update()
		
		# Get new frame scale after changing
		new_scale, new_offset = self.get_frame_transform()
		
		# Notify transform widget to rescale proportionally
		if self.canvas_area and hasattr(self.canvas_area, 'transform_widget') and self.canvas_area.transform_widget.visible:
			scale_ratio_x = new_scale[0] / old_scale[0] if old_scale[0] != 0 else 1.0
			scale_ratio_y = new_scale[1] / old_scale[1] if old_scale[1] != 0 else 1.0
			offset_delta_x = new_offset[0] - old_offset[0]
			offset_delta_y = new_offset[1] - old_offset[1]
			self.canvas_area.transform_widget.rescale_for_frame_change(scale_ratio_x, scale_ratio_y, offset_delta_x, offset_delta_y)
	
	def get_frame_transform(self):
		"""Get the current frame's scale and offset
		
		Returns:
			tuple: ((scale_x, scale_y), (offset_x, offset_y))
		"""
		if self.current_frame_name == "None":
			return ((1.0, 1.0), (0.0, 0.0))
		elif self.current_frame_name in self.frame_scales:
			scale = self.frame_scales[self.current_frame_name]
			offset = self.frame_offsets.get(self.current_frame_name, (0.0, 0.04))
			return (scale, offset)
		else:
			# Default for unlisted frames
			return ((0.9, 0.9), (0.0, 0.04))
	
	def coa_to_frame_space(self, pos_x, pos_y):
		"""Convert CoA space coordinates to frame-adjusted visual space
		
		Args:
			pos_x, pos_y: Position in CoA space (0-1 range)
			
		Returns:
			tuple: (frame_x, frame_y) in visual frame space
		"""
		scale, offset = self.get_frame_transform()
		# Apply frame scale and offset
		frame_x = (pos_x - 0.5) * scale[0] + 0.5 + offset[0]
		frame_y = (pos_y - 0.5) * scale[1] + 0.5 + offset[1]
		return (frame_x, frame_y)
	
	def frame_to_coa_space(self, frame_x, frame_y):
		"""Convert frame-adjusted visual space to CoA space coordinates
		
		Args:
			frame_x, frame_y: Position in frame visual space
			
		Returns:
			tuple: (pos_x, pos_y) in CoA space (0-1 range)
		"""
		scale, offset = self.get_frame_transform()
		# Remove frame offset and scale
		pos_x = (frame_x - 0.5 + offset[0]) / scale[0] + 0.5
		pos_y = (frame_y - 0.5 + offset[1]) / scale[1] + 0.5
		return (pos_x, pos_y)
	
	def set_prestige(self, level):
		"""Set the prestige level (0-5)"""
		if 0 <= level <= 5:
			self.prestige_level = level
			self.update()
	
	def set_splendor(self, level):
		"""Set the splendor level (0-5) - same as prestige for rendering"""
		if 0 <= level <= 5:
			self.prestige_level = level
			self.update()
	
	def set_base_texture(self, filename):
		"""Set the base pattern texture"""
		if filename and filename in self.texture_uv_map:
			self.base_texture = filename
			self.update()
	
	def set_base_colors(self, colors):
		"""Set the base layer colors [color1, color2, color3] as RGB float arrays"""
		self.base_colors = colors
		self.update()
	
	def set_layers(self, layers):
		"""Update the emblem layers to render (DEPRECATED - kept for compatibility)"""
		# Deprecated: Canvas now uses CoA directly via get_all_layer_uuids()
		pass
	
	def resizeGL(self, w, h):
		"""Handle window resize - maintain square aspect ratio"""
		# Calculate square viewport centered in the widget
		size = min(w, h)
		x = (w - size) // 2
		y = (h - size) // 2
		gl.glViewport(x, y, size, size)
	
	# ========================================
	# Zoom and View Controls
	# ========================================
	
	def zoom_in(self):
		"""Zoom in by 25%"""
		self.zoom_level = min(self.zoom_level * 1.25, 4.0)  # Max 4x zoom
		self.update()
	
	def zoom_out(self):
		"""Zoom out by 25%"""
		self.zoom_level = max(self.zoom_level / 1.25, 0.25)  # Min 0.25x zoom
		self.update()
	
	def zoom_reset(self):
		"""Reset zoom to 100%"""
		self.zoom_level = 1.0
		self.update()
	
	def set_show_grid(self, show):
		"""Toggle grid visibility"""
		self.show_grid = show
		self.update()
	
	def set_grid_divisions(self, divisions):
		"""Set grid size (2, 4, 8, or 16)"""
		self.grid_divisions = divisions
		if self.show_grid:
			self.update()
	
	def export_to_png(self, filename):
		"""Export the current CoA rendering to PNG with transparency
		
		Args:
			filename: Path to save PNG file
			
		Returns:
			True if successful, False otherwise
		"""
		try:
			from PyQt5.QtGui import QImage, QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat
			from PyQt5.QtCore import QSize
			import numpy as np
			
			# Use 512x512 for export
			export_size = 512
			
			# Make this widget's context current
			self.makeCurrent()
			
			# Create framebuffer format with alpha channel
			fbo_format = QOpenGLFramebufferObjectFormat()
			fbo_format.setAttachment(QOpenGLFramebufferObject.CombinedDepthStencil)
			fbo_format.setInternalTextureFormat(0x8058)  # GL_RGBA8
			
			# Create Qt's OpenGL framebuffer object
			fbo = QOpenGLFramebufferObject(QSize(export_size, export_size), fbo_format)
			if not fbo.isValid():
				raise Exception("Failed to create framebuffer")
			
			# Bind the framebuffer
			fbo.bind()
			
			# Set viewport to export size
			gl.glViewport(0, 0, export_size, export_size)
			
			# Enable alpha blending for transparency
			gl.glEnable(gl.GL_BLEND)
			gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
			
			# Clear with transparent background
			gl.glClearColor(0.0, 0.0, 0.0, 0.0)
			gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
			
			# Render the CoA
			self._render_coa_for_export()
			
			# Read pixels directly from framebuffer to preserve alpha
			gl.glReadBuffer(gl.GL_COLOR_ATTACHMENT0)
			pixels = gl.glReadPixels(0, 0, export_size, export_size, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE)
			
			# Release framebuffer before creating image
			fbo.release()
			
			# Convert to numpy array and flip vertically (OpenGL origin is bottom-left)
			arr = np.frombuffer(pixels, dtype=np.uint8).reshape(export_size, export_size, 4)
			arr = np.flipud(arr).copy()  # copy() to make contiguous
			
			# Create QImage from bytes
			image = QImage(arr.tobytes(), export_size, export_size, export_size * 4, QImage.Format_RGBA8888)
			
			# Make a copy since the buffer will be deallocated
			image = image.copy()
			
			# Restore normal viewport and clear color
			gl.glViewport(0, 0, self.width(), self.height())
			gl.glClearColor(*self.clear_color)
			
			self.doneCurrent()
			
			# Save the image
			return image.save(filename, "PNG")
			
		except Exception as e:
			print(f"PNG export error: {e}")
			import traceback
			traceback.print_exc()
			
			# Try to restore context state
			try:
				gl.glViewport(0, 0, self.width(), self.height())
				gl.glClearColor(*self.clear_color)
				self.doneCurrent()
			except:
				pass
			
			return False
	
	def _render_coa_for_export(self):
		"""Render the CoA for export using the RTT pipeline"""
		if not self.vao:
			return
		
		# Save the export FBO handle and viewport before RTT unbinds it
		export_fbo = gl.glGetIntegerv(gl.GL_FRAMEBUFFER_BINDING)
		viewport = gl.glGetIntegerv(gl.GL_VIEWPORT)  # [x, y, width, height]
		
		# Render to internal RTT framebuffer (this will unbind to screen)
		self._render_coa_to_framebuffer()
		
		# Re-bind export FBO and restore viewport
		gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, export_fbo)
		gl.glViewport(viewport[0], viewport[1], viewport[2], viewport[3])
		
		# Composite RTT texture to export FBO
		self._composite_to_fbo(export_fbo)
		
		# Render frame on top if present
		if self.frameTexture:
			self._render_frame()
	
	# ========================================
	# Mouse Event Handlers
	# ========================================
	
	def mousePressEvent(self, event):
		"""Handle mouse press events"""
		pass
