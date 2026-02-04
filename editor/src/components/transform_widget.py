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


class TransformWidget(QWidget):
	"""Interactive transform widget for manipulating layer transforms"""
	
	# Signals
	transformChanged = pyqtSignal(float, float, float, float, float)  # center_x, center_y, half_w, half_h, rotation (pixels)
	nonUniformScaleUsed = pyqtSignal()  # Emitted when side handles are used for non-uniform scaling
	transformEnded = pyqtSignal()  # Emitted when drag ends (for history saving)
	layerDuplicated = pyqtSignal()  # Emitted when Ctrl+drag duplicates layer
	
	def __init__(self, parent=None, canvas_widget=None):
		super().__init__(parent)
		self.setAttribute(Qt.WA_TranslucentBackground)
		self.setMouseTracking(True)
		
		# Reference to canvas widget for coordinate calculations
		# If not provided, assume parent is the canvas (backward compatibility)
		self.canvas_widget = canvas_widget if canvas_widget else parent
		
		# Transform state (PURE PIXEL SPACE - Decision 3)
		self.center_x = 0.0  # Widget pixel X
		self.center_y = 0.0  # Widget pixel Y
		self.half_w = 100.0  # AABB half-width (pixels)
		self.half_h = 100.0  # AABB half-height (pixels)
		self.rotation = 0.0  # Degrees
		
		# Interaction state
		self.active_handle = None  # Now stores handle_type string from mode
		self.drag_start_pos = None
		self.drag_start_transform = None  # (center_x, center_y, half_w, half_h, rotation)
		self.visible = False
		
		# Multi-selection state
		self.is_multi_selection = False  # Flag to skip scale clamping for group transforms
		
		# Drag context (Decision 5)
		from .transform_widgets import DragContext
		self.drag_context = None
		
		# Mode system (Handle Architecture)
		from .transform_widgets import create_mode
		self.current_mode = create_mode('bbox')  # Start in bbox mode
		self.transform_mode = 'bbox'  # Track mode name
		
		# Handle constants (from constants.py)
		from constants import TRANSFORM_HANDLE_SIZE, TRANSFORM_ROTATION_HANDLE_OFFSET
		self.handle_size = TRANSFORM_HANDLE_SIZE
		self.rotation_handle_offset = TRANSFORM_ROTATION_HANDLE_OFFSET
		
		# Backward compatibility flags
		self.minimal_mode = False
		self.bounding_rect = QRectF()
		
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
		
	def set_transform(self, center_x, center_y, half_w, half_h, rotation, is_multi_selection=False):
		"""Set the transform values in pixel space (Decision 3).
		
		Args:
			center_x: Center X in canvas pixels (canvas center-origin)
			center_y: Center Y in canvas pixels (canvas center-origin)
			half_w: AABB half-width in pixels
			half_h: AABB half-height in pixels
			rotation: Rotation in degrees
			is_multi_selection: If True, this is a group selection AABB
		"""
		import math
		
		# Validate all inputs (Decision 8)
		if any(math.isnan(v) or math.isinf(v) for v in [center_x, center_y, half_w, half_h, rotation]):
			from utils.logger import loggerRaise
			e = ValueError(f"Invalid transform values: center=({center_x}, {center_y}), half=({half_w}, {half_h}), rotation={rotation}")
			loggerRaise(e, "set_transform received invalid values")
			return  # Skip update with invalid values
		
		self.is_multi_selection = is_multi_selection
		self.center_x = center_x
		self.center_y = center_y
		self.half_w = half_w
		self.half_h = half_h
		self.rotation = rotation
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
			mode: str - "bbox", "minimal_bbox", or "gimble"
		"""
		# Map old names to new names
		mode_map = {
			'normal': 'bbox',
			'minimal': 'minimal_bbox',
			'gimble': 'gimble'
		}
		mode = mode_map.get(mode, mode)
		
		self.transform_mode = mode
		from .transform_widgets import create_mode
		self.current_mode = create_mode(mode)
		self.minimal_mode = (mode == "minimal_bbox")  # Update backward compat flag
		self.update()
	
	def set_minimal_mode(self, enabled):
		"""Toggle minimal transform widget mode (backward compatibility)"""
		self.set_transform_mode("minimal_bbox" if enabled else "bbox")
	
	def paintEvent(self, event):
		"""Paint the transform widget overlay using handle.draw() methods"""
		if not self.visible:
			return
		
		# Validate transform values (Decision 8)
		import math
		if (math.isnan(self.center_x) or math.isnan(self.center_y) or 
		    math.isnan(self.half_w) or math.isnan(self.half_h) or
		    math.isnan(self.rotation)):
			return  # Skip painting with invalid values
		
		painter = QPainter(self)
		painter.setRenderHint(QPainter.Antialiasing)
		
		# Widget stores pixels directly - no conversion needed
		# Iterate mode's handles and call draw()
		for handle in self.current_mode.handles.values():
			handle.draw(painter, self.center_x, self.center_y, self.half_w, self.half_h, self.rotation)
	
	def _get_handle_at_pos(self, pos):
		"""Get which handle is at the given position - delegates to mode"""
		if not self.visible:
			return None
		
		# Convert widget-space mouse position to canvas-space (Decision 9)
		mouse_x, mouse_y = self.canvas_widget.canvas_area.canvas_area_to_canvas_widget(pos.x(), pos.y())
		
		# Delegate to current mode's get_handle_at_pos()
		# Mode handles priority ordering internally
		return self.current_mode.get_handle_at_pos(mouse_x, mouse_y, self.center_x, self.center_y, 
		                                           self.half_w, self.half_h, self.rotation)
	
	def _forward_event_to_canvas(self, event):
		"""Reusable event forwarding (Decision 7 - eliminates 15-line duplication).
		
		Forwards mouse events to canvas widget for panning when not over handles.
		
		Args:
			event: QMouseEvent to forward
		"""
		if self.canvas_widget:
			canvas_pos = self.canvas_widget.mapFromGlobal(self.mapToGlobal(event.pos()))
			canvas_event = QMouseEvent(
				event.type(),
				canvas_pos,
				event.globalPos(),
				event.button(),
				event.buttons(),
				event.modifiers()
			)
			# Dispatch based on event type
			if event.type() == QEvent.MouseButtonPress:
				self.canvas_widget.mousePressEvent(canvas_event)
			elif event.type() == QEvent.MouseMove:
				self.canvas_widget.mouseMoveEvent(canvas_event)
			elif event.type() == QEvent.MouseButtonRelease:
				self.canvas_widget.mouseReleaseEvent(canvas_event)
	
	def mousePressEvent(self, event):
		"""Handle mouse press - now works with pixel storage"""
		if event.button() == Qt.LeftButton:
			# Get handle at position (delegates to mode)
			self.active_handle = self._get_handle_at_pos(event.pos())
			
			if self.active_handle:
				# Start drag
				self.drag_start_pos = event.pos()
				self.drag_start_transform = (self.center_x, self.center_y, self.half_w, self.half_h, self.rotation)
				
				# Create DragContext (Decision 5)
				from .transform_widgets import DragContext
				modifiers = set()
				if event.modifiers() & Qt.ControlModifier:
					modifiers.add('ctrl')
				if event.modifiers() & Qt.AltModifier:
					modifiers.add('alt')
				if event.modifiers() & Qt.ShiftModifier:
					modifiers.add('shift')
				
				# Determine operation type from handle
				if self.active_handle in ['rotate', 'ring']:
					operation = 'rotate'
				elif self.active_handle in ['tl', 'tr', 'bl', 'br']:
					operation = 'scale_corner'
				elif self.active_handle in ['t', 'b', 'l', 'r']:
					operation = 'scale_edge'
				elif self.active_handle == 'axis_x':
					operation = 'axis_x'
				elif self.active_handle == 'axis_y':
					operation = 'axis_y'
				else:  # center handles
					operation = 'translate'
				
				self.drag_context = DragContext(
					operation=operation,
					modifiers=modifiers,
					duplicate_created=False,
					is_multi_selection=self.is_multi_selection,
					cached_aabb=self.drag_start_transform,
					metadata={}
				)
				
				event.accept()
				return
		
		# No handle clicked - forward to canvas widget for panning
		self._forward_event_to_canvas(event)
		event.ignore()
	
	def mouseMoveEvent(self, event):
		"""Handle mouse move - drag handling and cursor updates"""
		if self.drag_start_pos and self.drag_context:
			# Check for Ctrl+drag duplication with threshold (Decision 6)
			from constants import TRANSFORM_DUPLICATE_DRAG_THRESHOLD
			if ('ctrl' in self.drag_context.modifiers and 
			    not self.drag_context.duplicate_created and 
			    self.drag_context.operation in ['translate', 'axis_x', 'axis_y']):
				# Check if mouse has moved past threshold
				dx = event.pos().x() - self.drag_start_pos.x()
				dy = event.pos().y() - self.drag_start_pos.y()
				distance = math.sqrt(dx*dx + dy*dy)
				
				if distance >= TRANSFORM_DUPLICATE_DRAG_THRESHOLD:
					self.drag_context.duplicate_created = True
					self.layerDuplicated.emit()
			
			# Handle drag
			self._handle_drag(event.pos(), event.modifiers())
			event.accept()
			return
		
		# Update cursor based on handle under mouse
		handle = self._get_handle_at_pos(event.pos())
		if handle:
			if handle in ['center', 'gimble_center']:
				self.setCursor(Qt.SizeAllCursor)
			elif handle == 'axis_x':
				self.setCursor(Qt.SizeHorCursor)
			elif handle == 'axis_y':
				self.setCursor(Qt.SizeVerCursor)
			elif handle in ['rotate', 'ring']:
				self.setCursor(Qt.CrossCursor)
			else:
				self.setCursor(Qt.SizeFDiagCursor)
		else:
			self.setCursor(Qt.ArrowCursor)
		
		self.update()
	
	def mouseReleaseEvent(self, event):
		"""Handle mouse release - complete drag operation"""
		if not self.active_handle:
			self._forward_event_to_canvas(event)
			event.ignore()
			return
		
		if event.button() == Qt.LeftButton and self.active_handle:
			# Track if this was a duplicate drag for history
			was_duplicate_drag = self.drag_context and self.drag_context.duplicate_created
			
			# Clear drag state
			self.active_handle = None
			self.drag_start_pos = None
			self.drag_start_transform = None
			self.drag_context = None
			
			# Emit signal for history saving
			self.transformEnded.emit()
			
			event.accept()
			return
		
		self._forward_event_to_canvas(event)
		event.ignore()
	
	def wheelEvent(self, event):
		"""Handle mouse wheel for scaling and rotation while dragging"""
		# Only respond to wheel events when actively dragging
		if not self.active_handle:
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
			elif modifiers & Qt.ControlModifier:
				# Ctrl + wheel: Scale X only (pixels)
				pixel_increment = 2.0 if delta > 0 else -2.0
				self.half_w = max(1.0, self.half_w + pixel_increment)
				self.nonUniformScaleUsed.emit()
			elif modifiers & Qt.ShiftModifier:
				# Shift + wheel: Scale Y only (pixels)
				pixel_increment = 2.0 if delta > 0 else -2.0
				self.half_h = max(1.0, self.half_h + pixel_increment)
				self.nonUniformScaleUsed.emit()
			else:
				# No modifier: Scale both X and Y uniformly (pixels)
				pixel_increment = 2.0 if delta > 0 else -2.0
				self.half_w = max(1.0, self.half_w + pixel_increment)
				self.half_h = max(1.0, self.half_h + pixel_increment)
		
			# Update drag_start_transform to new values to prevent jump on release
			if self.drag_start_transform:
				self.drag_start_transform = (self.center_x, self.center_y, self.half_w, self.half_h, self.rotation)
			
			# CRITICAL: Update drag_start_pos to current mouse position to prevent jump
			# When wheel scaling during drag, the mouse hasn't moved but the transform has changed
			# We need to reset the drag start position so continuing the drag doesn't apply old deltas
			if self.drag_start_pos:
				self.drag_start_pos = event.pos()
			
			# Emit signal and update
			self.transformChanged.emit(self.center_x, self.center_y, self.half_w, self.half_h, self.rotation)
			self.update()
			event.accept()
		except Exception as e:
			# If error occurs (e.g., during drag state changes), just ignore
			print(f"wheelEvent error: {e}")
			event.accept()
	
	def _handle_drag(self, current_pos, modifiers=None):
		"""Handle dragging in pure pixel space - no coordinate conversions needed"""
		if not self.drag_start_pos or not self.drag_start_transform:
			return
		
		# Pixel deltas (widget already in pixel space)
		dx = current_pos.x() - self.drag_start_pos.x()
		dy = current_pos.y() - self.drag_start_pos.y()
		
		start_cx, start_cy, start_hw, start_hh, start_rot = self.drag_start_transform
		
		# Check modifiers
		alt_pressed = modifiers and (modifiers & Qt.AltModifier)
		shift_pressed = modifiers and (modifiers & Qt.ShiftModifier)
		
		# Translation handles (center, axis_x, axis_y, gimble_center)
		if self.active_handle in ['center', 'gimble_center']:
			self.center_x = start_cx + dx
			self.center_y = start_cy + dy
		
		elif self.active_handle == 'axis_x':
			self.center_x = start_cx + dx
			# Y locked
		
		elif self.active_handle == 'axis_y':
			self.center_y = start_cy + dy
			# X locked
		
		# Rotation handles
		elif self.active_handle in ['rotate', 'ring']:
			start_angle = math.degrees(math.atan2(self.drag_start_pos.y() - start_cy, 
			                                       self.drag_start_pos.x() - start_cx))
			current_angle = math.degrees(math.atan2(current_pos.y() - start_cy,
			                                         current_pos.x() - start_cx))
			angle_delta = current_angle - start_angle
			self.rotation = start_rot + angle_delta
			
			if shift_pressed:
				self.rotation = round(self.rotation / 45.0) * 45.0
		
		# Corner scale handles (uniform)
		elif self.active_handle in ['tl', 'tr', 'bl', 'br']:
			if alt_pressed:
				# Alt: anchor opposite corner
				anchor_map = {'tl': (start_cx + start_hw, start_cy + start_hh),
				              'tr': (start_cx - start_hw, start_cy + start_hh),
				              'bl': (start_cx + start_hw, start_cy - start_hh),
				              'br': (start_cx - start_hw, start_cy - start_hh)}
				anchor_x, anchor_y = anchor_map[self.active_handle]
				
				curr_dist = math.sqrt((current_pos.x() - anchor_x)**2 + (current_pos.y() - anchor_y)**2)
				start_dist = math.sqrt((self.drag_start_pos.x() - anchor_x)**2 + (self.drag_start_pos.y() - anchor_y)**2)
				
				if start_dist > 0:
					scale_factor = curr_dist / start_dist
					self.half_w = start_hw * scale_factor
					self.half_h = start_hh * scale_factor
					# Reposition center to keep anchor fixed
					self.center_x = anchor_x + (start_cx - anchor_x) * scale_factor
					self.center_y = anchor_y + (start_cy - anchor_y) * scale_factor
			else:
				# Normal: scale from center
				start_dist = math.sqrt((self.drag_start_pos.x() - start_cx)**2 + (self.drag_start_pos.y() - start_cy)**2)
				curr_dist = math.sqrt((current_pos.x() - start_cx)**2 + (current_pos.y() - start_cy)**2)
				
				if start_dist > 0:
					scale_factor = curr_dist / start_dist
					self.half_w = start_hw * scale_factor
					self.half_h = start_hh * scale_factor
		
		# Edge scale handles (non-uniform)
		elif self.active_handle in ['l', 'r']:
			if alt_pressed:
				anchor_x = start_cx + start_hw if self.active_handle == 'l' else start_cx - start_hw
				new_width_px = abs(current_pos.x() - anchor_x)
				self.half_w = new_width_px
				# Reposition center
				self.center_x = anchor_x + (start_cx - anchor_x) * (new_width_px / start_hw) if start_hw > 0 else anchor_x
			else:
				start_dist = abs(self.drag_start_pos.x() - start_cx)
				curr_dist = abs(current_pos.x() - start_cx)
				if start_dist > 0:
					self.half_w = start_hw * (curr_dist / start_dist)
			self.nonUniformScaleUsed.emit()
		
		elif self.active_handle in ['t', 'b']:
			if alt_pressed:
				anchor_y = start_cy + start_hh if self.active_handle == 't' else start_cy - start_hh
				new_height_px = abs(current_pos.y() - anchor_y)
				self.half_h = new_height_px
				# Reposition center
				self.center_y = anchor_y + (start_cy - anchor_y) * (new_height_px / start_hh) if start_hh > 0 else anchor_y
			else:
				start_dist = abs(self.drag_start_pos.y() - start_cy)
				curr_dist = abs(current_pos.y() - start_cy)
				if start_dist > 0:
					self.half_h = start_hh * (curr_dist / start_dist)
			self.nonUniformScaleUsed.emit()
		
		# Clamp scale for single selection (not multi-selection groups)
		# Note: Clamping now happens in canvas_area after converting back to CoA space
		
		# Emit signal with current pixel values
		self.transformChanged.emit(self.center_x, self.center_y, self.half_w, self.half_h, self.rotation)
		self.update()