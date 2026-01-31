"""Radial pattern generator - rays emanating from center."""

import numpy as np
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QWidget
from ..base_generator import BaseGenerator


class RadialGenerator(BaseGenerator):
    """Generate instances in radial pattern (rays from center)."""
    
    # Default parameter values
    DEFAULT_COUNT = 8
    DEFAULT_MIN_RADIUS = 0.1
    DEFAULT_MAX_RADIUS = 0.45
    DEFAULT_INSTANCES_PER_RAY = 3
    DEFAULT_SCALE = 0.06
    
    def __init__(self):
        super().__init__()
        
        # Initialize default settings
        self.settings = {
            'count': self.DEFAULT_COUNT,  # Number of rays
            'min_radius': self.DEFAULT_MIN_RADIUS,
            'max_radius': self.DEFAULT_MAX_RADIUS,
            'instances_per_ray': self.DEFAULT_INSTANCES_PER_RAY,
            'uniform_scale': self.DEFAULT_SCALE,
        }
    
    def get_title(self) -> str:
        """Return display title."""
        return "Radial Pattern"
    
    def build_controls(self, parent: QWidget) -> QVBoxLayout:
        """Build parameter controls."""
        layout = QVBoxLayout()
        
        # Ray count
        count_layout = QHBoxLayout()
        count_label = QLabel("Number of Rays:")
        count_spin = QDoubleSpinBox()
        count_spin.setRange(1, 36)
        count_spin.setDecimals(0)
        count_spin.setValue(self.settings['count'])
        count_spin.valueChanged.connect(lambda v: self._on_param_changed('count', int(v)))
        count_layout.addWidget(count_label)
        count_layout.addWidget(count_spin)
        layout.addLayout(count_layout)
        
        self._controls['count'] = count_spin
        
        # Instances per ray
        instances_layout = QHBoxLayout()
        instances_label = QLabel("Instances per Ray:")
        instances_spin = QDoubleSpinBox()
        instances_spin.setRange(1, 20)
        instances_spin.setDecimals(0)
        instances_spin.setValue(self.settings['instances_per_ray'])
        instances_spin.valueChanged.connect(lambda v: self._on_param_changed('instances_per_ray', int(v)))
        instances_layout.addWidget(instances_label)
        instances_layout.addWidget(instances_spin)
        layout.addLayout(instances_layout)
        
        self._controls['instances_per_ray'] = instances_spin
        
        # Min radius
        min_radius_layout = QHBoxLayout()
        min_radius_label = QLabel("Min Radius:")
        min_radius_spin = QDoubleSpinBox()
        min_radius_spin.setRange(0.0, 1.0)
        min_radius_spin.setSingleStep(0.01)
        min_radius_spin.setValue(self.settings['min_radius'])
        min_radius_spin.valueChanged.connect(lambda v: self._on_param_changed('min_radius', v))
        min_radius_layout.addWidget(min_radius_label)
        min_radius_layout.addWidget(min_radius_spin)
        layout.addLayout(min_radius_layout)
        
        self._controls['min_radius'] = min_radius_spin
        
        # Max radius
        max_radius_layout = QHBoxLayout()
        max_radius_label = QLabel("Max Radius:")
        max_radius_spin = QDoubleSpinBox()
        max_radius_spin.setRange(0.0, 1.0)
        max_radius_spin.setSingleStep(0.01)
        max_radius_spin.setValue(self.settings['max_radius'])
        max_radius_spin.valueChanged.connect(lambda v: self._on_param_changed('max_radius', v))
        max_radius_layout.addWidget(max_radius_label)
        max_radius_layout.addWidget(max_radius_spin)
        layout.addLayout(max_radius_layout)
        
        self._controls['max_radius'] = max_radius_spin
        
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
        
        return layout
    
    def _on_param_changed(self, param_name: str, value):
        """Handle parameter value change."""
        self.settings[param_name] = value
        if self.on_parameter_changed:
            self.on_parameter_changed()
    
    def generate_positions(self, **kwargs) -> np.ndarray:
        """Generate radial arrangement (rays from center).
        
        Returns:
            5xN numpy array [[x, y, scale_x, scale_y, rotation], ...]
        """
        # Use settings as defaults, override with kwargs
        ray_count = kwargs.get('count', self.settings['count'])
        instances_per_ray = kwargs.get('instances_per_ray', self.settings['instances_per_ray'])
        min_radius = kwargs.get('min_radius', self.settings['min_radius'])
        max_radius = kwargs.get('max_radius', self.settings['max_radius'])
        scale = kwargs.get('uniform_scale', self.settings['uniform_scale'])
        
        if ray_count < 1 or instances_per_ray < 1:
            return np.array([]).reshape(0, 5)
        
        total_count = ray_count * instances_per_ray
        positions = []
        
        # Center position
        center_x, center_y = 0.5, 0.5
        
        # Calculate ray angles (evenly distributed)
        for ray_idx in range(ray_count):
            angle = (ray_idx / ray_count) * 2 * np.pi
            
            # Place instances along this ray
            for inst_idx in range(instances_per_ray):
                # Interpolate radius
                if instances_per_ray == 1:
                    t = 0.5
                else:
                    t = inst_idx / (instances_per_ray - 1)
                
                radius = min_radius + t * (max_radius - min_radius)
                
                # Calculate position
                x = center_x + radius * np.sin(angle)
                y = center_y + radius * np.cos(angle)
                
                # Rotation aligned with ray direction
                rotation = np.rad2deg(angle)
                
                positions.append([x, y, scale, scale, rotation])
        
        return np.array(positions)
