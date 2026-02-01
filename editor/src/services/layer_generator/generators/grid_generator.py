"""Grid pattern generator - arranges instances in rows and columns."""

import numpy as np
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QWidget
from ..base_generator import BaseGenerator


class GridGenerator(BaseGenerator):
    """Generate instances arranged in a grid pattern."""
    
    # Default parameter values
    DEFAULT_ROWS = 5
    DEFAULT_COLUMNS = 5
    DEFAULT_SCALE = 0.08
    DEFAULT_INSET = 0.02  # Fixed constant - padding from edges
    
    def __init__(self):
        super().__init__()
        
        # Initialize default settings
        self.settings = {
            'rows': self.DEFAULT_ROWS,
            'columns': self.DEFAULT_COLUMNS,
            'uniform_scale': self.DEFAULT_SCALE,
        }
    
    def get_title(self) -> str:
        """Return display title."""
        return "Grid Pattern"
    
    def build_controls(self, parent: QWidget) -> QVBoxLayout:
        """Build parameter controls."""
        layout = QVBoxLayout()
        
        # Rows parameter
        rows_layout = QHBoxLayout()
        rows_label = QLabel("Rows:")
        rows_spin = QDoubleSpinBox()
        rows_spin.setRange(1, 20)
        rows_spin.setDecimals(0)
        rows_spin.setValue(self.settings['rows'])
        rows_spin.valueChanged.connect(lambda v: self._on_param_changed('rows', int(v)))
        rows_layout.addWidget(rows_label)
        rows_layout.addWidget(rows_spin)
        layout.addLayout(rows_layout)
        
        self._controls['rows'] = rows_spin
        
        # Columns parameter
        columns_layout = QHBoxLayout()
        columns_label = QLabel("Columns:")
        columns_spin = QDoubleSpinBox()
        columns_spin.setRange(1, 20)
        columns_spin.setDecimals(0)
        columns_spin.setValue(self.settings['columns'])
        columns_spin.valueChanged.connect(lambda v: self._on_param_changed('columns', int(v)))
        columns_layout.addWidget(columns_label)
        columns_layout.addWidget(columns_spin)
        layout.addLayout(columns_layout)
        
        self._controls['columns'] = columns_spin
        
        # Scale control (uniform only for grid)
        scale_layout = QHBoxLayout()
        scale_label = QLabel("Scale:")
        scale_spin = QDoubleSpinBox()
        scale_spin.setRange(0.01, 1.0)
        scale_spin.setSingleStep(0.01)
        scale_spin.setValue(self.settings['uniform_scale'])
        scale_spin.valueChanged.connect(lambda v: self._on_param_changed('uniform_scale', v))
        scale_layout.addWidget(scale_label)
        scale_layout.addWidget(scale_spin)
        layout.addLayout(scale_layout)
        
        self._controls['uniform_scale'] = scale_spin
        
        # Info note
        note = QLabel("Note: Grid fills 0-1 space. Use transform tools to resize after generation.")
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
        """Generate grid arrangement of instances.
        
        Returns:
            5xN numpy array [[x, y, scale_x, scale_y, rotation], ...]
        """
        # Use settings as defaults, override with kwargs
        rows = kwargs.get('rows', self.settings['rows'])
        columns = kwargs.get('columns', self.settings['columns'])
        scale = kwargs.get('uniform_scale', self.settings['uniform_scale'])
        
        if rows < 1 or columns < 1:
            return np.array([]).reshape(0, 5)
        
        count = rows * columns
        positions = np.zeros((count, 5))
        
        # Calculate spacing with inset (fill INSET to 1-INSET space)
        usable_range = 1.0 - 2 * self.DEFAULT_INSET
        
        if columns == 1:
            x_spacing = 0
            x_start = 0.5
        else:
            x_spacing = usable_range / (columns - 1)
            x_start = self.DEFAULT_INSET
        
        if rows == 1:
            y_spacing = 0
            y_start = 0.5
        else:
            y_spacing = usable_range / (rows - 1)
            y_start = self.DEFAULT_INSET
        
        # Generate grid positions
        idx = 0
        for row in range(rows):
            for col in range(columns):
                x = x_start + col * x_spacing
                y = y_start + row * y_spacing
                
                positions[idx] = [x, y, scale, scale, 0.0]
                idx += 1
        
        return positions
