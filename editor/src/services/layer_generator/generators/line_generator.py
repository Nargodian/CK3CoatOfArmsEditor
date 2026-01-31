"""Line pattern generator - arranges instances along a straight line."""

import numpy as np
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QWidget
from ..base_generator import BaseGenerator


class LineGenerator(BaseGenerator):
    """Generate instances arranged in a line."""
    
    # Default parameter values
    DEFAULT_COUNT = 5
    DEFAULT_SCALE = 0.1
    DEFAULT_START_PERCENT = 0.0
    DEFAULT_END_PERCENT = 100.0
    DEFAULT_ROTATION_MODE = 'global'
    DEFAULT_BASE_ROTATION = 0.0
    DEFAULT_ARC_BEND = 0.0
    DEFAULT_MODE = 'count'
    
    def __init__(self):
        super().__init__()
        
        # Initialize default settings
        self.settings = {
            'mode': self.DEFAULT_MODE,
            'count': self.DEFAULT_COUNT,
            'text': '',
            'start_percent': self.DEFAULT_START_PERCENT,
            'end_percent': self.DEFAULT_END_PERCENT,
            'gradient_enabled': False,
            'uniform_scale': self.DEFAULT_SCALE,
            'start_scale': self.DEFAULT_SCALE,
            'end_scale': self.DEFAULT_SCALE,
            'rotation_mode': self.DEFAULT_ROTATION_MODE,
            'base_rotation': self.DEFAULT_BASE_ROTATION,
            'arc_bend': self.DEFAULT_ARC_BEND,
        }
    
    def get_title(self) -> str:
        """Return display title."""
        return "Line Pattern"
    
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
        
        # Percent controls (defines line extent along horizontal)
        percent_controls = self.add_percent_controls(
            layout,
            default_start=self.settings['start_percent'],
            default_end=self.settings['end_percent']
        )
        percent_controls['start_percent'].valueChanged.connect(
            lambda v: self._on_param_changed('start_percent', v))
        percent_controls['end_percent'].valueChanged.connect(
            lambda v: self._on_param_changed('end_percent', v))
        
        # Arc bend parameter
        arc_layout = QHBoxLayout()
        arc_label = QLabel("Arc Bend:")
        arc_spin = QDoubleSpinBox()
        arc_spin.setRange(-1.0, 1.0)
        arc_spin.setSingleStep(0.05)
        arc_spin.setDecimals(2)
        arc_spin.setValue(self.settings['arc_bend'])
        arc_spin.valueChanged.connect(lambda v: self._on_param_changed('arc_bend', v))
        arc_layout.addWidget(arc_label)
        arc_layout.addWidget(arc_spin)
        layout.addLayout(arc_layout)
        
        self._controls['arc_bend'] = arc_spin
        
        # Add explanation
        explanation = QLabel("Note: Arc bend curves the line (±1 = semicircle). Line runs left-to-right along x-axis.")
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
        # In text mode, use text length instead of count
        count = self.get_effective_count()
        
        start_percent = kwargs.get('start_percent', self.settings['start_percent'])
        end_percent = kwargs.get('end_percent', self.settings['end_percent'])
        gradient_enabled = kwargs.get('gradient_enabled', self.settings['gradient_enabled'])
        uniform_scale = kwargs.get('uniform_scale', self.settings['uniform_scale'])
        start_scale = kwargs.get('start_scale', self.settings['start_scale'])
        end_scale = kwargs.get('end_scale', self.settings['end_scale'])
        rotation_mode = kwargs.get('rotation_mode', self.settings['rotation_mode'])
        base_rotation = kwargs.get('base_rotation', self.settings['base_rotation'])
        arc_bend = kwargs.get('arc_bend', self.settings['arc_bend'])
        
        if count < 1:
            return np.array([]).reshape(0, 5)
        
        # Convert percent to normalized range (0-1)
        start_t = start_percent / 100.0
        end_t = end_percent / 100.0
        
        # Line runs horizontally across x-axis
        # x: 0.1 to 0.9 (leave margins)
        # y: 0.5 (center)
        margin = 0.1
        line_length = 1.0 - 2 * margin
        
        # Generate positions
        positions = np.zeros((count, 5))
        
        for i in range(count):
            # Interpolate along line extent
            if count == 1:
                t = (start_t + end_t) / 2.0
            else:
                t = start_t + (i / (count - 1)) * (end_t - start_t)
            
            # Base position on horizontal line
            x = margin + t * line_length
            y = 0.5
            tangent_angle = 0.0  # Default for straight line
            
            # Apply arc bend if non-zero
            if abs(arc_bend) > 0.001:
                # Arc bend creates a circular arc
                # Positive bend: arc upward (decrease y)
                # Negative bend: arc downward (increase y)
                # ±1 = semicircle (π radians)
                
                # Calculate radius for semicircle at bend=±1
                # When bend=1, the line becomes a semicircle
                # Arc length = π * radius for semicircle
                # We want the arc to span the same horizontal distance as the line
                span = (end_t - start_t) * line_length
                if span > 0:
                    radius = span / (np.pi * abs(arc_bend))
                else:
                    radius = line_length / (np.pi * abs(arc_bend))
                
                # Arc center
                center_x = 0.5
                center_y = 0.5 + (radius if arc_bend > 0 else -radius)
                
                # Calculate angle for this position along arc
                # Map t from start_t to end_t to angle from -π/2 to +π/2
                if abs(end_t - start_t) > 0.001:
                    normalized_t = (t - start_t) / (end_t - start_t)
                else:
                    normalized_t = 0.5
                
                # Angle sweeps from left to right
                angle = (normalized_t - 0.5) * np.pi * arc_bend
                
                # Calculate position
                x = center_x + radius * np.sin(angle)
                y = center_y - radius * np.cos(angle) * (1 if arc_bend > 0 else -1)
                
                # Calculate tangent angle (perpendicular to radius)
                tangent_angle = angle
            
            # Scale
            if gradient_enabled:
                local_t = (t - start_t) / (end_t - start_t) if (end_t - start_t) > 0 else 0
                scale = start_scale + local_t * (end_scale - start_scale)
            else:
                scale = uniform_scale
            
            # Rotation
            if rotation_mode == 'aligned':
                # Aligned: follow tangent direction
                if abs(arc_bend) > 0.001:
                    # Tangent is perpendicular to radius (90° clockwise)
                    # For bearing system: add 90° to get tangent direction
                    rotation = np.rad2deg(tangent_angle + np.pi / 2) + base_rotation
                else:
                    # Horizontal line: 90° (pointing right)
                    rotation = 90.0 + base_rotation
            else:
                # Global: all same rotation
                rotation = base_rotation
            
            positions[i] = [x, y, scale, scale, rotation]
        
        # Add label codes for text mode preview
        positions = self.add_label_codes(positions)
        
        return positions
