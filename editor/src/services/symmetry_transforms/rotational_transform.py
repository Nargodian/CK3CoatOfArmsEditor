"""Rotational symmetry transform - radial mirrors around center point."""

import math
from typing import List
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QSpinBox, QCheckBox, QSlider)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QColor
from models.transform import Vec2, Transform
from .base_transform import BaseSymmetryTransform


class RotationalTransform(BaseSymmetryTransform):
    """Rotate instances around center point with optional kaleidoscope."""
    
    # Default parameter values
    DEFAULT_OFFSET_X = 0.5
    DEFAULT_OFFSET_Y = 0.5
    DEFAULT_COUNT = 4
    DEFAULT_ROTATION_OFFSET = 0.0
    DEFAULT_KALEIDOSCOPE = False
    
    def __init__(self):
        super().__init__()
        
        # Initialize default settings
        self.settings = {
            'offset_x': self.DEFAULT_OFFSET_X,
            'offset_y': self.DEFAULT_OFFSET_Y,
            'count': self.DEFAULT_COUNT,
            'rotation_offset': self.DEFAULT_ROTATION_OFFSET,
            'kaleidoscope': self.DEFAULT_KALEIDOSCOPE,
        }
    
    def get_name(self) -> str:
        return "rotational"
    
    def get_display_name(self) -> str:
        return "Rotational"
    
    def build_controls(self, parent: QWidget) -> QVBoxLayout:
        """Build UI controls for rotational parameters."""
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
        
        # Count spinner
        count_layout = QHBoxLayout()
        count_label = QLabel("Count:")
        count_spinner = QSpinBox()
        count_spinner.setRange(2, 12)
        count_spinner.setValue(self.settings['count'])
        count_spinner.valueChanged.connect(
            lambda v: self._on_param_changed('count', int(v)))
        count_layout.addWidget(count_label)
        count_layout.addWidget(count_spinner)
        layout.addLayout(count_layout)
        self._controls['count'] = count_spinner
        
        # Rotation offset slider
        rotation_layout = QHBoxLayout()
        rotation_label = QLabel("Rotation:")
        rotation_slider = QSlider(Qt.Horizontal)
        rotation_slider.setRange(-180, 180)
        rotation_slider.setValue(int(self.settings['rotation_offset']))
        rotation_slider.valueChanged.connect(
            lambda v: self._on_param_changed('rotation_offset', float(v)))
        rotation_layout.addWidget(rotation_label)
        rotation_layout.addWidget(rotation_slider)
        layout.addLayout(rotation_layout)
        self._controls['rotation'] = rotation_slider
        
        # Kaleidoscope checkbox
        kaleidoscope_check = QCheckBox("Kaleidoscope (mirror + rotate)")
        kaleidoscope_check.setChecked(self.settings['kaleidoscope'])
        kaleidoscope_check.toggled.connect(
            lambda v: self._on_param_changed('kaleidoscope', v))
        layout.addWidget(kaleidoscope_check)
        self._controls['kaleidoscope'] = kaleidoscope_check
        
        return layout
    
    def calculate_transforms(self, seed_transform) -> List:
        """Calculate rotational transforms."""
        from models.transform import Transform, Vec2
        
        offset_x = self.settings['offset_x']
        offset_y = self.settings['offset_y']
        count = self.settings['count']
        rotation_offset = self.settings['rotation_offset']
        kaleidoscope = self.settings['kaleidoscope']
        
        mirrors = []
        angle_step = 360.0 / count
        
        for i in range(1, count):  # Skip first (i=0) since that's the seed
            angle = rotation_offset + (i * angle_step)
            
            # Rotate around offset point
            rotated = self._rotate_around_point(
                seed_transform, offset_x, offset_y, angle)
            mirrors.append(rotated)
            
            # If kaleidoscope, also add mirrored version
            if kaleidoscope:
                # Mirror across radial line
                mirrored = self._mirror_across_radial(
                    seed_transform, offset_x, offset_y, angle)
                mirrors.append(mirrored)
        
        return mirrors
    
    def _rotate_around_point(self, transform, pivot_x, pivot_y, angle):
        """Rotate transform around pivot point."""
        from models.transform import Transform, Vec2
        
        # Get position relative to pivot
        rel_x = transform.pos.x - pivot_x
        rel_y = transform.pos.y - pivot_y
        
        # Rotate around pivot
        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        
        rotated_rel_x = rel_x * cos_a - rel_y * sin_a
        rotated_rel_y = rel_x * sin_a + rel_y * cos_a
        
        # Convert back to absolute position
        rotated_x = rotated_rel_x + pivot_x
        rotated_y = rotated_rel_y + pivot_y
        
        # Rotate the instance's own rotation
        rotated_rotation = transform.rotation + angle
        
        return Transform(
            Vec2(rotated_x, rotated_y),
            Vec2(transform.scale.x, transform.scale.y),
            rotated_rotation
        )
    
    def _mirror_across_radial(self, transform, pivot_x, pivot_y, angle):
        """Mirror transform across radial line at given angle."""
        from models.transform import Transform, Vec2
        
        # Get position relative to pivot
        rel_x = transform.pos.x - pivot_x
        rel_y = transform.pos.y - pivot_y
        
        # Convert angle to radians
        theta = math.radians(angle)
        cos_2theta = math.cos(2 * theta)
        sin_2theta = math.sin(2 * theta)
        
        # Mirror using reflection matrix
        mirrored_rel_x = rel_x * cos_2theta + rel_y * sin_2theta
        mirrored_rel_y = rel_x * sin_2theta - rel_y * cos_2theta
        
        # Convert back to absolute position
        mirrored_x = mirrored_rel_x + pivot_x
        mirrored_y = mirrored_rel_y + pivot_y
        
        # Mirror rotation
        mirrored_rotation = 2 * angle - transform.rotation
        
        return Transform(
            Vec2(mirrored_x, mirrored_y),
            Vec2(transform.scale.x, transform.scale.y),
            mirrored_rotation
        )
    
    def draw_overlay(self, painter: QPainter, layer_uuid: str, coa):
        """Draw radial dashed lines on canvas."""
        offset_x = self.settings['offset_x']
        offset_y = self.settings['offset_y']
        count = self.settings['count']
        rotation_offset = self.settings['rotation_offset']
        
        # Set up pen for dashed lines
        pen = QPen(QColor(255, 255, 0, 180))  # Yellow, semi-transparent
        pen.setWidth(2)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        
        # Convert offset to pixel coordinates
        center_x = offset_x * 512
        center_y = offset_y * 512
        
        # Draw radial lines
        angle_step = 360.0 / count
        for i in range(count):
            angle = rotation_offset + (i * angle_step)
            rad = math.radians(angle)
            
            # Draw line from center outward
            dx = math.cos(rad) * 300  # Extended length
            dy = math.sin(rad) * 300
            
            painter.drawLine(
                int(center_x), int(center_y),
                int(center_x + dx), int(center_y + dy)
            )
    
    def get_properties(self) -> List[float]:
        """Serialize to property list."""
        return [
            self.settings['offset_x'],
            self.settings['offset_y'],
            float(self.settings['count']),
            self.settings['rotation_offset'],
            float(self.settings['kaleidoscope']),
        ]
    
    def set_properties(self, properties: List[float]):
        """Deserialize from property list."""
        if len(properties) >= 5:
            self.settings['offset_x'] = properties[0]
            self.settings['offset_y'] = properties[1]
            self.settings['count'] = int(properties[2])
            self.settings['rotation_offset'] = properties[3]
            self.settings['kaleidoscope'] = bool(int(properties[4]))
            self._save_to_cache()
