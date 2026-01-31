"""Base class for all layer generators.

Defines interface for generator implementations and provides helper methods
for building common UI controls.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import numpy as np
from PyQt5.QtWidgets import (QWidget, QLabel, QSlider, QSpinBox, QDoubleSpinBox,
                             QHBoxLayout, QVBoxLayout, QRadioButton, QButtonGroup,
                             QCheckBox, QComboBox, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal


class BaseGenerator(ABC):
    """Abstract base class for all pattern generators.
    
    Subclasses must implement:
    - get_title(): Return display title for popup
    - build_controls(): Create parameter UI widgets
    - generate_positions(): Calculate instance transforms
    """
    
    # Signal emitted when parameters change (for preview updates)
    parameters_changed = pyqtSignal()
    
    def __init__(self):
        """Initialize generator with default settings."""
        self.settings = {}  # Stores parameter values
        self._controls = {}  # Maps parameter names to widgets
        self._last_generated = None  # Cache last generation result
    
    def is_text_mode(self) -> bool:
        """Check if generator is in text mode.
        
        Returns:
            True if text mode is active
        """
        return self.settings.get('mode', 'count') == 'text'
    
    def get_text(self) -> str:
        """Get text input for text mode.
        
        Returns:
            Text string from input
        """
        return self.settings.get('text', '')
    
    def get_effective_count(self) -> int:
        """Get effective count, using text length in text mode.
        
        Returns:
            Count value (from count setting or text length)
        """
        if self.is_text_mode():
            from services.layer_generator.text_emblem_mapper import text_to_emblems
            text = self.get_text()
            emblems = text_to_emblems(text)
            return len(emblems)
        else:
            return self.settings.get('count', 1)
    
    @abstractmethod
    def get_title(self) -> str:
        """Return display title for generator popup.
        
        Returns:
            Title string to display in popup window
        """
        pass
    
    @abstractmethod
    def build_controls(self, parent: QWidget) -> QVBoxLayout:
        """Build parameter control widgets for this generator.
        
        Args:
            parent: Parent widget to attach controls to
            
        Returns:
            QVBoxLayout containing all parameter controls
        """
        pass
    
    @abstractmethod
    def generate_positions(self, **kwargs) -> np.ndarray:
        """Generate instance positions and transforms.
        
        Args:
            **kwargs: Generator-specific parameters
            
        Returns:
            5xN numpy array with format [[x, y, scale_x, scale_y, rotation], ...]
            where coordinates are in 0-1 CoA space
        """
        pass
    
    def get_settings(self) -> Dict[str, Any]:
        """Get current generator settings.
        
        Returns:
            Dictionary of parameter name -> value
        """
        return self.settings.copy()
    
    def set_settings(self, settings: Dict[str, Any]):
        """Restore generator settings.
        
        Args:
            settings: Dictionary of parameter name -> value
        """
        self.settings.update(settings)
        self._update_controls_from_settings()
    
    def add_label_codes(self, positions: np.ndarray) -> np.ndarray:
        """Add label codes (6th column) to positions array for text mode preview.
        
        Label codes:
        - 0 = regular preview (white square + red triangle)
        - -1 = space (bounding box only, no emblem)
        - 1-26 = letters a-z
        - 27 = alpha (α), 28 = omega (ω)
        
        Args:
            positions: 5xN array [[x, y, scale_x, scale_y, rotation], ...]
            
        Returns:
            6xN array with label codes appended
        """
        if not self.is_text_mode():
            # Not text mode: append zeros (no labels)
            label_codes = np.zeros((len(positions), 1))
            return np.hstack([positions, label_codes])
        
        # Text mode: map characters to label codes
        from services.layer_generator.text_emblem_mapper import text_to_label_codes
        text = self.get_text()
        label_codes = text_to_label_codes(text)
        
        # Ensure label_codes matches positions length
        if len(label_codes) < len(positions):
            # Pad with zeros
            label_codes = np.concatenate([label_codes, np.zeros(len(positions) - len(label_codes))])
        elif len(label_codes) > len(positions):
            # Truncate
            label_codes = label_codes[:len(positions)]
        
        # Append as 6th column
        label_codes = label_codes.reshape(-1, 1)
        return np.hstack([positions, label_codes])
    
    @staticmethod
    def remove_overlapping_endpoints(positions: np.ndarray, tolerance: float = 0.01) -> np.ndarray:
        """Remove last point if it overlaps with first point (closed paths).
        
        Args:
            positions: 5xN numpy array [[x, y, scale_x, scale_y, rotation], ...]
            tolerance: Distance threshold for considering points as overlapping
            
        Returns:
            Filtered array with last point removed if overlapping
        """
        if len(positions) < 2:
            return positions
        
        # Calculate distance between first and last points
        first_pos = positions[0, :2]  # [x, y]
        last_pos = positions[-1, :2]
        distance = np.linalg.norm(first_pos - last_pos)
        
        # If they're too close, drop the last one
        if distance < tolerance:
            return positions[:-1]
        
        return positions
    
    def _update_controls_from_settings(self):
        """Update UI controls to match current settings."""
        for param_name, widget in self._controls.items():
            if param_name not in self.settings:
                continue
            
            value = self.settings[param_name]
            
            if isinstance(widget, QSlider):
                widget.setValue(int(value * 100))  # Assume 0-1 range scaled to 0-100
            elif isinstance(widget, QSpinBox):
                widget.setValue(int(value))
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(value))
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
            elif isinstance(widget, QComboBox):
                idx = widget.findText(str(value))
                if idx >= 0:
                    widget.setCurrentIndex(idx)
            elif isinstance(widget, QRadioButton):
                widget.setChecked(bool(value))
    
    # Helper methods for building common UI controls
    
    def add_count_text_radio(self, layout: QVBoxLayout, default_mode: str = 'count',
                            default_count: int = 10) -> Dict[str, QWidget]:
        """Add Count/Text mode radio buttons with associated controls.
        
        Args:
            layout: Layout to add controls to
            default_mode: 'count' or 'text'
            default_count: Default count value
            
        Returns:
            Dict with keys: 'mode_group', 'count_radio', 'text_radio', 
                          'count_spin', 'text_input'
        """
        mode_label = QLabel("Mode:")
        layout.addWidget(mode_label)
        
        mode_group = QButtonGroup()
        count_radio = QRadioButton("Count")
        text_radio = QRadioButton("Text")
        mode_group.addButton(count_radio, 0)
        mode_group.addButton(text_radio, 1)
        
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(count_radio)
        radio_layout.addWidget(text_radio)
        layout.addLayout(radio_layout)
        
        # Count spinbox
        count_layout = QHBoxLayout()
        count_label = QLabel("Count:")
        count_spin = QSpinBox()
        count_spin.setRange(1, 100)
        count_spin.setValue(default_count)
        count_layout.addWidget(count_label)
        count_layout.addWidget(count_spin)
        layout.addLayout(count_layout)
        
        # Text input
        text_label = QLabel("Text (max 100 chars):")
        layout.addWidget(text_label)
        text_input = QTextEdit()
        text_input.setMaximumHeight(60)
        text_input.setPlaceholderText("Enter text here...")
        layout.addWidget(text_input)
        
        # Add text validation and filtering
        def on_text_changed():
            from services.layer_generator.text_emblem_mapper import filter_text
            current_text = text_input.toPlainText()
            filtered_text = filter_text(current_text)
            
            # Only update if text was filtered (to avoid infinite loop)
            if current_text != filtered_text:
                # Block signals to prevent recursive calls
                text_input.blockSignals(True)
                cursor_pos = text_input.textCursor().position()
                text_input.setPlainText(filtered_text)
                # Restore cursor position (or move to end if beyond filtered length)
                cursor = text_input.textCursor()
                cursor.setPosition(min(cursor_pos, len(filtered_text)))
                text_input.setTextCursor(cursor)
                text_input.blockSignals(False)
        
        text_input.textChanged.connect(on_text_changed)
        
        # Set initial mode
        if default_mode == 'count':
            count_radio.setChecked(True)
            text_input.setEnabled(False)
        else:
            text_radio.setChecked(True)
            count_spin.setEnabled(False)
        
        # Connect mode switching
        def on_mode_changed():
            is_count = count_radio.isChecked()
            count_spin.setEnabled(is_count)
            text_input.setEnabled(not is_count)
        
        count_radio.toggled.connect(on_mode_changed)
        
        self._controls['mode'] = mode_group
        self._controls['count'] = count_spin
        self._controls['text_input'] = text_input
        
        return {
            'mode_group': mode_group,
            'count_radio': count_radio,
            'text_radio': text_radio,
            'count_spin': count_spin,
            'text_input': text_input
        }
    
    def add_scale_controls(self, layout: QVBoxLayout, default_scale: float = 1.0,
                          enable_gradient: bool = False) -> Dict[str, QWidget]:
        """Add scale controls with optional gradient.
        
        Args:
            layout: Layout to add controls to
            default_scale: Default uniform scale value
            enable_gradient: Whether to enable separate start/end scales
            
        Returns:
            Dict with keys: 'gradient_check', 'uniform_scale', 'start_scale', 'end_scale'
        """
        gradient_check = QCheckBox("Enable scale gradient")
        gradient_check.setChecked(enable_gradient)
        layout.addWidget(gradient_check)
        
        # Uniform scale
        uniform_layout = QHBoxLayout()
        uniform_label = QLabel("Scale:")
        uniform_scale = QDoubleSpinBox()
        uniform_scale.setRange(0.01, 10.0)
        uniform_scale.setSingleStep(0.1)
        uniform_scale.setValue(default_scale)
        uniform_layout.addWidget(uniform_label)
        uniform_layout.addWidget(uniform_scale)
        layout.addLayout(uniform_layout)
        
        # Start scale
        start_layout = QHBoxLayout()
        start_label = QLabel("Start Scale:")
        start_scale = QDoubleSpinBox()
        start_scale.setRange(0.01, 10.0)
        start_scale.setSingleStep(0.1)
        start_scale.setValue(default_scale)
        start_layout.addWidget(start_label)
        start_layout.addWidget(start_scale)
        layout.addLayout(start_layout)
        
        # End scale
        end_layout = QHBoxLayout()
        end_label = QLabel("End Scale:")
        end_scale = QDoubleSpinBox()
        end_scale.setRange(0.01, 10.0)
        end_scale.setSingleStep(0.1)
        end_scale.setValue(default_scale)
        end_layout.addWidget(end_label)
        end_layout.addWidget(end_scale)
        layout.addLayout(end_layout)
        
        # Initially hide gradient controls
        start_label.setVisible(enable_gradient)
        start_scale.setVisible(enable_gradient)
        end_label.setVisible(enable_gradient)
        end_scale.setVisible(enable_gradient)
        uniform_label.setVisible(not enable_gradient)
        uniform_scale.setVisible(not enable_gradient)
        
        # Connect checkbox
        def on_gradient_toggled(checked):
            start_label.setVisible(checked)
            start_scale.setVisible(checked)
            end_label.setVisible(checked)
            end_scale.setVisible(checked)
            uniform_label.setVisible(not checked)
            uniform_scale.setVisible(not checked)
        
        gradient_check.toggled.connect(on_gradient_toggled)
        
        self._controls['gradient_enabled'] = gradient_check
        self._controls['uniform_scale'] = uniform_scale
        self._controls['start_scale'] = start_scale
        self._controls['end_scale'] = end_scale
        
        return {
            'gradient_check': gradient_check,
            'uniform_scale': uniform_scale,
            'start_scale': start_scale,
            'end_scale': end_scale
        }
    
    def add_rotation_controls(self, layout: QVBoxLayout, default_mode: str = 'global',
                             default_rotation: float = 0.0) -> Dict[str, QWidget]:
        """Add rotation mode and base rotation controls.
        
        Args:
            layout: Layout to add controls to
            default_mode: 'global' or 'aligned'
            default_rotation: Default base rotation in degrees
            
        Returns:
            Dict with keys: 'mode_combo', 'base_rotation'
        """
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Rotation Mode:")
        mode_combo = QComboBox()
        mode_combo.addItems(['global', 'aligned'])
        mode_combo.setCurrentText(default_mode)
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(mode_combo)
        layout.addLayout(mode_layout)
        
        rotation_layout = QHBoxLayout()
        rotation_label = QLabel("Base Rotation (°):")
        base_rotation = QDoubleSpinBox()
        base_rotation.setRange(0.0, 359.9)
        base_rotation.setSingleStep(1.0)
        base_rotation.setValue(default_rotation)
        rotation_layout.addWidget(rotation_label)
        rotation_layout.addWidget(base_rotation)
        layout.addLayout(rotation_layout)
        
        self._controls['rotation_mode'] = mode_combo
        self._controls['base_rotation'] = base_rotation
        
        return {
            'mode_combo': mode_combo,
            'base_rotation': base_rotation
        }
    
    def add_angle_controls(self, layout: QVBoxLayout, default_start: float = 0.0,
                          default_end: float = 360.0) -> Dict[str, QWidget]:
        """Add start/end angle controls.
        
        Args:
            layout: Layout to add controls to
            default_start: Default start angle in degrees
            default_end: Default end angle in degrees
            
        Returns:
            Dict with keys: 'start_angle', 'end_angle'
        """
        start_layout = QHBoxLayout()
        start_label = QLabel("Start Angle (°):")
        start_angle = QDoubleSpinBox()
        start_angle.setRange(0.0, 359.9)
        start_angle.setSingleStep(1.0)
        start_angle.setValue(default_start)
        start_layout.addWidget(start_label)
        start_layout.addWidget(start_angle)
        layout.addLayout(start_layout)
        
        end_layout = QHBoxLayout()
        end_label = QLabel("End Angle (°):")
        end_angle = QDoubleSpinBox()
        end_angle.setRange(0.0, 359.9)
        end_angle.setSingleStep(1.0)
        end_angle.setValue(default_end)
        end_layout.addWidget(end_label)
        end_layout.addWidget(end_angle)
        layout.addLayout(end_layout)
        
        self._controls['start_angle'] = start_angle
        self._controls['end_angle'] = end_angle
        
        return {
            'start_angle': start_angle,
            'end_angle': end_angle
        }
    
    def add_percent_controls(self, layout: QVBoxLayout, default_start: float = 0.0,
                            default_end: float = 100.0) -> Dict[str, QWidget]:
        """Add start/end percent controls (for path-based patterns).
        
        Args:
            layout: Layout to add controls to
            default_start: Default start percent (0-100)
            default_end: Default end percent (0-100)
            
        Returns:
            Dict with keys: 'start_percent', 'end_percent'
        """
        start_layout = QHBoxLayout()
        start_label = QLabel("Start Position (%):")
        start_percent = QDoubleSpinBox()
        start_percent.setRange(0.0, 100.0)
        start_percent.setSingleStep(1.0)
        start_percent.setValue(default_start)
        start_layout.addWidget(start_label)
        start_layout.addWidget(start_percent)
        layout.addLayout(start_layout)
        
        end_layout = QHBoxLayout()
        end_label = QLabel("End Position (%):")
        end_percent = QDoubleSpinBox()
        end_percent.setRange(0.0, 100.0)
        end_percent.setSingleStep(1.0)
        end_percent.setValue(default_end)
        end_layout.addWidget(end_label)
        end_layout.addWidget(end_percent)
        layout.addLayout(end_layout)
        
        self._controls['start_percent'] = start_percent
        self._controls['end_percent'] = end_percent
        
        return {
            'start_percent': start_percent,
            'end_percent': end_percent
        }
