"""Line pattern generator - arranges instances along a straight line."""

import numpy as np
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QWidget
from ..base_generator import BaseGenerator


class LineGenerator(BaseGenerator):
    """Generate instances arranged in a line."""
    
    # Default parameter values
    DEFAULT_COUNT = 5
    DEFAULT_SCALE = 0.1
    DEFAULT_START_ANGLE = 0.0
    DEFAULT_END_ANGLE = 180.0
    DEFAULT_ROTATION_MODE = 'global'
    DEFAULT_BASE_ROTATION = 0.0
    
    def __init__(self):
        super().__init__()
        
        # Initialize default settings
        self.settings = {
            'count': self.DEFAULT_COUNT,
            'start_angle': self.DEFAULT_START_ANGLE,
            'end_angle': self.DEFAULT_END_ANGLE,
            'gradient_enabled': False,
            'uniform_scale': self.DEFAULT_SCALE,
            'start_scale': self.DEFAULT_SCALE,
            'end_scale': self.DEFAULT_SCALE,
            'rotation_mode': self.DEFAULT_ROTATION_MODE,
            'base_rotation': self.DEFAULT_BASE_ROTATION,
        }
    
    def get_title(self) -> str:
        """Return display title."""
        return "Line Pattern"
    
    def build_controls(self, parent: QWidget) -> QVBoxLayout:
        """Build parameter controls."""
        layout = QVBoxLayout()
        
        # Count parameter
        count_layout = QHBoxLayout()
        count_label = QLabel("Count:")
        count_spin = QDoubleSpinBox()
        count_spin.setRange(1, 100)
        count_spin.setDecimals(0)
        count_spin.setValue(self.settings['count'])
        count_spin.valueChanged.connect(lambda v: self._on_param_changed('count', int(v)))
        count_layout.addWidget(count_label)
        count_layout.addWidget(count_spin)
        layout.addLayout(count_layout)
        
        self._controls['count'] = count_spin
        
        # Angle controls (defines line direction and length)
        angle_controls = self.add_angle_controls(
            layout,
            default_start=self.settings['start_angle'],
            default_end=self.settings['end_angle']
        )
        angle_controls['start_angle'].valueChanged.connect(
            lambda v: self._on_param_changed('start_angle', v))
        angle_controls['end_angle'].valueChanged.connect(
            lambda v: self._on_param_changed('end_angle', v))
        
        # Add explanation
        explanation = QLabel("Note: Start/End angles define the line endpoints")
        explanation.setWordWrap(True)
        explanation.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(explanation)
        
        # Scale controls
        scale_controls = self.add_scale_controls(
            layout,
            default_scale=self.settings['uniform_scale'],
            enable_gradient=self.settings['gradient_enabled']
        )
        scale_controls['gradient_check'].toggled.connect(
            lambda v: self._on_param_changed('gradient_enabled', v))
        scale_controls['uniform_scale'].valueChanged.connect(
            lambda v: self._on_param_changed('uniform_scale', v))
        scale_controls['start_scale'].valueChanged.connect(
            lambda v: self._on_param_changed('start_scale', v))
        scale_controls['end_scale'].valueChanged.connect(
            lambda v: self._on_param_changed('end_scale', v))
        
        # Rotation controls
        rotation_controls = self.add_rotation_controls(
            layout,
            default_mode=self.settings['rotation_mode'],
            default_rotation=self.settings['base_rotation']
        )
        rotation_controls['mode_combo'].currentTextChanged.connect(
            lambda v: self._on_param_changed('rotation_mode', v))
        rotation_controls['base_rotation'].valueChanged.connect(
            lambda v: self._on_param_changed('base_rotation', v))
        
        return layout
    
    def _on_param_changed(self, param_name: str, value):
        """Handle parameter value change."""
        self.settings[param_name] = value
        if self.on_parameter_changed:
            self.on_parameter_changed()
    
    def generate_positions(self, **kwargs) -> np.ndarray:
        """Generate line arrangement of instances.
        
        Returns:
            5xN numpy array [[x, y, scale_x, scale_y, rotation], ...]
        """
        # Use settings as defaults, override with kwargs
        count = kwargs.get('count', self.settings['count'])
        start_angle = kwargs.get('start_angle', self.settings['start_angle'])
        end_angle = kwargs.get('end_angle', self.settings['end_angle'])
        gradient_enabled = kwargs.get('gradient_enabled', self.settings['gradient_enabled'])
        uniform_scale = kwargs.get('uniform_scale', self.settings['uniform_scale'])
        start_scale = kwargs.get('start_scale', self.settings['start_scale'])
        end_scale = kwargs.get('end_scale', self.settings['end_scale'])
        rotation_mode = kwargs.get('rotation_mode', self.settings['rotation_mode'])
        base_rotation = kwargs.get('base_rotation', self.settings['base_rotation'])
        
        if count < 1:
            return np.array([]).reshape(0, 5)
        
        # Convert angles to radians
        start_rad = np.deg2rad(start_angle)
        end_rad = np.deg2rad(end_angle)
        
        # Calculate line endpoints from angles
        # Use radius 0.4 to keep within bounds
        center_x, center_y = 0.5, 0.5
        radius = 0.4
        
        start_x = center_x + radius * np.sin(start_rad)
        start_y = center_y + radius * np.cos(start_rad)
        end_x = center_x + radius * np.sin(end_rad)
        end_y = center_y + radius * np.cos(end_rad)
        
        # Generate positions along line
        positions = np.zeros((count, 5))
        
        for i in range(count):
            # Interpolate position
            if count == 1:
                t = 0.5
            else:
                t = i / (count - 1)
            
            x = start_x + t * (end_x - start_x)
            y = start_y + t * (end_y - start_y)
            
            # Scale
            if gradient_enabled:
                scale = start_scale + t * (end_scale - start_scale)
            else:
                scale = uniform_scale
            
            # Rotation
            if rotation_mode == 'aligned':
                # Aligned: follow line direction
                line_angle = np.arctan2(end_x - start_x, end_y - start_y)
                rotation = np.rad2deg(line_angle) + base_rotation
            else:
                # Global: all same rotation
                rotation = base_rotation
            
            positions[i] = [x, y, scale, scale, rotation]
        
        return positions
