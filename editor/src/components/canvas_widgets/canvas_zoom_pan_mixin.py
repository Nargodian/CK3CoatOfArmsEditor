"""Mixin for handling zoom and pan in the CoA canvas.

Provides viewport navigation including:
- Zoom in/out/reset with zoom-to-cursor
- Pan with mouse drag
- Grid display toggle
"""

from PyQt5.QtCore import Qt


class CanvasZoomPanMixin:
    """Mixin providing zoom and pan functionality for canvas."""
    
    # Expected state variables (initialized in main class):
    # - zoom_level: float
    # - pan_x, pan_y: float
    # - is_panning: bool
    # - last_mouse_pos: QPoint
    # - show_grid: bool
    # - grid_divisions: int
    # - canvas_area: reference to parent
    
    def zoom_in(self, cursor_pos=None):
        """Zoom in by 25%."""
        old_zoom = self.zoom_level
        self.zoom_level = min(self.zoom_level * 1.25, 5.0)
        if cursor_pos:
            self._adjust_pan_for_zoom(cursor_pos, old_zoom, self.zoom_level)
        if self.zoom_level <= 1.0:
            self.pan_x = 0.0
            self.pan_y = 0.0
        self.update()
        self._update_zoom_toolbar()
        if hasattr(self, 'canvas_area') and hasattr(self.canvas_area, 'transform_widget'):
            self.canvas_area.transform_widget.update()
    
    def zoom_out(self, cursor_pos=None):
        """Zoom out by 25%."""
        old_zoom = self.zoom_level
        self.zoom_level = max(self.zoom_level / 1.25, 0.25)
        if cursor_pos:
            self._adjust_pan_for_zoom(cursor_pos, old_zoom, self.zoom_level)
        if self.zoom_level <= 1.0:
            self.pan_x = 0.0
            self.pan_y = 0.0
        self.update()
        self._update_zoom_toolbar()
        if hasattr(self, 'canvas_area') and hasattr(self.canvas_area, 'transform_widget'):
            self.canvas_area.transform_widget.update()
    
    def zoom_reset(self):
        """Reset zoom to 100%."""
        self.zoom_level = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.update()
        if hasattr(self, 'canvas_area') and hasattr(self.canvas_area, 'transform_widget'):
            self.canvas_area.transform_widget.update()
    
    def set_zoom_level(self, zoom_percent):
        """Set zoom to specific percentage."""
        self.zoom_level = max(0.25, min(5.0, zoom_percent / 100.0))
        self.update()
        self._update_zoom_toolbar()
        if hasattr(self, 'canvas_area') and hasattr(self.canvas_area, 'transform_widget'):
            self.canvas_area.transform_widget.update()
    
    def get_zoom_percent(self):
        """Get current zoom percentage."""
        return int(self.zoom_level * 100)
    
    def _update_zoom_toolbar(self):
        """Update zoom toolbar display."""
        if not self.canvas_area:
            return
        widget = self.canvas_area
        while widget:
            if hasattr(widget, 'zoom_toolbar'):
                widget.zoom_toolbar.set_zoom_percent(self.get_zoom_percent(), emit_signal=False)
                return
            widget = widget.parent() if hasattr(widget, 'parent') else None
    
    def _adjust_pan_for_zoom(self, cursor_pos, old_zoom, new_zoom):
        """Adjust pan to keep cursor position fixed."""
        cursor_offset_x = cursor_pos.x() - self.width() / 2
        cursor_offset_y = cursor_pos.y() - self.height() / 2
        scale_ratio = new_zoom / old_zoom
        self.pan_x += cursor_offset_x * (1 - scale_ratio)
        self.pan_y += cursor_offset_y * (1 - scale_ratio)
    
    def set_show_grid(self, show):
        """Toggle grid visibility."""
        self.show_grid = show
        self.update()
    
    def set_grid_divisions(self, divisions):
        """Set grid divisions."""
        self.grid_divisions = divisions
        if self.show_grid:
            self.update()
    
    # ========================================
    # Mouse Event Handlers
    # ========================================
    
    def wheelEvent(self, event):
        """Handle mouse wheel for zoom."""
        if event.modifiers() & Qt.ControlModifier:
            cursor_pos = event.pos()
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in(cursor_pos)
            elif delta < 0:
                self.zoom_out(cursor_pos)
    
    def _handle_pan_mouse_press(self, event):
        """Handle mouse press for panning. Returns True if event was handled."""
        if event.button() == Qt.LeftButton and self.zoom_level > 1.0:
            self.is_panning = True
            self.last_mouse_pos = event.globalPos()
            self.setCursor(Qt.ClosedHandCursor)
            return True
        return False
    
    def _handle_pan_mouse_move(self, event):
        """Handle mouse move for panning. Returns True if event was handled."""
        if self.is_panning and self.last_mouse_pos:
            delta = event.globalPos() - self.last_mouse_pos
            self.last_mouse_pos = event.globalPos()
            self.pan_x += delta.x()
            self.pan_y += delta.y()
            
            canvas_size = min(self.width(), self.height())
            max_pan = canvas_size * self.zoom_level * 0.3
            self.pan_x = max(-max_pan, min(max_pan, self.pan_x))
            self.pan_y = max(-max_pan, min(max_pan, self.pan_y))
            
            self.update()
            if hasattr(self, 'canvas_area') and hasattr(self.canvas_area, 'transform_widget'):
                self.canvas_area.transform_widget.update()
            return True
        else:
            # Update cursor based on zoom level
            if self.zoom_level > 1.0:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
        return False
    
    def _handle_pan_mouse_release(self, event):
        """Handle mouse release for panning. Returns True if event was handled."""
        if event.button() == Qt.LeftButton and self.is_panning:
            self.is_panning = False
            self.last_mouse_pos = None
            if self.zoom_level > 1.0:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            return True
        return False
