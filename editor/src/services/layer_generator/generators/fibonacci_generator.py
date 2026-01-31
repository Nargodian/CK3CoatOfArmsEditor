"""Fibonacci spiral pattern generator - sunflower seed arrangement."""

import numpy as np
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QWidget
from ..base_generator import BaseGenerator


class FibonacciGenerator(BaseGenerator):
    """Generate instances in Fibonacci spiral (sunflower) pattern.
    
    Uses the golden angle (~137.5°) to create an even radial distribution
    similar to sunflower seed arrangements.
    """
    
    # Default parameter values
    DEFAULT_COUNT = 50
    DEFAULT_SCALE = 0.05
    GOLDEN_ANGLE = 137.508  # Golden angle in degrees
    PADDING = 0.05  # Padding from edges
    
    def __init__(self):
        super().__init__()
        
        # Initialize default settings
        self.settings = {
            'count': self.DEFAULT_COUNT,
            'uniform_scale': self.DEFAULT_SCALE,
        }
    
    def get_title(self) -> str:
        """Return display title."""
        return "Fibonacci Spiral (Sunflower)"
    
    def build_controls(self, parent: QWidget) -> QVBoxLayout:
        """Build parameter controls."""
        layout = QVBoxLayout()
        
        # Count parameter
        count_layout = QHBoxLayout()
        count_label = QLabel("Count:")
        count_spin = QDoubleSpinBox()
        count_spin.setRange(1, 200)
        count_spin.setDecimals(0)
        count_spin.setValue(self.settings['count'])
        count_spin.valueChanged.connect(lambda v: self._on_param_changed('count', int(v)))
        count_layout.addWidget(count_label)
        count_layout.addWidget(count_spin)
        layout.addLayout(count_layout)
        
        self._controls['count'] = count_spin
        
        # Scale control
        scale_layout = QHBoxLayout()
        scale_label = QLabel("Scale:")
        scale_spin = QDoubleSpinBox()
        scale_spin.setRange(0.01, 0.5)
        scale_spin.setSingleStep(0.01)
        scale_spin.setValue(self.settings['uniform_scale'])
        scale_spin.valueChanged.connect(lambda v: self._on_param_changed('uniform_scale', v))
        scale_layout.addWidget(scale_label)
        scale_layout.addWidget(scale_spin)
        layout.addLayout(scale_layout)
        
        self._controls['uniform_scale'] = scale_spin
        
        # Info note
        note = QLabel("Creates natural sunflower seed pattern. More points = smaller individual instances.")
        note.setWordWrap(True)
        note.setStyleSheet("color: #888; font-style: italic; font-size: 9pt;")
        layout.addWidget(note)
        
        return layout
    
    def _on_param_changed(self, param_name: str, value):
        """Handle parameter value change."""
        self.settings[param_name] = value
        if self.on_parameter_changed:
            self.on_parameter_changed()
    
    def generate_positions(self, **kwargs) -> np.ndarray:
        """Generate Fibonacci spiral arrangement.
        
        Uses Vogel's method for evenly distributing points in a circle
        using the golden angle.
        
        Returns:
            5xN numpy array [[x, y, scale_x, scale_y, rotation], ...]
        """
        # Use settings as defaults, override with kwargs
        count = kwargs.get('count', self.settings['count'])
        scale = kwargs.get('uniform_scale', self.settings['uniform_scale'])
        
        if count < 1:
            return np.array([]).reshape(0, 5)
        
        positions = np.zeros((count, 5))
        
        # Convert golden angle to radians
        golden_angle_rad = np.deg2rad(self.GOLDEN_ANGLE)
        
        # Center position
        center_x, center_y = 0.5, 0.5
        
        # Maximum radius (with padding)
        max_radius = 0.5 - self.PADDING
        
        for i in range(count):
            # Calculate angle using golden angle
            angle = i * golden_angle_rad
            
            # Calculate radius - grows with square root for even density
            # Normalized to fit within max_radius
            radius = max_radius * np.sqrt(i / max(count - 1, 1))
            
            # Calculate position
            x = center_x + radius * np.cos(angle)
            y = center_y + radius * np.sin(angle)
            
            # Rotation follows the spiral (aligned with angle)
            rotation = np.rad2deg(angle)
            
            positions[i] = [x, y, scale, scale, rotation]
        
        return positions
