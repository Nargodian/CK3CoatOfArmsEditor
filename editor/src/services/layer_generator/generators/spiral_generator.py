"""Spiral pattern generator - arranges instances in a spiral."""

import numpy as np
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QWidget
from ..base_generator import BaseGenerator


class SpiralGenerator(BaseGenerator):
    """Generate instances arranged in a spiral pattern."""
    
    # Default parameter values
    DEFAULT_COUNT = 20
    DEFAULT_START_RADIUS = 0.05
    DEFAULT_END_RADIUS = 0.45
    DEFAULT_TURNS = 2.5
    DEFAULT_SCALE = 0.06
    DEFAULT_START_ANGLE = 0.0
    DEFAULT_END_ANGLE = 360.0
    DEFAULT_ROTATION_MODE = 'aligned'
    DEFAULT_BASE_ROTATION = 0.0
    DEFAULT_MODE = 'count'
    
    def __init__(self):
        super().__init__()
        
        # Initialize default settings
        self.settings = {
            'mode': self.DEFAULT_MODE,
            'count': self.DEFAULT_COUNT,
            'text': '',
            'start_radius': self.DEFAULT_START_RADIUS,
            'end_radius': self.DEFAULT_END_RADIUS,
            'turns': self.DEFAULT_TURNS,
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
        return "Spiral Pattern"
    
    def build_controls(self, parent: QWidget) -> QVBoxLayout:
        """Build parameter controls."""
        layout = QVBoxLayout()
        
        # Count/Text mode radio buttons
        mode_controls = self.add_count_text_radio(
            layout,
            default_mode=self.settings['mode'],
            default_count=self.settings['count']
        )
        
        # Connect mode switching
        def on_mode_changed():
            is_count = mode_controls['count_radio'].isChecked()
            self._on_param_changed('mode', 'count' if is_count else 'text')
        
        mode_controls['count_radio'].toggled.connect(on_mode_changed)
        mode_controls['count_spin'].valueChanged.connect(
            lambda v: self._on_param_changed('count', int(v)))
        mode_controls['text_input'].textChanged.connect(
            lambda: self._on_param_changed('text', mode_controls['text_input'].toPlainText()))
        
        self._controls['mode_controls'] = mode_controls
        
        # Start radius
        start_radius_layout = QHBoxLayout()
        start_radius_label = QLabel("Start Radius:")
        start_radius_spin = QDoubleSpinBox()
        start_radius_spin.setRange(0.0, 1.0)
        start_radius_spin.setSingleStep(0.01)
        start_radius_spin.setValue(self.settings['start_radius'])
        start_radius_spin.valueChanged.connect(lambda v: self._on_param_changed('start_radius', v))
        start_radius_layout.addWidget(start_radius_label)
        start_radius_layout.addWidget(start_radius_spin)
        layout.addLayout(start_radius_layout)
        
        self._controls['start_radius'] = start_radius_spin
        
        # End radius
        end_radius_layout = QHBoxLayout()
        end_radius_label = QLabel("End Radius:")
        end_radius_spin = QDoubleSpinBox()
        end_radius_spin.setRange(0.0, 1.0)
        end_radius_spin.setSingleStep(0.01)
        end_radius_spin.setValue(self.settings['end_radius'])
        end_radius_spin.valueChanged.connect(lambda v: self._on_param_changed('end_radius', v))
        end_radius_layout.addWidget(end_radius_label)
        end_radius_layout.addWidget(end_radius_spin)
        layout.addLayout(end_radius_layout)
        
        self._controls['end_radius'] = end_radius_spin
        
        # Turns
        turns_layout = QHBoxLayout()
        turns_label = QLabel("Turns:")
        turns_spin = QDoubleSpinBox()
        turns_spin.setRange(0.1, 10.0)
        turns_spin.setSingleStep(0.5)
        turns_spin.setValue(self.settings['turns'])
        turns_spin.valueChanged.connect(lambda v: self._on_param_changed('turns', v))
        turns_layout.addWidget(turns_label)
        turns_layout.addWidget(turns_spin)
        layout.addLayout(turns_layout)
        
        self._controls['turns'] = turns_spin
        
        # Angle controls
        angle_controls = self.add_angle_controls(
            layout,
            default_start=self.settings['start_angle'],
            default_end=self.settings['end_angle']
        )
        angle_controls['start_angle'].valueChanged.connect(
            lambda v: self._on_param_changed('start_angle', v))
        angle_controls['end_angle'].valueChanged.connect(
            lambda v: self._on_param_changed('end_angle', v))
        
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
        """Generate spiral arrangement of instances.
        
        Returns:
            5xN numpy array [[x, y, scale_x, scale_y, rotation], ...]
        """
        # Use settings as defaults, override with kwargs
        # In text mode, use text length instead of count
        count = self.get_effective_count()
        
        start_radius = kwargs.get('start_radius', self.settings['start_radius'])
        end_radius = kwargs.get('end_radius', self.settings['end_radius'])
        turns = kwargs.get('turns', self.settings['turns'])
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
        
        # Calculate total angular range including full turns
        angle_range = end_rad - start_rad
        if angle_range < 0:
            angle_range += 2 * np.pi
        
        total_angle = turns * 2 * np.pi
        
        # Generate positions
        center_x, center_y = 0.5, 0.5
        positions = np.zeros((count, 5))
        
        for i in range(count):
            # Interpolation parameter
            if count == 1:
                t = 0.5
            else:
                t = i / (count - 1)
            
            # Radius increases linearly
            radius = start_radius + t * (end_radius - start_radius)
            
            # Angle increases with spiral
            angle = start_rad + t * total_angle
            
            # Position
            x = center_x + radius * np.sin(angle)
            y = center_y + radius * np.cos(angle)
            
            # Scale
            if gradient_enabled:
                scale = start_scale + t * (end_scale - start_scale)
            else:
                scale = uniform_scale
            
            # Rotation
            if rotation_mode == 'aligned':
                # Aligned: tangent to spiral
                # Tangent angle = spiral angle + correction for radius growth
                tangent_angle = angle + np.arctan2(
                    end_radius - start_radius,
                    total_angle * (start_radius + t * (end_radius - start_radius))
                )
                rotation = np.rad2deg(tangent_angle) + base_rotation
            else:
                # Global: all same rotation
                rotation = base_rotation
            
            positions[i] = [x, y, scale, scale, rotation]
        
        # Add label codes for text mode preview
        positions = self.add_label_codes(positions)
        
        return positions
