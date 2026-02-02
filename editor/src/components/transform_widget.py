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
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QTransform, QMouseEvent
import math

# Import coordinate conversion functions from canvas_widget
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canvas_widget import layer_pos_to_qt_pixels, qt_pixels_to_layer_pos, VIEWPORT_BASE_SIZE, COMPOSITE_SCALE


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
	HANDLE_AXIS_X = 11  # X-axis arrow (gimble mode)
	HANDLE_AXIS_Y = 12  # Y-axis arrow (gimble mode)
	HANDLE_GIMBLE_ROTATE = 13  # Rotation ring (gimble mode)
	HANDLE_GIMBLE_CENTER = 14  # Center dot (gimble mode)
	
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
		
		# Transform mode: normal, minimal, or gimble
		self.transform_mode = "normal"
		self.minimal_mode = False  # Kept for backward compatibility
		self.bounding_rect = QRectF()  # Initialize bounding rect
		
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
		Also retrieve current zoom level and pan offsets for coordinate calculations.
		
		Returns:
			tuple: (x, y, width, height, size, offset_x, offset_y, zoom_level, pan_x, pan_y)
				- x, y: canvas position in container
				- width, height: canvas dimensions
				- size: square viewport size (min of width/height) for backward compat
				- offset_x, offset_y: position of square CoA area within canvas (centered)
				- zoom_level: current canvas zoom (default 1.0 if not available)
				- pan_x, pan_y: current pan offsets (default 0.0 if not available)
		"""
		geom = self.canvas_widget.geometry()
		x, y = geom.x(), geom.y()
		width, height = geom.width(), geom.height()
		size = min(width, height)
		# CoA is centered within the canvas area
		offset_x = x + (width - size) / 2
		offset_y = y + (height - size) / 2
		# Get zoom level and pan offsets from canvas widget if available
		zoom_level = getattr(self.canvas_widget, 'zoom_level', 1.0)
		pan_x = getattr(self.canvas_widget, 'pan_x', 0.0)
		pan_y = getattr(self.canvas_widget, 'pan_y', 0.0)
		return x, y, width, height, size, offset_x, offset_y, zoom_level, pan_x, pan_y
		
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
	
	def rescale_for_frame_change(self, scale_ratio_x, scale_ratio_y, offset_delta_x, offset_delta_y, new_scale_x, new_scale_y):
		"""Rescale widget proportionally when frame changes to prevent false transforms
		
		The widget's coordinates are in old frame space. We need to convert them to
		represent the same CoA position but in new frame space.
		
		Formula: new_frame = (old_frame + old_offset*old_scale) * (new_scale/old_scale) + 0.5*(1 - new_scale/old_scale) - new_offset*new_scale
		Simplified: new_frame = old_frame * scale_ratio + 0.5*(1 - scale_ratio) - offset_delta*new_scale
		
		Args:
			scale_ratio_x: new_frame_scale_x / old_frame_scale_x
			scale_ratio_y: new_frame_scale_y / old_frame_scale_y
			offset_delta_x: new_frame_offset_x - old_frame_offset_x
			offset_delta_y: new_frame_offset_y - old_frame_offset_y
			new_scale_x: new frame scale X
			new_scale_y: new frame scale Y
		"""
		# Scale position around center (0.5, 0.5)
		self.pos_x = self.pos_x * scale_ratio_x + 0.5 * (1 - scale_ratio_x)
		self.pos_y = self.pos_y * scale_ratio_y + 0.5 * (1 - scale_ratio_y)
		
		# Adjust for offset change (offset is scaled by new frame scale)
		self.pos_x -= offset_delta_x * new_scale_x
		self.pos_y -= offset_delta_y * new_scale_y
		
		# Adjust scale by frame scale ratio
		self.scale_x *= scale_ratio_x
		self.scale_y *= scale_ratio_y
		
		self.update()
	
	def set_visible(self, visible):
		"""Show/hide the transform widget"""
		self.visible = visible
		# Make widget transparent to mouse events when not visible
		if visible:
			self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
		else:
			self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
		self.update()
	
	def set_transform_mode(self, mode):
		"""Set transform widget mode
		
		Args:
			mode: str - "normal", "minimal", or "gimble"
		"""
		self.transform_mode = mode
		self.minimal_mode = (mode == "minimal")  # Update backward compat flag
		self.update()
	
	def set_minimal_mode(self, enabled):
		"""Toggle minimal transform widget mode (backward compatibility)"""
		self.transform_mode = "minimal" if enabled else "normal"
		self.minimal_mode = enabled
		self.update()
	
	def paintEvent(self, event):
		"""Draw the transform widget"""
		if not self.visible:
			return
		
		# Validate transform values - skip painting if any are NaN or invalid
		import math
		if (math.isnan(self.pos_x) or math.isnan(self.pos_y) or 
		    math.isnan(self.scale_x) or math.isnan(self.scale_y) or
		    math.isnan(self.rotation)):
			return  # Skip painting with invalid values
		
		painter = QPainter(self)
		painter.setRenderHint(QPainter.Antialiasing)
		
		# Get canvas position, size, zoom level, and pan offsets
		_, _, width, height, size, offset_x, offset_y, zoom_level, pan_x, pan_y = self._get_canvas_rect()
		
		# Convert layer position to Qt pixel coordinates
		center_x, center_y = layer_pos_to_qt_pixels(self.pos_x, self.pos_y, (width, height), offset_x, offset_y, zoom_level, pan_x, pan_y)
		
		# Widget box shows fixed size based on scale values
		# Must match emblem rendering: multiply by VIEWPORT_BASE_SIZE * COMPOSITE_SCALE * zoom_level
		# size already incorporates widget dimensions, multiply by zoom for visual scaling
		scale_w = abs(self.scale_x) * (size / 2) * VIEWPORT_BASE_SIZE * COMPOSITE_SCALE * zoom_level
		scale_h = abs(self.scale_y) * (size / 2) * VIEWPORT_BASE_SIZE * COMPOSITE_SCALE * zoom_level
		
		# Render based on transform mode
		if self.transform_mode == "minimal":
			self._paint_minimal_mode(painter, center_x, center_y, scale_w, scale_h)
		elif self.transform_mode == "gimble":
			self._paint_gimble_mode(painter, center_x, center_y, scale_w, scale_h)
		else:  # normal mode
			self._paint_normal_mode(painter, center_x, center_y, scale_w, scale_h)
	
	def _paint_minimal_mode(self, painter, center_x, center_y, scale_w, scale_h):
		"""Paint minimal mode: just faint bounding box"""
		self.bounding_rect = QRectF(
			center_x - scale_w, center_y - scale_h,
			scale_w * 2, scale_h * 2
		)
		painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
		painter.drawRect(self.bounding_rect)
	
	def _paint_normal_mode(self, painter, center_x, center_y, scale_w, scale_h):
		"""Paint normal mode: scale handles + rotation handle (no arrows, no center dot)"""
		# Draw axis-aligned bounding box
		painter.setPen(QPen(QColor(90, 141, 191, 200), 2))
		painter.setBrush(Qt.NoBrush)
		rect = QRectF(center_x - scale_w, center_y - scale_h, scale_w * 2, scale_h * 2)
		painter.drawRect(rect)
		
		# Draw handles
		handle_brush = QBrush(QColor(90, 141, 191, 255))
		handle_pen = QPen(QColor(255, 255, 255, 255), 1)
		painter.setPen(handle_pen)
		painter.setBrush(handle_brush)
		
		# Get corner positions
		corners = self._get_handle_positions(center_x, center_y, scale_w, scale_h)
		
		# Draw corner handles (circles)
		for handle_type in [self.HANDLE_TL, self.HANDLE_TR, self.HANDLE_BL, self.HANDLE_BR]:
			pos = corners[handle_type]
			painter.drawEllipse(pos, self.handle_size, self.handle_size)
		
		# Draw edge handles (squares)
		for handle_type in [self.HANDLE_T, self.HANDLE_B, self.HANDLE_L, self.HANDLE_R]:
			pos = corners[handle_type]
			painter.drawRect(int(pos.x() - self.handle_size/2), int(pos.y() - self.handle_size/2), 
			                self.handle_size, self.handle_size)
		
		# Draw rotation handle
		center_pos = corners[self.HANDLE_CENTER]
		rot_pos = corners[self.HANDLE_ROTATE]
		painter.drawEllipse(rot_pos, self.handle_size, self.handle_size)
		
		# Draw line to rotation handle
		painter.setPen(QPen(QColor(90, 141, 191, 150), 1, Qt.DashLine))
		painter.drawLine(center_pos, rot_pos)
	
	def _paint_gimble_mode(self, painter, center_x, center_y, scale_w, scale_h):
		"""Paint gimble mode: X/Y arrows, center dot, rotation ring"""
		# No bounding box in gimble mode
		
		arrow_start_offset = 15
		arrow_length = 50
		arrow_head_size = 8
		
		# Check if hovering for highlight
		hover_handle = self._get_handle_at_pos(self.mapFromGlobal(self.cursor().pos())) if hasattr(self, 'cursor') else self.HANDLE_NONE
		
		# X-axis arrow (red, pointing right)
		x_alpha = 255 if hover_handle == self.HANDLE_AXIS_X else 200
		painter.setPen(QPen(QColor(255, 80, 80, x_alpha), 4 if hover_handle == self.HANDLE_AXIS_X else 3))
		painter.setBrush(QBrush(QColor(255, 80, 80, x_alpha)))
		x_start = QPointF(center_x + arrow_start_offset, center_y)
		x_end = QPointF(center_x + arrow_start_offset + arrow_length, center_y)
		painter.drawLine(x_start, x_end)
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
		painter.drawPolygon([
			y_end,
			QPointF(y_end.x() - arrow_head_size/2, y_end.y() + arrow_head_size),
			QPointF(y_end.x() + arrow_head_size/2, y_end.y() + arrow_head_size)
		])
		
		# Center dot (blue) for free 2D movement
		center_alpha = 255 if hover_handle == self.HANDLE_GIMBLE_CENTER else 200
		painter.setPen(QPen(QColor(100, 150, 255, center_alpha), 2))
		painter.setBrush(QBrush(QColor(100, 150, 255, center_alpha)))
		painter.drawEllipse(QPointF(center_x, center_y), 6, 6)
		
		# Yellow rotation ring (extends beyond arrows)
		ring_radius = arrow_start_offset + arrow_length + 15  # Beyond arrow tips
		ring_alpha = 255 if hover_handle == self.HANDLE_GIMBLE_ROTATE else 180
		painter.setPen(QPen(QColor(255, 220, 80, ring_alpha), 3 if hover_handle == self.HANDLE_GIMBLE_ROTATE else 2))
		painter.setBrush(Qt.NoBrush)
		painter.drawEllipse(QPointF(center_x, center_y), ring_radius, ring_radius)
	
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
		positions[self.HANDLE_GIMBLE_CENTER] = QPointF(center_x, center_y)  # Gimble center dot
		# HANDLE_GIMBLE_ROTATE is a ring, hit detection uses radius instead of position
		
		return positions
	
	def _get_handle_at_pos(self, pos):
		"""Get which handle is at the given position"""
		if not self.visible:
			return self.HANDLE_NONE
		
		# Get canvas position, size, zoom level, and pan offsets
		_, _, width, height, size, offset_x, offset_y, zoom_level, pan_x, pan_y = self._get_canvas_rect()
		
		center_x, center_y = layer_pos_to_qt_pixels(self.pos_x, self.pos_y, (width, height), offset_x, offset_y, zoom_level, pan_x, pan_y)
		
		# Must match paintEvent scaling: multiply by VIEWPORT_BASE_SIZE * COMPOSITE_SCALE * zoom_level
		# size already incorporates widget dimensions, multiply by zoom for visual scaling
		scaled_w = abs(self.scale_x) * (size / 2) * VIEWPORT_BASE_SIZE * COMPOSITE_SCALE * zoom_level
		scaled_h = abs(self.scale_y) * (size / 2) * VIEWPORT_BASE_SIZE * COMPOSITE_SCALE * zoom_level
		
		handles = self._get_handle_positions(center_x, center_y, scaled_w, scaled_h)
		
		# Build check order based on mode
		if self.transform_mode == "gimble":
			# Gimble mode: check rotation ring, arrows, center dot
			# Check rotation ring first (it's a ring, not a point)
			ring_radius = 80  # 15 + 50 + 15
			dist_from_center = math.sqrt((pos.x() - center_x)**2 + (pos.y() - center_y)**2)
			if abs(dist_from_center - ring_radius) < 8:  # Hit tolerance for ring
				return self.HANDLE_GIMBLE_ROTATE
			
			# Check arrows (along shaft)
			if abs(pos.y() - center_y) < 10 and center_x + 15 < pos.x() < center_x + 65:
				return self.HANDLE_AXIS_X
			if abs(pos.x() - center_x) < 10 and center_y - 65 < pos.y() < center_y - 15:
				return self.HANDLE_AXIS_Y
			
			# Check center dot
			if math.sqrt((pos.x() - center_x)**2 + (pos.y() - center_y)**2) < 8:
				return self.HANDLE_GIMBLE_CENTER
			
			return self.HANDLE_NONE
		
		elif self.transform_mode == "minimal":
			# Minimal mode: check if inside bounding box for center drag
			left = center_x - scaled_w
			right = center_x + scaled_w
			top = center_y - scaled_h
			bottom = center_y + scaled_h
			
			if left <= pos.x() <= right and top <= pos.y() <= bottom:
				return self.HANDLE_CENTER
			return self.HANDLE_NONE
		
		else:  # normal mode
			# Normal mode: check scale handles and rotation handle (no arrows, no center dot)
			check_order = [
				self.HANDLE_ROTATE,
				self.HANDLE_TL, self.HANDLE_TR, self.HANDLE_BL, self.HANDLE_BR,
				self.HANDLE_T, self.HANDLE_B, self.HANDLE_L, self.HANDLE_R
			]
			
			hit_distance = self.handle_size + 4
			
			for handle_type in check_order:
				handle_pos = handles[handle_type]
				dx = pos.x() - handle_pos.x()
				dy = pos.y() - handle_pos.y()
				distance = math.sqrt(dx*dx + dy*dy)
				
				if distance <= hit_distance:
					return handle_type
			
			# Check if inside AABB for translation (grab anywhere in box)
			left = center_x - scaled_w
			right = center_x + scaled_w
			top = center_y - scaled_h
			bottom = center_y + scaled_h
			
			if left <= pos.x() <= right and top <= pos.y() <= bottom:
				return self.HANDLE_CENTER
			
			return self.HANDLE_NONE
	
	def mousePressEvent(self, event):
		"""Handle mouse press"""
		if event.button() == Qt.LeftButton:
			# Minimal mode: only allow center drag (no handle picking)
			if self.minimal_mode:
				# Check if click is inside bounding rect
				if self.bounding_rect.contains(event.pos()):
					self.active_handle = self.HANDLE_CENTER
					self.drag_start_pos = event.pos()
					self.drag_start_transform = (self.pos_x, self.pos_y, self.scale_x, self.scale_y, self.rotation)
					self.is_rotating = False
					self.ctrl_pressed_at_drag_start = (event.modifiers() & Qt.ControlModifier) == Qt.ControlModifier
					self.duplicate_created = False
					event.accept()
					return
				super().mousePressEvent(event)
				return
			
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
		
		# No handle clicked - forward to canvas widget for panning
		if self.canvas_widget:
			# Convert position to canvas widget coordinates
			canvas_pos = self.canvas_widget.mapFromGlobal(self.mapToGlobal(event.pos()))
			canvas_event = QMouseEvent(
				event.type(),
				canvas_pos,
				event.globalPos(),
				event.button(),
				event.buttons(),
				event.modifiers()
			)
			self.canvas_widget.mousePressEvent(canvas_event)
		event.ignore()
	
	def mouseMoveEvent(self, event):
		"""Handle mouse move"""
		# If not dragging a handle, forward to canvas for panning
		if self.active_handle == self.HANDLE_NONE:
			if self.canvas_widget:
				# Convert position to canvas widget coordinates
				canvas_pos = self.canvas_widget.mapFromGlobal(self.mapToGlobal(event.pos()))
				canvas_event = QMouseEvent(
					event.type(),
					canvas_pos,
					event.globalPos(),
					event.button(),
					event.buttons(),
					event.modifiers()
				)
				self.canvas_widget.mouseMoveEvent(canvas_event)
			event.ignore()
			return
		
		if self.drag_start_pos:
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
			
			self._handle_drag(event.pos(), event.modifiers())
			event.accept()
			return
		
		# Skip cursor changes in minimal mode
		if self.minimal_mode:
			self.setCursor(Qt.ArrowCursor)
			return
		
		# Update cursor based on handle
		handle = self._get_handle_at_pos(event.pos())
		if handle != self.HANDLE_NONE:
			if handle == self.HANDLE_CENTER or handle == self.HANDLE_GIMBLE_CENTER:
				self.setCursor(Qt.SizeAllCursor)
			elif handle == self.HANDLE_AXIS_X:
				self.setCursor(Qt.SizeHorCursor)
			elif handle == self.HANDLE_AXIS_Y:
				self.setCursor(Qt.SizeVerCursor)
			elif handle == self.HANDLE_ROTATE or handle == self.HANDLE_GIMBLE_ROTATE:
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
		# If we weren't handling this drag, forward to canvas
		if self.active_handle == self.HANDLE_NONE:
			if self.canvas_widget:
				# Convert position to canvas widget coordinates
				canvas_pos = self.canvas_widget.mapFromGlobal(self.mapToGlobal(event.pos()))
				canvas_event = QMouseEvent(
					event.type(),
					canvas_pos,
					event.globalPos(),
					event.button(),
					event.buttons(),
					event.modifiers()
				)
				self.canvas_widget.mouseReleaseEvent(canvas_event)
			event.ignore()
			return
		
		if event.button() == Qt.LeftButton and self.active_handle != self.HANDLE_NONE:
			# Clear rotation state when releasing any handle (could have used Alt+wheel on any handle)
			if self.is_rotating:
				self.is_rotating = False
			
			self.active_handle = self.HANDLE_NONE
			self.drag_start_pos = None
			self.drag_start_transform = None
			
			# Save history for ctrl+drag duplication (deferred from duplicate time)
			was_duplicate_drag = self.duplicate_created
			
			self.duplicate_created = False  # Reset for next drag
			self.ctrl_pressed_at_drag_start = False
			
			# Emit signal for history saving
			self.transformEnded.emit()
			
			# Save duplicate history after transform completes
			if was_duplicate_drag:
				try:
					if hasattr(self, 'canvas_area') and self.canvas_area and hasattr(self.canvas_area, 'main_window'):
						self.canvas_area.main_window._save_state("Duplicate and move layer(s)")
				except:
					pass  # Don't break drag if history save fails
			event.accept()
			return
		super().mouseReleaseEvent(event)
	
	def wheelEvent(self, event):
		"""Handle mouse wheel for scaling and rotation while dragging"""
		# Only respond to wheel events when actively dragging
		if self.active_handle == self.HANDLE_NONE:
			# Pass wheel event to the canvas widget underneath for zoom control
			if self.canvas_widget:
				self.canvas_widget.wheelEvent(event)
			return
		
		try:
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
		
			# Update drag_start_transform to new values to prevent jump on release
			if self.drag_start_transform:
				self.drag_start_transform = (self.pos_x, self.pos_y, self.scale_x, self.scale_y, self.rotation)
			
			# CRITICAL: Update drag_start_pos to current mouse position to prevent jump
			# When wheel scaling during drag, the mouse hasn't moved but the transform has changed
			# We need to reset the drag start position so continuing the drag doesn't apply old deltas
			if self.drag_start_pos:
				self.drag_start_pos = event.pos()
		
			# Emit signal and update
			self.transformChanged.emit(self.pos_x, self.pos_y, self.scale_x, self.scale_y, self.rotation)
			self.update()
			event.accept()
		except Exception as e:
			# If error occurs (e.g., during drag state changes), just ignore
			print(f"wheelEvent error: {e}")
			event.accept()
	
	def _handle_drag(self, current_pos, modifiers=None):
		"""Handle dragging based on active handle"""
		if not self.drag_start_pos or not self.drag_start_transform:
			return
		
		# Check if Alt modifier is pressed for anchor-based scaling
		alt_pressed = modifiers and (modifiers & Qt.AltModifier)
		
		dx = current_pos.x() - self.drag_start_pos.x()
		dy = current_pos.y() - self.drag_start_pos.y()
		
		start_x, start_y, start_sx, start_sy, start_rot = self.drag_start_transform
		
		# Get canvas size, zoom level, and pan offsets for coordinate conversion
		_, _, width, height, size, offset_x, offset_y, zoom_level, pan_x, pan_y = self._get_canvas_rect()
		
		if self.active_handle == self.HANDLE_CENTER or self.active_handle == self.HANDLE_GIMBLE_CENTER:
			# Move - apply pixel delta to starting position
			# Convert start position to pixels
			start_x_px, start_y_px = layer_pos_to_qt_pixels(start_x, start_y, (width, height), offset_x, offset_y, zoom_level, pan_x, pan_y)
			# Apply pixel delta
			new_x_px = start_x_px + dx
			new_y_px = start_y_px + dy
			# Convert back to layer coords with zoom
			new_pos_x, new_pos_y = qt_pixels_to_layer_pos(new_x_px, new_y_px, (width, height), offset_x, offset_y, zoom_level, pan_x, pan_y)
			self.pos_x = new_pos_x
			self.pos_y = new_pos_y
			
		elif self.active_handle == self.HANDLE_AXIS_X:
			# X-axis constrained movement (only horizontal)
			canvas_scale = size * VIEWPORT_BASE_SIZE * COMPOSITE_SCALE * zoom_level
			delta_x = dx / canvas_scale
			self.pos_x = start_x + delta_x
			# Y position stays locked
			self.pos_y = start_y
		
		elif self.active_handle == self.HANDLE_AXIS_Y:
			# Y-axis constrained movement (only vertical)
			canvas_scale = size * VIEWPORT_BASE_SIZE * COMPOSITE_SCALE * zoom_level
			delta_y = dy / canvas_scale
			self.pos_y = start_y + delta_y
			# X position stays locked
			self.pos_x = start_x
			
		elif self.active_handle == self.HANDLE_ROTATE or self.active_handle == self.HANDLE_GIMBLE_ROTATE:
			# Rotate - calculate delta angle from start position
			# Get center in screen coords with zoom and pan
			_, _, width, height, size, offset_x, offset_y, zoom_level, pan_x, pan_y = self._get_canvas_rect()
			center_x, center_y = layer_pos_to_qt_pixels(self.pos_x, self.pos_y, (width, height), offset_x, offset_y, zoom_level, pan_x, pan_y)
			
			# Calculate angle from center to start position
			start_angle = math.degrees(math.atan2(self.drag_start_pos.y() - center_y, self.drag_start_pos.x() - center_x))
			# Calculate angle from center to current position
			current_angle = math.degrees(math.atan2(current_pos.y() - center_y, current_pos.x() - center_x))
			# Apply delta rotation
			angle_delta = current_angle - start_angle
			start_rotation = self.drag_start_transform[4]  # rotation is index 4 in tuple
			new_rotation = start_rotation + angle_delta
			
			# Shift-hold: snap to 45° increments
			if modifiers and (modifiers & Qt.ShiftModifier):
				new_rotation = round(new_rotation / 45.0) * 45.0
			
			self.rotation = new_rotation
			
		elif self.active_handle in [self.HANDLE_TL, self.HANDLE_TR, self.HANDLE_BL, self.HANDLE_BR]:
			# Corner scale (uniform scaling)
			if alt_pressed:
				# Alt+drag: Anchor opposite corner, scale from that fixed point
				# Get opposite corner position in layer coords
				if self.active_handle == self.HANDLE_TL:
					anchor_x, anchor_y = start_x + start_sx * 0.5, start_y + start_sy * 0.5  # BR
				elif self.active_handle == self.HANDLE_TR:
					anchor_x, anchor_y = start_x - start_sx * 0.5, start_y + start_sy * 0.5  # BL
				elif self.active_handle == self.HANDLE_BL:
					anchor_x, anchor_y = start_x + start_sx * 0.5, start_y - start_sy * 0.5  # TR
				else:  # HANDLE_BR
					anchor_x, anchor_y = start_x - start_sx * 0.5, start_y - start_sy * 0.5  # TL
				
				# Convert anchor to screen coords with zoom and pan
				_, _, width, height, size, offset_x, offset_y, zoom_level, pan_x, pan_y = self._get_canvas_rect()
				anchor_x_px, anchor_y_px = layer_pos_to_qt_pixels(anchor_x, anchor_y, (width, height), offset_x, offset_y, zoom_level, pan_x, pan_y)
				
				# Calculate distance from anchor to current mouse position
				curr_vec_x = current_pos.x() - anchor_x_px
				curr_vec_y = current_pos.y() - anchor_y_px
				curr_dist = math.sqrt(curr_vec_x**2 + curr_vec_y**2)
				
				# Calculate distance from anchor to original handle position
				start_vec_x = self.drag_start_pos.x() - anchor_x_px
				start_vec_y = self.drag_start_pos.y() - anchor_y_px
				start_dist = math.sqrt(start_vec_x**2 + start_vec_y**2)
				
				if start_dist > 0:
					scale_factor = curr_dist / start_dist
					self.scale_x = start_sx * scale_factor
					self.scale_y = start_sy * scale_factor
					
					# Reposition center to keep anchor fixed
					# New center is anchor + (original offset from anchor) * scale_factor
					new_center_x = anchor_x + (start_x - anchor_x) * scale_factor
					new_center_y = anchor_y + (start_y - anchor_y) * scale_factor
					self.pos_x = new_center_x
					self.pos_y = new_center_y
			else:
				# Normal center-based scaling
				# Calculate distance in viewport space
				distance = math.sqrt(dx*dx + dy*dy)
				# Base scale factor on distance relative to viewport
				base_scale = abs(start_sx) if abs(start_sx) > 0.01 else 0.5
				scale_delta = distance / (size * base_scale)
				
				# Determine if moving away or towards center
				_, _, width, height, size, offset_x, offset_y, zoom_level, pan_x, pan_y = self._get_canvas_rect()
				center_x, center_y = layer_pos_to_qt_pixels(self.pos_x, self.pos_y, (width, height), offset_x, offset_y, zoom_level, pan_x, pan_y)
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
			# Horizontal scale with zoom and pan
			_, _, _, _, size, offset_x, offset_y, zoom_level, pan_x, pan_y = self._get_canvas_rect()
			center_x, center_y = layer_pos_to_qt_pixels(self.pos_x, self.pos_y, size, offset_x, offset_y, zoom_level, pan_x, pan_y)
			
			if alt_pressed:
				# Alt+drag: Anchor opposite edge
				if self.active_handle == self.HANDLE_L:
					# Anchor right edge
					anchor_x = start_x + start_sx * 0.5
				else:  # HANDLE_R
					# Anchor left edge
					anchor_x = start_x - start_sx * 0.5
				
				# Convert anchor to screen coords with zoom and pan
				anchor_x_px, _ = layer_pos_to_qt_pixels(anchor_x, start_y, (width, height), offset_x, offset_y, zoom_level, pan_x, pan_y)
				
				# Calculate new scale based on distance from anchor to mouse
				# Distance is full width (anchor is at opposite edge)
				# Scale value IS the full width in layer coordinates
				new_width_px = abs(current_pos.x() - anchor_x_px)
				canvas_scale = size * VIEWPORT_BASE_SIZE * COMPOSITE_SCALE * zoom_level
				new_scale_x = new_width_px / canvas_scale
				
				# Preserve sign
				sign_x = 1 if start_sx >= 0 else -1
				self.scale_x = sign_x * new_scale_x
				
				# Reposition center to keep anchor fixed
				new_center_x = anchor_x + (start_x - anchor_x) * (new_scale_x / abs(start_sx))
				self.pos_x = new_center_x
			else:
				# Normal center-based scaling
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
			# Vertical scale with zoom and pan
			_, _, width, height, size, offset_x, offset_y, zoom_level, pan_x, pan_y = self._get_canvas_rect()
			center_x, center_y = layer_pos_to_qt_pixels(self.pos_x, self.pos_y, (width, height), offset_x, offset_y, zoom_level, pan_x, pan_y)
			
			if alt_pressed:
				# Alt+drag: Anchor opposite edge
				if self.active_handle == self.HANDLE_T:
					# Anchor bottom edge
					anchor_y = start_y + start_sy * 0.5
				else:  # HANDLE_B
					# Anchor top edge
					anchor_y = start_y - start_sy * 0.5
				
				# Convert anchor to screen coords with zoom and pan
				_, anchor_y_px = layer_pos_to_qt_pixels(start_x, anchor_y, (width, height), offset_x, offset_y, zoom_level, pan_x, pan_y)
				
				# Calculate new scale based on distance from anchor to mouse
				# Distance is full height (anchor is at opposite edge)
				# Scale value IS the full height in layer coordinates
				new_height_px = abs(current_pos.y() - anchor_y_px)
				canvas_scale = size * VIEWPORT_BASE_SIZE * COMPOSITE_SCALE * zoom_level
				new_scale_y = new_height_px / canvas_scale
				
				# Preserve sign
				sign_y = 1 if start_sy >= 0 else -1
				self.scale_y = sign_y * new_scale_y
				
				# Reposition center to keep anchor fixed
				new_center_y = anchor_y + (start_y - anchor_y) * (new_scale_y / abs(start_sy))
				self.pos_y = new_center_y
			else:
				# Normal center-based scaling
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