"""Symmetry overlay widget - transparent layer for drawing symmetry visualizations."""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush
from models.transform import Vec2
from services.symmetry_transforms import get_transform


class SymmetryOverlayWidget(QWidget):
    """Transparent overlay widget for drawing symmetry transform visualizations.
    
    Sits on top of canvas widget but under transform widget. Draws grid lines,
    radial mirrors, bisector lines, etc. for selected layers with symmetry.
    
    Uses canvas coordinate transforms to convert CoA space to pixel coordinates.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Make transparent to mouse events (pass through to canvas)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        # Transparent background
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # References set by CanvasArea
        self.canvas_widget = None  # Reference to canvas for coordinate transforms
        self.property_sidebar = None  # Reference to get selected layers
        
        self.setVisible(True)
    
    def paintEvent(self, event):
        """Draw symmetry overlays and grid for selected layers."""
        if not self.canvas_widget or not self.property_sidebar:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw grid if enabled
        if hasattr(self.canvas_widget, 'show_grid') and self.canvas_widget.show_grid:
            self._draw_grid(painter)
        
        # Get selected layer UUIDs
        selected_uuids = self.property_sidebar.get_selected_uuids()
        if not selected_uuids:
            return
        
        # Get CoA model
        from models.coa import CoA
        if not CoA.has_active():
            return
        coa = CoA.get_active()
        
        # Draw overlays for each selected layer with symmetry
        for uuid in selected_uuids:
            layer = coa.get_layer_by_uuid(uuid)
            if not layer:
                continue
            
            symmetry_type = layer.symmetry_type
            if symmetry_type == 'none':
                continue
            
            # Get transform plugin
            transform_plugin = get_transform(symmetry_type)
            if not transform_plugin:
                continue
            
            # Load properties from layer
            properties = coa.get_layer_symmetry_properties(uuid)
            if properties:
                transform_plugin.set_properties(properties)
            
            # Call draw_overlay with coordinate converter
            transform_plugin.draw_overlay(painter, uuid, coa, self._coa_to_canvas)
    
    def _coa_to_canvas(self, coa_pos):
        """Convert CoA space (0-1) to canvas pixel coordinates.
        
        Args:
            coa_pos: Vec2 or tuple (x, y) in CoA space (0-1)
            
        Returns:
            Vec2 in canvas pixel coordinates
        """
        if not self.canvas_widget:
            return Vec2(0, 0)
        
        # Handle tuple input
        if isinstance(coa_pos, tuple):
            coa_pos = Vec2(coa_pos[0], coa_pos[1])
        
        # Use canvas coordinate transform
        return self.canvas_widget.coa_to_canvas(coa_pos)
    
    def refresh(self):
        """Trigger repaint of overlay."""
        self.update()    
    def _draw_grid(self, painter):
        """Draw grid overlay based on canvas grid settings.
        
        Args:
            painter: QPainter instance to draw with
        """
        if not self.canvas_widget:
            return
        
        divisions = getattr(self.canvas_widget, 'grid_divisions', 4)
        if divisions <= 0:
            return
        
        # Set up grid pen (semi-transparent white)
        pen = QPen(QColor(255, 255, 255, 80))
        pen.setWidth(1)
        pen.setStyle(Qt.SolidLine)
        painter.setPen(pen)
        
        # Draw vertical lines
        for i in range(divisions + 1):
            x_coa = i / divisions
            pos = self._coa_to_canvas(Vec2(x_coa, 0.0))
            x_px = pos.x
            
            # Get canvas bounds in pixels
            top = self._coa_to_canvas(Vec2(0.5, 0.0))
            bottom = self._coa_to_canvas(Vec2(0.5, 1.0))
            
            painter.drawLine(int(x_px), int(top.y), int(x_px), int(bottom.y))
        
        # Draw horizontal lines
        for i in range(divisions + 1):
            y_coa = i / divisions
            pos = self._coa_to_canvas(Vec2(0.0, y_coa))
            y_px = pos.y
            
            # Get canvas bounds in pixels
            left = self._coa_to_canvas(Vec2(0.0, 0.5))
            right = self._coa_to_canvas(Vec2(1.0, 0.5))
            
            painter.drawLine(int(left.x), int(y_px), int(right.x), int(y_px))