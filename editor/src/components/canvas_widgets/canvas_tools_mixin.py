"""Canvas tool mode system - layer picker, eyedropper, etc."""
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QCursor, QImage
from PyQt5.QtWidgets import QToolTip


class CanvasToolsMixin:
	"""Mixin for canvas widget tool modes (picker, eyedropper, etc.)
	
	Keeps canvas_widget.py from growing too large by separating tool functionality.
	"""
	
	def _init_tools(self):
		"""Initialize tool system state (called from canvas_widget __init__)"""
		self.active_tool = None  # Current tool mode (None, 'layer_picker', 'eyedropper')
		self.hovered_uuid = None  # UUID currently under mouse (for tooltip)
		self.last_picker_mouse_pos = None  # Last mouse position for UV calculation
		
		# Picker RTT - rendered once, cached until CoA changes
		self.picker_rtt = None  # QImage with UUID encoded as RGB
		self.picker_rtt_valid = False
		self.picker_uuid_map = {}  # RGB tuple -> UUID mapping
		self.picker_texture_id = None  # OpenGL texture ID for picker RTT
		
		# Paint select state (ctrl+drag in picker mode)
		self.paint_selecting = False  # True when ctrl+dragging to paint select
		self.paint_select_mode = None  # 'select' or 'deselect' based on first click
		self.paint_selected_uuids = set()  # UUIDs already processed in this paint session
		
		# Tool cursors
		self.tool_cursors = {
			'layer_picker': Qt.CrossCursor,
			'eyedropper': Qt.CrossCursor,  # TODO: Custom eyedropper cursor
		}
		
		# Original cursor to restore
		self._original_cursor = None
	
	def set_tool_mode(self, tool_name):
		"""Activate or deactivate a tool mode
		
		Args:
			tool_name: 'layer_picker', 'eyedropper', or None to deactivate
		"""
		# Deactivate old tool
		if self.active_tool:
			self._deactivate_tool(self.active_tool)
		
		# Activate new tool
		self.active_tool = tool_name
		if tool_name:
			self._activate_tool(tool_name)
	
	def _activate_tool(self, tool_name):
		"""Activate a tool mode
		
		Args:
			tool_name: Tool to activate
		"""
		# Change cursor
		if tool_name in self.tool_cursors:
			self._original_cursor = self.cursor()
			self.setCursor(self.tool_cursors[tool_name])
		
		# Tool-specific activation
		if tool_name == 'layer_picker':
			self._activate_layer_picker()
		elif tool_name == 'eyedropper':
			self._activate_eyedropper()
		
		# Enable mouse tracking for hover
		self.setMouseTracking(True)
	
	def _deactivate_tool(self, tool_name):
		"""Deactivate a tool mode
		
		Args:
			tool_name: Tool to deactivate
		"""
		# Restore original cursor
		if self._original_cursor:
			self.setCursor(self._original_cursor)
			self._original_cursor = None
		else:
			self.unsetCursor()
		
		# Tool-specific deactivation
		if tool_name == 'layer_picker':
			self._deactivate_layer_picker()
		elif tool_name == 'eyedropper':
			self._deactivate_eyedropper()
		
		# Clear hover state
		self.hovered_uuid = None
		QToolTip.hideText()
		
		# Disable mouse tracking unless needed elsewhere
		self.setMouseTracking(False)
	
	# ========================================
	# Layer Picker Tool
	# ========================================
	
	def _activate_layer_picker(self):
		"""Activate layer picker tool"""
		# Always regenerate picker RTT when activating (layers may have changed)
		self._generate_picker_rtt()
		
		# Hide transform widget (but keep selection)
		if hasattr(self, 'canvas_area') and self.canvas_area:
			if hasattr(self.canvas_area, 'transform_widget'):
				self.canvas_area.transform_widget.set_visible(False)
		
		# Trigger repaint to ensure clean OpenGL state
		self.update()
	
	def _deactivate_layer_picker(self):
		"""Deactivate layer picker tool"""
		# Keep picker RTT cached for reuse
		pass
	
	def _generate_picker_rtt(self):
		"""Generate picker render target with UUID color coding
		
		Each layer rendered with unique RGB color encoding its UUID.
		Background = rgb(0, 0, 0) for "no layer"
		"""
		# Import here to avoid circular dependency
		from models.coa import CoA
		
		if not CoA.has_active():
			return
		
		coa = CoA.get_active()
		
		# Build UUID -> RGB mapping AND index -> RGB mapping
		# Store BOTH the int color (for lookup) and float color (for rendering)
		self.picker_uuid_map = {}  # (r_int, g_int, b_int) -> UUID
		self.picker_color_map = {}  # layer_index -> (r_float, g_float, b_float)
		layer_count = coa.get_layer_count()
		
		import colorsys
		golden_ratio = 0.618033988749895
		
		for i in range(layer_count):
			layer = coa.get_layer_by_index(i)
			if layer:
				# Use golden ratio hue distribution with varied S/V for visual distinction
				hue = (i * golden_ratio) % 1.0
				saturation = 0.65 + 0.35 * ((i * 0.382) % 1.0)
				value = 0.55 + 0.45 * ((i * 0.754) % 1.0)
				r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
				
				# Store float version for rendering
				self.picker_color_map[i] = (r, g, b)
				
				# Convert to 0-255 range for lookup mapping
				r_int = int(r * 255)
				g_int = int(g * 255)
				b_int = int(b * 255)
				self.picker_uuid_map[(r_int, g_int, b_int)] = layer.uuid
		
		# Now actually render the picker RTT using OpenGL
		success = self._render_picker_to_framebuffer()
		self.picker_rtt_valid = success
		
		if success:
			print(f"Generated picker RTT: {len(self.picker_uuid_map)} layers mapped")
		else:
			print("ERROR: Failed to generate picker RTT")
	
	def _render_picker_to_framebuffer(self):
		"""Render picker RTT using OpenGL picker shader
		
		Returns:
			bool: True if rendering succeeded, False otherwise
		"""
		import OpenGL.GL as gl
		import numpy as np
		from models.coa import CoA
		import math
		
		# Validation checks
		if not CoA.has_active():
			print("WARNING: Cannot generate picker RTT - no active CoA")
			return False
		
		if not hasattr(self, 'picker_framebuffer') or not self.picker_framebuffer:
			print("ERROR: Cannot generate picker RTT - no picker framebuffer")
			return False
		
		if not hasattr(self, 'picker_shader') or not self.picker_shader:
			print("ERROR: Cannot generate picker RTT - no picker shader")
			return False
		
		if not hasattr(self, 'vao') or not self.vao:
			print("ERROR: Cannot generate picker RTT - no VAO")
			return False
		
		if not hasattr(self, 'texture_uv_map') or not self.texture_uv_map:
			print("WARNING: Cannot generate picker RTT - no texture UV map")
			return False
		
		coa = CoA.get_active()
		
		# Make sure OpenGL context is current
		self.makeCurrent()
		
		# Bind picker framebuffer for rendering (separate from CoA RTT)
		if not hasattr(self, 'picker_framebuffer') or not self.picker_framebuffer:
			return
		
		self.picker_framebuffer.bind()
		
		# Set viewport to match framebuffer size
		gl.glViewport(0, 0, self.picker_framebuffer.COA_RTT_WIDTH, self.picker_framebuffer.COA_RTT_HEIGHT)
		
		# Clear to black (0,0,0 = no layer)
		gl.glClearColor(0.0, 0.0, 0.0, 1.0)
		gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
		
		# Disable blending to get exact colors
		gl.glDisable(gl.GL_BLEND)
		
		if not self.picker_shader or not self.vao:
			self.picker_framebuffer.unbind(self.defaultFramebufferObject())
			return
		
		self.picker_shader.bind()
		self.vao.bind()
		
		# Render each layer with unique color
		layer_count = coa.get_layer_count()
		for layer_idx in range(layer_count):
			layer = coa.get_layer_by_index(layer_idx)
			if not layer:
				continue
			
			layer_uuid = layer.uuid
			
			# Get picker color for this layer (use pre-computed color)
			if layer_idx not in self.picker_color_map:
				continue
			r, g, b = self.picker_color_map[layer_idx]
			self.picker_shader.setUniformValue("indexColor", r, g, b)
			
			# Get texture UV coordinates
			texture_filename = getattr(layer, 'texture', getattr(layer, 'path', None))
			if not texture_filename or texture_filename not in self.texture_uv_map:
				continue
			
			atlas_index, u0, v0, u1, v1 = self.texture_uv_map[texture_filename]
			
			# Bind emblem texture atlas for this layer
			if atlas_index >= len(self.texture_atlases):
				continue
			
			gl.glActiveTexture(gl.GL_TEXTURE0)
			gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_atlases[atlas_index])
			self.picker_shader.setUniformValue("emblemMaskSampler", 0)
			
			# Set emblem tile index (32×32 grid)
			tile_index_loc = self.picker_shader.uniformLocation("emblemTileIndex")
			if tile_index_loc != -1:
				tile_x = int(u0 * 32.0)
				tile_y = int(v0 * 32.0)
				gl.glUniform2ui(tile_index_loc, tile_x, tile_y)
			
			# Get pattern mask info from layer
			mask_data = layer.mask  # Returns [r, g, b] or None
			if mask_data and len(mask_data) >= 4:
				# mask_data is [r, g, b, texture_name]
				pattern_mask = mask_data[3]
				if pattern_mask in self.texture_uv_map:
					pattern_atlas_idx, pu0, pv0, pu1, pv1 = self.texture_uv_map[pattern_mask]
					
					# Bind pattern mask texture atlas
					if pattern_atlas_idx < len(self.texture_atlases):
						gl.glActiveTexture(gl.GL_TEXTURE1)
						gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_atlases[pattern_atlas_idx])
						self.picker_shader.setUniformValue("patternMaskSampler", 1)
					
					# Set pattern tile index (32×32 grid)
					pattern_tile_index_loc = self.picker_shader.uniformLocation("patternTileIndex")
					if pattern_tile_index_loc != -1:
						ptile_x = int(pu0 * 32.0)
						ptile_y = int(pv0 * 32.0)
						gl.glUniform2ui(pattern_tile_index_loc, ptile_x, ptile_y)
					
					# Pattern flag: sum of enabled channels (r=1, g=2, b=4)
					pattern_flag = (mask_data[0] * 1) + (mask_data[1] * 2) + (mask_data[2] * 4)
					self.picker_shader.setUniformValue("patternFlag", pattern_flag)
				else:
					self.picker_shader.setUniformValue("patternFlag", 7)
			else:
				self.picker_shader.setUniformValue("patternFlag", 7)
			
			# Render layer instances using shared rendering method
			# (delegates transform math to shader via uniforms instead of CPU-side rogue math)
			self._render_layer_instances(coa, layer_uuid, (u0, v0, u1, v1), self.picker_shader)
		gl.glFlush()
		
		# Read pixels from picker framebuffer
		width = self.picker_framebuffer.COA_RTT_WIDTH
		height = self.picker_framebuffer.COA_RTT_HEIGHT
		pixels = gl.glReadPixels(0, 0, width, height, gl.GL_RGB, gl.GL_UNSIGNED_BYTE)
		
		# Convert to numpy array and save as PNG for debugging
		pixel_array = np.frombuffer(pixels, dtype=np.uint8).reshape(height, width, 3)
		pixel_array = np.flipud(pixel_array)  # Flip vertically (OpenGL bottom-up to image top-down)
		
		# DEBUG: Save picker RTT as PNG (disabled for performance)
		# from PIL import Image
		# import os
		# debug_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'picker_debug.png')
		# Image.fromarray(pixel_array, 'RGB').save(debug_path)
		# print(f"Saved picker RTT to: {debug_path}")
		
		# Convert to QImage for picker sampling (pixel() method)
		from PyQt5.QtGui import QImage
		self.picker_rtt = QImage(pixels, width, height, width * 3, QImage.Format_RGB888)
		self.picker_rtt = self.picker_rtt.mirrored(False, True)
		
		# Unbind and restore blending
		self.vao.release()
		self.picker_shader.release()
		self.picker_framebuffer.unbind(self.defaultFramebufferObject())
		
		# Restore viewport to widget size
		gl.glViewport(0, 0, self.width(), self.height())
		
		gl.glEnable(gl.GL_BLEND)
		gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
		
		return True  # Success
	
	def get_picker_color_for_layer_index(self, layer_index):
		"""Get normalized RGB color for layer index (for shader uniform)
		
		Uses golden ratio distribution in HSV space for maximum visual distinction.
		
		Args:
			layer_index: 0-based layer index
		
		Returns:
			Tuple of (r, g, b) normalized to 0.0-1.0 range
		"""
		import colorsys
		
		# Golden ratio for optimal hue distribution
		golden_ratio = 0.618033988749895
		
		# Distribute hues using golden angle for maximum visual separation
		hue = (layer_index * golden_ratio) % 1.0
		
		# Vary saturation and value to add more distinction while avoiding extremes
		# Use different prime offsets to decorrelate from hue
		saturation = 0.65 + 0.35 * ((layer_index * 0.382) % 1.0)  # Range: 0.65-1.0
		value = 0.55 + 0.45 * ((layer_index * 0.754) % 1.0)       # Range: 0.55-1.0
		
		r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
		return (r, g, b)
	
	def _get_picker_texture_id(self):
		"""Get OpenGL texture ID for picker RTT
		
		Returns:
			Texture ID or None if picker not active/valid
		"""
		if not self.active_tool or not self.picker_rtt_valid or not self.picker_rtt:
			return None
		
		# Create OpenGL texture from QImage if needed
		if not hasattr(self, 'picker_texture_id') or not self.picker_texture_id:
			import OpenGL.GL as gl
			
			self.picker_texture_id = gl.glGenTextures(1)
			gl.glBindTexture(gl.GL_TEXTURE_2D, self.picker_texture_id)
			
			# Use nearest-neighbor filtering to preserve exact colors
			gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
			gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
			gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
			gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
			
			# Upload QImage data to texture
			width = self.picker_rtt.width()
			height = self.picker_rtt.height()
			img_data = self.picker_rtt.bits().asstring(width * height * 3)
			gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB, width, height, 0, 
			                gl.GL_RGB, gl.GL_UNSIGNED_BYTE, img_data)
		
		return self.picker_texture_id
	
	def _get_picker_mouse_uv(self):
		"""Get normalized mouse UV coordinates for picker highlighting
		
		Returns:
			Tuple of (u, v) normalized coordinates, negative if not hovering
		"""
		# Only return valid coords when picker tool is active
		if not self.active_tool or self.active_tool != 'layer_picker':
			return (-1.0, -1.0)
		
		# Get last mouse position and convert to UV
		if hasattr(self, 'last_picker_mouse_pos') and self.last_picker_mouse_pos:
			# Convert canvas pixels to CoA space using instance method
			from models.transform import Vec2
			canvas_pos = Vec2(self.last_picker_mouse_pos.x(), self.last_picker_mouse_pos.y())
			coa_pos = self.canvas_to_coa(canvas_pos)
			return (coa_pos.x, coa_pos.y)
		
		return (-1.0, -1.0)
	
	def _cleanup_picker_resources(self):
		"""Clean up picker RTT OpenGL resources (call before widget destruction)"""
		if hasattr(self, 'picker_texture_id') and self.picker_texture_id:
			try:
				import OpenGL.GL as gl
				self.makeCurrent()  # Ensure context active
				gl.glDeleteTextures([self.picker_texture_id])
				self.picker_texture_id = None
				self.picker_rtt = None
				self.picker_rtt_valid = False
				print("Cleaned up picker RTT resources")
			except Exception as e:
				print(f"WARNING: Error cleaning up picker resources: {e}")
	
	def invalidate_picker_rtt(self):
		"""Invalidate picker RTT (call when CoA changes)"""
		self.picker_rtt_valid = False
		
		# Delete old texture if it exists
		if hasattr(self, 'picker_texture_id') and self.picker_texture_id:
			import OpenGL.GL as gl
			gl.glDeleteTextures([self.picker_texture_id])
			self.picker_texture_id = None
	
	def on_coa_structure_changed(self):
		"""Called when CoA structure changes (layers added/removed/reordered)
		
		Call this from canvas_widget whenever layers change to invalidate picker RTT.
		"""
		self.invalidate_picker_rtt()
	
	def _sample_picker_at_mouse(self, mouse_pos):
		"""Sample picker RTT at mouse position, return UUID or None
		
		Args:
			mouse_pos: QPoint in widget coordinates
		
		Returns:
			UUID string or None if no layer at position
		"""
		if not self.picker_rtt or not self.picker_rtt_valid:
			return None
		
		# Convert canvas pixels to CoA space using instance method
		from models.transform import Vec2
		canvas_pos = Vec2(mouse_pos.x(), mouse_pos.y())
		coa_pos = self.canvas_to_coa(canvas_pos)
		coa_x, coa_y = coa_pos.x, coa_pos.y
		
		# Convert CoA space to RTT pixel coords
		# Add 0.5 to round to nearest pixel (OpenGL texture centers are at pixel+0.5)
		rtt_x = int(coa_x * self.picker_rtt.width() + 0.5) if coa_x < 1.0 else self.picker_rtt.width() - 1
		rtt_y = int(coa_y * self.picker_rtt.height() + 0.5) if coa_y < 1.0 else self.picker_rtt.height() - 1
		
		# Bounds check
		if rtt_x < 0 or rtt_x >= self.picker_rtt.width() or rtt_y < 0 or rtt_y >= self.picker_rtt.height():
			return None
		
		# Sample pixel
		pixel = self.picker_rtt.pixel(rtt_x, rtt_y)
		r = (pixel >> 16) & 0xFF
		g = (pixel >> 8) & 0xFF
		b = pixel & 0xFF
		
		# Look up UUID with tolerance for precision errors (GPU float->int rounding)
		# Try exact match first
		if (r, g, b) in self.picker_uuid_map:
			return self.picker_uuid_map[(r, g, b)]
		
		# If no exact match, find closest color within tolerance (±1 for each channel)
		best_match = None
		best_distance = float('inf')
		for (mr, mg, mb), uuid in self.picker_uuid_map.items():
			dist = abs(r - mr) + abs(g - mg) + abs(b - mb)  # Manhattan distance
			if dist <= 3 and dist < best_distance:  # Tolerance: max 1 per channel
				best_distance = dist
				best_match = uuid
		
		return best_match
	
	def _on_tool_mouse_move(self, event):
		"""Handle mouse move for active tool
		
		Args:
			event: QMouseEvent
		"""
		if not self.active_tool:
			return
		
		mouse_pos = event.pos()
		self.last_picker_mouse_pos = mouse_pos  # Store for UV calculation
		
		if self.active_tool == 'layer_picker':
			# Sample UUID at mouse position
			uuid = self._sample_picker_at_mouse(mouse_pos)
			
			# Paint select mode - toggle layers as we drag over them
			if self.paint_selecting and uuid and uuid not in self.paint_selected_uuids:
				if hasattr(self, 'canvas_area') and self.canvas_area:
					if hasattr(self.canvas_area, 'main_window') and self.canvas_area.main_window:
						main_window = self.canvas_area.main_window
						layer_list = main_window.right_sidebar.layer_list_widget
						
						# Mark as processed
						self.paint_selected_uuids.add(uuid)
						
						# Apply paint mode (select or deselect)
						if self.paint_select_mode == 'select':
							if uuid not in layer_list.selected_layer_uuids:
								layer_list.selected_layer_uuids.add(uuid)
								layer_list.last_selected_uuid = uuid
						elif self.paint_select_mode == 'deselect':
							if uuid in layer_list.selected_layer_uuids:
								layer_list.selected_layer_uuids.remove(uuid)
								if layer_list.last_selected_uuid == uuid:
									layer_list.last_selected_uuid = None
						
						layer_list.update_selection_visuals()
						main_window.right_sidebar._on_layer_selection_changed()
			
			# Show tooltip for hovered layer
			if uuid != self.hovered_uuid:
				self.hovered_uuid = uuid
				
				if uuid:
					# Show tooltip with layer name
					layer_name = self._get_layer_display_name(uuid)
					QToolTip.showText(
						self.mapToGlobal(mouse_pos),
						layer_name,
						self
					)
					# Trigger repaint for highlight
					self.update()
				else:
					QToolTip.hideText()
					self.update()
		
		elif self.active_tool == 'eyedropper':
			# TODO: Sample color and show tooltip
			pass
	
	def _on_tool_mouse_press(self, event):
		"""Handle mouse press for active tool
		
		Args:
			event: QMouseEvent
		
		Returns:
			True if event was handled by tool, False otherwise
		"""
		if not self.active_tool:
			return False
		
		if event.button() != Qt.LeftButton:
			return False
		
		mouse_pos = event.pos()
		modifiers = event.modifiers()
		
		if self.active_tool == 'layer_picker':
			# Sample UUID at click position
			uuid = self._sample_picker_at_mouse(mouse_pos)
			
			# Get modifiers
			ctrl_held = modifiers & Qt.ControlModifier
			shift_held = modifiers & Qt.ShiftModifier
			
			# Handle click (if we hit a layer)
			if uuid and hasattr(self, 'canvas_area') and self.canvas_area:
				if hasattr(self.canvas_area, 'main_window') and self.canvas_area.main_window:
					main_window = self.canvas_area.main_window
					layer_list = main_window.right_sidebar.layer_list_widget
					
					if ctrl_held:
						# PAINT MODE - stay active, track paint state
						self._start_paint_selection(uuid, layer_list, main_window)
						return True  # Keep picker active
					else:
						# REGULAR SELECT - toggle layer selection
						self._toggle_layer_selection(uuid, layer_list, main_window)
						# Fall through to deactivation check below
			
			# Deactivation check (after selection is handled)
			if shift_held:
				# PERSISTENT MODE - keep picker active
				return True
			else:
				# ONE-SHOT MODE - deactivate picker
				self._deactivate_picker()
				return True
		
		elif self.active_tool == 'eyedropper':
			# TODO: Sample color and apply to selected layer
			pass
		
		return False
	
	def _on_tool_mouse_release(self, event):
		"""Handle mouse release for active tool
		
		Args:
			event: QMouseEvent
		
		Returns:
			True if event was handled by tool, False otherwise
		"""
		if not self.active_tool:
			return False
		
		if event.button() != Qt.LeftButton:
			return False
		
		if self.active_tool == 'layer_picker':
			# End paint selection mode
			if self.paint_selecting:
				self.paint_selecting = False
				self.paint_select_mode = None
				self.paint_selected_uuids.clear()
				return True
		
		return False
	
	def _start_paint_selection(self, uuid, layer_list, main_window):
		"""Start ctrl+click paint selection mode
		
		Args:
			uuid: UUID of clicked layer
			layer_list: Layer list widget
			main_window: Main window reference
		"""
		self.paint_selecting = True
		self.paint_selected_uuids = {uuid}
		
		if uuid in layer_list.selected_layer_uuids:
			self.paint_select_mode = 'deselect'
			layer_list.selected_layer_uuids.remove(uuid)
		else:
			self.paint_select_mode = 'select'
			layer_list.selected_layer_uuids.add(uuid)
			layer_list.last_selected_uuid = uuid
		
		layer_list.update_selection_visuals()
		main_window.right_sidebar._on_layer_selection_changed()
	
	def _toggle_layer_selection(self, uuid, layer_list, main_window):
		"""Toggle layer selection for regular click
		
		Args:
			uuid: UUID of clicked layer
			layer_list: Layer list widget
			main_window: Main window reference
		"""
		if uuid in layer_list.selected_layer_uuids:
			layer_list.selected_layer_uuids.remove(uuid)
			if layer_list.last_selected_uuid == uuid:
				layer_list.last_selected_uuid = None
		else:
			layer_list.selected_layer_uuids.add(uuid)
			layer_list.last_selected_uuid = uuid
		
		layer_list.update_selection_visuals()
		main_window.right_sidebar._on_layer_selection_changed()
	
	def _deactivate_picker(self):
		"""Deactivate picker tool and update UI"""
		self.set_tool_mode(None)
		
		if hasattr(self, 'canvas_area') and self.canvas_area:
			if hasattr(self.canvas_area, 'bottom_bar') and hasattr(self.canvas_area.bottom_bar, 'picker_btn'):
				btn = self.canvas_area.bottom_bar.picker_btn
				btn.blockSignals(True)
				btn.setChecked(False)
				btn.blockSignals(False)
			
			self.canvas_area.update_transform_widget_for_layer()
	
	def _get_layer_display_name(self, uuid):
		"""Get display name for layer tooltip
		
		Args:
			uuid: Layer UUID
		
		Returns:
			Display string with layer name and container if applicable
		"""
		from models.coa import CoA
		
		if not CoA.has_active():
			return "Unknown Layer"
		
		coa = CoA.get_active()
		layer = coa.get_layer_by_uuid(uuid)
		if not layer:
			return "Unknown Layer"
		
		# Get layer name
		layer_name = getattr(layer, 'name', None)
		if not layer_name:
			# Fallback to texture name
			texture = getattr(layer, 'texture', getattr(layer, 'path', getattr(layer, 'filename', 'layer')))
			if texture:
				# Extract filename without path and extension
				import os
				layer_name = os.path.splitext(os.path.basename(texture))[0]
			else:
				layer_name = "layer"
		
		# Check for container
		container_uuid = coa.get_layer_container(uuid)
		if container_uuid:
			# Parse container name from container_uuid
			# Format: "container_{uuid}_{name}"
			parts = container_uuid.split('_', 2)
			container_name = parts[2] if len(parts) >= 3 else "Container"
			if container_name:
				return f"{layer_name} ({container_name})"
		
		return layer_name
	
	# ========================================
	# Eyedropper Tool (placeholder for future)
	# ========================================
	
	def _activate_eyedropper(self):
		"""Activate eyedropper tool"""
		# Generate picker RTT if needed (reuse same RTT)
		if not self.picker_rtt_valid:
			self._generate_picker_rtt()
		
		# Don't clear selection - we need it to apply color to
		# Just hide transform widget
		if hasattr(self, 'canvas_area') and self.canvas_area:
			if hasattr(self.canvas_area, 'transform_widget'):
				self.canvas_area.transform_widget.set_visible(False)
	
	def _deactivate_eyedropper(self):
		"""Deactivate eyedropper tool"""
		# Restore transform widget visibility if layer selected
		if hasattr(self, 'canvas_area') and self.canvas_area:
			self.canvas_area.update_transform_widget_for_layer()
