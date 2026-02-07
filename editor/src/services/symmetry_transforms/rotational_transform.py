"""Rotational symmetry transform - radial mirrors around center point."""

import math
from typing import List
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QSpinBox, QCheckBox, QSlider)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QColor
from models.transform import Vec2, Transform
from .base_transform import BaseSymmetryTransform
from utils.ui_utils import NumberSliderWidget


class RotationalTransform(BaseSymmetryTransform):
    """Rotate instances around center point with optional kaleidoscope."""
    
    # Default parameter values
    DEFAULT_OFFSET_X = 0.5
    DEFAULT_OFFSET_Y = 0.5
    DEFAULT_COUNT = 4
    DEFAULT_KALEIDOSCOPE = False
    DEFAULT_ROTATION_OFFSET = 0.0
    
    def __init__(self):
        super().__init__()
        
        # Initialize default settings
        self.settings = {
            'offset_x': self.DEFAULT_OFFSET_X,
            'offset_y': self.DEFAULT_OFFSET_Y,
            'count': self.DEFAULT_COUNT,
            'kaleidoscope': self.DEFAULT_KALEIDOSCOPE,
            'rotation_offset': self.DEFAULT_ROTATION_OFFSET,
        }
    
    def get_name(self) -> str:
        return "rotational"
    
    def get_display_name(self) -> str:
        return "Rotational"
    
    def build_controls(self, parent: QWidget) -> QVBoxLayout:
        """Build UI controls for rotational parameters."""
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
        
        # Count slider
        count_widget = NumberSliderWidget("Count", self.settings['count'],
                                         min_val=2, max_val=12, is_int=True)
        count_widget.valueChanged.connect(
            lambda v: self._on_param_changed('count', int(v)))
        layout.addWidget(count_widget)
        self._controls['count'] = count_widget
        
        # Kaleidoscope checkbox
        kaleidoscope_check = QCheckBox("Kaleidoscope (mirror + rotate)")
        kaleidoscope_check.setChecked(self.settings['kaleidoscope'])
        kaleidoscope_check.toggled.connect(
            lambda v: self._on_param_changed('kaleidoscope', v))
        layout.addWidget(kaleidoscope_check)
        self._controls['kaleidoscope'] = kaleidoscope_check
        
        # Rotation offset slider
        rotation_offset_widget = NumberSliderWidget("Rotation Offset", 
                                                   self.settings['rotation_offset'],
                                                   min_val=0, max_val=359, is_int=True)
        rotation_offset_widget.valueChanged.connect(
            lambda v: self._on_param_changed('rotation_offset', float(v)))
        layout.addWidget(rotation_offset_widget)
        self._controls['rotation_offset'] = rotation_offset_widget
        
        return layout
    
    def calculate_transforms(self, seed_transform) -> List:
        """Calculate rotational transforms."""
        from models.transform import Transform, Vec2
        
        offset_x = self.settings['offset_x']
        offset_y = self.settings['offset_y']
        count = self.settings['count']
        kaleidoscope = self.settings['kaleidoscope']
        rotation_offset = self.settings['rotation_offset']
        
        mirrors = []
        angle_step = 360.0 / count
        
        if kaleidoscope:
            # Kaleidoscope mode: create mirror seed, then rotate both versions
            # Create mirror seed by reflecting across bisector
            bisector_angle = angle_step/2 + rotation_offset
            mirrored = self._mirror_across_radial(
                seed_transform, offset_x, offset_y, bisector_angle)
            mirror_seed = Transform(
                Vec2(mirrored.pos.x, mirrored.pos.y),
                Vec2(seed_transform.scale.x, seed_transform.scale.y),
                2*bisector_angle - seed_transform.rotation - 180,
                flip_x=not getattr(seed_transform, 'flip_x', False),
                flip_y=getattr(seed_transform, 'flip_y', False)
            )
            
            # Pattern both seed and mirror_seed with rotations
            base_versions = [seed_transform, mirror_seed]
            for base_transform in base_versions:
                for i in range(count):
                    angle = i * angle_step
                    # Skip i=0 for seed_transform since that's the original
                    if base_transform is seed_transform and i == 0:
                        continue
                    rotated = self._rotate_around_point(
                        base_transform, offset_x, offset_y, angle)
                    mirrors.append(rotated)
        else:
            # Regular mode: just rotations
            for i in range(1, count):
                angle = i * angle_step
                rotated = self._rotate_around_point(
                    seed_transform, offset_x, offset_y, angle)
                mirrors.append(rotated)
        
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
        
        # Convert back to absolute position and clamp to [0, 1]
        rotated_x = max(0.0, min(1.0, rotated_rel_x + pivot_x))
        rotated_y = max(0.0, min(1.0, rotated_rel_y + pivot_y))
        
        # Rotate the instance's own rotation
        rotated_rotation = transform.rotation + angle
        
        return Transform(
            Vec2(rotated_x, rotated_y),
            Vec2(transform.scale.x, transform.scale.y),
            rotated_rotation,
            flip_x=getattr(transform, 'flip_x', False),
            flip_y=getattr(transform, 'flip_y', False)
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
        
        # Convert back to absolute position and clamp to [0, 1]
        mirrored_x = max(0.0, min(1.0, mirrored_rel_x + pivot_x))
        mirrored_y = max(0.0, min(1.0, mirrored_rel_y + pivot_y))
        
        # Mirror rotation
        mirrored_rotation = 2 * angle - transform.rotation
        
        return Transform(
            Vec2(mirrored_x, mirrored_y),
            Vec2(transform.scale.x, transform.scale.y),
            mirrored_rotation
        )
    
    def draw_overlay(self, painter: QPainter, layer_uuid: str, coa, coa_to_canvas):
        """Draw radial dashed lines on canvas.
        
        Args:
            painter: QPainter for drawing
            layer_uuid: UUID of layer to visualize
            coa: CoA model instance
            coa_to_canvas: Function to convert CoA space (0-1) to canvas pixels
        """
        offset_x = self.settings['offset_x']
        offset_y = self.settings['offset_y']
        count = self.settings['count']
        rotation_offset = self.settings['rotation_offset']
        
        # Set up pen for dashed lines
        pen = QPen(QColor(255, 255, 150, 100))  # Pastel yellow, more transparent
        pen.setWidth(2)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        
        # Convert center position from CoA space to canvas pixels
        from models.transform import Vec2
        center_coa = Vec2(offset_x, offset_y)
        center_canvas = coa_to_canvas(center_coa)
        center_x = center_canvas.x
        center_y = center_canvas.y
        
        # Draw radial lines
        angle_step = 360.0 / count
        for i in range(count):
            angle = rotation_offset + (i * angle_step)
            rad = math.radians(angle)
            
            # Draw line from center outward
            dx = math.cos(rad) * 300  # Extended length in pixels
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
            float(self.settings['kaleidoscope']),
            self.settings['rotation_offset'],
        ]
    
    def set_properties(self, properties: List[float]):
        """Deserialize from property list."""
        if len(properties) >= 4:
            self.settings['offset_x'] = properties[0]
            self.settings['offset_y'] = properties[1]
            self.settings['count'] = int(properties[2])
            self.settings['kaleidoscope'] = bool(int(properties[3]))
            if len(properties) >= 5:
                self.settings['rotation_offset'] = properties[4]
            else:
                self.settings['rotation_offset'] = self.DEFAULT_ROTATION_OFFSET
            self._save_to_cache()
