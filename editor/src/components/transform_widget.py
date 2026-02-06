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

from models.transform import Transform, Vec2


class TransformWidget(QWidget):
    """Interactive transform widget for manipulating layer transforms"""
    
    # Signals
    transformChanged = pyqtSignal(object)  # Transform object (widget pixel space)
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
        
        # Reference to main window for edit lock (set by canvas_area)
        self.main_window = None
        
        # Transform state (PURE PIXEL SPACE - Decision 3)
        self.center_x = 0.0  # Widget pixel X
        self.center_y = 0.0  # Widget pixel Y
        self.half_w = 100.0  # AABB half-width (pixels)
        self.half_h = 100.0  # AABB half-height (pixels)
        self.rotation = 0.0  # Degrees
        
        # Interaction state
        self.active_handle = None  # Now stores Handle object from mode
        self.drag_start_pos = None
        self.drag_start_transform = None  # (center_x, center_y, half_w, half_h, rotation)
        self.visible = False
        
        # Multi-selection state
        self.is_multi_selection = False  # Flag to skip scale clamping for group transforms
        
        # Rotation state (for AABB caching)
        self.is_rotating = False  # Flag to prevent AABB recalculation during rotation
        
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
        
        # Translate painter to center-origin (handles expect center-origin coordinates)
        painter.translate(self.width() / 2, self.height() / 2)
        
        # Widget stores pixels directly - no conversion needed
        # Draw bounding box FIRST (so handles appear on top)
        if 'center' in self.current_mode.handles:
            self.current_mode.handles['center'].draw(painter, self.center_x, self.center_y, 
                                                      self.half_w, self.half_h, self.rotation)
        
        # Then draw all other handles on top
        for handle_type, handle in self.current_mode.handles.items():
            if handle_type != 'center':  # Skip center - already drawn
                handle.draw(painter, self.center_x, self.center_y, self.half_w, self.half_h, self.rotation)
    
    # ============= Coordinate Conversion Helpers (Decision 9) =============
    def _widget_to_center_origin(self, pos):
        """Convert widget top-left coordinates to center-origin coordinates.
        
        Args:
            pos: QPoint in widget coordinates
            
        Returns:
            tuple: (x, y) in center-origin coordinates
        """
        return (pos.x() - self.width() / 2, pos.y() - self.height() / 2)
    
    def _center_origin_to_widget(self, x, y):
        """Convert center-origin coordinates to widget top-left coordinates.
        
        Args:
            x, y: Coordinates in center-origin space
            
        Returns:
            QPoint in widget coordinates
        """
        from PyQt5.QtCore import QPoint
        return QPoint(int(x + self.width() / 2), int(y + self.height() / 2))
    
    # ============= Geometry Calculation Helpers =============
    @staticmethod
    def _calculate_distance(x1, y1, x2, y2):
        """Calculate Euclidean distance between two points."""
        import math
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    
    @staticmethod
    def _calculate_angle(x1, y1, x2, y2):
        """Calculate angle in degrees from point 1 to point 2."""
        import math
        return math.degrees(math.atan2(y2 - y1, x2 - x1))
    
    # ============= Handle and Mode Interaction =============
    def _get_handle_at_pos(self, pos):
        """Get which handle is at the given position - delegates to mode"""
        if not self.visible:
            return None
        
        # Convert mouse from widget top-left to center-origin coordinates
        mouse_x, mouse_y = self._widget_to_center_origin(pos)
        
        # Delegate to current mode's get_handle_at_pos()
        # Mode handles priority ordering internally
        result = self.current_mode.get_handle_at_pos(mouse_x, mouse_y, self.center_x, self.center_y, 
                                                   self.half_w, self.half_h, self.rotation)
        return result
    
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
                # Acquire edit lock (Decision 4 - prevent feedback loops)
                if self.main_window:
                    try:
                        self.main_window.acquire_edit_lock(self)
                    except RuntimeError:
                        # Lock already held - abort drag
                        self.active_handle = None
                        event.ignore()
                        return
                
                # Start drag
                self.drag_start_pos = event.pos()
                self.drag_start_transform = (self.center_x, self.center_y, self.half_w, self.half_h, self.rotation)
                
                # Create DragContext (Decision 5)
                from .transform_widgets import DragContext
                from .transform_widgets.handles import (RotationHandle, RingHandle, CornerHandle, 
                                                         EdgeHandle, ArrowHandle, CenterHandle, 
                                                         GimbleCenterHandle)
                modifiers = set()
                if event.modifiers() & Qt.ControlModifier:
                    modifiers.add('ctrl')
                if event.modifiers() & Qt.AltModifier:
                    modifiers.add('alt')
                if event.modifiers() & Qt.ShiftModifier:
                    modifiers.add('shift')
                
                # Determine operation type from handle class
                if isinstance(self.active_handle, (RotationHandle, RingHandle)):
                    operation = 'rotate'
                elif isinstance(self.active_handle, CornerHandle):
                    operation = 'scale_corner'
                elif isinstance(self.active_handle, EdgeHandle):
                    operation = 'scale_edge'
                elif isinstance(self.active_handle, ArrowHandle):
                    operation = 'axis_x' if self.active_handle.axis == 'x' else 'axis_y'
                else:  # CenterHandle, GimbleCenterHandle
                    operation = 'translate'
                
                # Set is_rotating flag for rotation operations (used by canvas_area to cache AABB)
                self.is_rotating = (operation == 'rotate')
                
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
            # Use polymorphic get_cursor() method
            self.setCursor(handle.get_cursor())
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
            
            # Release edit lock in try/finally to guarantee release (Decision 4)
            try:
                # TODO: Sync widget display to model truth before releasing lock
                # This ensures UI matches model values and catches conversion rounding errors
                pass
            finally:
                if self.main_window:
                    try:
                        self.main_window.release_edit_lock(self)
                    except RuntimeError:
                        pass  # Lock wasn't acquired (e.g., main_window not set)
            
            # Clear drag state
            self.active_handle = None
            self.drag_start_pos = None
            self.drag_start_transform = None
            self.drag_context = None
            self.is_rotating = False  # Clear rotation flag
            
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
            self.transformChanged.emit(Transform(
                Vec2(self.center_x, self.center_y),
                Vec2(self.half_w, self.half_h),
                self.rotation
            ))
            self.update()
            event.accept()
        except Exception as e:
            # If error occurs (e.g., during drag state changes), just ignore
            print(f"wheelEvent error: {e}")
            event.accept()
    
    def _handle_drag(self, current_pos, modifiers=None):
        """Delegate drag handling to the active handle's polymorphic drag() method."""
        if not self.drag_start_pos or not self.drag_start_transform or not self.active_handle:
            return
        
        # Convert mouse positions to center-origin coordinates
        start_mouse_x, start_mouse_y = self._widget_to_center_origin(self.drag_start_pos)
        curr_mouse_x, curr_mouse_y = self._widget_to_center_origin(current_pos)
        
        # Create Transform object from drag start state
        start_transform = Transform(
            Vec2(self.drag_start_transform[0], self.drag_start_transform[1]),
            Vec2(self.drag_start_transform[2], self.drag_start_transform[3]),
            self.drag_start_transform[4]
        )
        
        # Delegate to handle's drag method (polymorphism!)
        new_transform = self.active_handle.drag(
            curr_mouse_x, curr_mouse_y,
            start_mouse_x, start_mouse_y,
            start_transform,
            modifiers
        )
        
        # Update internal state from returned Transform
        self.center_x = new_transform.pos.x
        self.center_y = new_transform.pos.y
        self.half_w = new_transform.scale.x
        self.half_h = new_transform.scale.y
        self.rotation = new_transform.rotation
        
        # Emit signal for non-uniform scaling (edge handles)
        from .transform_widgets.handles import EdgeHandle
        if isinstance(self.active_handle, EdgeHandle):
            self.nonUniformScaleUsed.emit()
        
        # Emit transform change signal
        self.transformChanged.emit(new_transform)
        self.update()