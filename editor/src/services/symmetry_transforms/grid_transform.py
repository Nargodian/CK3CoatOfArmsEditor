"""Grid symmetry transform - tile instances in grid pattern."""

import math
from typing import List
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QSpinBox, QComboBox, QSlider)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor
from models.transform import Vec2, Transform
from .base_transform import BaseSymmetryTransform


class GridTransform(BaseSymmetryTransform):
    """Tile instances in grid pattern with various fill modes."""
    
    # Default parameter values
    DEFAULT_OFFSET_X = 0.5
    DEFAULT_OFFSET_Y = 0.5
    DEFAULT_COUNT_X = 3
    DEFAULT_COUNT_Y = 3
    DEFAULT_FILL = 0  # 0=full, 1=diamond, 2=alt-diamond
    
    def __init__(self):
        super().__init__()
        
        # Initialize default settings
        self.settings = {
            'offset_x': self.DEFAULT_OFFSET_X,
            'offset_y': self.DEFAULT_OFFSET_Y,
            'count_x': self.DEFAULT_COUNT_X,
            'count_y': self.DEFAULT_COUNT_Y,
            'fill': self.DEFAULT_FILL,
        }
    
    def get_name(self) -> str:
        return "grid"
    
    def get_display_name(self) -> str:
        return "Grid"
    
    def build_controls(self, parent: QWidget) -> QVBoxLayout:
        """Build UI controls for grid parameters."""
        layout = QVBoxLayout()
        
        # Offset X slider
        offset_x_layout = QHBoxLayout()
        offset_x_label = QLabel("Offset X:")
        offset_x_slider = QSlider(Qt.Horizontal)
        offset_x_slider.setRange(0, 100)
        offset_x_slider.setValue(int(self.settings['offset_x'] * 100))
        offset_x_slider.valueChanged.connect(
            lambda v: self._on_param_changed('offset_x', v / 100.0))
        offset_x_layout.addWidget(offset_x_label)
        offset_x_layout.addWidget(offset_x_slider)
        layout.addLayout(offset_x_layout)
        self._controls['offset_x'] = offset_x_slider
        
        # Offset Y slider
        offset_y_layout = QHBoxLayout()
        offset_y_label = QLabel("Offset Y:")
        offset_y_slider = QSlider(Qt.Horizontal)
        offset_y_slider.setRange(0, 100)
        offset_y_slider.setValue(int(self.settings['offset_y'] * 100))
        offset_y_slider.valueChanged.connect(
            lambda v: self._on_param_changed('offset_y', v / 100.0))
        offset_y_layout.addWidget(offset_y_label)
        offset_y_layout.addWidget(offset_y_slider)
        layout.addLayout(offset_y_layout)
        self._controls['offset_y'] = offset_y_slider
        
        # Count X spinner
        count_x_layout = QHBoxLayout()
        count_x_label = QLabel("Columns:")
        count_x_spinner = QSpinBox()
        count_x_spinner.setRange(1, 8)
        count_x_spinner.setValue(self.settings['count_x'])
        count_x_spinner.valueChanged.connect(
            lambda v: self._on_param_changed('count_x', int(v)))
        count_x_layout.addWidget(count_x_label)
        count_x_layout.addWidget(count_x_spinner)
        layout.addLayout(count_x_layout)
        self._controls['count_x'] = count_x_spinner
        
        # Count Y spinner
        count_y_layout = QHBoxLayout()
        count_y_label = QLabel("Rows:")
        count_y_spinner = QSpinBox()
        count_y_spinner.setRange(1, 8)
        count_y_spinner.setValue(self.settings['count_y'])
        count_y_spinner.valueChanged.connect(
            lambda v: self._on_param_changed('count_y', int(v)))
        count_y_layout.addWidget(count_y_label)
        count_y_layout.addWidget(count_y_spinner)
        layout.addLayout(count_y_layout)
        self._controls['count_y'] = count_y_spinner
        
        # Fill mode dropdown
        fill_layout = QHBoxLayout()
        fill_label = QLabel("Fill:")
        fill_dropdown = QComboBox()
        fill_dropdown.addItems(["Full", "Diamond", "Alt-Diamond"])
        fill_dropdown.setCurrentIndex(self.settings['fill'])
        fill_dropdown.currentIndexChanged.connect(
            lambda idx: self._on_param_changed('fill', idx))
        fill_layout.addWidget(fill_label)
        fill_layout.addWidget(fill_dropdown)
        layout.addLayout(fill_layout)
        self._controls['fill'] = fill_dropdown
        
        return layout
    
    def calculate_transforms(self, seed_transform) -> List:
        """Calculate grid transforms."""
        from models.transform import Transform, Vec2
        
        offset_x = self.settings['offset_x']
        offset_y = self.settings['offset_y']
        count_x = self.settings['count_x']
        count_y = self.settings['count_y']
        fill = self.settings['fill']
        
        mirrors = []
        
        # Calculate cell size (grid spans CoA space 0-1)
        cell_width = 1.0 / count_x
        cell_height = 1.0 / count_y
        
        # Find which cell the seed is in
        seed_cell_x = int((seed_transform.pos.x - offset_x) / cell_width)
        seed_cell_y = int((seed_transform.pos.y - offset_y) / cell_height)
        
        # Generate positions for all cells
        for row in range(count_y):
            for col in range(count_x):
                # Skip seed cell
                if row == seed_cell_y and col == seed_cell_x:
                    continue
                
                # Check fill pattern
                if not self._should_fill_cell(row, col, count_x, count_y, fill):
                    continue
                
                # Calculate position for this cell
                cell_offset_x = col * cell_width
                cell_offset_y = row * cell_height
                
                # Offset within cell (relative to seed's offset within its cell)
                within_cell_x = (seed_transform.pos.x - offset_x) % cell_width
                within_cell_y = (seed_transform.pos.y - offset_y) % cell_height
                
                new_x = offset_x + cell_offset_x + within_cell_x
                new_y = offset_y + cell_offset_y + within_cell_y
                
                mirror = Transform(
                    Vec2(new_x, new_y),
                    Vec2(seed_transform.scale.x, seed_transform.scale.y),
                    seed_transform.rotation
                )
                mirrors.append(mirror)
        
        return mirrors
    
    def _should_fill_cell(self, row, col, count_x, count_y, fill):
        """Check if cell should be filled based on fill pattern."""
        if fill == 0:  # Full
            return True
        elif fill == 1:  # Diamond
            # Diamond pattern: abs(row - center_y) + abs(col - center_x) <= radius
            center_x = count_x / 2.0
            center_y = count_y / 2.0
            distance = abs(col - center_x) + abs(row - center_y)
            radius = min(count_x, count_y) / 2.0
            return distance <= radius
        elif fill == 2:  # Alt-Diamond (checkerboard)
            return (row + col) % 2 == 0
        return False
    
    def draw_overlay(self, painter: QPainter, layer_uuid: str, coa):
        """Draw grid lines and shaded cells on canvas."""
        offset_x = self.settings['offset_x']
        offset_y = self.settings['offset_y']
        count_x = self.settings['count_x']
        count_y = self.settings['count_y']
        fill = self.settings['fill']
        
        # Set up pen for grid lines
        pen = QPen(QColor(255, 255, 0, 180))  # Yellow, semi-transparent
        pen.setWidth(1)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        
        # Calculate cell size in pixels
        cell_width_px = 512.0 / count_x
        cell_height_px = 512.0 / count_y
        
        offset_x_px = offset_x * 512
        offset_y_px = offset_y * 512
        
        # Draw grid lines and shade cells
        for row in range(count_y + 1):
            y = offset_y_px + (row * cell_height_px)
            painter.drawLine(int(offset_x_px), int(y), 
                           int(offset_x_px + count_x * cell_width_px), int(y))
        
        for col in range(count_x + 1):
            x = offset_x_px + (col * cell_width_px)
            painter.drawLine(int(x), int(offset_y_px), 
                           int(x), int(offset_y_px + count_y * cell_height_px))
        
        # Shade cells based on fill pattern
        brush = QBrush(QColor(255, 255, 0, 40))  # Very transparent yellow
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        
        for row in range(count_y):
            for col in range(count_x):
                if self._should_fill_cell(row, col, count_x, count_y, fill):
                    x = offset_x_px + (col * cell_width_px)
                    y = offset_y_px + (row * cell_height_px)
                    painter.drawRect(int(x), int(y), 
                                   int(cell_width_px), int(cell_height_px))
    
    def get_properties(self) -> List[float]:
        """Serialize to property list."""
        return [
            self.settings['offset_x'],
            self.settings['offset_y'],
            float(self.settings['count_x']),
            float(self.settings['count_y']),
            float(self.settings['fill']),
        ]
    
    def set_properties(self, properties: List[float]):
        """Deserialize from property list."""
        if len(properties) >= 5:
            self.settings['offset_x'] = properties[0]
            self.settings['offset_y'] = properties[1]
            self.settings['count_x'] = int(properties[2])
            self.settings['count_y'] = int(properties[3])
            self.settings['fill'] = int(properties[4])
            self._save_to_cache()
