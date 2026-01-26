# PyQt5 imports
from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QOpenGLShaderProgram, QOpenGLShader, QOpenGLVertexArrayObject, QOpenGLBuffer

# External library imports
import OpenGL.GL as gl
import numpy as np
import os
import json
from constants import (
	DEFAULT_FRAME,
	DEFAULT_BASE_COLOR1, DEFAULT_BASE_COLOR2, DEFAULT_BASE_COLOR3,
	CK3_NAMED_COLORS
)
from PIL import Image
from pathlib import Path

# Local imports
from components.canvas_widgets.shader_manager import ShaderManager
from utils.path_resolver import (get_pattern_metadata_path, get_emblem_metadata_path, 
                                  get_pattern_source_dir, get_emblem_source_dir, get_frames_dir)


class CoatOfArmsCanvas(QOpenGLWidget):
	"""OpenGL canvas for rendering coat of arms with shaders"""
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.base_shader = None  # Shader for base layer
		self.design_shader = None  # Shader for emblem layers
		self.basic_shader = None  # Shader for frame rendering
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
		self.layers = []  # List of layer data from property sidebar
		self.frame_texture = None  # Current frame texture
		self.frame_textures = {}  # Frame name -> texture ID
		self.frame_masks = {}  # Frame name -> mask texture ID
		self.mask_texture = None  # Current mask texture (changes with frame)
		self.default_mask_texture = None  # Default white mask (fallback)
		self.material_mask_texture = None  # CK3 material texture (dirt/fabric/paint)
		self.noise_texture = None  # Noise texture for grain effect
		self.current_frame_name = DEFAULT_FRAME  # Track current frame name
		self.prestige_level = 0  # Current prestige level (0-5)
		
		# Zoom and grid properties
		self.zoom_level = 1.0  # Current zoom level (1.0 = 100%)
		self.show_grid = False  # Whether to show alignment grid
		self.grid_divisions = 4  # Grid size (2, 4, 8, or 16)
	
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
		gl.glClearColor(0.05, 0.05, 0.05, 1.0)  # Darker background to distinguish from black CoA elements
		gl.glEnable(gl.GL_BLEND)
		gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
		
		# Create shaders using ShaderManager
		shader_manager = ShaderManager()
		self.base_shader = shader_manager.create_base_shader(self)
		self.design_shader = shader_manager.create_design_shader(self)
		self.basic_shader = shader_manager.create_basic_shader(self)
		
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
		
		# Set defaults after initialization
		self.set_frame(DEFAULT_FRAME)
		self.set_prestige(3)
		# Set default base pattern
		if "pattern__solid_designer.dds" in self.texture_uv_map:
			self.set_base_texture("pattern__solid_designer.dds")
		
	def paintGL(self):
		"""Render the scene - base layer with base.frag, emblem layers with design.frag"""
		gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
		
		if not self.vao:
			return
		
		self.vao.bind()
		
		# Render base layer with base.frag
		if self.base_texture and self.base_texture in self.texture_uv_map and self.base_shader:
			self.base_shader.bind()
			atlas_idx, u0, v0, u1, v1 = self.texture_uv_map[self.base_texture]
			
			if atlas_idx < len(self.texture_atlases):
				gl.glActiveTexture(gl.GL_TEXTURE0)
				gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_atlases[atlas_idx])
				self.base_shader.setUniformValue("textureSampler", 0)
				
				# Bind mask texture if available
				if self.mask_texture:
					gl.glActiveTexture(gl.GL_TEXTURE1)
					gl.glBindTexture(gl.GL_TEXTURE_2D, self.mask_texture)
					if self.base_shader.uniformLocation("coaMaskSampler") != -1:
						self.base_shader.setUniformValue("coaMaskSampler", 1)
				
				# Bind material mask texture
				if self.material_mask_texture:
					gl.glActiveTexture(gl.GL_TEXTURE2)
					gl.glBindTexture(gl.GL_TEXTURE_2D, self.material_mask_texture)
					if self.base_shader.uniformLocation("materialMaskSampler") != -1:
						self.base_shader.setUniformValue("materialMaskSampler", 2)
				
				# Bind noise texture
				if self.noise_texture:
					gl.glActiveTexture(gl.GL_TEXTURE3)
					gl.glBindTexture(gl.GL_TEXTURE_2D, self.noise_texture)
					if self.base_shader.uniformLocation("noiseSampler") != -1:
						self.base_shader.setUniformValue("noiseSampler", 3)
				
				# Set viewport size for mask coordinate calculation
				self.base_shader.setUniformValue("viewportSize", float(self.width()), float(self.height()))
				
				# Set base colors from property sidebar
				color1 = self.base_colors[0] if len(self.base_colors) > 0 else [0.439, 0.129, 0.086]
				color2 = self.base_colors[1] if len(self.base_colors) > 1 else [0.588, 0.224, 0.0]
				color3 = self.base_colors[2] if len(self.base_colors) > 2 else [0.733, 0.510, 0.180]
				self.base_shader.setUniformValue("primaryColor", color1[0], color1[1], color1[2])
				self.base_shader.setUniformValue("secondaryColor", color2[0], color2[1], color2[2])
				self.base_shader.setUniformValue("tertiaryColor", color3[0], color3[1], color3[2])
				
				# Update UV coordinates for base texture with zoom applied
				base_size = 0.8 * self.zoom_level
				vertices = np.array([
					-base_size, -base_size, 0.0,  u0, v1,
					 base_size, -base_size, 0.0,  u1, v1,
					 base_size,  base_size, 0.0,  u1, v0,
					-base_size,  base_size, 0.0,  u0, v0,
				], dtype=np.float32)
				
				self.vbo.bind()
				self.vbo.write(0, vertices.tobytes(), vertices.nbytes)
				
				gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
				self.base_shader.release()
		
		# Render emblem layers with design.frag
		if self.layers and self.design_shader:
			self.design_shader.bind()
			
			for layer in self.layers:
				# Skip hidden layers
				if not layer.get('visible', True):
					continue
					
				filename = layer.get('filename')
				if not filename or filename not in self.texture_uv_map:
					continue
				
				atlas_idx, u0, v0, u1, v1 = self.texture_uv_map[filename]
				
				if atlas_idx < len(self.texture_atlases):
					gl.glActiveTexture(gl.GL_TEXTURE0)
					gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_atlases[atlas_idx])
					self.design_shader.setUniformValue("textureSampler", 0)
					
					# Bind mask texture if available
					if self.mask_texture:
						gl.glActiveTexture(gl.GL_TEXTURE1)
						gl.glBindTexture(gl.GL_TEXTURE_2D, self.mask_texture)
						if self.design_shader.uniformLocation("coaMaskSampler") != -1:
							self.design_shader.setUniformValue("coaMaskSampler", 1)
					
					# Bind material mask texture
					if self.material_mask_texture:
						gl.glActiveTexture(gl.GL_TEXTURE2)
						gl.glBindTexture(gl.GL_TEXTURE_2D, self.material_mask_texture)
						if self.design_shader.uniformLocation("materialMaskSampler") != -1:
							self.design_shader.setUniformValue("materialMaskSampler", 2)
					
					# Bind noise texture
					if self.noise_texture:
						gl.glActiveTexture(gl.GL_TEXTURE3)
						gl.glBindTexture(gl.GL_TEXTURE_2D, self.noise_texture)
						if self.design_shader.uniformLocation("noiseSampler") != -1:
							self.design_shader.setUniformValue("noiseSampler", 3)
					
					# Set viewport size for mask coordinate calculation
					self.design_shader.setUniformValue("viewportSize", float(self.width()), float(self.height()))
					
					# Set emblem colors from layer properties
					color1 = layer.get('color1', [0.439, 0.129, 0.086])
					color2 = layer.get('color2', [0.588, 0.224, 0.0])
					color3 = layer.get('color3', [0.733, 0.510, 0.180])
					self.design_shader.setUniformValue("primaryColor", color1[0], color1[1], color1[2])
					self.design_shader.setUniformValue("secondaryColor", color2[0], color2[1], color2[2])
					self.design_shader.setUniformValue("tertiaryColor", color3[0], color3[1], color3[2])
					
					# Apply transform properties
					pos_x = layer.get('pos_x', 0.5)
					pos_y = layer.get('pos_y', 0.5)
					scale_x = layer.get('scale_x', 0.5)
					scale_y = layer.get('scale_y', 0.5)
					flip_x = layer.get('flip_x', False)
					flip_y = layer.get('flip_y', False)
					rotation = layer.get('rotation', 0)
					
					# Convert properties to screen coordinates
					# pos: 0.0-1.0 → -0.8 to 0.8 screen space
					center_x = (pos_x - 0.5) * 1.1 * self.zoom_level
					center_y = -(pos_y - 0.5) * 1.1 * self.zoom_level  # Invert Y-axis (CK3 uses top-down, OpenGL uses bottom-up)
					
					# CK3 transformation order: position, then rotation, then scale
					# Calculate rotated and scaled quad vertices
					import math
				angle_rad = math.radians(-rotation)  # Negate for correct rotation direction
				cos_a = math.cos(angle_rad)
				sin_a = math.sin(angle_rad)
				
				# Apply flip separately from scale magnitude
				scale_sign_x = -1 if flip_x else 1
				scale_sign_y = -1 if flip_y else 1
				half_width = scale_x * 0.6 * self.zoom_level
				half_height = scale_y * 0.6 * self.zoom_level
				
				# Define unit quad corners
				unit_corners = [
					(-1.0, -1.0),  # Bottom-left
					( 1.0, -1.0),  # Bottom-right
					( 1.0,  1.0),  # Top-right
					(-1.0,  1.0),  # Top-left
				]
				
				# Apply transformations: flip first, then rotate, then scale magnitude, then translate
				transformed = []
				for ux, uy in unit_corners:
					# First apply flip (sign)
					fx = ux * scale_sign_x
					fy = uy * scale_sign_y
					# Then rotate the flipped corner
					rx = fx * cos_a - fy * sin_a
					ry = fx * sin_a + fy * cos_a
					# Then scale by magnitude in screen space
					sx = rx * half_width
					sy = ry * half_height
					# Finally translate to position
					transformed.append((sx + center_x, sy + center_y))
				
				# Update UV coordinates for this layer
				vertices = np.array([
					transformed[0][0], transformed[0][1], 0.0,  u0, v1,
					transformed[1][0], transformed[1][1], 0.0,  u1, v1,
					transformed[2][0], transformed[2][1], 0.0,  u1, v0,
					transformed[3][0], transformed[3][1], 0.0,  u0, v0,
				], dtype=np.float32)
				
				self.vbo.bind()
				self.vbo.write(0, vertices.tobytes(), vertices.nbytes)
				
				gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
			
			self.design_shader.release()
		
		# Render frame on top if selected
		if self.frame_texture and self.basic_shader:
			self.basic_shader.bind()
			
			gl.glActiveTexture(gl.GL_TEXTURE0)
			gl.glBindTexture(gl.GL_TEXTURE_2D, self.frame_texture)
			self.basic_shader.setUniformValue("textureSampler", 0)
			
			# Frame textures are 6x1 tiles for prestige levels
			# Calculate UV coordinates for the selected prestige level
			tile_width = 1.0 / 6.0
			u_start = self.prestige_level * tile_width
			u_end = u_start + tile_width
			
			# Full screen quad for frame with prestige tile UVs, with zoom applied
			frame_size = 0.8 * self.zoom_level
			vertices = np.array([
				-frame_size, -frame_size, 0.0,  u_start, 1.0,
				 frame_size, -frame_size, 0.0,  u_end, 1.0,
				 frame_size,  frame_size, 0.0,  u_end, 0.0,
				-frame_size,  frame_size, 0.0,  u_start, 0.0,
			], dtype=np.float32)
			
			self.vbo.bind()
			self.vbo.write(0, vertices.tobytes(), vertices.nbytes)
			
			gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
			self.basic_shader.release()
		
		# Render grid if enabled
		if self.show_grid:
			self._render_grid()
		
		self.vao.release()
	
	def _render_grid(self):
		"""Render a grid overlay for alignment"""
		# Enable line rendering
		gl.glDisable(gl.GL_TEXTURE_2D)
		gl.glLineWidth(1.0)
		
		# Set grid color (light gray)
		gl.glColor4f(0.5, 0.5, 0.5, 0.5)
		
		# Draw vertical and horizontal lines
		grid_size = 0.8 * self.zoom_level
		grid_step = (1.6 * self.zoom_level) / self.grid_divisions  # Divide into grid_divisions
		
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
					
					self.frame_textures[name] = texture_id
					
					# Load corresponding mask file
					mask_filename = filename.replace('.png', '_mask.png')
					mask_path = os.path.join(frame_dir, mask_filename)
					if os.path.exists(mask_path):
						mask_img = Image.open(mask_path).convert('RGBA')
						
						# Check if mask is valid (not all black/zero)
						mask_data = np.array(mask_img)
						max_rgb = max(mask_data[:,:,0].max(), mask_data[:,:,1].max(), mask_data[:,:,2].max())
						
						# Skip invalid masks (all black RGB, which would block everything)
						if max_rgb == 0:
							continue
						
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
		except Exception as e:
			print(f"Error loading frame textures: {e}")
	
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
				
				self.material_mask_texture = gl.glGenTextures(1)
				gl.glBindTexture(gl.GL_TEXTURE_2D, self.material_mask_texture)
				
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
				
				self.material_mask_texture = gl.glGenTextures(1)
				gl.glBindTexture(gl.GL_TEXTURE_2D, self.material_mask_texture)
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
				
				self.noise_texture = gl.glGenTextures(1)
				gl.glBindTexture(gl.GL_TEXTURE_2D, self.noise_texture)
				
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
				
				self.noise_texture = gl.glGenTextures(1)
				gl.glBindTexture(gl.GL_TEXTURE_2D, self.noise_texture)
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
		if frame_name in self.frame_textures:
			self.frame_texture = self.frame_textures[frame_name]
			self.current_frame_name = frame_name
			# Update mask texture to match frame, or use default white mask
			if frame_name in self.frame_masks:
				self.mask_texture = self.frame_masks[frame_name]
			else:
				self.mask_texture = self.default_mask_texture
			self.update()
		elif frame_name == "None":
			self.frame_texture = None
			self.mask_texture = self.default_mask_texture
			self.update()
	
	def set_prestige(self, level):
		"""Set the prestige level (0-5)"""
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
		"""Update the emblem layers to render"""
		self.layers = layers
		self.update()
	
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
			
			# Use high resolution for quality export
			export_size = 2048
			
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
			
			# Clear with transparent background
			gl.glClearColor(0.0, 0.0, 0.0, 0.0)
			gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
			
			# Render the CoA
			self._render_coa_for_export()
			
			# Get the image from the framebuffer
			image = fbo.toImage()
			
			# Release framebuffer
			fbo.release()
			
			# Restore normal viewport and clear color
			gl.glViewport(0, 0, self.width(), self.height())
			gl.glClearColor(0.05, 0.05, 0.05, 1.0)
			
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
				gl.glClearColor(0.05, 0.05, 0.05, 1.0)
				self.doneCurrent()
			except:
				pass
			
			return False
	
	def _render_coa_for_export(self):
		"""Render the CoA for export (similar to paintGL but without grid)"""
		if not self.vao:
			return
		
		self.vao.bind()
		
		# Render base layer with base.frag
		if self.base_texture and self.base_texture in self.texture_uv_map and self.base_shader:
			self.base_shader.bind()
			atlas_idx, u0, v0, u1, v1 = self.texture_uv_map[self.base_texture]
			
			if atlas_idx < len(self.texture_atlases):
				gl.glActiveTexture(gl.GL_TEXTURE0)
				gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_atlases[atlas_idx])
				self.base_shader.setUniformValue("textureSampler", 0)
				
				# Bind mask texture if available
				if self.mask_texture:
					gl.glActiveTexture(gl.GL_TEXTURE1)
					gl.glBindTexture(gl.GL_TEXTURE_2D, self.mask_texture)
					if self.base_shader.uniformLocation("coaMaskSampler") != -1:
						self.base_shader.setUniformValue("coaMaskSampler", 1)
				
				# Bind material mask texture
				if self.material_mask_texture:
					gl.glActiveTexture(gl.GL_TEXTURE2)
					gl.glBindTexture(gl.GL_TEXTURE_2D, self.material_mask_texture)
					if self.base_shader.uniformLocation("materialMaskSampler") != -1:
						self.base_shader.setUniformValue("materialMaskSampler", 2)
				
				# Bind noise texture
				if self.noise_texture:
					gl.glActiveTexture(gl.GL_TEXTURE3)
					gl.glBindTexture(gl.GL_TEXTURE_2D, self.noise_texture)
					if self.base_shader.uniformLocation("noiseSampler") != -1:
						self.base_shader.setUniformValue("noiseSampler", 3)
				
				# Set viewport size for mask coordinate calculation
				# Use export size (2048) instead of widget size
				self.base_shader.setUniformValue("viewportSize", 2048.0, 2048.0)
				
				# Set base colors from property sidebar
				color1 = self.base_colors[0] if len(self.base_colors) > 0 else [0.439, 0.129, 0.086]
				color2 = self.base_colors[1] if len(self.base_colors) > 1 else [0.588, 0.224, 0.0]
				color3 = self.base_colors[2] if len(self.base_colors) > 2 else [0.733, 0.510, 0.180]
				self.base_shader.setUniformValue("primaryColor", color1[0], color1[1], color1[2])
				self.base_shader.setUniformValue("secondaryColor", color2[0], color2[1], color2[2])
				self.base_shader.setUniformValue("tertiaryColor", color3[0], color3[1], color3[2])
				
				# Update UV coordinates for base texture (no zoom for export)
				base_size = 0.8
				vertices = np.array([
					-base_size, -base_size, 0.0,  u0, v1,
					 base_size, -base_size, 0.0,  u1, v1,
					 base_size,  base_size, 0.0,  u1, v0,
					-base_size,  base_size, 0.0,  u0, v0,
				], dtype=np.float32)
				
				self.vbo.bind()
				self.vbo.write(0, vertices.tobytes(), vertices.nbytes)
				
				gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
				self.base_shader.release()
		
		# Render emblem layers with design.frag
		if self.layers and self.design_shader:
			self.design_shader.bind()
			
			for layer in self.layers:
				# Skip hidden layers
				if not layer.get('visible', True):
					continue
					
				filename = layer.get('filename')
				if not filename or filename not in self.texture_uv_map:
					continue
				
				atlas_idx, u0, v0, u1, v1 = self.texture_uv_map[filename]
				
				if atlas_idx < len(self.texture_atlases):
					gl.glActiveTexture(gl.GL_TEXTURE0)
					gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_atlases[atlas_idx])
					self.design_shader.setUniformValue("textureSampler", 0)
					
					# Bind mask texture if available
					if self.mask_texture:
						gl.glActiveTexture(gl.GL_TEXTURE1)
						gl.glBindTexture(gl.GL_TEXTURE_2D, self.mask_texture)
						if self.design_shader.uniformLocation("coaMaskSampler") != -1:
							self.design_shader.setUniformValue("coaMaskSampler", 1)
					
					# Bind material mask texture
					if self.material_mask_texture:
						gl.glActiveTexture(gl.GL_TEXTURE2)
						gl.glBindTexture(gl.GL_TEXTURE_2D, self.material_mask_texture)
						if self.design_shader.uniformLocation("materialMaskSampler") != -1:
							self.design_shader.setUniformValue("materialMaskSampler", 2)
					
					# Bind noise texture
					if self.noise_texture:
						gl.glActiveTexture(gl.GL_TEXTURE3)
						gl.glBindTexture(gl.GL_TEXTURE_2D, self.noise_texture)
						if self.design_shader.uniformLocation("noiseSampler") != -1:
							self.design_shader.setUniformValue("noiseSampler", 3)
					
					# Set viewport size for mask coordinate calculation
					self.design_shader.setUniformValue("viewportSize", 2048.0, 2048.0)
					
					# Set emblem colors from layer properties
					color1 = layer.get('color1', [0.439, 0.129, 0.086])
					color2 = layer.get('color2', [0.588, 0.224, 0.0])
					color3 = layer.get('color3', [0.733, 0.510, 0.180])
					self.design_shader.setUniformValue("primaryColor", color1[0], color1[1], color1[2])
					self.design_shader.setUniformValue("secondaryColor", color2[0], color2[1], color2[2])
					self.design_shader.setUniformValue("tertiaryColor", color3[0], color3[1], color3[2])
					
					# Apply transform properties (no zoom for export)
					pos_x = layer.get('pos_x', 0.5)
					pos_y = layer.get('pos_y', 0.5)
					scale_x = layer.get('scale_x', 0.5)
					scale_y = layer.get('scale_y', 0.5)
					flip_x = layer.get('flip_x', False)
					flip_y = layer.get('flip_y', False)
					rotation = layer.get('rotation', 0)
					
					# Convert properties to screen coordinates (no zoom)
					center_x = (pos_x - 0.5) * 1.1
					center_y = -(pos_y - 0.5) * 1.1
					
					# Calculate rotated and scaled quad vertices
					import math
					angle_rad = math.radians(-rotation)
					cos_a = math.cos(angle_rad)
					sin_a = math.sin(angle_rad)
					
					# Apply flip separately from scale magnitude
					scale_sign_x = -1 if flip_x else 1
					scale_sign_y = -1 if flip_y else 1
					half_width = scale_x * 0.6
					half_height = scale_y * 0.6
					
					# Define unit quad corners
					unit_corners = [
						(-1.0, -1.0),  # Bottom-left
						( 1.0, -1.0),  # Bottom-right
						( 1.0,  1.0),  # Top-right
						(-1.0,  1.0),  # Top-left
					]
					
					# Apply transformations
					transformed = []
					for ux, uy in unit_corners:
						fx = ux * scale_sign_x
						fy = uy * scale_sign_y
						rx = fx * cos_a - fy * sin_a
						ry = fx * sin_a + fy * cos_a
						sx = rx * half_width
						sy = ry * half_height
						transformed.append((sx + center_x, sy + center_y))
					
					# Update UV coordinates for this layer
					vertices = np.array([
						transformed[0][0], transformed[0][1], 0.0,  u0, v1,
						transformed[1][0], transformed[1][1], 0.0,  u1, v1,
						transformed[2][0], transformed[2][1], 0.0,  u1, v0,
						transformed[3][0], transformed[3][1], 0.0,  u0, v0,
					], dtype=np.float32)
					
					self.vbo.bind()
					self.vbo.write(0, vertices.tobytes(), vertices.nbytes)
					
					gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
			
			self.design_shader.release()
		
		# Render frame on top if selected
		if self.frame_texture and self.basic_shader:
			self.basic_shader.bind()
			
			gl.glActiveTexture(gl.GL_TEXTURE0)
			gl.glBindTexture(gl.GL_TEXTURE_2D, self.frame_texture)
			self.basic_shader.setUniformValue("textureSampler", 0)
			
			# Frame textures are 6x1 tiles for prestige levels
			tile_width = 1.0 / 6.0
			u_start = self.prestige_level * tile_width
			u_end = u_start + tile_width
			
			# Full screen quad for frame (no zoom)
			frame_size = 0.8
			vertices = np.array([
				-frame_size, -frame_size, 0.0,  u_start, 1.0,
				 frame_size, -frame_size, 0.0,  u_end, 1.0,
				 frame_size,  frame_size, 0.0,  u_end, 0.0,
				-frame_size,  frame_size, 0.0,  u_start, 0.0,
			], dtype=np.float32)
			
			self.vbo.bind()
			self.vbo.write(0, vertices.tobytes(), vertices.nbytes)
			
			gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
			self.basic_shader.release()
		
		self.vao.release()
