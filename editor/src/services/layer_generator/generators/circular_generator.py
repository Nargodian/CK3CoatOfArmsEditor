"""Circular pattern generator - arranges instances in a circle or arc."""

import numpy as np
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QWidget
from ..base_generator import BaseGenerator


class CircularGenerator(BaseGenerator):
    """Generate instances arranged in a circular pattern."""
    
    # Default parameter values
    DEFAULT_COUNT = 12
    DEFAULT_RADIUS = 0.4
    DEFAULT_SCALE = 0.08
    DEFAULT_START_ANGLE = 0.0
    DEFAULT_END_ANGLE = 360.0
    DEFAULT_ROTATION_MODE = 'aligned'
    DEFAULT_BASE_ROTATION = 0.0
    DEFAULT_MODE = 'count'
    
    def __init__(self):
        # Initialize default settings BEFORE calling super()
        # so cache restoration can update these defaults
        self.settings = {
            'mode': self.DEFAULT_MODE,
            'count': self.DEFAULT_COUNT,
            'text': '',
            'full_span': False,
            'radius': self.DEFAULT_RADIUS,
            'start_angle': self.DEFAULT_START_ANGLE,
            'end_angle': self.DEFAULT_END_ANGLE,
            'gradient_enabled': False,
            'uniform_scale': self.DEFAULT_SCALE,
            'start_scale': self.DEFAULT_SCALE,
            'end_scale': self.DEFAULT_SCALE,
            'rotation_mode': self.DEFAULT_ROTATION_MODE,
            'base_rotation': self.DEFAULT_BASE_ROTATION,
        }
        
        super().__init__()
    
    def get_title(self) -> str:
        """Return display title."""
        return "Circular Pattern"
    
    def build_controls(self, parent: QWidget) -> QVBoxLayout:
        """Build parameter controls."""
        layout = QVBoxLayout()
        
        # Count/Text mode radio buttons with full_span toggle
        mode_controls = self.add_count_text_radio(
            layout,
            default_mode=self.settings['mode'],
            default_count=self.settings['count'],
            enable_full_span=True,
            default_full_span=self.settings.get('full_span', False)
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
        
        # Connect full_span checkbox if present
        if 'full_span_check' in mode_controls:
            mode_controls['full_span_check'].toggled.connect(
                lambda v: self._on_param_changed('full_span', v))
        
        self._controls['mode_controls'] = mode_controls
        
        # Radius parameter
        radius_layout = QHBoxLayout()
        radius_label = QLabel("Radius:")
        radius_spin = QDoubleSpinBox()
        radius_spin.setRange(0.01, 1.0)
        radius_spin.setSingleStep(0.01)
        radius_spin.setValue(self.settings['radius'])
        radius_spin.valueChanged.connect(lambda v: self._on_param_changed('radius', v))
        radius_layout.addWidget(radius_label)
        radius_layout.addWidget(radius_spin)
        layout.addLayout(radius_layout)
        
        self._controls['radius'] = radius_spin
        
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
            lambda v: self._on_param_changed('uniform_scale', v / 100.0))
        scale_controls['start_scale'].valueChanged.connect(
            lambda v: self._on_param_changed('start_scale', v / 100.0))
        scale_controls['end_scale'].valueChanged.connect(
            lambda v: self._on_param_changed('end_scale', v / 100.0))
        
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
        # Trigger preview update
        if self.on_parameter_changed:
            self.on_parameter_changed()
    
    def generate_positions(self, **kwargs) -> np.ndarray:
        """Generate circular arrangement of instances.
        
        Returns:
            5xN numpy array [[x, y, scale_x, scale_y, rotation], ...]
        """
        # Use settings as defaults, override with kwargs
        # In text mode, use text length instead of count
        count = self.get_effective_count()
        
        radius = kwargs.get('radius', self.settings['radius'])
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
        
        # Handle angle wrap-around
        angle_range = end_rad - start_rad
        if angle_range < 0:
            angle_range += 2 * np.pi
        
        # Get full_span setting
        full_span = kwargs.get('full_span', self.settings.get('full_span', False))
        
        # Generate angles using distribution calculation
        angles = np.zeros(count)
        for i in range(count):
            t = self.calculate_distribution_t(i, count, full_span)
            angles[i] = start_rad + angle_range * t
        
        # Calculate positions (center at 0.5, 0.5)
        center_x, center_y = 0.5, 0.5
        positions = np.zeros((count, 5))
        
        for i, angle in enumerate(angles):
            # Position on circle
            x = center_x + radius * np.sin(angle)
            y = center_y - radius * np.cos(angle)
            
            # Scale
            if gradient_enabled:
                t = i / (count - 1) if count > 1 else 0.5
                scale = start_scale + t * (end_scale - start_scale)
            else:
                scale = uniform_scale
            
            # Rotation
            if rotation_mode == 'aligned':
                # Aligned: tangent to circle (perpendicular to radius)
                rotation = np.rad2deg(angle) + base_rotation
            else:
                # Global: all same rotation
                rotation = base_rotation
            
            positions[i] = [x, y, scale, scale, rotation]
        
        # Remove overlapping endpoints if first and last are too close
        positions = self.remove_overlapping_endpoints(positions)
        
        # Add label codes for text mode preview
        positions = self.add_label_codes(positions)
        
        return positions
