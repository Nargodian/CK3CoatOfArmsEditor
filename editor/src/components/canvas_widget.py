# PyQt5 imports
from PyQt5.QtWidgets import QOpenGLWidget, QSizePolicy
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QOpenGLShaderProgram, QOpenGLShader, QOpenGLVertexArrayObject, QOpenGLBuffer, QVector2D, QVector3D, QVector4D
from models.coa import CoA

#COA INTEGRATION ACTION: Step 5 - Import Layer and CoA models for type hints and future use
from models.coa import CoA, Layer

# Canvas tools mixin
from components.canvas_widgets.canvas_tools_mixin import CanvasToolsMixin
from components.canvas_widgets.canvas_preview_mixin import CanvasPreviewMixin

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


def layer_pos_to_qt_pixels(pos_x, pos_y, canvas_size, offset_x=0, offset_y=0, zoom_level=1.0, pan_x=0.0, pan_y=0.0):
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
		
	Returns:
		(qt_x, qt_y): Qt pixel coordinates (Y-down)
	"""
	# First convert to OpenGL coords
	gl_x, gl_y = layer_pos_to_opengl_coords(pos_x, pos_y)
	
	# Convert OpenGL normalized (-1.0 to +1.0) to pixels
	# Apply zoom and composite scale
	# Use canvas_size (the square dimension) for both to maintain square aspect
	pixel_x = gl_x * (canvas_size[1] / 2) * VIEWPORT_BASE_SIZE * COMPOSITE_SCALE * zoom_level
	pixel_y = gl_y * (canvas_size[1] / 2) * VIEWPORT_BASE_SIZE * COMPOSITE_SCALE * zoom_level
	
	# Qt Y-axis is inverted (down is positive)
	# Canvas center is at (offset + size/2, offset + size/2)
	# Apply pan offset (already in pixels)
	qt_x = offset_x + canvas_size[1] / 2 + pixel_x + pan_x
	qt_y = offset_y + canvas_size[1] / 2 - pixel_y + pan_y  # Negate Y for Qt coords
	
	return qt_x, qt_y


def qt_pixels_to_layer_pos(qt_x, qt_y, canvas_size, offset_x=0, offset_y=0, zoom_level=1.0, pan_x=0.0, pan_y=0.0):
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
		
	Returns:
		(pos_x, pos_y): Layer position (0-1 range, 0=top in CK3)
	"""
	# Remove pan offset first
	pixel_x = qt_x - offset_x - canvas_size[1] / 2 - pan_x
	pixel_y = qt_y - offset_y - canvas_size[1] / 2 - pan_y
	
	# Convert pixels to OpenGL normalized space
	# Qt Y-down to OpenGL Y-up: negate pixel_y
	# Account for zoom and composite scale
	gl_x = pixel_x / (canvas_size[1] / 2) / VIEWPORT_BASE_SIZE / COMPOSITE_SCALE / zoom_level
	gl_y = -pixel_y / (canvas_size[1] / 2) / VIEWPORT_BASE_SIZE / COMPOSITE_SCALE / zoom_level
	
	# Convert OpenGL coords back to layer position
	# layer_pos_to_opengl_coords: gl_x = pos_x * 2.0 - 1.0
	# Reversing: pos_x = (gl_x + 1.0) / 2.0
	# layer_pos_to_opengl_coords: gl_y = -(pos_y * 2.0 - 1.0)
	# Reversing: pos_y = (-gl_y + 1.0) / 2.0
	pos_x = (gl_x + 1.0) / 2.0
	pos_y = (-gl_y + 1.0) / 2.0
	
	return pos_x, pos_y


class CoatOfArmsCanvas(CanvasPreviewMixin, CanvasToolsMixin, QOpenGLWidget):
	"""OpenGL canvas for rendering coat of arms with shaders"""
	
	def __init__(self, parent=None):
		super().__init__(parent)
		
		# Enable wheel events and mouse tracking
		self.setFocusPolicy(Qt.WheelFocus)
		self.setMouseTracking(True)
		
		# Allow widget to expand to fill available space
		self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
		
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
		
		# Pan properties (OpenGL coordinates -1 to 1)
		self.pan_x = 0.0
		self.pan_y = 0.0
		
		# Mouse drag state for panning
		self.is_panning = False
		self.last_mouse_pos = None
		
		# Store clear color for restoration after export
		self.clear_color = (0.95, 0.95, 0.95, 0.0)  # Default, updated in initializeGL
		
		# Initialize tool system (from CanvasToolsMixin)
		self._init_tools()
		
		# Preview system
		self.preview_enabled = False
		self.preview_government = "_default"  # Default government type
		self.preview_rank = "Duke"  # Default rank
		self.preview_size = 86  # Default size in pixels
		self.realm_frame_masks = {}  # government_name -> texture ID
		self.realm_frame_frames = {}  # (government_name, size) -> texture ID
		self.realm_frame_shadows = {}  # (government_name, size) -> texture ID
		self.title_mask = None  # title_mask.png texture ID
		self.crown_strips = {}  # size -> texture ID
		self.title_frames = {}  # size -> texture ID  
		self.topframes = {}  # size -> texture ID
	
	# ========================================
	# Qt OpenGL Widget Overrides
	# ========================================
	
	def resizeEvent(self, event):
		"""Override resize - allow full container size when zoomed, square when at 100%"""
		super().resizeEvent(event)
		# Don't force square when zoomed - let it use full container space
		# The viewport will be set correctly in paintGL
	
	def sizeHint(self):
		"""Suggest initial size - will expand to fill container"""
		# Return parent size if available, otherwise default
		if self.parent():
			return self.parent().size()
		return QSize(800, 600)
	
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
			self.clear_color = (0.08, 0.08, 0.08, 1.0)  # Dark gray background
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
		self.picker_shader = shader_manager.create_picker_shader(self)
		self.main_composite_shader = shader_manager.create_main_composite_shader(self)
		
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
		
		# Load realm frames and title frames for preview system
		self._load_realm_frame_textures()
		self._load_title_frame_textures()
		
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
		# Use full widget dimensions (no longer forcing square)
		gl.glViewport(0, 0, self.width(), self.height())
		
		# Composite framebuffer to viewport with frame mask
		self._composite_to_viewport()
		
		# Render frame graphic on top
		self._render_frame()
		
		# Render preview overlays if enabled
		if self.preview_enabled:
			self._render_government_preview()
			self._render_title_preview()
	
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
				
				# Determine if selection tint should be shown
				# Show if: show_selection button is checked OR picker tool is active
				show_tint = False
				if hasattr(self, 'canvas_area') and self.canvas_area:
					show_selection_checked = getattr(self.canvas_area, 'show_selection_btn', None) and self.canvas_area.show_selection_btn.isChecked()
					picker_active = getattr(self.canvas_area, 'picker_btn', None) and self.canvas_area.picker_btn.isChecked()
					show_tint = show_selection_checked or picker_active
				
				# Check if this layer is selected
				is_selected = False
				if show_tint and hasattr(self, 'canvas_area') and self.canvas_area:
					if hasattr(self.canvas_area, 'main_window') and self.canvas_area.main_window:
						if hasattr(self.canvas_area.main_window, 'right_sidebar'):
							selected_uuids = self.canvas_area.main_window.right_sidebar.layer_list_widget.selected_layer_uuids
							is_selected = layer_uuid in selected_uuids
				
				# Set selection tint uniform (1.0 if selected and tint enabled, 0.0 otherwise)
				self.design_shader.setUniformValue("selectionTint", 1.0 if is_selected else 0.0)
				
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
					pos_x = instance.pos.x
					pos_y = instance.pos.y
					scale_x = instance.scale.x
					scale_y = instance.scale.y
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
		
		# Bind picker texture and set mouse UV
		picker_texture_id = self._get_picker_texture_id()
		if picker_texture_id:
			gl.glActiveTexture(gl.GL_TEXTURE4)
			gl.glBindTexture(gl.GL_TEXTURE_2D, picker_texture_id)
			self.composite_shader.setUniformValue("pickerTextureSampler", 4)
		
		# Set mouse UV (negative if not in picker mode)
		mouse_uv = self._get_picker_mouse_uv()
		self.composite_shader.setUniformValue("mouseUV", QVector2D(mouse_uv[0], mouse_uv[1]))
		
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
		
		# Composite quad size with zoom and pan applied
		base_size = VIEWPORT_BASE_SIZE * COMPOSITE_SCALE * safeMargin * self.zoom_level
		
		# Calculate aspect ratio correction to keep CoA square
		aspect = self.width() / self.height() if self.height() > 0 else 1.0
		if aspect > 1.0:
			# Width > Height: compress horizontally
			size_x = base_size / aspect
			size_y = base_size
		else:
			# Height > Width: compress vertically
			size_x = base_size
			size_y = base_size * aspect
		
		# Apply pan offset (convert from pixels to normalized coordinates)
		# Use square canvas_size to match coordinate conversion functions
		canvas_size = min(self.width(), self.height())
		pan_offset_x = self.pan_x / (canvas_size / 2) if canvas_size > 0 else 0
		pan_offset_y = -self.pan_y / (canvas_size / 2) if canvas_size > 0 else 0
		
		# Scale pan offset by same aspect correction applied to quad
		if aspect > 1.0:
			pan_offset_x /= aspect
		else:
			pan_offset_y *= aspect
		
		# Texture coords: RTT renders Y-up (OpenGL standard), texture V=0 at bottom, V=1 at top
		# Position Y=-1 (bottom) → V=0, Position Y=+1 (top) → V=1
		vertices = np.array([
			-size_x + pan_offset_x, -size_y + pan_offset_y, 0.0,  0.0, 0.0,  # bottom-left
			 size_x + pan_offset_x, -size_y + pan_offset_y, 0.0,  1.0, 0.0,  # bottom-right
			 size_x + pan_offset_x,  size_y + pan_offset_y, 0.0,  1.0, 1.0,  # top-right
			-size_x + pan_offset_x,  size_y + pan_offset_y, 0.0,  0.0, 1.0,  # top-left
		], dtype=np.float32)
		
		self.vbo.write(0, vertices.tobytes(), vertices.nbytes)
		
		# OLD COMPOSITE: Skip draw call - keeping setup for infrastructure
		# gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
		
		self.composite_shader.release()
		
		# NEW MAIN COMPOSITE: Render with frame-aware positioning
		self._render_main_composite(vertices, size_x, size_y, pan_offset_x, pan_offset_y, aspect)
		
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
	
	def _render_frame(self, viewport_size=None):
		"""Render frame graphic on top of CoA
		
		Args:
			viewport_size: Optional (width, height) tuple for export rendering.
			              If None, uses widget dimensions.
		"""
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
		
		# Frame renders at VIEWPORT_BASE_SIZE (larger than composite which is scaled down)
		# Apply zoom and pan to match composite positioning
		# Use viewport_size for export, or widget dimensions for normal rendering
		if viewport_size:
			width, height = viewport_size
		else:
			width = self.width()
			height = self.height()
		base_size = VIEWPORT_BASE_SIZE * self.zoom_level
		
		# Calculate aspect ratio correction to keep frame square
		aspect = width / height if height > 0 else 1.0
		if aspect > 1.0:
			# Width > Height: compress horizontally
			size_x = base_size / aspect
			size_y = base_size
		else:
			# Height > Width: compress vertically
			size_x = base_size
			size_y = base_size * aspect
		
		# Apply pan offset (convert to normalized coordinates)
		# Use square canvas_size to match coordinate conversion functions
		canvas_size = min(width, height)
		pan_offset_x = self.pan_x / (canvas_size / 2)
		pan_offset_y = -self.pan_y / (canvas_size / 2)
		
		# Scale pan offset by same aspect correction applied to quad
		if aspect > 1.0:
			pan_offset_x /= aspect
		else:
			pan_offset_y *= aspect
		
		vertices = np.array([
			-size_x + pan_offset_x, -size_y + pan_offset_y, 0.0,  u0, 1.0,
			 size_x + pan_offset_x, -size_y + pan_offset_y, 0.0,  u1, 1.0,
			 size_x + pan_offset_x,  size_y + pan_offset_y, 0.0,  u1, 0.0,
			-size_x + pan_offset_x,  size_y + pan_offset_y, 0.0,  u0, 0.0,
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
		
		# Draw vertical and horizontal lines - zoom handled by widget resize
		grid_size = VIEWPORT_BASE_SIZE
		grid_step = (VIEWPORT_BASE_SIZE * 2.0) / self.grid_divisions  # Divide into grid_divisions
		
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
	
	# Government and title preview methods moved to CanvasPreviewMixin
	
	# ========================================
	# Texture Loading and Atlas Management
	# ========================================
		"""Render government preview in top-left corner"""
		if not self.composite_shader or not self.vao:
			return
		
		# Get government mask
		gov_mask = self.realm_frame_masks.get(self.preview_government)
		if not gov_mask:
			return
		
		# Calculate corner-anchored position (top-left with 20px padding)
		# Size in pixels, then convert to NDC
		preview_size_px = self.preview_size
		viewport_width = self.width()
		viewport_height = self.height()
		
		# Convert to NDC
		size_x = preview_size_px / viewport_width
		size_y = preview_size_px / viewport_height
		
		# 20px padding from corner
		padding_x = 20.0 / viewport_width
		padding_y = 20.0 / viewport_height
		
		# Position: top-left corner with padding
		left = -1.0 + padding_x * 2.0
		top = 1.0 - padding_y * 2.0
		right = left + size_x * 2.0
		bottom = top - size_y * 2.0
		
		# Shift entire preview down to accommodate crown above
		crown_height = size_y * 2.0 * (80.0 / 128.0)
		top -= crown_height
		bottom -= crown_height
		
		# Render government shadow FIRST (behind everything, flipped vertically)
		# TEMPORARILY DISABLED to debug ghosty layer
		"""
		gov_shadow = self.realm_frame_shadows.get((self.preview_government, self.preview_size))
		if gov_shadow and self.basic_shader:
			self.vao.bind()
			self.basic_shader.bind()
			
			gl.glActiveTexture(gl.GL_TEXTURE0)
			gl.glBindTexture(gl.GL_TEXTURE_2D, gov_shadow)
			self.basic_shader.setUniformValue("textureSampler", 0)
			
			# Flip V coordinates for shadow
			shadow_verts = np.array([
				left, bottom, 0.0,  0.0, 1.0,  # Flipped V
				right, bottom, 0.0,  1.0, 1.0,
				right, top, 0.0,  1.0, 0.0,
				left, top, 0.0,  0.0, 0.0,
			], dtype=np.float32)
			
			self.vbo.write(0, shadow_verts.tobytes(), shadow_verts.nbytes)
			gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
			
			self.basic_shader.release()
			self.vao.release()
		"""
		
		# Render CoA with government mask
		self.vao.bind()
		self.composite_shader.bind()
		
		# Bind RTT texture (same CoA)
		gl.glActiveTexture(gl.GL_TEXTURE0)
		gl.glBindTexture(gl.GL_TEXTURE_2D, self.framebuffer_rtt.get_texture())
		self.composite_shader.setUniformValue("coaTextureSampler", 0)
		
		# Bind government mask
		gl.glActiveTexture(gl.GL_TEXTURE1)
		gl.glBindTexture(gl.GL_TEXTURE_2D, gov_mask)
		self.composite_shader.setUniformValue("frameMaskSampler", 1)
		
		# Bind material and noise textures
		if self.texturedMask:
			gl.glActiveTexture(gl.GL_TEXTURE2)
			gl.glBindTexture(gl.GL_TEXTURE_2D, self.texturedMask)
			self.composite_shader.setUniformValue("texturedMaskSampler", 2)
		
		if self.noiseMask:
			gl.glActiveTexture(gl.GL_TEXTURE3)
			gl.glBindTexture(gl.GL_TEXTURE_2D, self.noiseMask)
			self.composite_shader.setUniformValue("noiseMaskSampler", 3)
		
		# Set CoA scale and offset
		self.composite_shader.setUniformValue("coaScale", QVector2D(0.9, 0.9))
		self.composite_shader.setUniformValue("coaOffset", QVector2D(0.0, 0.1))
		self.composite_shader.setUniformValue("bleedMargin", 1.0)
		
		# Render quad
		vertices = np.array([
			left, bottom, 0.0,  0.0, 0.0,
			right, bottom, 0.0,  1.0, 0.0,
			right, top, 0.0,  1.0, 1.0,
			left, top, 0.0,  0.0, 1.0,
		], dtype=np.float32)
		
		self.vbo.write(0, vertices.tobytes(), vertices.nbytes)
		gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
		
		self.composite_shader.release()
		
		# Render government frame on top (flipped vertically)
		gov_frame = self.realm_frame_frames.get((self.preview_government, self.preview_size))
		if gov_frame and self.basic_shader:
			self.basic_shader.bind()
			
			gl.glActiveTexture(gl.GL_TEXTURE0)
			gl.glBindTexture(gl.GL_TEXTURE_2D, gov_frame)
			self.basic_shader.setUniformValue("textureSampler", 0)
			
			# Flip V coordinates
			frame_verts = np.array([
				left, bottom, 0.0,  0.0, 1.0,  # Flipped V
				right, bottom, 0.0,  1.0, 1.0,
				right, top, 0.0,  1.0, 0.0,
				left, top, 0.0,  0.0, 0.0,
			], dtype=np.float32)
			
			self.vbo.write(0, frame_verts.tobytes(), frame_verts.nbytes)
			gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
			
			self.basic_shader.release()
		
		# Render crown strip (rank-based UV from 7x1 atlas)
		# Crown dimensions: 896x80 (each section 128x80, aspect ratio 1.6:1)
		# Crown sits ABOVE the CoA, with crown bottom aligned to CoA top
		crown_strip = self.crown_strips.get(self.preview_size)
		if crown_strip and self.basic_shader:
			u0, u1 = self._get_rank_uv(self.preview_rank)
			self.basic_shader.bind()
			
			gl.glActiveTexture(gl.GL_TEXTURE0)
			gl.glBindTexture(gl.GL_TEXTURE_2D, crown_strip)
			self.basic_shader.setUniformValue("textureSampler", 0)
			
			# Crown aspect ratio: 128:80 = 1.6:1 (wider than tall)
			# Crown bottom aligns with CoA top, crown extends upward
			# Shift up 7.5px at size 115, scale proportionally
			crown_offset_px = (7.5 / 115.0) * self.preview_size
			crown_offset = (crown_offset_px / viewport_height) * 2.0
			crown_bottom = top + crown_offset
			crown_top = top + crown_height + crown_offset
			
			# Use rank-specific UV coordinates, flipped vertically (V: 1.0 to 0.0)
			crown_verts = np.array([
				left, crown_bottom, 0.0,  u0, 1.0,  # Flipped V
				right, crown_bottom, 0.0,  u1, 1.0,
				right, crown_top, 0.0,  u1, 0.0,
				left, crown_top, 0.0,  u0, 0.0,
			], dtype=np.float32)
			
			self.vbo.write(0, crown_verts.tobytes(), crown_verts.nbytes)
			gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
			
			self.basic_shader.release()
		
		# Render topframe (rank-based UV from 7x1 atlas)
		# Topframe dimensions: 896x128 (each section 128x128, aspect ratio 1:1)
		topframe = self.topframes.get(self.preview_size)
		if topframe and self.basic_shader:
			u0, u1 = self._get_rank_uv(self.preview_rank)
			self.basic_shader.bind()
			
			gl.glActiveTexture(gl.GL_TEXTURE0)
			gl.glBindTexture(gl.GL_TEXTURE_2D, topframe)
			self.basic_shader.setUniformValue("textureSampler", 0)
			
			# Topframe is square (128x128), use full preview size
			# Topframe content starts ~7% from top of image (varies by size)
			# Content start pixels: size 28:1px, 44:2px, 62:3px, 86:5px, 115:8px
			# Position topframe so content sits just below crown (0px gap)
			# Scale the offset based on size: 10px at 115 scales to other sizes
			# Plus 6px upward shift
			topframe_offset_px = (10.0 / 115.0) * self.preview_size + (6.0 / 115.0) * self.preview_size
			topframe_offset = (topframe_offset_px / viewport_height) * 2.0
			topframe_bottom = bottom + topframe_offset
			topframe_top = top + topframe_offset
			
			# Use rank-specific UV coordinates, flipped vertically
			topframe_verts = np.array([
				left, topframe_bottom, 0.0,  u0, 1.0,  # Flipped V
				right, topframe_bottom, 0.0,  u1, 1.0,
				right, topframe_top, 0.0,  u1, 0.0,
				left, topframe_top, 0.0,  u0, 0.0,
			], dtype=np.float32)
			
			self.vbo.write(0, topframe_verts.tobytes(), topframe_verts.nbytes)
			gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
			
			self.basic_shader.release()
		
		self.vao.release()
	
	# ========================================
	# Texture Loading and Atlas Management
	# ========================================
		"""Render title preview in top-right corner"""
		if not self.composite_shader or not self.vao:
			return
		
		# Get title mask
		if not self.title_mask:
			return
		
		# Calculate corner-anchored position (top-right with 20px padding)
		preview_size_px = self.preview_size
		viewport_width = self.width()
		viewport_height = self.height()
		
		# Convert to NDC
		size_x = preview_size_px / viewport_width
		size_y = preview_size_px / viewport_height
		
		# 20px padding from corner
		padding_x = 20.0 / viewport_width
		padding_y = 20.0 / viewport_height
		
		# Position: top-right corner with padding
		right = 1.0 - padding_x * 2.0
		top = 1.0 - padding_y * 2.0
		left = right - size_x * 2.0
		bottom = top - size_y * 2.0
		
		# Shift entire preview down to accommodate crown above
		crown_height = size_y * 2.0 * (80.0 / 128.0)
		top -= crown_height
		bottom -= crown_height
		
		# Render CoA with title mask
		self.vao.bind()
		self.composite_shader.bind()
		
		# Bind RTT texture (same CoA)
		gl.glActiveTexture(gl.GL_TEXTURE0)
		gl.glBindTexture(gl.GL_TEXTURE_2D, self.framebuffer_rtt.get_texture())
		self.composite_shader.setUniformValue("coaTextureSampler", 0)
		
		# Bind title mask
		gl.glActiveTexture(gl.GL_TEXTURE1)
		gl.glBindTexture(gl.GL_TEXTURE_2D, self.title_mask)
		self.composite_shader.setUniformValue("frameMaskSampler", 1)
		
		# Bind material and noise textures
		if self.texturedMask:
			gl.glActiveTexture(gl.GL_TEXTURE2)
			gl.glBindTexture(gl.GL_TEXTURE_2D, self.texturedMask)
			self.composite_shader.setUniformValue("texturedMaskSampler", 2)
		
		if self.noiseMask:
			gl.glActiveTexture(gl.GL_TEXTURE3)
			gl.glBindTexture(gl.GL_TEXTURE_2D, self.noiseMask)
			self.composite_shader.setUniformValue("noiseMaskSampler", 3)
		
		# Set CoA scale and offset
		self.composite_shader.setUniformValue("coaScale", QVector2D(0.9, 0.9))
		self.composite_shader.setUniformValue("coaOffset", QVector2D(0.0, 0.04))
		self.composite_shader.setUniformValue("bleedMargin", 1.0)
		
		# Render quad
		vertices = np.array([
			left, bottom, 0.0,  0.0, 0.0,
			right, bottom, 0.0,  1.0, 0.0,
			right, top, 0.0,  1.0, 1.0,
			left, top, 0.0,  0.0, 1.0,
		], dtype=np.float32)
		
		self.vbo.write(0, vertices.tobytes(), vertices.nbytes)
		gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
		
		self.composite_shader.release()
		
		# Render crown strip (rank-based UV from 7x1 atlas)
		# Crown dimensions: 896x80 (each section 128x80, aspect ratio 1.6:1)
		# Crown sits ABOVE the CoA, with crown bottom aligned to CoA top
		crown_strip = self.crown_strips.get(self.preview_size)
		if crown_strip and self.basic_shader:
			u0, u1 = self._get_rank_uv(self.preview_rank)
			self.basic_shader.bind()
			
			gl.glActiveTexture(gl.GL_TEXTURE0)
			gl.glBindTexture(gl.GL_TEXTURE_2D, crown_strip)
			self.basic_shader.setUniformValue("textureSampler", 0)
			
			# Crown aspect ratio: 128:80 = 1.6:1 (wider than tall)
			# Crown bottom aligns with CoA top, crown extends upward
			# Move crown up 1.5px at size 115, scale proportionally
			# Additional adjustment: 0px at 115, -2px at 22 (linear interpolation)
			base_offset_px = (1.5 / 115.0) * self.preview_size
			size_adjustment = -2.0 * (115.0 - self.preview_size) / 93.0
			crown_offset_px = base_offset_px + size_adjustment
			crown_offset = (crown_offset_px / viewport_height) * 2.0
			crown_bottom = top + crown_offset
			crown_top = top + crown_height + crown_offset
			
			# Use rank-specific UV coordinates, flipped vertically (V: 1.0 to 0.0)
			crown_verts = np.array([
				left, crown_bottom, 0.0,  u0, 1.0,  # Flipped V
				right, crown_bottom, 0.0,  u1, 1.0,
				right, crown_top, 0.0,  u1, 0.0,
				left, crown_top, 0.0,  u0, 0.0,
			], dtype=np.float32)
			
			self.vbo.write(0, crown_verts.tobytes(), crown_verts.nbytes)
			gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
			
			self.basic_shader.release()
		
		# Title frame (flipped vertically, scaled 1.2x)
		title_frame = self.title_frames.get(self.preview_size)
		# Fallback: if title_115 missing, use title_86 scaled up
		if not title_frame and self.preview_size == 115:
			title_frame = self.title_frames.get(86)
		
		if title_frame and self.basic_shader:
			self.basic_shader.bind()
			
			gl.glActiveTexture(gl.GL_TEXTURE0)
			gl.glBindTexture(gl.GL_TEXTURE_2D, title_frame)
			self.basic_shader.setUniformValue("textureSampler", 0)
			
			# Apply 1.2x scale to title frame
			scale_factor = 1.1
			frame_width = (right - left) * scale_factor
			frame_height = (top - bottom) * scale_factor
			frame_center_x = (left + right) / 2.0
			frame_center_y = (top + bottom) / 2.0
			frame_left = frame_center_x - frame_width / 2.0
			frame_right = frame_center_x + frame_width / 2.0
			frame_bottom = frame_center_y - frame_height / 2.0
			frame_top = frame_center_y + frame_height / 2.0
			
			# Flip V coordinates
			title_frame_verts = np.array([
				frame_left, frame_bottom, 0.0,  0.0, 1.0,  # Flipped V
				frame_right, frame_bottom, 0.0,  1.0, 1.0,
				frame_right, frame_top, 0.0,  1.0, 0.0,
				frame_left, frame_top, 0.0,  0.0, 0.0,
			], dtype=np.float32)
			
			self.vbo.write(0, title_frame_verts.tobytes(), title_frame_verts.nbytes)
			gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
			
			self.basic_shader.release()
		
		self.vao.release()
	
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
			from utils.path_resolver import get_assets_dir
			transform_path = get_assets_dir() / "frame_transforms.json"
			
			if transform_path.exists():
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
	
	def _load_realm_frame_textures(self):
		"""Load government-specific realm frame masks, frames, and shadows"""
		try:
			from utils.path_resolver import get_resource_path
			realm_frames_dir = get_resource_path('..', 'ck3_assets', 'realm_frames')
			
			if not os.path.exists(realm_frames_dir):
				print(f"Realm frames directory not found: {realm_frames_dir}")
				return
			
			# Load masks (one per government type)
			for mask_file in Path(realm_frames_dir).glob("*_mask.png"):
				gov_name = mask_file.stem.replace("_mask", "")
				
				img = Image.open(mask_file).convert('RGBA')
				img_data = np.array(img)
				
				texture_id = gl.glGenTextures(1)
				gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
				gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, img.width, img.height,
				               0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, img_data.tobytes())
				
				self.realm_frame_masks[gov_name] = texture_id
			
			# Load frames and shadows (per government + size)
			for frame_file in Path(realm_frames_dir).glob("*_frame.png"):
				# Parse filename: government_size_frame.png
				stem = frame_file.stem.replace("_frame", "")
				parts = stem.rsplit("_", 1)
				if len(parts) == 2:
					gov_name, size_str = parts
					try:
						size = int(size_str)
						img = Image.open(frame_file).convert('RGBA')
						img_data = np.array(img)
						
						texture_id = gl.glGenTextures(1)
						gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
						gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
						gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
						gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
						gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
						gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, img.width, img.height,
						               0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, img_data.tobytes())
						
						self.realm_frame_frames[(gov_name, size)] = texture_id
					except ValueError:
						pass
			
			for shadow_file in Path(realm_frames_dir).glob("*_shadow.png"):
				stem = shadow_file.stem.replace("_shadow", "")
				parts = stem.rsplit("_", 1)
				if len(parts) == 2:
					gov_name, size_str = parts
					try:
						size = int(size_str)
						img = Image.open(shadow_file).convert('RGBA')
						img_data = np.array(img)
						
						texture_id = gl.glGenTextures(1)
						gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
						gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
						gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
						gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
						gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
						gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, img.width, img.height,
						               0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, img_data.tobytes())
						
						self.realm_frame_shadows[(gov_name, size)] = texture_id
					except ValueError:
						pass
			
			print(f"Loaded {len(self.realm_frame_masks)} government masks, {len(self.realm_frame_frames)} frames, {len(self.realm_frame_shadows)} shadows")
		except Exception as e:
			print(f"Error loading realm frame textures: {e}")
	
	def _load_title_frame_textures(self):
		"""Load title frame assets (title_mask, crown_strip, title, topframe)"""
		try:
			from utils.path_resolver import get_resource_path
			title_frames_dir = get_resource_path('..', 'ck3_assets', 'title_frames')
			
			if not os.path.exists(title_frames_dir):
				print(f"Title frames directory not found: {title_frames_dir}")
				return
			
			# Load title mask
			title_mask_path = Path(title_frames_dir) / "title_mask.png"
			if title_mask_path.exists():
				img = Image.open(title_mask_path).convert('RGBA')
				img_data = np.array(img)
				
				self.title_mask = gl.glGenTextures(1)
				gl.glBindTexture(gl.GL_TEXTURE_2D, self.title_mask)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
				gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
				gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, img.width, img.height,
				               0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, img_data.tobytes())
			
			# Load crown strips (by size)
			for crown_file in Path(title_frames_dir).glob("crown_strip_*.png"):
				if "gameconcept" in crown_file.stem:
					continue  # Skip gameconcept variant
				size_str = crown_file.stem.replace("crown_strip_", "")
				try:
					size = int(size_str)
					img = Image.open(crown_file).convert('RGBA')
					img_data = np.array(img)
					
					texture_id = gl.glGenTextures(1)
					gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
					gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
					gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
					gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
					gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
					gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, img.width, img.height,
					               0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, img_data.tobytes())
					
					self.crown_strips[size] = texture_id
				except ValueError:
					pass
			
			# Load title frames (by size)
			for title_file in Path(title_frames_dir).glob("title_*.png"):
				if title_file.name == "title_mask.png":
					continue
				size_str = title_file.stem.replace("title_", "")
				try:
					size = int(size_str)
					img = Image.open(title_file).convert('RGBA')
					img_data = np.array(img)
					
					texture_id = gl.glGenTextures(1)
					gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
					gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
					gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
					gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
					gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
					gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, img.width, img.height,
					               0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, img_data.tobytes())
					
					self.title_frames[size] = texture_id
				except ValueError:
					pass
			
			# Load topframes (by size)
			for topframe_file in Path(title_frames_dir).glob("topframe_*.png"):
				size_str = topframe_file.stem.replace("topframe_", "")
				try:
					size = int(size_str)
					img = Image.open(topframe_file).convert('RGBA')
					img_data = np.array(img)
					
					texture_id = gl.glGenTextures(1)
					gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
					gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
					gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
					gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
					gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
					gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, img.width, img.height,
					               0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, img_data.tobytes())
					
					self.topframes[size] = texture_id
				except ValueError:
					pass
			
			print(f"Loaded title mask, {len(self.crown_strips)} crown strips, {len(self.title_frames)} title frames, {len(self.topframes)} topframes")
		except Exception as e:
			print(f"Error loading title frame textures: {e}")
	
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
			self.canvas_area.transform_widget.rescale_for_frame_change(
				scale_ratio_x, scale_ratio_y, 
				offset_delta_x, offset_delta_y,
				new_scale[0], new_scale[1]
			)
	
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
	
	def _render_main_composite(self, frame_vertices, size_x, size_y, pan_offset_x, pan_offset_y, aspect):
		"""Render CoA using new main composite shader with frame-aware positioning
		
		Args:
			frame_vertices: Frame quad vertices array
			size_x: Half-width of frame quad in NDC
			size_y: Half-height of frame quad in NDC
			pan_offset_x: Pan offset in NDC X
			pan_offset_y: Pan offset in NDC Y
			aspect: Viewport aspect ratio
		"""
		if not self.main_composite_shader:
			return
		
		self.main_composite_shader.bind()
		
		# Bind RTT texture
		gl.glActiveTexture(gl.GL_TEXTURE0)
		gl.glBindTexture(gl.GL_TEXTURE_2D, self.framebuffer_rtt.get_texture())
		self.main_composite_shader.setUniformValue("coaTextureSampler", 0)
		
		# Get frame transform (scale and offset for CoA positioning)
		frame_scale, frame_offset = self.get_frame_transform()
		
		# Calculate CoA render area in NDC space (same as frame quad space)
		# Frame quad spans from -size_x to +size_x, -size_y to +size_y (in NDC)
		# Apply frame scale and offset to get CoA area
		coa_width = size_x * 2.0 * frame_scale[0]
		coa_height = size_y * 2.0 * frame_scale[1]
		coa_center_x = pan_offset_x + frame_offset[0] * size_x * 2.0
		coa_center_y = pan_offset_y + frame_offset[1] * size_y * 2.0
		
		# Convert NDC corners to viewport pixel coordinates
		viewport_width = self.width()
		viewport_height = self.height()
		
		# NDC to pixels: NDC=0 is center, NDC=-1 is left/bottom, NDC=+1 is right/top
		coa_left_ndc = coa_center_x - coa_width / 2.0
		coa_right_ndc = coa_center_x + coa_width / 2.0
		coa_bottom_ndc = coa_center_y - coa_height / 2.0
		coa_top_ndc = coa_center_y + coa_height / 2.0
		
		# Convert to pixel coordinates (0,0 is bottom-left in OpenGL)
		coa_left_px = (coa_left_ndc + 1.0) / 2.0 * viewport_width
		coa_right_px = (coa_right_ndc + 1.0) / 2.0 * viewport_width
		coa_bottom_px = (coa_bottom_ndc + 1.0) / 2.0 * viewport_height
		coa_top_px = (coa_top_ndc + 1.0) / 2.0 * viewport_height
		
		# Set uniforms
		self.main_composite_shader.setUniformValue("coaTopLeft", coa_left_px, coa_top_px)
		self.main_composite_shader.setUniformValue("coaBottomRight", coa_right_px, coa_bottom_px)
		
		# DEBUG: Print values once
		if not hasattr(self, '_debug_printed'):
			print(f"DEBUG Main Composite:")
			print(f"  Frame scale: {frame_scale}, offset: {frame_offset}")
			print(f"  Viewport: {viewport_width}x{viewport_height}")
			print(f"  NDC size_x: {size_x}, size_y: {size_y}")
			print(f"  CoA NDC width: {coa_width}, height: {coa_height}")
			print(f"  CoA center NDC: ({coa_center_x}, {coa_center_y})")
			print(f"  CoA pixels: left={coa_left_px}, right={coa_right_px}, bottom={coa_bottom_px}, top={coa_top_px}")
			self._debug_printed = True
		
		# Use same vertices as frame (already in VBO from composite setup)
		gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
		
		self.main_composite_shader.release()
	
	def coa_to_frame_space(self, pos_x, pos_y):
		"""Convert CoA space coordinates to frame-adjusted visual space
		
		Args:
			pos_x, pos_y: Position in CoA space (0-1 range)
			
		Returns:
			tuple: (frame_x, frame_y) in visual frame space
		"""
		scale, offset = self.get_frame_transform()
		
		# Center position (move to origin)
		centered_x = pos_x - 0.5
		centered_y = pos_y - 0.5
		
		# Apply frame scale
		scaled_x = centered_x * scale[0]
		scaled_y = centered_y * scale[1]
		
		# Move back from origin
		uncentered_x = scaled_x + 0.5
		uncentered_y = scaled_y + 0.5
		
		# Apply frame offset (must match inverse of frame_to_coa_space)
		frame_x = uncentered_x - offset[0]*scale[0]
		frame_y = uncentered_y - offset[1]*scale[1]
		
		return (frame_x, frame_y)
	
	def frame_to_coa_space(self, frame_x, frame_y):
		"""Convert frame-adjusted visual space to CoA space coordinates
		
		Args:
			frame_x, frame_y: Position in frame visual space
			
		Returns:
			tuple: (pos_x, pos_y) in CoA space (0-1 range)
		"""
		scale, offset = self.get_frame_transform()
		
		# Remove frame offset
		no_offset_x = frame_x + offset[0]*scale[0]
		no_offset_y = frame_y + offset[1]*scale[1]
		
		# Center position (move to origin)
		centered_x = no_offset_x - 0.5
		centered_y = no_offset_y - 0.5
		
		# Remove frame scale
		unscaled_x = centered_x / scale[0]
		unscaled_y = centered_y / scale[1]
		
		# Move back from origin
		pos_x = unscaled_x + 0.5
		pos_y = unscaled_y + 0.5
		
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
		"""Handle window resize - use full widget dimensions"""
		# Use full widget dimensions (no longer forcing square aspect)
		gl.glViewport(0, 0, w, h)
	
	# ========================================
	# Zoom and View Controls
	# ========================================
	
	def zoom_in(self, cursor_pos=None):
		"""Zoom in by 25%"""
		old_zoom = self.zoom_level
		self.zoom_level = min(self.zoom_level * 1.25, 5.0)  # Max 5x zoom (500%)
		
		if cursor_pos:
			self._adjust_pan_for_zoom(cursor_pos, old_zoom, self.zoom_level)
		
		# Lock pan at 100% or below
		if self.zoom_level <= 1.0:
			self.pan_x = 0.0
			self.pan_y = 0.0
		
		self.update()
		# Update zoom toolbar - traverse up to find main window
		self._update_zoom_toolbar()
		# Trigger transform widget update
		if hasattr(self, 'canvas_area') and hasattr(self.canvas_area, 'transform_widget'):
			self.canvas_area.transform_widget.update()
	
	def zoom_out(self, cursor_pos=None):
		"""Zoom out by 25%"""
		old_zoom = self.zoom_level
		self.zoom_level = max(self.zoom_level / 1.25, 0.25)  # Min 0.25x zoom (25%)
		
		if cursor_pos:
			self._adjust_pan_for_zoom(cursor_pos, old_zoom, self.zoom_level)
		
		# Lock pan at 100% or below
		if self.zoom_level <= 1.0:
			self.pan_x = 0.0
			self.pan_y = 0.0
		
		self.update()
		# Update zoom toolbar - traverse up to find main window
		self._update_zoom_toolbar()
		# Trigger transform widget update
		if hasattr(self, 'canvas_area') and hasattr(self.canvas_area, 'transform_widget'):
			self.canvas_area.transform_widget.update()
	
	def zoom_reset(self):
		"""Reset zoom to 100%"""
		self.zoom_level = 1.0
		self.pan_x = 0.0
		self.pan_y = 0.0
		self.update()
		# Trigger transform widget update
		if hasattr(self, 'canvas_area') and hasattr(self.canvas_area, 'transform_widget'):
			self.canvas_area.transform_widget.update()
	
	def set_zoom_level(self, zoom_percent):
		"""Set zoom to specific percentage (25-500)"""
		self.zoom_level = max(0.25, min(5.0, zoom_percent / 100.0))
		self.update()
		# Update zoom toolbar display
		self._update_zoom_toolbar()
		# Trigger transform widget update
		if hasattr(self, 'canvas_area') and hasattr(self.canvas_area, 'transform_widget'):
			self.canvas_area.transform_widget.update()
	
	def get_zoom_percent(self):
		"""Get current zoom as percentage"""
		return int(self.zoom_level * 100)
	
	def _update_widget_size(self):
		"""Resize widget based on zoom level"""
		base_size = 600  # Base widget size at 100% zoom
		new_size = int(base_size * self.zoom_level)
		
		# Update size and position in one atomic operation
		if self.parent():
			center_x = (self.parent().width() - new_size) // 2
			center_y = (self.parent().height() - new_size) // 2
			self.setGeometry(
				int(center_x + self.pan_x),
				int(center_y + self.pan_y),
				new_size,
				new_size
			)
		else:
			self.setFixedSize(new_size, new_size)
	
	def _update_position(self):
		"""Update widget position based on pan offset (centered + pan)"""
		if not self.parent():
			return
		
		# Disable updates during geometry change to prevent flicker
		self.setUpdatesEnabled(False)
		
		# Calculate centered position
		center_x = (self.parent().width() - self.width()) // 2
		center_y = (self.parent().height() - self.height()) // 2
		
		# Apply pan offset from center - use setGeometry to avoid flicker
		self.setGeometry(
			int(center_x + self.pan_x),
			int(center_y + self.pan_y),
			self.width(),
			self.height()
		)
		
		# Re-enable updates
		self.setUpdatesEnabled(True)
		self.update()
	
	def _update_zoom_toolbar(self):
		"""Update zoom toolbar display by traversing up widget hierarchy"""
		if not self.canvas_area:
			return
		
		# Traverse up the widget hierarchy to find main window with zoom_toolbar
		widget = self.canvas_area
		while widget:
			if hasattr(widget, 'zoom_toolbar'):
				widget.zoom_toolbar.set_zoom_percent(self.get_zoom_percent(), emit_signal=False)
				return
			widget = widget.parent() if hasattr(widget, 'parent') else None
	
	def _adjust_pan_for_zoom(self, cursor_pos, old_zoom, new_zoom):
		"""Adjust pan offset to keep cursor position fixed during zoom"""
		# Get widget dimensions
		widget_width = self.width()
		widget_height = self.height()
		
		# Calculate cursor position relative to widget center
		cursor_offset_x = cursor_pos.x() - widget_width / 2
		cursor_offset_y = cursor_pos.y() - widget_height / 2
		
		# Calculate how much the canvas scaled
		scale_ratio = new_zoom / old_zoom
		
		# Adjust pan to keep the same world point under cursor
		# Pan offset compensates for the canvas scaling around center
		self.pan_x += cursor_offset_x * (1 - scale_ratio)
		self.pan_y += cursor_offset_y * (1 - scale_ratio)
	
	def set_show_grid(self, show):
		"""Toggle grid visibility"""
		self.show_grid = show
		self.update()
	
	def set_grid_divisions(self, divisions):
		"""Set grid size (2, 4, 8, or 16)"""
		self.grid_divisions = divisions
		if self.show_grid:
			self.update()
	
	# ========================================
	# Preview Control Methods
	# ========================================
	
	def _get_rank_uv(self, rank_name):
		"""Get UV coordinates for rank in 7x1 atlas (indices 1-6, no rank 0 unused)"""
		rank_map = {
			"Baron": 1,
			"Count": 2,
			"Duke": 3,
			"King": 4,
			"Emperor": 5,
			"Hegemon": 6
		}
		rank_index = rank_map.get(rank_name, 3)  # Default to Duke
		# Each rank is 1/7th of the width
		u0 = rank_index / 7.0
		u1 = (rank_index + 1) / 7.0
		return u0, u1
	
	def set_preview_enabled(self, enabled):
		"""Enable/disable preview overlays"""
		self.preview_enabled = enabled
		self.update()
	
	def set_preview_government(self, government):
		"""Set government type for preview (e.g., 'clan_government')"""
		self.preview_government = government
		if self.preview_enabled:
			self.update()
	
	def set_preview_rank(self, rank):
		"""Set rank for preview (e.g., 'Duke')"""
		self.preview_rank = rank
		if self.preview_enabled:
			self.update()
	
	def set_preview_size(self, size):
		"""Set size for preview in pixels (28, 44, 62, 86, 115)"""
		self.preview_size = size
		if self.preview_enabled:
			self.update()
	
	# ========================================
	# Export
	# ========================================
	
	def export_to_png(self, filename):
		"""Export the current CoA rendering to PNG with transparency
		Also exports government and title previews as separate files.
		
		Args:
			filename: Path to save main PNG file
			
		Returns:
			True if successful, False otherwise
		"""
		try:
			from PyQt5.QtGui import QImage, QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat
			from PyQt5.QtCore import QSize
			import numpy as np
			import os
			
			# Use 512x512 for main export
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
			
			# Save the main image
			success = image.save(filename, "PNG")
			
			# Export government and title previews if preview mode is enabled
			if self.preview_enabled:
				base_name = os.path.splitext(filename)[0]
				preview_export_size = 256
				
				# Export government preview
				if self.realm_frame_masks.get(self.preview_government):
					gov_filename = f"{base_name}_gov.png"
					self._export_preview_to_png(gov_filename, 'government', preview_export_size, fbo_format)
				
				# Export title preview
				if self.title_mask:
					title_filename = f"{base_name}_title.png"
					self._export_preview_to_png(title_filename, 'title', preview_export_size, fbo_format)
			
			# Restore normal viewport and clear color
			gl.glViewport(0, 0, self.width(), self.height())
			gl.glClearColor(*self.clear_color)
			
			self.doneCurrent()
			
			return success
			
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
	
	def _export_preview_to_png(self, filename, preview_type, export_size, fbo_format):
		"""Export government or title preview to PNG
		
		Args:
			filename: Path to save PNG file
			preview_type: 'government' or 'title'
			export_size: Size of export (e.g., 512)
			fbo_format: QOpenGLFramebufferObjectFormat to use
		
		Returns:
			True if successful, False otherwise
		"""
		try:
			from PyQt5.QtGui import QImage, QOpenGLFramebufferObject
			from PyQt5.QtCore import QSize
			import numpy as np
			
			# Create framebuffer for preview export
			fbo = QOpenGLFramebufferObject(QSize(export_size, export_size), fbo_format)
			if not fbo.isValid():
				print(f"Failed to create preview framebuffer for {preview_type}")
				return False
			
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
			
			# Render preview centered in the export frame
			# Calculate center position (NDC coordinates)
			dims = self.get_preview_dimensions(viewport_size=(export_size, export_size))
			size_x, size_y = dims['size_ndc']
			
			# Center the preview
			ndc_left = -size_x / 2.0
			ndc_top = size_y / 2.0 + dims['crown_height_ndc']
			
			# Render appropriate preview
			if preview_type == 'government':
				self._render_government_preview_at(ndc_left, ndc_top, viewport_size=(export_size, export_size))
			elif preview_type == 'title':
				self._render_title_preview_at(ndc_left, ndc_top, viewport_size=(export_size, export_size))
			
			# Read pixels from framebuffer
			gl.glReadBuffer(gl.GL_COLOR_ATTACHMENT0)
			pixels = gl.glReadPixels(0, 0, export_size, export_size, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE)
			
			# Release framebuffer
			fbo.release()
			
			# Convert to numpy array and flip vertically
			arr = np.frombuffer(pixels, dtype=np.uint8).reshape(export_size, export_size, 4)
			arr = np.flipud(arr).copy()
			
			# Create QImage from bytes
			image = QImage(arr.tobytes(), export_size, export_size, export_size * 4, QImage.Format_RGBA8888)
			image = image.copy()
			
			# Save the image
			success = image.save(filename, "PNG")
			return success
			
		except Exception as e:
			print(f"Preview export error ({preview_type}): {e}")
			import traceback
			traceback.print_exc()
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
		
		# Render frame on top if present (pass viewport size for correct aspect)
		if self.frameTexture:
			self._render_frame(viewport_size=(viewport[2], viewport[3]))
	
	# ========================================
	# Mouse Event Handlers
	# ========================================
	
	def wheelEvent(self, event):
		"""Handle mouse wheel events"""
		from PyQt5.QtCore import Qt
		
		# Check for Ctrl key modifier
		if event.modifiers() & Qt.ControlModifier:
			# Zoom in/out with Ctrl+Wheel centered on cursor
			cursor_pos = event.pos()
			delta = event.angleDelta().y()
			if delta > 0:
				self.zoom_in(cursor_pos)
			elif delta < 0:
				self.zoom_out(cursor_pos)
			
			# zoom_in/zoom_out already update toolbar, no need to do it again
	
	def mousePressEvent(self, event):
		"""Handle mouse press for panning when zoomed"""
		from PyQt5.QtCore import Qt
		
		# Tool mode takes priority
		if self.active_tool and self._on_tool_mouse_press(event):
			return
		
		# Enable panning when zoomed in (>100%) with left button
		if event.button() == Qt.LeftButton and self.zoom_level > 1.0:
			self.is_panning = True
			self.last_mouse_pos = event.globalPos()  # Use global position, not widget-relative
			self.setCursor(Qt.ClosedHandCursor)
			event.accept()
		else:
			super().mousePressEvent(event)
	
	def mouseMoveEvent(self, event):
		"""Handle mouse move for panning"""
		from PyQt5.QtCore import Qt
		
		# Always update mouse position for red dot tracker
		self.last_picker_mouse_pos = event.pos()
		self.update()  # Trigger repaint to show red dot
		
		# Tool mode hover handling
		if self.active_tool:
			self._on_tool_mouse_move(event)
		
		if self.is_panning and self.last_mouse_pos:
			# Calculate delta using global coordinates
			delta = event.globalPos() - self.last_mouse_pos
			self.last_mouse_pos = event.globalPos()
			
			# Update pan offset with bounds
			self.pan_x += delta.x()
			self.pan_y += delta.y()
			
			# Clamp panning to reasonable bounds based on zoom level
			# Allow panning up to half the canvas size in each direction
			canvas_size = min(self.width(), self.height())
			max_pan = canvas_size * self.zoom_level * 0.3
			self.pan_x = max(-max_pan, min(max_pan, self.pan_x))
			self.pan_y = max(-max_pan, min(max_pan, self.pan_y))
			
			# Trigger repaint and transform widget update
			self.update()
			if hasattr(self, 'canvas_area') and hasattr(self.canvas_area, 'transform_widget'):
				self.canvas_area.transform_widget.update()
			event.accept()
		else:
			# Show open hand cursor when hovering and zoomed in
			if self.zoom_level > 1.0:
				self.setCursor(Qt.OpenHandCursor)
			else:
				self.setCursor(Qt.ArrowCursor)
			super().mouseMoveEvent(event)
	
	def mouseReleaseEvent(self, event):
		"""Handle mouse release to end panning or tool actions"""
		from PyQt5.QtCore import Qt
		
		# Let tool handle release first
		if hasattr(self, '_on_tool_mouse_release'):
			if self._on_tool_mouse_release(event):
				event.accept()
				return
		
		if event.button() == Qt.LeftButton and self.is_panning:
			self.is_panning = False
			self.last_mouse_pos = None
			# Restore cursor
			if self.zoom_level > 1.0:
				self.setCursor(Qt.OpenHandCursor)
			else:
				self.setCursor(Qt.ArrowCursor)
			event.accept()
		else:
			super().mouseReleaseEvent(event)
