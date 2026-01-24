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
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setAttribute(Qt.WA_TranslucentBackground)
		self.setMouseTracking(True)
		
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
		# - Y-axis inverted for CK3 coordinate system
		
		# Calculate viewport (canvas uses square viewport centered)
		size = min(self.width(), self.height())
		offset_x = (self.width() - size) / 2
		offset_y = (self.height() - size) / 2
		
		# Convert normalized coords to screen space matching canvas
		# Canvas: center_x = (pos_x - 0.5) * 1.1 in normalized space (-0.8 to 0.8)
		# Canvas: center_y = -(pos_y - 0.5) * 1.1 (Y inverted in OpenGL)
		# But widget uses Qt coords where Y increases downward, so we don't invert
		# Then multiply by (size / 2) to get pixels (OpenGL normalized space conversion)
		canvas_x = (self.pos_x - 0.5) * 1.1 * (size / 2)
		canvas_y = (self.pos_y - 0.5) * 1.1 * (size / 2)  # No inversion for Qt coords
		
		center_x = offset_x + size / 2 + canvas_x
		center_y = offset_y + size / 2 + canvas_y
		
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
		
		return positions
	
	def _get_handle_at_pos(self, pos):
		"""Get which handle is at the given position"""
		if not self.visible:
			return self.HANDLE_NONE
		
		# Calculate same coordinates as paintEvent
		size = min(self.width(), self.height())
		offset_x = (self.width() - size) / 2
		offset_y = (self.height() - size) / 2
		
		canvas_x = (self.pos_x - 0.5) * 1.1 * (size / 2)
		canvas_y = (self.pos_y - 0.5) * 1.1 * (size / 2)
		
		center_x = offset_x + size / 2 + canvas_x
		center_y = offset_y + size / 2 + canvas_y
		
		scaled_w = abs(self.scale_x) * 0.6 * (size / 2)
		scaled_h = abs(self.scale_y) * 0.6 * (size / 2)
		
		handles = self._get_handle_positions(center_x, center_y, scaled_w, scaled_h)
		
		# Check handles in priority order (rotation first, then corners, edges, center)
		check_order = [
			self.HANDLE_ROTATE,
			self.HANDLE_TL, self.HANDLE_TR, self.HANDLE_BL, self.HANDLE_BR,
			self.HANDLE_T, self.HANDLE_B, self.HANDLE_L, self.HANDLE_R,
			self.HANDLE_CENTER
		]
		
		hit_distance = self.handle_size + 4  # Slightly larger hit area
		
		for handle_type in check_order:
			handle_pos = handles[handle_type]
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
			# Check for Ctrl+drag duplication (only once per drag, only for translation/center handle)
			if (self.ctrl_pressed_at_drag_start and 
			    not self.duplicate_created and 
			    self.active_handle == self.HANDLE_CENTER):
				# Check if mouse has moved enough to trigger duplication (avoid accidental triggers)
				dx = event.pos().x() - self.drag_start_pos.x()
				dy = event.pos().y() - self.drag_start_pos.y()
				distance = math.sqrt(dx*dx + dy*dy)
				
				if distance > 10:  # Minimum 10 pixels movement to trigger
					self.duplicate_created = True
					self.layerDuplicated.emit()
					# Reset drag start to current position for smoother continuation
					self.drag_start_pos = event.pos()
					self.drag_start_transform = (self.pos_x, self.pos_y, self.scale_x, self.scale_y, self.rotation)
			
			self._handle_drag(event.pos())
			event.accept()
			return
		
		# Update cursor based on handle
		handle = self._get_handle_at_pos(event.pos())
		if handle != self.HANDLE_NONE:
			if handle == self.HANDLE_CENTER:
				self.setCursor(Qt.SizeAllCursor)
			elif handle == self.HANDLE_ROTATE:
				self.setCursor(Qt.CrossCursor)
			else:
				self.setCursor(Qt.SizeFDiagCursor)
		else:
			self.setCursor(Qt.ArrowCursor)
		
		super().mouseMoveEvent(event)
	
	def mouseReleaseEvent(self, event):
		"""Handle mouse release"""
		if event.button() == Qt.LeftButton and self.active_handle != self.HANDLE_NONE:
			# Clear rotation state when releasing rotation handle
			if self.active_handle == self.HANDLE_ROTATE:
				self.is_rotating = False
				self.cached_aabb = None
			
			self.active_handle = self.HANDLE_NONE
			self.drag_start_pos = None
			self.drag_start_transform = None
			# Emit signal for history saving
			self.transformEnded.emit()
			event.accept()
			return
		super().mouseReleaseEvent(event)
	
	def _handle_drag(self, current_pos):
		"""Handle dragging based on active handle"""
		if not self.drag_start_pos or not self.drag_start_transform:
			return
		
		dx = current_pos.x() - self.drag_start_pos.x()
		dy = current_pos.y() - self.drag_start_pos.y()
		
		start_x, start_y, start_sx, start_sy, start_rot = self.drag_start_transform
		
		# Calculate viewport size for coordinate conversion
		size = min(self.width(), self.height())
		# OpenGL normalized space: 1 unit = size/2 pixels
		# Canvas uses (pos - 0.5) * 1.1, so conversion is:
		canvas_scale = 1.1 * (size / 2)
		
		if self.active_handle == self.HANDLE_CENTER:
			# Move - convert pixel delta to normalized coords
			delta_x = dx / canvas_scale
			delta_y = dy / canvas_scale
			
			self.pos_x = start_x + delta_x
			self.pos_y = start_y + delta_y
			
		elif self.active_handle == self.HANDLE_ROTATE:
			# Rotate - calculate delta angle from start position
			# Get center in screen coords
			offset_x = (self.width() - size) / 2
			offset_y = (self.height() - size) / 2
			canvas_x = (self.pos_x - 0.5) * 1.1 * (size / 2)
			canvas_y = (self.pos_y - 0.5) * 1.1 * (size / 2)
			center_x = offset_x + size / 2 + canvas_x
			center_y = offset_y + size / 2 + canvas_y
			
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
			# Check the direction relative to center
			offset_x = (self.width() - size) / 2
			offset_y = (self.height() - size) / 2
			canvas_x = (self.pos_x - 0.5) * 1.1 * (size / 2)
			canvas_y = (self.pos_y - 0.5) * 1.1 * (size / 2)
			center_x = offset_x + size / 2 + canvas_x
			center_y = offset_y + size / 2 + canvas_y
			
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
			offset_x = (self.width() - size) / 2
			offset_y = (self.height() - size) / 2
			canvas_x = (self.pos_x - 0.5) * 1.1 * (size / 2)
			canvas_y = (self.pos_y - 0.5) * 1.1 * (size / 2)
			center_x = offset_x + size / 2 + canvas_x
			center_y = offset_y + size / 2 + canvas_y
			
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
			offset_x = (self.width() - size) / 2
			offset_y = (self.height() - size) / 2
			canvas_x = (self.pos_x - 0.5) * 1.1 * (size / 2)
			canvas_y = (self.pos_y - 0.5) * 1.1 * (size / 2)
			center_x = offset_x + size / 2 + canvas_x
			center_y = offset_y + size / 2 + canvas_y
			
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
		if not self.is_multi_selection:
			sign_x = 1 if self.scale_x >= 0 else -1
			sign_y = 1 if self.scale_y >= 0 else -1
			self.scale_x = sign_x * max(0.01, min(1.0, abs(self.scale_x)))
			self.scale_y = sign_y * max(0.01, min(1.0, abs(self.scale_y)))
		
		# Emit signal
		self.transformChanged.emit(self.pos_x, self.pos_y, self.scale_x, self.scale_y, self.rotation)
		self.update()