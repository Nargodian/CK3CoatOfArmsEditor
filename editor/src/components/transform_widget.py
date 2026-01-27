"""
Transform Widget - Interactive transform controls for CoA layers

Provides a draggable transform widget with:
- 4 corner handles for scaling
- 4 edge handles for directional scaling  
- Center handle for positioning
- Rotation handle for rotation
- Visual bounding box overlay
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal, QEvent
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QTransform
import math

# Import coordinate conversion functions from canvas_widget
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canvas_widget import layer_pos_to_qt_pixels, qt_pixels_to_layer_pos


class TransformWidget(QWidget):
	"""Interactive transform widget for manipulating layer transforms"""
	
	# Signals
	transformChanged = pyqtSignal(float, float, float, float, float)  # pos_x, pos_y, scale_x, scale_y, rotation
	nonUniformScaleUsed = pyqtSignal()  # Emitted when side handles are used for non-uniform scaling
	transformEnded = pyqtSignal()  # Emitted when drag ends (for history saving)
	layerDuplicated = pyqtSignal()  # Emitted when Ctrl+drag duplicates layer
	
	# Handle types
	HANDLE_NONE = 0
	HANDLE_CENTER = 1
	HANDLE_TL = 2  # Top-left corner
	HANDLE_TR = 3  # Top-right corner
	HANDLE_BL = 4  # Bottom-left corner
	HANDLE_BR = 5  # Bottom-right corner
	HANDLE_T = 6   # Top edge
	HANDLE_B = 7   # Bottom edge
	HANDLE_L = 8   # Left edge
	HANDLE_R = 9   # Right edge
	HANDLE_ROTATE = 10
	HANDLE_AXIS_X = 11  # X-axis arrow
	HANDLE_AXIS_Y = 12  # Y-axis arrow
	
	def __init__(self, parent=None, canvas_widget=None):
		super().__init__(parent)
		self.setAttribute(Qt.WA_TranslucentBackground)
		self.setMouseTracking(True)
		
		# Reference to canvas widget for coordinate calculations
		# If not provided, assume parent is the canvas (backward compatibility)
		self.canvas_widget = canvas_widget if canvas_widget else parent
		
		# Transform state
		self.pos_x = 0.5  # Normalized [0-1]
		self.pos_y = 0.5
		self.scale_x = 1.0
		self.scale_y = 1.0
		self.rotation = 0.0  # Degrees
		
		# Widget size (base size for the transform box)
		self.base_width = 200
		self.base_height = 200
		
		# Interaction state
		self.active_handle = self.HANDLE_NONE
		self.drag_start_pos = None
		self.drag_start_transform = None
		self.visible = False
		
		# Rotation drag state (Task 3.2)
		self.is_rotating = False  # Flag to prevent AABB recalculation during rotation
		self.cached_aabb = None  # Cache AABB during rotation drag
		
		# Multi-selection state
		self.is_multi_selection = False  # Flag to skip scale clamping for group transforms
		
		# Ctrl+drag duplication state
		self.ctrl_pressed_at_drag_start = False
		self.duplicate_created = False  # Prevent spam
		
		# Handle size
		self.handle_size = 8
		self.rotation_handle_offset = 30
		
		# Position absolutely on top of parent
		if parent:
			self.setGeometry(0, 0, parent.width(), parent.height())
			parent.installEventFilter(self)
	
	def eventFilter(self, obj, event):
		"""Handle parent resize to keep widget covering parent"""
		if event.type() == event.Resize and obj == self.parent():
			self.setGeometry(0, 0, obj.width(), obj.height())
		return super().eventFilter(obj, event)
	
	def _get_canvas_rect(self):
		"""Get canvas widget's geometry (position and size within parent container).
		
		Returns:
			tuple: (x, y, width, height, size, offset_x, offset_y)
				- x, y: canvas position in container
				- width, height: canvas dimensions
				- size: square viewport size (min of width/height)
				- offset_x, offset_y: position of square viewport center
		"""
		geom = self.canvas_widget.geometry()
		x, y = geom.x(), geom.y()
		width, height = geom.width(), geom.height()
		size = min(width, height)
		offset_x = x + (width - size) / 2
		offset_y = y + (height - size) / 2
		return x, y, width, height, size, offset_x, offset_y
		
	def set_transform(self, pos_x, pos_y, scale_x, scale_y, rotation, is_multi_selection=False):
		"""Set the transform values
		
		Args:
			is_multi_selection: If True, skip scale clamping (group AABB can exceed 1.0)
		"""
		self.is_multi_selection = is_multi_selection
		self.pos_x = pos_x
		self.pos_y = pos_y
		self.scale_x = scale_x
		self.scale_y = scale_y
		self.rotation = rotation
		self.update()
	
	def set_visible(self, visible):
		"""Show/hide the transform widget"""
		self.visible = visible
		self.update()
	
	def paintEvent(self, event):
		"""Draw the transform widget"""
		if not self.visible:
			return
		
		painter = QPainter(self)
		painter.setRenderHint(QPainter.Antialiasing)
		
		# Match canvas coordinate system:
		# - Canvas uses -0.8 to 0.8 screen space for the CoA
		# - Position 0.5 = center (0.0 in screen space)
		# - Scale is multiplied by 0.6 for actual size
		
		# Get canvas position and size within parent container
		_, _, _, _, size, offset_x, offset_y = self._get_canvas_rect()
		
		# Convert layer position to Qt pixel coordinates using shared function
		center_x, center_y = layer_pos_to_qt_pixels(self.pos_x, self.pos_y, size, offset_x, offset_y)
		
		# Widget box shows fixed size based on scale values only
		# Rotation doesn't affect the widget box size
		scale_w = abs(self.scale_x) * 0.6 * (size / 2)
		scale_h = abs(self.scale_y) * 0.6 * (size / 2)
		
		# Draw axis-aligned bounding box (fixed size)
		painter.setPen(QPen(QColor(90, 141, 191, 200), 2))
		painter.setBrush(Qt.NoBrush)
		rect = QRectF(center_x - scale_w, center_y - scale_h, scale_w * 2, scale_h * 2)
		painter.drawRect(rect)
		
		# Draw handles
		handle_brush = QBrush(QColor(90, 141, 191, 255))
		handle_pen = QPen(QColor(255, 255, 255, 255), 1)
		painter.setPen(handle_pen)
		painter.setBrush(handle_brush)
		
		# Get corner positions in screen space (fixed box size)
		corners = self._get_handle_positions(center_x, center_y, scale_w, scale_h)
		
		# Draw corner handles
		for handle_type in [self.HANDLE_TL, self.HANDLE_TR, self.HANDLE_BL, self.HANDLE_BR]:
			pos = corners[handle_type]
			painter.drawEllipse(pos, self.handle_size, self.handle_size)
		
		# Draw edge handles
		for handle_type in [self.HANDLE_T, self.HANDLE_B, self.HANDLE_L, self.HANDLE_R]:
			pos = corners[handle_type]
			painter.drawRect(int(pos.x() - self.handle_size/2), int(pos.y() - self.handle_size/2), 
			                self.handle_size, self.handle_size)
		
		# Draw center handle
		center_pos = corners[self.HANDLE_CENTER]
		painter.drawEllipse(center_pos, self.handle_size, self.handle_size)
		
		# Draw rotation handle
		rot_pos = corners[self.HANDLE_ROTATE]
		painter.drawEllipse(rot_pos, self.handle_size, self.handle_size)
		
		# Draw line to rotation handle
		painter.setPen(QPen(QColor(90, 141, 191, 150), 1, Qt.DashLine))
		painter.drawLine(center_pos, rot_pos)
		
		# Draw axis arrows for constrained translation
		arrow_start_offset = 15  # Start arrows a bit away from center
		arrow_length = 50
		arrow_head_size = 8
		
		# Check if hovering over arrows for highlight
		hover_handle = self._get_handle_at_pos(self.mapFromGlobal(self.cursor().pos())) if hasattr(self, 'cursor') else self.HANDLE_NONE
		
		# X-axis arrow (red, pointing right)
		x_alpha = 255 if hover_handle == self.HANDLE_AXIS_X else 200
		painter.setPen(QPen(QColor(255, 80, 80, x_alpha), 4 if hover_handle == self.HANDLE_AXIS_X else 3))
		painter.setBrush(QBrush(QColor(255, 80, 80, x_alpha)))
		x_start = QPointF(center_x + arrow_start_offset, center_y)
		x_end = QPointF(center_x + arrow_start_offset + arrow_length, center_y)
		painter.drawLine(x_start, x_end)
		# Arrow head
		painter.drawPolygon([
			x_end,
			QPointF(x_end.x() - arrow_head_size, x_end.y() - arrow_head_size/2),
			QPointF(x_end.x() - arrow_head_size, x_end.y() + arrow_head_size/2)
		])
		
		# Y-axis arrow (green, pointing up)
		y_alpha = 255 if hover_handle == self.HANDLE_AXIS_Y else 200
		painter.setPen(QPen(QColor(80, 255, 80, y_alpha), 4 if hover_handle == self.HANDLE_AXIS_Y else 3))
		painter.setBrush(QBrush(QColor(80, 255, 80, y_alpha)))
		y_start = QPointF(center_x, center_y - arrow_start_offset)
		y_end = QPointF(center_x, center_y - arrow_start_offset - arrow_length)
		painter.drawLine(y_start, y_end)
		# Arrow head
		painter.drawPolygon([
			y_end,
			QPointF(y_end.x() - arrow_head_size/2, y_end.y() + arrow_head_size),
			QPointF(y_end.x() + arrow_head_size/2, y_end.y() + arrow_head_size)
		])
	
	def _get_handle_positions(self, center_x, center_y, half_w, half_h):
		"""Calculate handle positions in screen space.
		Widget uses fixed-size box based on scale values.
		"""
		positions = {}
		
		# Handles on fixed-size box
		left = center_x - half_w
		right = center_x + half_w
		top = center_y - half_h
		bottom = center_y + half_h
		
		positions[self.HANDLE_TL] = QPointF(left, top)
		positions[self.HANDLE_TR] = QPointF(right, top)
		positions[self.HANDLE_BL] = QPointF(left, bottom)
		positions[self.HANDLE_BR] = QPointF(right, bottom)
		positions[self.HANDLE_T] = QPointF(center_x, top)
		positions[self.HANDLE_B] = QPointF(center_x, bottom)
		positions[self.HANDLE_L] = QPointF(left, center_y)
		positions[self.HANDLE_R] = QPointF(right, center_y)
		positions[self.HANDLE_CENTER] = QPointF(center_x, center_y)
		positions[self.HANDLE_ROTATE] = QPointF(center_x, top - self.rotation_handle_offset)
		positions[self.HANDLE_AXIS_X] = QPointF(center_x + 65, center_y)  # End of X arrow (15 + 50)
		positions[self.HANDLE_AXIS_Y] = QPointF(center_x, center_y - 65)  # End of Y arrow (15 + 50, pointing up)
		
		return positions
	
	def _get_handle_at_pos(self, pos):
		"""Get which handle is at the given position"""
		if not self.visible:
			return self.HANDLE_NONE
		
		# Get canvas position and size
		_, _, _, _, size, offset_x, offset_y = self._get_canvas_rect()
		
		center_x, center_y = layer_pos_to_qt_pixels(self.pos_x, self.pos_y, size, offset_x, offset_y)
		
		scaled_w = abs(self.scale_x) * 0.6 * (size / 2)
		scaled_h = abs(self.scale_y) * 0.6 * (size / 2)
		
		handles = self._get_handle_positions(center_x, center_y, scaled_w, scaled_h)
		
		# Check handles in priority order (rotation first, then axis arrows, then corners, edges, center)
		check_order = [
			self.HANDLE_ROTATE,
			self.HANDLE_AXIS_X, self.HANDLE_AXIS_Y,
			self.HANDLE_TL, self.HANDLE_TR, self.HANDLE_BL, self.HANDLE_BR,
			self.HANDLE_T, self.HANDLE_B, self.HANDLE_L, self.HANDLE_R,
			self.HANDLE_CENTER
		]
		
		hit_distance = self.handle_size + 4  # Slightly larger hit area
		
		# Use wider hit area for axis arrows (check along the arrow shaft)
		for handle_type in check_order:
			handle_pos = handles[handle_type]
			
			if handle_type == self.HANDLE_AXIS_X:
				# Check along X arrow line (pointing right, starting at center_x + 15)
				if abs(pos.y() - center_y) < 10 and center_x + 15 < pos.x() < center_x + 65:
					return handle_type
			elif handle_type == self.HANDLE_AXIS_Y:
				# Check along Y arrow line (pointing up, starting at center_y - 15)
				if abs(pos.x() - center_x) < 10 and center_y - 65 < pos.y() < center_y - 15:
					return handle_type
			else:
				# Regular circular hit detection
				dx = pos.x() - handle_pos.x()
				dy = pos.y() - handle_pos.y()
				distance = math.sqrt(dx*dx + dy*dy)
				
				if distance <= hit_distance:
					return handle_type
		
		# If no handle hit, check if we're inside the AABB (for translation)
		# This makes the entire bounding box grabbable for moving
		left = center_x - scaled_w
		right = center_x + scaled_w
		top = center_y - scaled_h
		bottom = center_y + scaled_h
		
		if left <= pos.x() <= right and top <= pos.y() <= bottom:
			return self.HANDLE_CENTER  # Treat as center handle (translation)
		
		return self.HANDLE_NONE
	
	def mousePressEvent(self, event):
		"""Handle mouse press"""
		if event.button() == Qt.LeftButton:
			self.active_handle = self._get_handle_at_pos(event.pos())
			if self.active_handle != self.HANDLE_NONE:
				self.drag_start_pos = event.pos()
			self.drag_start_transform = (self.pos_x, self.pos_y, self.scale_x, self.scale_y, self.rotation)
			
			# Track Ctrl key state at drag start (explicit check)
			self.ctrl_pressed_at_drag_start = (event.modifiers() & Qt.ControlModifier) == Qt.ControlModifier
			self.duplicate_created = False  # Reset spam protection
			
			# Task 3.2: Set rotation flag and cache AABB
			if self.active_handle == self.HANDLE_ROTATE:
				self.is_rotating = True
				self.cached_aabb = (self.pos_x, self.pos_y, self.scale_x, self.scale_y)
			
			event.accept()
			return
		super().mousePressEvent(event)
	
	def mouseMoveEvent(self, event):
		"""Handle mouse move"""
		if self.active_handle != self.HANDLE_NONE and self.drag_start_pos:
			# Check for Ctrl+drag duplication with 5-pixel threshold
			if (self.ctrl_pressed_at_drag_start and 
			    not self.duplicate_created and 
			    self.active_handle == self.HANDLE_CENTER):
				# Check if mouse has moved at least 5 pixels from drag start
				dx = event.pos().x() - self.drag_start_pos.x()
				dy = event.pos().y() - self.drag_start_pos.y()
				distance = math.sqrt(dx*dx + dy*dy)
				
				if distance >= 5:  # 5-pixel threshold
					self.duplicate_created = True
					self.layerDuplicated.emit()
					# Note: Don't reset drag_start_pos - keep dragging from original position
			
			self._handle_drag(event.pos())
			event.accept()
			return
		
		# Update cursor based on handle
		handle = self._get_handle_at_pos(event.pos())
		if handle != self.HANDLE_NONE:
			if handle == self.HANDLE_CENTER:
				self.setCursor(Qt.SizeAllCursor)
			elif handle == self.HANDLE_AXIS_X:
				self.setCursor(Qt.SizeHorCursor)
			elif handle == self.HANDLE_AXIS_Y:
				self.setCursor(Qt.SizeVerCursor)
			elif handle == self.HANDLE_ROTATE:
				self.setCursor(Qt.CrossCursor)
			else:
				self.setCursor(Qt.SizeFDiagCursor)
		else:
			self.setCursor(Qt.ArrowCursor)
		
		# Trigger repaint for hover effects
		self.update()
		
		super().mouseMoveEvent(event)
	
	def mouseReleaseEvent(self, event):
		"""Handle mouse release"""
		if event.button() == Qt.LeftButton and self.active_handle != self.HANDLE_NONE:
			# Clear rotation state when releasing any handle (could have used Alt+wheel on any handle)
			if self.is_rotating:
				self.is_rotating = False
			
			self.active_handle = self.HANDLE_NONE
			self.drag_start_pos = None
			self.drag_start_transform = None
			# Emit signal for history saving
			self.transformEnded.emit()
			event.accept()
			return
		super().mouseReleaseEvent(event)
	
	def wheelEvent(self, event):
		"""Handle mouse wheel for scaling and rotation while dragging"""
		# Only respond to wheel events when actively dragging
		if self.active_handle == self.HANDLE_NONE:
			super().wheelEvent(event)
			return
		
		# Get wheel delta (check both angleDelta and pixelDelta for different input devices)
		angle_delta = event.angleDelta()
		pixel_delta = event.pixelDelta()
		
		# Try angleDelta first (traditional mouse wheel), then pixelDelta (touchpad/trackpad)
		delta = 0
		if angle_delta.y() != 0:
			delta = angle_delta.y()
		elif angle_delta.x() != 0:
			delta = angle_delta.x()
		elif pixel_delta.y() != 0:
			delta = pixel_delta.y()
		elif pixel_delta.x() != 0:
			delta = pixel_delta.x()
		
		if delta == 0:
			return
		
		# Normalize delta to a small increment
		increment = 0.02 if delta > 0 else -0.02
		
		modifiers = event.modifiers()
		
		if modifiers & Qt.AltModifier:
			# Alt + wheel: Rotate
			rotation_increment = 5.0 if delta > 0 else -5.0
			self.rotation += rotation_increment
			# Normalize to 0-360 range
			self.rotation = self.rotation % 360
			# Set rotation flag for multi-selection group rotation
			if not self.is_rotating:
				self.is_rotating = True
				self.cached_aabb = (self.pos_x, self.pos_y, self.scale_x, self.scale_y)
		elif modifiers & Qt.ControlModifier:
			# Ctrl + wheel: Scale X only
			sign_x = 1 if self.scale_x >= 0 else -1
			new_scale_x = abs(self.scale_x) + increment
			# Only clamp max for single selection (groups can exceed 1.0)
			if self.is_multi_selection:
				new_scale_x = max(0.01, new_scale_x)
			else:
				new_scale_x = max(0.01, min(1.0, new_scale_x))
			self.scale_x = sign_x * new_scale_x
			self.nonUniformScaleUsed.emit()
		elif modifiers & Qt.ShiftModifier:
			# Shift + wheel: Scale Y only
			sign_y = 1 if self.scale_y >= 0 else -1
			new_scale_y = abs(self.scale_y) + increment
			# Only clamp max for single selection (groups can exceed 1.0)
			if self.is_multi_selection:
				new_scale_y = max(0.01, new_scale_y)
			else:
				new_scale_y = max(0.01, min(1.0, new_scale_y))
			self.scale_y = sign_y * new_scale_y
			self.nonUniformScaleUsed.emit()
		else:
			# No modifier: Scale both X and Y uniformly
			sign_x = 1 if self.scale_x >= 0 else -1
			sign_y = 1 if self.scale_y >= 0 else -1
			new_scale_x = abs(self.scale_x) + increment
			new_scale_y = abs(self.scale_y) + increment
			# Only clamp max for single selection (groups can exceed 1.0)
			if self.is_multi_selection:
				new_scale_x = max(0.01, new_scale_x)
				new_scale_y = max(0.01, new_scale_y)
			else:
				new_scale_x = max(0.01, min(1.0, new_scale_x))
				new_scale_y = max(0.01, min(1.0, new_scale_y))
			self.scale_x = sign_x * new_scale_x
			self.scale_y = sign_y * new_scale_y
		
		# Emit signal and update
		self.transformChanged.emit(self.pos_x, self.pos_y, self.scale_x, self.scale_y, self.rotation)
		self.update()
		event.accept()
	
	def _handle_drag(self, current_pos):
		"""Handle dragging based on active handle"""
		if not self.drag_start_pos or not self.drag_start_transform:
			return
		
		dx = current_pos.x() - self.drag_start_pos.x()
		dy = current_pos.y() - self.drag_start_pos.y()
		
		start_x, start_y, start_sx, start_sy, start_rot = self.drag_start_transform
		
		# Get canvas size for coordinate conversion
		_, _, _, _, size, offset_x, offset_y = self._get_canvas_rect()
		
		if self.active_handle == self.HANDLE_CENTER:
			# Move - convert current pixel position to layer coords
			new_pos_x, new_pos_y = qt_pixels_to_layer_pos(
				current_pos.x(), current_pos.y(), size, offset_x, offset_y
			)
			self.pos_x = new_pos_x
			self.pos_y = new_pos_y
			
		elif self.active_handle == self.HANDLE_AXIS_X:
			# X-axis constrained movement (only horizontal)
			new_pos_x, _ = qt_pixels_to_layer_pos(
				current_pos.x(), current_pos.y(), size, offset_x, offset_y
			)
			self.pos_x = new_pos_x
			# Y position stays locked
			self.pos_y = start_y
			
		elif self.active_handle == self.HANDLE_AXIS_Y:
			# Y-axis constrained movement (only vertical)
			_, new_pos_y = qt_pixels_to_layer_pos(
				current_pos.x(), current_pos.y(), size, offset_x, offset_y
			)
			self.pos_y = new_pos_y
			# X position stays locked
			self.pos_x = start_x
			
		elif self.active_handle == self.HANDLE_ROTATE:
			# Rotate - calculate delta angle from start position
			# Get center in screen coords
			_, _, _, _, size, offset_x, offset_y = self._get_canvas_rect()
			center_x, center_y = layer_pos_to_qt_pixels(self.pos_x, self.pos_y, size, offset_x, offset_y)
			
			# Calculate angle from center to start position
			start_angle = math.degrees(math.atan2(self.drag_start_pos.y() - center_y, self.drag_start_pos.x() - center_x))
			# Calculate angle from center to current position
			current_angle = math.degrees(math.atan2(current_pos.y() - center_y, current_pos.x() - center_x))
			# Apply delta rotation
			angle_delta = current_angle - start_angle
			start_rotation = self.drag_start_transform[4]  # rotation is index 4 in tuple
			self.rotation = start_rotation + angle_delta
			
		elif self.active_handle in [self.HANDLE_TL, self.HANDLE_TR, self.HANDLE_BL, self.HANDLE_BR]:
			# Corner scale (uniform scaling)
			# Calculate distance in viewport space
			distance = math.sqrt(dx*dx + dy*dy)
			# Base scale factor on distance relative to viewport
			base_scale = abs(start_sx) if abs(start_sx) > 0.01 else 0.5
			scale_delta = distance / (size * base_scale)
			
			# Determine if moving away or towards center
			_, _, _, _, size, offset_x, offset_y = self._get_canvas_rect()
			center_x, center_y = layer_pos_to_qt_pixels(self.pos_x, self.pos_y, size, offset_x, offset_y)
			
			# Vector from center to drag start
			start_vec_x = self.drag_start_pos.x() - center_x
			start_vec_y = self.drag_start_pos.y() - center_y
			# Vector from center to current position
			curr_vec_x = current_pos.x() - center_x
			curr_vec_y = current_pos.y() - center_y
			
			# Dot product to determine direction
			dot = start_vec_x * curr_vec_x + start_vec_y * curr_vec_y
			start_len = math.sqrt(start_vec_x**2 + start_vec_y**2)
			curr_len = math.sqrt(curr_vec_x**2 + curr_vec_y**2)
			
			if start_len > 0:
				scale_factor = curr_len / start_len
			else:
				scale_factor = 1.0
			
			self.scale_x = start_sx * scale_factor
			self.scale_y = start_sy * scale_factor
			
		elif self.active_handle in [self.HANDLE_L, self.HANDLE_R]:
			# Horizontal scale - simple X-axis scaling
			_, _, _, _, size, offset_x, offset_y = self._get_canvas_rect()
			center_x, center_y = layer_pos_to_qt_pixels(self.pos_x, self.pos_y, size, offset_x, offset_y)
			
			# Calculate horizontal distance change
			start_dist = abs(self.drag_start_pos.x() - center_x)
			curr_dist = abs(current_pos.x() - center_x)
			
			# Calculate scale factor
			if start_dist > 0:
				scale_factor = curr_dist / start_dist
				self.scale_x = start_sx * scale_factor
			self.scale_y = start_sy  # Preserve Y scale
			# Emit signal to disable unified scale
			self.nonUniformScaleUsed.emit()
		
		elif self.active_handle in [self.HANDLE_T, self.HANDLE_B]:
			# Vertical scale - simple Y-axis scaling
			_, _, _, _, size, offset_x, offset_y = self._get_canvas_rect()
			center_x, center_y = layer_pos_to_qt_pixels(self.pos_x, self.pos_y, size, offset_x, offset_y)
			
			# Calculate vertical distance change
			start_dist = abs(self.drag_start_pos.y() - center_y)
			curr_dist = abs(current_pos.y() - center_y)
			
			# Calculate scale factor
			if start_dist > 0:
				scale_factor = curr_dist / start_dist
				self.scale_y = start_sy * scale_factor
			self.scale_x = start_sx  # Preserve X scale
			# Emit signal to disable unified scale
			self.nonUniformScaleUsed.emit()
		
		# Clamp scale magnitude while preserving sign (for flipped layers)
		# Only clamp for single emblem transforms, not group transforms (AABB can exceed 1.0)
		# Only clamp when actually modifying scale (skip rotation and translation)
		scale_handles = [self.HANDLE_TL, self.HANDLE_TR, self.HANDLE_BL, self.HANDLE_BR,
		                  self.HANDLE_L, self.HANDLE_R, self.HANDLE_T, self.HANDLE_B]
		if not self.is_multi_selection and self.active_handle in scale_handles:
			sign_x = 1 if self.scale_x >= 0 else -1
			sign_y = 1 if self.scale_y >= 0 else -1
			self.scale_x = sign_x * max(0.01, min(1.0, abs(self.scale_x)))
			self.scale_y = sign_y * max(0.01, min(1.0, abs(self.scale_y)))
		
		# Emit signal
		self.transformChanged.emit(self.pos_x, self.pos_y, self.scale_x, self.scale_y, self.rotation)
		self.update()