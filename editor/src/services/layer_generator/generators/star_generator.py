"""Star path pattern generator - instances along star outline."""

import numpy as np
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QWidget
from ..base_generator import BaseGenerator


class StarGenerator(BaseGenerator):
    """Generate instances arranged along star outline."""
    
    # Default parameter values
    DEFAULT_POINTS = 5
    DEFAULT_RADIUS = 0.4
    DEFAULT_INNER_RADIUS_RATIO = 0.4
    DEFAULT_INSTANCES_PER_EDGE = 3
    DEFAULT_SCALE = 0.06
    
    def __init__(self):
        super().__init__()
        
        # Initialize default settings
        self.settings = {
            'points': self.DEFAULT_POINTS,
            'radius': self.DEFAULT_RADIUS,
            'inner_ratio': self.DEFAULT_INNER_RADIUS_RATIO,
            'instances_per_edge': self.DEFAULT_INSTANCES_PER_EDGE,
            'uniform_scale': self.DEFAULT_SCALE,
            'rotation_mode': 'global',
            'base_rotation': 0.0,
        }
    
    def get_title(self) -> str:
        """Return display title."""
        return "Star Path Pattern"
    
    def build_controls(self, parent: QWidget) -> QVBoxLayout:
        """Build parameter controls."""
        layout = QVBoxLayout()
        
        # Number of points
        points_layout = QHBoxLayout()
        points_label = QLabel("Star Points:")
        points_spin = QDoubleSpinBox()
        points_spin.setRange(3, 20)
        points_spin.setDecimals(0)
        points_spin.setValue(self.settings['points'])
        points_spin.valueChanged.connect(lambda v: self._on_param_changed('points', int(v)))
        points_layout.addWidget(points_label)
        points_layout.addWidget(points_spin)
        layout.addLayout(points_layout)
        
        self._controls['points'] = points_spin
        
        # Radius
        radius_layout = QHBoxLayout()
        radius_label = QLabel("Outer Radius:")
        radius_spin = QDoubleSpinBox()
        radius_spin.setRange(0.1, 0.5)
        radius_spin.setSingleStep(0.01)
        radius_spin.setValue(self.settings['radius'])
        radius_spin.valueChanged.connect(lambda v: self._on_param_changed('radius', v))
        radius_layout.addWidget(radius_label)
        radius_layout.addWidget(radius_spin)
        layout.addLayout(radius_layout)
        
        self._controls['radius'] = radius_spin
        
        # Inner radius ratio
        ratio_layout = QHBoxLayout()
        ratio_label = QLabel("Inner Radius Ratio:")
        ratio_spin = QDoubleSpinBox()
        ratio_spin.setRange(0.1, 0.9)
        ratio_spin.setSingleStep(0.05)
        ratio_spin.setValue(self.settings['inner_ratio'])
        ratio_spin.valueChanged.connect(lambda v: self._on_param_changed('inner_ratio', v))
        ratio_layout.addWidget(ratio_label)
        ratio_layout.addWidget(ratio_spin)
        layout.addLayout(ratio_layout)
        
        self._controls['inner_ratio'] = ratio_spin
        
        # Instances per edge
        instances_layout = QHBoxLayout()
        instances_label = QLabel("Instances per Edge:")
        instances_spin = QDoubleSpinBox()
        instances_spin.setRange(1, 10)
        instances_spin.setDecimals(0)
        instances_spin.setValue(self.settings['instances_per_edge'])
        instances_spin.valueChanged.connect(lambda v: self._on_param_changed('instances_per_edge', int(v)))
        instances_layout.addWidget(instances_label)
        instances_layout.addWidget(instances_spin)
        layout.addLayout(instances_layout)
        
        self._controls['instances_per_edge'] = instances_spin
        
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
        
        # Rotation controls
        rotation_controls = self.add_rotation_controls(
            layout,
            default_mode=self.settings['rotation_mode'],
            default_rotation=self.settings['base_rotation']
        )
        rotation_controls['mode_combo'].currentTextChanged.connect(
            lambda v: self._on_param_changed('rotation_mode', v))
        rotation_controls['base_rotation'].valueChanged.connect(
            lambda v: self._on_param_changed('base_rotation', float(v)))
        
        return layout
    
    def _on_param_changed(self, param_name: str, value):
        """Handle parameter value change."""
        self.settings[param_name] = value
        if self.on_parameter_changed:
            self.on_parameter_changed()
    
    def generate_positions(self, **kwargs) -> np.ndarray:
        """Generate star path arrangement.
        
        Creates a star outline with alternating outer and inner vertices,
        then places instances along the edges.
        
        Returns:
            5xN numpy array [[x, y, scale_x, scale_y, rotation], ...]
        """
        # Use settings as defaults, override with kwargs
        points = kwargs.get('points', self.settings['points'])
        radius = kwargs.get('radius', self.settings['radius'])
        inner_ratio = kwargs.get('inner_ratio', self.settings['inner_ratio'])
        instances_per_edge = kwargs.get('instances_per_edge', self.settings['instances_per_edge'])
        scale = kwargs.get('uniform_scale', self.settings['uniform_scale'])
        rotation_mode = kwargs.get('rotation_mode', self.settings['rotation_mode'])
        base_rotation = kwargs.get('base_rotation', self.settings['base_rotation'])
        
        if points < 3 or instances_per_edge < 1:
            return np.array([]).reshape(0, 5)
        
        # Center position
        center_x, center_y = 0.5, 0.5
        inner_radius = radius * inner_ratio
        
        # Generate star vertices (alternating outer and inner points)
        vertices = []
        for i in range(points * 2):
            angle = (i / (points * 2)) * 2 * np.pi - np.pi / 2  # Start at top
            r = radius if i % 2 == 0 else inner_radius
            
            x = center_x + r * np.cos(angle)
            y = center_y + r * np.sin(angle)
            vertices.append((x, y))
        
        # Generate instances along edges
        positions = []
        
        for i in range(len(vertices)):
            start_x, start_y = vertices[i]
            end_x, end_y = vertices[(i + 1) % len(vertices)]  # Wrap around to close star
            
            # Place instances along this edge (skip j==0 after first edge to avoid doubling corners)
            start_j = 0 if i == 0 else 1
            for j in range(start_j, instances_per_edge):
                if instances_per_edge == 1:
                    t = 0.5
                else:
                    t = j / (instances_per_edge - 1)
                
                x = start_x + t * (end_x - start_x)
                y = start_y + t * (end_y - start_y)
                
                # Calculate rotation
                if rotation_mode == 'aligned':
                    # Radial from center with offset
                    dx = x - center_x
                    dy = y - center_y
                    rotation = -np.rad2deg(np.arctan2(dx, dy)) + 180 + base_rotation
                else:
                    # Global rotation
                    rotation = base_rotation
                
                positions.append([x, y, scale, scale, rotation])
        
        return np.array(positions)
