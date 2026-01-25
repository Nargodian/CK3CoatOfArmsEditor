"""
Stacked emblem widget for high-performance color previews.

Uses 3 layered colored rectangles with alpha masks applied.
Colors can be updated via dynamic properties for instant updates.
"""

from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor
from PyQt5.QtCore import Qt, QRect, pyqtProperty
from pathlib import Path


class StackedEmblemWidget(QWidget):
    """
    Widget that displays an emblem using 3 stacked colored layers.
    
    Like cel animation, each layer is a solid color with an alpha mask
    applied from the atlas quadrant. Colors are set via properties.
    """
    
    def __init__(self, atlas_path: str, size: int = 64, parent=None):
        """
        Create a stacked emblem widget.
        
        Args:
            atlas_path: Path to the 512x512 emblem atlas PNG
            size: Display size (square)
            parent: Parent widget
        """
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.size = size
        
        # Load atlas and extract quadrants
        atlas = QImage(atlas_path)
        if atlas.isNull():
            return
        
        top_left_quad = atlas.copy(QRect(0, 0, 256, 256))      # r×a - color3
        top_right_quad = atlas.copy(QRect(256, 0, 256, 256))   # g×a - color2
        bottom_left_quad = atlas.copy(QRect(0, 256, 256, 256)) # b×2 - color1
        
        # Create masked pixmaps (will be colored in paintEvent)
        self.mask1 = self._create_alpha_mask(bottom_left_quad, size)
        self.mask2 = self._create_alpha_mask(top_right_quad, size)
        self.mask3 = self._create_alpha_mask(top_left_quad, size)
        
        # Colors (will be set externally)
        self._bg_color = QColor(255, 255, 255)
        self._color1 = QColor(255, 0, 0)
        self._color2 = QColor(0, 255, 0)
        self._color3 = QColor(0, 0, 255)
    
    def _create_alpha_mask(self, quad_image: QImage, size: int) -> QPixmap:
        """Extract alpha channel as a mask pixmap"""
        scaled = quad_image.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        # Convert to alpha mask
        mask = QPixmap.fromImage(scaled)
        return mask
    
    def paintEvent(self, event):
        """Paint the 4 layers with current colors"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Layer 1: Background
        painter.fillRect(0, 0, self.size, self.size, self._bg_color)
        
        # Layer 2-4: Colored layers with alpha masks
        for color, mask in [(self._color1, self.mask1), (self._color2, self.mask2), (self._color3, self.mask3)]:
            # Create colored layer
            colored = QImage(self.size, self.size, QImage.Format_ARGB32)
            colored.fill(color)
            # Apply mask
            layer_painter = QPainter(colored)
            layer_painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            layer_painter.drawPixmap(0, 0, mask)
            layer_painter.end()
            # Draw to widget
            painter.drawImage(0, 0, colored)
        
        painter.end()
    
    def set_background_color(self, color: tuple):
        """Set the background color (0-1 range RGB)"""
        self._bg_color = QColor(int(color[0] * 255), int(color[1] * 255), int(color[2] * 255))
        self.update()
    
    def set_colors(self, color1: tuple, color2: tuple, color3: tuple):
        """Set all three layer colors at once (0-1 range RGB)"""
        self._color1 = QColor(int(color1[0] * 255), int(color1[1] * 255), int(color1[2] * 255))
        self._color2 = QColor(int(color2[0] * 255), int(color2[1] * 255), int(color2[2] * 255))
        self._color3 = QColor(int(color3[0] * 255), int(color3[1] * 255), int(color3[2] * 255))
        self.update()
