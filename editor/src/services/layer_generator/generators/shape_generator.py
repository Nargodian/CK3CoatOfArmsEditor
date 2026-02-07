"""Shape pattern generator - arranges instances along SVG shape paths."""

import numpy as np
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QWidget, QComboBox
from ..base_generator import BaseGenerator
from ..path_sampler import PathSampler
import os


class ShapeGenerator(BaseGenerator):
    """Generate instances arranged along an SVG shape path.
    
    Single generator class that handles all SVG shapes. Path data is swapped
    based on selected shape from dropdown.
    """
    
    # Default parameter values
    DEFAULT_COUNT = 20
    DEFAULT_START_PERCENT = 0.0
    DEFAULT_END_PERCENT = 100.0
    DEFAULT_SCALE = 0.08
    DEFAULT_ROTATION_MODE = 'aligned'
    DEFAULT_BASE_ROTATION = 0.0
    DEFAULT_INSET = 0.02  # Fixed constant
    DEFAULT_MODE = 'count'
    
    # Class-level storage for preloaded shapes
    _loaded_shapes = {}  # Dict[shape_name, PathSampler]
    _shape_names = []  # List of available shape names
    
    @classmethod
    def preload_shapes(cls, svg_directory: str):
        """Preload all SVG shapes from directory at application startup.
        
        Args:
            svg_directory: Path to directory containing .svg files
        """
        cls._loaded_shapes.clear()
        cls._shape_names.clear()
        
        if not os.path.exists(svg_directory):
            print(f"Warning: SVG directory not found: {svg_directory}")
            return
        
        for filename in os.listdir(svg_directory):
            if not filename.endswith('.svg'):
                continue
            
            shape_name = os.path.splitext(filename)[0]
            filepath = os.path.join(svg_directory, filename)
            
            try:
                path_sampler = PathSampler(filepath)
                cls._loaded_shapes[shape_name] = path_sampler
                cls._shape_names.append(shape_name)
                print(f"Loaded shape: {shape_name}")
            except Exception as e:
                print(f"Warning: Failed to load shape {shape_name}: {e}")
                # Skip this shape - continue loading others
        
        cls._shape_names.sort()
    
    @classmethod
    def get_shape_names(cls):
        """Get list of available shape names."""
        return cls._shape_names.copy()
    
    def __init__(self, initial_shape: str = None):
        """Initialize shape generator.
        
        Args:
            initial_shape: Name of shape to use (without .svg extension).
                          If None, uses first available shape.
        """
        # Select initial shape BEFORE super() and settings
        if initial_shape and initial_shape in self._loaded_shapes:
            self.current_shape = initial_shape
        elif self._shape_names:
            self.current_shape = self._shape_names[0]
        else:
            self.current_shape = None
            print("Warning: No shapes available")
        
        # Initialize default settings BEFORE calling super()
        # so cache restoration can update these defaults
        self.settings = {
            'shape_name': self.current_shape,
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
        }
        
        super().__init__()
    
    def get_title(self) -> str:
        """Return display title."""
        if self.current_shape:
            return f"Shape Pattern - {self.current_shape}"
        return "Shape Pattern"
    
    def set_shape(self, shape_name: str):
        """Switch to a different shape.
        
        Args:
            shape_name: Name of shape to use
        """
        if shape_name in self._loaded_shapes:
            self.current_shape = shape_name
            self.settings['shape_name'] = shape_name
    
    def build_controls(self, parent: QWidget) -> QVBoxLayout:
        """Build parameter controls."""
        layout = QVBoxLayout()
        
        # Shape selector dropdown
        shape_layout = QHBoxLayout()
        shape_label = QLabel("Shape:")
        shape_combo = QComboBox()
        shape_combo.addItems(self._shape_names)
        if self.current_shape:
            shape_combo.setCurrentText(self.current_shape)
        shape_combo.currentTextChanged.connect(self._on_shape_changed)
        shape_layout.addWidget(shape_label)
        shape_layout.addWidget(shape_combo)
        layout.addLayout(shape_layout)
        
        self._controls['shape'] = shape_combo
        
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
        
        # Percent controls (portion of path)
        percent_controls = self.add_percent_controls(
            layout,
            default_start=self.settings['start_percent'],
            default_end=self.settings['end_percent']
        )
        percent_controls['start_percent'].valueChanged.connect(
            lambda v: self._on_param_changed('start_percent', v))
        percent_controls['end_percent'].valueChanged.connect(
            lambda v: self._on_param_changed('end_percent', v))
        
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
    
    def _on_shape_changed(self, shape_name: str):
        """Handle shape selection change."""
        self.set_shape(shape_name)
        # Update title would happen here if we had access to popup
        # For now, settings are updated
    
    def _on_param_changed(self, param_name: str, value):
        """Handle parameter value change."""
        self.settings[param_name] = value
        if self.on_parameter_changed:
            self.on_parameter_changed()
    
    def generate_positions(self, **kwargs) -> np.ndarray:
        """Generate shape path arrangement of instances.
        
        Returns:
            5xN numpy array [[x, y, scale_x, scale_y, rotation], ...]
        """
        # Check if we have a valid shape
        if not self.current_shape or self.current_shape not in self._loaded_shapes:
            return np.array([]).reshape(0, 5)
        
        # Get path sampler for current shape
        path_sampler = self._loaded_shapes[self.current_shape]
        
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
        
        if count < 1:
            return np.array([]).reshape(0, 5)
        
        # Sample points along path
        sampled_points = path_sampler.sample_points(count, start_percent, end_percent)
        
        positions = np.zeros((count, 5))
        
        for i, (x_path, y_path, tangent_angle) in enumerate(sampled_points):
            # Apply inset (move from -0.5..0.5 to slightly smaller range)
            x_scaled = x_path * (1.0 - 2 * self.DEFAULT_INSET)
            y_scaled = y_path * (1.0 - 2 * self.DEFAULT_INSET)
            
            # Transform from -0.5..0.5 to 0..1 (CoA coordinate space)
            x = 0.5 + x_scaled
            y = 0.5 + y_scaled
            
            # Scale
            if gradient_enabled:
                t = i / (count - 1) if count > 1 else 0.5
                scale = start_scale + t * (end_scale - start_scale)
            else:
                scale = uniform_scale
            
            # Rotation
            if rotation_mode == 'aligned':
                # Aligned: perpendicular to path (tangent + 90°)
                rotation = -(tangent_angle + 90) + 180 + base_rotation
            else:
                # Global: all same rotation
                rotation = base_rotation
            
            positions[i] = [x, y, scale, scale, rotation]
        
        # Remove overlapping endpoints for closed shapes
        positions = self.remove_overlapping_endpoints(positions)
        
        # Add label codes for text mode preview
        positions = self.add_label_codes(positions)
        
        return positions
