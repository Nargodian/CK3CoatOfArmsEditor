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
        fill_dropdown.addItems(["Full", "Checkerboard"])
        fill_dropdown.setCurrentIndex(self.settings['fill'])
        fill_dropdown.currentIndexChanged.connect(
            lambda idx: self._on_param_changed('fill', idx))
        fill_layout.addWidget(fill_label)
        fill_layout.addWidget(fill_dropdown)
        layout.addLayout(fill_layout)
        self._controls['fill'] = fill_dropdown
        
        return layout
    
    def calculate_transforms(self, seed_transform) -> List:
        """Calculate grid transforms with seed-based identity and auto-determined checkerboard."""
        from models.transform import Transform, Vec2
        
        offset_x = self.settings['offset_x']
        offset_y = self.settings['offset_y']
        count_x = self.settings['count_x']
        count_y = self.settings['count_y']
        fill = self.settings['fill']
        
        mirrors = []
        
        # Calculate cell size (grid spans CoA space 0-1, ignoring offset)
        cell_width = 1.0 / count_x
        cell_height = 1.0 / count_y
        
        # Calculate identity cell from seed position (dynamic, offset ignored)
        identity_col = int(seed_transform.pos.x / cell_width)
        identity_row = int(seed_transform.pos.y / cell_height)
        
        # Clamp to grid bounds
        identity_col = max(0, min(count_x - 1, identity_col))
        identity_row = max(0, min(count_y - 1, identity_row))
        
        # Calculate seed parity for checkerboard pattern
        seed_parity = (identity_row + identity_col) % 2
        
        # Calculate seed's offset from its identity cell center
        identity_cell_center_x = (identity_col + 0.5) * cell_width
        identity_cell_center_y = (identity_row + 0.5) * cell_height
        seed_offset_x = seed_transform.pos.x - identity_cell_center_x
        seed_offset_y = seed_transform.pos.y - identity_cell_center_y
        
        # Generate positions for all cells in grid
        base_mirrors = []
        for row in range(count_y):
            for col in range(count_x):
                # Skip identity cell (seed stays at original position)
                if row == identity_row and col == identity_col:
                    continue
                
                # Check fill pattern (pass seed parity for checkerboard)
                if not self._should_fill_cell(row, col, seed_parity, fill):
                    continue
                
                # Calculate cell center, then apply seed's offset from its cell center
                cell_center_x = (col + 0.5) * cell_width
                cell_center_y = (row + 0.5) * cell_height
                new_x = max(0.0, min(1.0, cell_center_x + seed_offset_x))
                new_y = max(0.0, min(1.0, cell_center_y + seed_offset_y))
                
                mirror = Transform(
                    Vec2(new_x, new_y),
                    Vec2(seed_transform.scale.x, seed_transform.scale.y),
                    seed_transform.rotation
                )
                base_mirrors.append(mirror)
        
        # Apply edge wrapping to all instances (seed + mirrors)
        mirrors = []
        EDGE_THRESHOLD = 0.01  # Within 1% of edge
        
        all_instances = [seed_transform] + base_mirrors
        for instance in all_instances:
            # Skip the actual seed when processing from base_mirrors (already in all_instances)
            if instance in base_mirrors:
                mirrors.append(instance)
            
            inst_x = instance.pos.x
            inst_y = instance.pos.y
            
            # Check if near edges
            near_left = inst_x <= EDGE_THRESHOLD
            near_right = inst_x >= (1.0 - EDGE_THRESHOLD)
            near_bottom = inst_y <= EDGE_THRESHOLD
            near_top = inst_y >= (1.0 - EDGE_THRESHOLD)
            
            # Wrap horizontally
            if near_left:
                mirrors.append(Transform(
                    Vec2(inst_x + 1.0, inst_y),
                    Vec2(instance.scale.x, instance.scale.y),
                    instance.rotation
                ))
            if near_right:
                mirrors.append(Transform(
                    Vec2(inst_x - 1.0, inst_y),
                    Vec2(instance.scale.x, instance.scale.y),
                    instance.rotation
                ))
            
            # Wrap vertically
            if near_bottom:
                mirrors.append(Transform(
                    Vec2(inst_x, inst_y + 1.0),
                    Vec2(instance.scale.x, instance.scale.y),
                    instance.rotation
                ))
            if near_top:
                mirrors.append(Transform(
                    Vec2(inst_x, inst_y - 1.0),
                    Vec2(instance.scale.x, instance.scale.y),
                    instance.rotation
                ))
            
            # Wrap corners
            if near_left and near_bottom:
                mirrors.append(Transform(
                    Vec2(inst_x + 1.0, inst_y + 1.0),
                    Vec2(instance.scale.x, instance.scale.y),
                    instance.rotation
                ))
            if near_left and near_top:
                mirrors.append(Transform(
                    Vec2(inst_x + 1.0, inst_y - 1.0),
                    Vec2(instance.scale.x, instance.scale.y),
                    instance.rotation
                ))
            if near_right and near_bottom:
                mirrors.append(Transform(
                    Vec2(inst_x - 1.0, inst_y + 1.0),
                    Vec2(instance.scale.x, instance.scale.y),
                    instance.rotation
                ))
            if near_right and near_top:
                mirrors.append(Transform(
                    Vec2(inst_x - 1.0, inst_y - 1.0),
                    Vec2(instance.scale.x, instance.scale.y),
                    instance.rotation
                ))
        
        return mirrors
    
    def _should_fill_cell(self, row, col, seed_parity, fill):
        """Check if cell should be filled based on fill pattern.
        
        Args:
            row: Cell row index
            col: Cell column index
            seed_parity: Parity of seed cell (0 or 1) for checkerboard
            fill: Fill mode (0=full, 1=checkerboard)
        """
        if fill == 0:  # Full
            return True
        elif fill == 1:  # Checkerboard (auto-determined by seed)
            # Fill cells matching seed's checkerboard parity
            return (row + col) % 2 == seed_parity
        return False
    
    def draw_overlay(self, painter: QPainter, layer_uuid: str, coa):
        """Draw grid lines and shaded cells on canvas."""
        offset_x = self.settings['offset_x']
        offset_y = self.settings['offset_y']
        count_x = self.settings['count_x']
        count_y = self.settings['count_y']
        fill = self.settings['fill']
        
        # Get seed position to calculate parity for checkerboard
        layer = coa.get_layer_by_uuid(layer_uuid)
        if not layer:
            return
        
        seed_pos = layer.pos
        cell_width = 1.0 / count_x
        cell_height = 1.0 / count_y
        identity_col = int(seed_pos.x / cell_width)
        identity_row = int(seed_pos.y / cell_height)
        identity_col = max(0, min(count_x - 1, identity_col))
        identity_row = max(0, min(count_y - 1, identity_row))
        seed_parity = (identity_row + identity_col) % 2
        
        # Set up pen for grid lines
        pen = QPen(QColor(255, 255, 0, 180))  # Yellow, semi-transparent
        pen.setWidth(1)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        
        # Calculate cell size in pixels (grid spans full canvas 0-512)
        cell_width_px = 512.0 / count_x
        cell_height_px = 512.0 / count_y
        
        # Draw grid lines
        for row in range(count_y + 1):
            y = row * cell_height_px
            painter.drawLine(0, int(y), 512, int(y))
        
        for col in range(count_x + 1):
            x = col * cell_width_px
            painter.drawLine(int(x), 0, int(x), 512)
        
        # Shade cells based on fill pattern
        brush = QBrush(QColor(255, 255, 0, 40))  # Very transparent yellow
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        
        for row in range(count_y):
            for col in range(count_x):
                if self._should_fill_cell(row, col, seed_parity, fill):
                    x = col * cell_width_px
                    y = row * cell_height_px
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
