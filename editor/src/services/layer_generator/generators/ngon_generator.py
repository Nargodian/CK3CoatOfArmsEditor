"""N-gon pattern generator - arranges instances along polygon perimeter."""

import numpy as np
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QDoubleSpinBox, QSlider, QWidget
from PyQt5.QtCore import Qt
from ..base_generator import BaseGenerator


class NgonGenerator(BaseGenerator):
    """Generate instances arranged along an N-sided polygon perimeter."""
    
    # Default parameter values
    DEFAULT_SIDES = 6
    DEFAULT_COUNT = 12
    DEFAULT_SCALE = 0.1
    DEFAULT_ROTATION_MODE = 'aligned'
    DEFAULT_BASE_ROTATION = 0.0
    DEFAULT_RADIUS = 0.35
    DEFAULT_MODE = 'count'
    DEFAULT_CORNER_FLAT = 0.01  # Small flat segment at each corner
    DEFAULT_ARC_BEND = 0.0  # Arc curvature for polygon edges
    
    def __init__(self):
        # Initialize default settings BEFORE calling super()
        # so cache restoration can update these defaults
        self.settings = {
            'mode': self.DEFAULT_MODE,
            'sides': self.DEFAULT_SIDES,
            'count': self.DEFAULT_COUNT,
            'text': '',
            'radius': self.DEFAULT_RADIUS,
            'corner_flat': self.DEFAULT_CORNER_FLAT,
            'gradient_enabled': False,
            'uniform_scale': self.DEFAULT_SCALE,
            'start_scale': self.DEFAULT_SCALE,
            'end_scale': self.DEFAULT_SCALE,
            'rotation_mode': self.DEFAULT_ROTATION_MODE,
            'base_rotation': self.DEFAULT_BASE_ROTATION,
            'arc_bend': self.DEFAULT_ARC_BEND,
        }
        
        super().__init__()
    
    def get_title(self) -> str:
        """Return display title."""
        return "N-gon Pattern"
    
    def build_controls(self, parent: QWidget) -> QVBoxLayout:
        """Build parameter controls."""
        layout = QVBoxLayout()
        
        # Number of sides control
        sides_layout = QHBoxLayout()
        sides_label = QLabel("Sides:")
        sides_spin = QSpinBox()
        sides_spin.setRange(3, 20)
        sides_spin.setValue(self.settings['sides'])
        sides_spin.setMaximumWidth(80)
        sides_spin.valueChanged.connect(lambda v: self._on_param_changed('sides', v))
        sides_layout.addWidget(sides_label)
        sides_layout.addWidget(sides_spin)
        sides_layout.addStretch()
        layout.addLayout(sides_layout)
        
        self._controls['sides'] = sides_spin
        
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
        
        # Radius control (manual - no helper method exists)
        radius_layout = QHBoxLayout()
        radius_label = QLabel("Radius:")
        radius_spin = QDoubleSpinBox()
        radius_spin.setRange(0.01, 1.0)
        radius_spin.setSingleStep(0.01)
        radius_spin.setValue(self.settings['radius'])
        radius_spin.valueChanged.connect(
            lambda v: self._on_param_changed('radius', v))
        radius_layout.addWidget(radius_label)
        radius_layout.addWidget(radius_spin)
        layout.addLayout(radius_layout)
        
        self._controls['radius'] = radius_spin
        
        # Arc bend parameter
        arc_layout = QHBoxLayout()
        arc_label = QLabel("Arc Bend:")
        arc_slider = QSlider(Qt.Horizontal)
        arc_slider.setRange(-100, 100)  # -1.0 to 1.0
        arc_slider.setValue(int(self.settings['arc_bend'] * 100))
        arc_spin = QDoubleSpinBox()
        arc_spin.setRange(-1.0, 1.0)
        arc_spin.setSingleStep(0.01)
        arc_spin.setDecimals(2)
        arc_spin.setValue(self.settings['arc_bend'])
        arc_spin.setMaximumWidth(80)
        arc_slider.valueChanged.connect(lambda v: arc_spin.setValue(v/100))
        arc_spin.valueChanged.connect(lambda v: arc_slider.setValue(int(v*100)))
        arc_slider.valueChanged.connect(lambda v: self._on_param_changed('arc_bend', v/100))
        arc_layout.addWidget(arc_label)
        arc_layout.addWidget(arc_slider)
        arc_layout.addWidget(arc_spin)
        layout.addLayout(arc_layout)
        
        self._controls['arc_bend'] = arc_slider
        
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
        if self.on_parameter_changed:
            self.on_parameter_changed()
    
    def _generate_arc_edge(self, v1, v2, arc_bend, num_segments=11):
        """Generate vertices for an arc between two points.
        
        Args:
            v1: Start vertex (x, y)
            v2: End vertex (x, y)
            arc_bend: Arc curvature amount (-1.0 to 1.0)
            num_segments: Number of line segments to approximate arc (use odd number for middle vertex)
            
        Returns:
            List of (x, y) tuples representing the arc
        """
        if abs(arc_bend) < 0.001:
            # No arc, just straight edge
            return [v1, v2]
        
        # Calculate arc midpoint offset perpendicular to edge
        edge_x = v2[0] - v1[0]
        edge_y = v2[1] - v1[1]
        edge_len = np.sqrt(edge_x**2 + edge_y**2)
        
        if edge_len < 0.0001:
            return [v1, v2]
        
        # Perpendicular direction (rotate 90° counterclockwise)
        perp_x = -edge_y / edge_len
        perp_y = edge_x / edge_len
        
        # Arc displacement at midpoint
        displacement = arc_bend * edge_len * 0.5
        
        # Generate arc points
        arc_points = []
        for i in range(num_segments + 1):
            t = i / num_segments
            # Linear interpolation along edge
            base_x = v1[0] + t * edge_x
            base_y = v1[1] + t * edge_y
            # Parabolic displacement (max at t=0.5)
            arc_amount = displacement * (1.0 - (2.0 * t - 1.0)**2)
            # Apply perpendicular offset
            x = base_x + perp_x * arc_amount
            y = base_y + perp_y * arc_amount
            arc_points.append((x, y))
        
        return arc_points
    
    def generate_positions(self, **kwargs) -> np.ndarray:
        """Generate N-gon arrangement of instances.
        
        Returns:
            5xN numpy array [[x, y, scale_x, scale_y, rotation], ...]
        """
        # Use settings as defaults, override with kwargs
        count = self.get_effective_count()
        sides = kwargs.get('sides', self.settings['sides'])
        radius = kwargs.get('radius', self.settings['radius'])
        gradient_enabled = kwargs.get('gradient_enabled', self.settings['gradient_enabled'])
        uniform_scale = kwargs.get('uniform_scale', self.settings['uniform_scale'])
        start_scale = kwargs.get('start_scale', self.settings['start_scale'])
        end_scale = kwargs.get('end_scale', self.settings['end_scale'])
        rotation_mode = kwargs.get('rotation_mode', self.settings['rotation_mode'])
        base_rotation = kwargs.get('base_rotation', self.settings['base_rotation'])
        corner_flat = kwargs.get('corner_flat', self.settings['corner_flat'])
        
        if count < 1:
            return np.array([]).reshape(0, 5)
        
        # Generate polygon vertices with flat corners
        # Each corner has 2 vertices: start and end of flat segment
        # Polygon sides between corners can optionally be arced
        # Start from top (angle = -π/2), go clockwise
        arc_bend = kwargs.get('arc_bend', self.settings['arc_bend'])
        
        # First generate corner vertices
        corner_vertices = []
        for i in range(sides):
            angle = -np.pi / 2 + (2 * np.pi * i / sides)
            
            # Vertex position
            vx = 0.5 + radius * np.cos(angle)
            vy = 0.5 + radius * np.sin(angle)
            
            # Radial direction (from center to vertex)
            radial_x = vx - 0.5
            radial_y = vy - 0.5
            radial_length = np.sqrt(radial_x**2 + radial_y**2)
            if radial_length > 0:
                radial_x /= radial_length
                radial_y /= radial_length
            
            # Perpendicular to radial (tangent to circle at this vertex)
            # Rotate 90 degrees counterclockwise: (x, y) -> (-y, x)
            perp_x = -radial_y
            perp_y = radial_x
            
            # Full corner: start point, then end point
            corner_start_x = vx - perp_x * corner_flat / 2
            corner_start_y = vy - perp_y * corner_flat / 2
            corner_end_x = vx + perp_x * corner_flat / 2
            corner_end_y = vy + perp_y * corner_flat / 2
            corner_vertices.append((corner_start_x, corner_start_y, corner_end_x, corner_end_y))
        
        # Build full vertex list: corner flats + arced polygon sides
        vertices = []
        for i in range(sides):
            # Add corner flat (start -> end)
            corner_start = (corner_vertices[i][0], corner_vertices[i][1])
            corner_end = (corner_vertices[i][2], corner_vertices[i][3])
            vertices.append(corner_start)
            vertices.append(corner_end)
            
            # Add polygon side edge (corner end -> next corner start)
            next_i = (i + 1) % sides
            next_corner_start = (corner_vertices[next_i][0], corner_vertices[next_i][1])
            
            # Generate arc for polygon side if arc_bend is non-zero
            if abs(arc_bend) > 0.001:
                arc_points = self._generate_arc_edge(corner_end, next_corner_start, arc_bend, num_segments=11)
                # Skip first point (it's already corner_end) to avoid duplicate
                for pt in arc_points[1:]:
                    vertices.append(pt)
            else:
                # No arc, just add next corner start
                # (creates straight edge from corner_end to next_corner_start)
                pass  # Next iteration will add next_corner_start
        
        # Calculate total perimeter
        total_length = 0
        edge_lengths = []
        for i in range(len(vertices)):
            v1 = vertices[i]
            v2 = vertices[(i + 1) % len(vertices)]
            edge_len = np.sqrt((v2[0] - v1[0])**2 + (v2[1] - v1[1])**2)
            edge_lengths.append(edge_len)
            total_length += edge_len
        
        # Offset starting position by half the first edge (to center first emblem on first flat)
        start_offset = edge_lengths[0] / 2.0
        
        # Distribute instances along perimeter
        positions = np.zeros((count, 5))
        
        for i in range(count):
            # Calculate distance along perimeter for this instance
            if count == 1:
                t = 0.5
            else:
                t = i / count
            
            # Apply offset to center emblems on flats
            target_dist = (start_offset + t * total_length) % total_length
            
            # Find which edge we're on
            cumulative_dist = 0
            edge_idx = 0
            for j, edge_len in enumerate(edge_lengths):
                if cumulative_dist + edge_len >= target_dist:
                    edge_idx = j
                    break
                cumulative_dist += edge_len
            
            # Position along this edge
            dist_along_edge = target_dist - cumulative_dist
            edge_t = dist_along_edge / edge_lengths[edge_idx] if edge_lengths[edge_idx] > 0 else 0
            
            # Interpolate position
            v1 = vertices[edge_idx]
            v2 = vertices[(edge_idx + 1) % len(vertices)]
            x = v1[0] + edge_t * (v2[0] - v1[0])
            y = v1[1] + edge_t * (v2[1] - v1[1])
            
            # Calculate edge angle for aligned rotation
            edge_angle = np.arctan2(v2[1] - v1[1], v2[0] - v1[0])
            
            # Scale
            if gradient_enabled:
                scale = start_scale + t * (end_scale - start_scale)
            else:
                scale = uniform_scale
            
            # Rotation
            if rotation_mode == 'aligned':
                # Perpendicular to edge (pointing outward from polygon)
                rotation = np.rad2deg(edge_angle) + base_rotation
            else:
                # Global: all same rotation
                rotation = base_rotation
            
            positions[i] = [x, y, scale, scale, rotation]
        
        # Add label codes for text mode preview
        positions = self.add_label_codes(positions)
        
        return positions
