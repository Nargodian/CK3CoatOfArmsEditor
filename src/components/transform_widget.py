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
		
	def set_transform(self, pos_x, pos_y, scale_x, scale_y, rotation):
		"""Set the transform values"""
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
		# pos_x: 0.0-1.0 → screen pixels, where 0.5 is center
		# Canvas space: (pos - 0.5) * 1.1 gives -0.55 to 0.55 range, then scale by viewport
		canvas_x = (self.pos_x - 0.5) * 1.1 * (size / 1.6)  # 1.6 is full canvas range (-0.8 to 0.8)
		canvas_y = (self.pos_y - 0.5) * 1.1 * (size / 1.6)
		
		center_x = offset_x + size / 2 + canvas_x
		center_y = offset_y + size / 2 + canvas_y  # Y already inverted in pos_y from CK3
		
		# Scale: canvas uses scale * 0.6 for half dimensions
		# Base size should represent the emblem's natural size
		scaled_w = abs(self.scale_x) * 0.6 * (size / 1.6)
		scaled_h = abs(self.scale_y) * 0.6 * (size / 1.6)
		
		# Create transform
		transform = QTransform()
		transform.translate(center_x, center_y)
		transform.rotate(self.rotation)
		transform.scale(1.0, 1.0)  # Scale already applied to dimensions
		
		painter.setTransform(transform)
		
		# Draw bounding box (using scaled dimensions)
		rect = QRectF(-scaled_w, -scaled_h, scaled_w * 2, scaled_h * 2)
		
		# Box outline
		pen = QPen(QColor(90, 141, 191, 200), 2)
		painter.setPen(pen)
		painter.setBrush(Qt.NoBrush)
		painter.drawRect(rect)
		
		# Reset transform for handles (draw in screen space)
		painter.resetTransform()
		
		# Draw handles
		handle_brush = QBrush(QColor(90, 141, 191, 255))
		handle_pen = QPen(QColor(255, 255, 255, 255), 1)
		painter.setPen(handle_pen)
		painter.setBrush(handle_brush)
		
		# Get corner positions in screen space
		corners = self._get_handle_positions(center_x, center_y, scaled_w, scaled_h)
		
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
		"""Calculate handle positions in screen space"""
		rad = math.radians(self.rotation)
		cos_r = math.cos(rad)
		sin_r = math.sin(rad)
		
		def rotate_point(x, y):
			"""Rotate point around origin"""
			rx = x * cos_r - y * sin_r
			ry = x * sin_r + y * cos_r
			return QPointF(center_x + rx, center_y + ry)
		
		positions = {}
		
		# Corners
		positions[self.HANDLE_TL] = rotate_point(-half_w, -half_h)
		positions[self.HANDLE_TR] = rotate_point(half_w, -half_h)
		positions[self.HANDLE_BL] = rotate_point(-half_w, half_h)
		positions[self.HANDLE_BR] = rotate_point(half_w, half_h)
		
		# Edges
		positions[self.HANDLE_T] = rotate_point(0, -half_h)
		positions[self.HANDLE_B] = rotate_point(0, half_h)
		positions[self.HANDLE_L] = rotate_point(-half_w, 0)
		positions[self.HANDLE_R] = rotate_point(half_w, 0)
		
		# Center
		positions[self.HANDLE_CENTER] = QPointF(center_x, center_y)
		
		# Rotation handle (above top edge)
		positions[self.HANDLE_ROTATE] = rotate_point(0, -half_h - self.rotation_handle_offset)
		
		return positions
	
	def _get_handle_at_pos(self, pos):
		"""Get which handle is at the given position"""
		if not self.visible:
			return self.HANDLE_NONE
		
		# Calculate same coordinates as paintEvent
		size = min(self.width(), self.height())
		offset_x = (self.width() - size) / 2
		offset_y = (self.height() - size) / 2
		
		canvas_x = (self.pos_x - 0.5) * 1.1 * (size / 1.6)
		canvas_y = (self.pos_y - 0.5) * 1.1 * (size / 1.6)
		
		center_x = offset_x + size / 2 + canvas_x
		center_y = offset_y + size / 2 + canvas_y
		
		scaled_w = abs(self.scale_x) * 0.6 * (size / 1.6)
		scaled_h = abs(self.scale_y) * 0.6 * (size / 1.6)
		
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
		
		return self.HANDLE_NONE
	
	def mousePressEvent(self, event):
		"""Handle mouse press"""
		if event.button() == Qt.LeftButton:
			self.active_handle = self._get_handle_at_pos(event.pos())
			if self.active_handle != self.HANDLE_NONE:
				self.drag_start_pos = event.pos()
				self.drag_start_transform = (self.pos_x, self.pos_y, self.scale_x, self.scale_y, self.rotation)
				event.accept()
				return
		super().mousePressEvent(event)
	
	def mouseMoveEvent(self, event):
		"""Handle mouse move"""
		if self.active_handle != self.HANDLE_NONE and self.drag_start_pos:
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
			self.active_handle = self.HANDLE_NONE
			self.drag_start_pos = None
			self.drag_start_transform = None
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
		canvas_scale = (size / 1.6) * 1.1  # Matches canvas coordinate system
		
		if self.active_handle == self.HANDLE_CENTER:
			# Move - convert pixel delta to normalized coords
			delta_x = dx / canvas_scale
			delta_y = dy / canvas_scale
			
			self.pos_x = start_x + delta_x
			self.pos_y = start_y + delta_y
			
		elif self.active_handle == self.HANDLE_ROTATE:
			# Rotate - calculate angle from center to current position
			# Get center in screen coords
			offset_x = (self.width() - size) / 2
			offset_y = (self.height() - size) / 2
			canvas_x = (self.pos_x - 0.5) * 1.1 * (size / 1.6)
			canvas_y = (self.pos_y - 0.5) * 1.1 * (size / 1.6)
			center_x = offset_x + size / 2 + canvas_x
			center_y = offset_y + size / 2 + canvas_y
			
			angle = math.degrees(math.atan2(current_pos.y() - center_y, current_pos.x() - center_x))
			self.rotation = angle + 90  # Offset so top is 0 degrees
			
		elif self.active_handle in [self.HANDLE_TL, self.HANDLE_TR, self.HANDLE_BL, self.HANDLE_BR]:
			# Corner scale (uniform scaling)
			distance = math.sqrt(dx*dx + dy*dy)
			# Determine direction (moving away = positive, towards center = negative)
			direction = 1 if (dx + dy > 0) != (self.active_handle in [self.HANDLE_TL, self.HANDLE_BR]) else -1
			scale_factor = 1.0 + (distance / (size * 0.3)) * direction
			
			self.scale_x = start_sx * scale_factor
			self.scale_y = start_sy * scale_factor
			
		elif self.active_handle in [self.HANDLE_L, self.HANDLE_R]:
			# Horizontal scale
			scale_delta = dx / (size * 0.3)
			if self.active_handle == self.HANDLE_L:
				scale_delta = -scale_delta
			self.scale_x = start_sx * (1.0 + scale_delta)
			
		elif self.active_handle in [self.HANDLE_T, self.HANDLE_B]:
			# Vertical scale
			scale_delta = dy / (size * 0.3)
			if self.active_handle == self.HANDLE_T:
				scale_delta = -scale_delta
			self.scale_y = start_sy * (1.0 + scale_delta)
		
		# Clamp values
		self.pos_x = max(0.0, min(1.0, self.pos_x))
		self.pos_y = max(0.0, min(1.0, self.pos_y))
		self.scale_x = max(0.01, min(5.0, self.scale_x))
		self.scale_y = max(0.01, min(5.0, self.scale_y))
		
		# Emit signal
		self.transformChanged.emit(self.pos_x, self.pos_y, self.scale_x, self.scale_y, self.rotation)
		self.update()