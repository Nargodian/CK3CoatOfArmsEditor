"""Bisector symmetry transform - mirror across line(s)."""

import math
from typing import List
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QRadioButton, QButtonGroup, QSlider)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QColor
from models.transform import Vec2, Transform
from .base_transform import BaseSymmetryTransform
from utils.ui_utils import NumberSliderWidget


class BisectorTransform(BaseSymmetryTransform):
    """Mirror instances across line(s) at specified angle."""
    
    # Default parameter values
    DEFAULT_OFFSET_X = 0.5
    DEFAULT_OFFSET_Y = 0.5
    DEFAULT_ROTATION_OFFSET = -90.0
    DEFAULT_MODE = 0  # 0=single, 1=double cross
    
    def __init__(self):
        super().__init__()
        
        # Initialize default settings
        self.settings = {
            'offset_x': self.DEFAULT_OFFSET_X,
            'offset_y': self.DEFAULT_OFFSET_Y,
            'rotation_offset': self.DEFAULT_ROTATION_OFFSET,
            'mode': self.DEFAULT_MODE,
        }
    
    def get_name(self) -> str:
        return "bisector"
    
    def get_display_name(self) -> str:
        return "Bisector"
    
    def build_controls(self, parent: QWidget) -> QVBoxLayout:
        """Build UI controls for bisector parameters."""
        layout = QVBoxLayout()
        
        # Offset X slider
        offset_x_widget = NumberSliderWidget("Offset X", self.settings['offset_x'],
                                            min_val=0.0, max_val=1.0, step=0.01)
        offset_x_widget.valueChanged.connect(
            lambda v: self._on_param_changed('offset_x', v))
        layout.addWidget(offset_x_widget)
        self._controls['offset_x'] = offset_x_widget
        
        # Offset Y slider
        offset_y_widget = NumberSliderWidget("Offset Y", self.settings['offset_y'],
                                            min_val=0.0, max_val=1.0, step=0.01)
        offset_y_widget.valueChanged.connect(
            lambda v: self._on_param_changed('offset_y', v))
        layout.addWidget(offset_y_widget)
        self._controls['offset_y'] = offset_y_widget
        
        # Rotation offset slider
        rotation_widget = NumberSliderWidget("Rotation", self.settings['rotation_offset'],
                                            min_val=-180, max_val=180, is_int=True)
        rotation_widget.valueChanged.connect(
            lambda v: self._on_param_changed('rotation_offset', float(v)))
        layout.addWidget(rotation_widget)
        self._controls['rotation'] = rotation_widget
        
        # Mode radio buttons
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Mode:")
        mode_layout.addWidget(mode_label)
        
        mode_group = QButtonGroup(parent)
        single_radio = QRadioButton("Single")
        double_radio = QRadioButton("Double Cross")
        mode_group.addButton(single_radio, 0)
        mode_group.addButton(double_radio, 1)
        
        if self.settings['mode'] == 0:
            single_radio.setChecked(True)
        else:
            double_radio.setChecked(True)
        
        mode_group.buttonClicked.connect(
            lambda btn: self._on_param_changed('mode', mode_group.id(btn)))
        
        mode_layout.addWidget(single_radio)
        mode_layout.addWidget(double_radio)
        layout.addLayout(mode_layout)
        
        self._controls['mode_group'] = mode_group
        
        return layout
    
    def calculate_transforms(self, seed_transform) -> List:
        """Calculate mirror transforms."""
        from models.transform import Transform, Vec2
        
        offset_x = self.settings['offset_x']
        offset_y = self.settings['offset_y']
        rotation_offset = self.settings['rotation_offset']
        mode = self.settings['mode']
        
        mirrors = []
        
        # Mirror across line at rotation_offset angle
        mirror1 = self._mirror_across_line(
            seed_transform, offset_x, offset_y, rotation_offset)
        mirrors.append(mirror1)
        
        # If double cross mode, add perpendicular mirror
        if mode == 1:
            mirror2 = self._mirror_across_line(
                seed_transform, offset_x, offset_y, rotation_offset + 90)
            mirrors.append(mirror2)
            
            # Also add the mirror of mirror1 across the perpendicular line
            mirror3 = self._mirror_across_line(
                mirror1, offset_x, offset_y, rotation_offset + 90)
            mirrors.append(mirror3)
        
        return mirrors
    
    def _mirror_across_line(self, transform, offset_x, offset_y, line_angle):
        """Mirror transform across line at given angle through offset point."""
        from models.transform import Transform, Vec2
        
        # Get position relative to offset point
        rel_x = transform.pos.x - offset_x
        rel_y = transform.pos.y - offset_y
        
        # Convert line angle to radians
        theta = math.radians(line_angle)
        cos_2theta = math.cos(2 * theta)
        sin_2theta = math.sin(2 * theta)
        
        # Mirror position using reflection matrix
        mirrored_rel_x = rel_x * cos_2theta + rel_y * sin_2theta
        mirrored_rel_y = rel_x * sin_2theta - rel_y * cos_2theta
        
        # Convert back to absolute position and clamp to [0, 1]
        mirrored_x = max(0.0, min(1.0, mirrored_rel_x + offset_x))
        mirrored_y = max(0.0, min(1.0, mirrored_rel_y + offset_y))
        
        # Mirror rotation: new_rotation = 2 * line_angle - old_rotation
        # Since we're also applying flip_x which visually adds 180 degrees,
        # we need to compensate by subtracting 180
        mirrored_rotation = 2 * line_angle - transform.rotation - 180
        
        # Create mirrored transform with flipped X axis
        mirrored_transform = Transform(
            Vec2(mirrored_x, mirrored_y),
            Vec2(transform.scale.x, transform.scale.y),
            mirrored_rotation
        )
        # Mark as flipped for rendering
        mirrored_transform.flip_x = not getattr(transform, 'flip_x', False)
        
        return mirrored_transform
    
    def draw_overlay(self, painter: QPainter, layer_uuid: str, coa, coa_to_canvas):
        """Draw dashed mirror line(s) on canvas.
        
        Args:
            painter: QPainter for drawing
            layer_uuid: UUID of layer to visualize
            coa: CoA model instance
            coa_to_canvas: Function to convert CoA space (0-1) to canvas pixels
        """
        offset_x = self.settings['offset_x']
        offset_y = self.settings['offset_y']
        rotation_offset = self.settings['rotation_offset']
        mode = self.settings['mode']
        
        # Set up pen for dashed line
        pen = QPen(QColor(255, 255, 150, 100))  # Pastel yellow, more transparent
        pen.setWidth(2)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        
        # Convert center from CoA space to canvas pixels
        from models.transform import Vec2
        center_coa = Vec2(offset_x, offset_y)
        center_canvas = coa_to_canvas(center_coa)
        center_x = center_canvas.x
        center_y = center_canvas.y
        
        # Draw first mirror line
        self._draw_line_at_angle(painter, center_x, center_y, rotation_offset, 600)
        
        # If double cross, draw perpendicular line
        if mode == 1:
            self._draw_line_at_angle(painter, center_x, center_y, rotation_offset + 90, 600)
    
    def _draw_line_at_angle(self, painter, cx, cy, angle, length):
        """Draw line through (cx, cy) at given angle."""
        rad = math.radians(angle)
        dx = math.cos(rad) * length
        dy = math.sin(rad) * length
        
        painter.drawLine(
            int(cx - dx), int(cy - dy),
            int(cx + dx), int(cy + dy)
        )
    
    def get_properties(self) -> List[float]:
        """Serialize to property list."""
        return [
            self.settings['offset_x'],
            self.settings['offset_y'],
            self.settings['rotation_offset'],
            float(self.settings['mode']),
        ]
    
    def set_properties(self, properties: List[float]):
        """Deserialize from property list."""
        if len(properties) >= 4:
            self.settings['offset_x'] = properties[0]
            self.settings['offset_y'] = properties[1]
            self.settings['rotation_offset'] = properties[2]
            self.settings['mode'] = int(properties[3])
            self._save_to_cache()
