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
    
    # Class-level settings cache (persists across instances)
    _settings_cache = {}
    
    def __init__(self):
        """Initialize generator with default settings."""
        # Only initialize settings if subclass hasn't already (for backwards compat)
        if not hasattr(self, 'settings'):
            self.settings = {}  # Stores parameter values
        self._controls = {}  # Maps parameter names to widgets
        self._last_generated = None  # Cache last generation result
        
        # Restore cached settings for this generator type if available
        # This updates the defaults set by subclass with cached values
        cache_key = self.__class__.__name__
        if cache_key in BaseGenerator._settings_cache:
            self.settings.update(BaseGenerator._settings_cache[cache_key])
    
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
            Count value (from count setting or text length including spaces)
        """
        if self.is_text_mode():
            from services.layer_generator.text_emblem_mapper import text_to_label_codes
            text = self.get_text()
            label_codes = text_to_label_codes(text)
            return len(label_codes)  # Includes spaces
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
    
    def save_settings_to_cache(self):
        """Save current settings to class-level cache for persistence."""
        cache_key = self.__class__.__name__
        BaseGenerator._settings_cache[cache_key] = self.settings.copy()
    
    def calculate_distribution_t(self, index: int, count: int, full_span: bool = False) -> float:
        """Calculate normalized parameter t for distributing items.
        
        Args:
            index: Item index (0 to count-1)
            count: Total number of items
            full_span: If True, use edge-to-edge distribution (0 to 1)
                      If False, use centered distribution with margins
        
        Returns:
            Normalized t value (0 to 1)
        """
        if count <= 1:
            return 0.5
        
        if full_span:
            # Full span: includes both endpoints (0 and 1)
            return index / (count - 1)
        else:
            # Staggered: excludes endpoint at 1
            return index / count
    
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
                            default_count: int = 10, enable_full_span: bool = False,
                            default_full_span: bool = False) -> Dict[str, QWidget]:
        """Add Count/Text mode radio buttons with associated controls.
        
        Args:
            layout: Layout to add controls to
            default_mode: 'count' or 'text'
            default_count: Default count value
            enable_full_span: If True, show Full Span checkbox
            default_full_span: Default Full Span state
            
        Returns:
            Dict with keys: 'mode_group', 'count_radio', 'text_radio', 
                          'count_spin', 'text_input', 'full_span_check' (if enabled)
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
        
        # Full Span checkbox (optional)
        full_span_check = None
        if enable_full_span:
            full_span_check = QCheckBox("Full Span")
            full_span_check.setChecked(default_full_span)
            full_span_check.setToolTip(
                "Full Span: Distribute evenly across entire range (edge to edge)\\n"
                "Unchecked: Center distribution within bounds (leaves margins)"
            )
            layout.addWidget(full_span_check)
            self._controls['full_span'] = full_span_check
        
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
            count_label.setVisible(True)
            count_spin.setVisible(True)
            text_label.setVisible(False)
            text_input.setVisible(False)
        else:
            text_radio.setChecked(True)
            count_label.setVisible(False)
            count_spin.setVisible(False)
            text_label.setVisible(True)
            text_input.setVisible(True)
        
        # Connect mode switching
        def on_mode_changed():
            is_count = count_radio.isChecked()
            count_label.setVisible(is_count)
            count_spin.setVisible(is_count)
            text_label.setVisible(not is_count)
            text_input.setVisible(not is_count)
        
        count_radio.toggled.connect(on_mode_changed)
        
        self._controls['mode'] = mode_group
        self._controls['count'] = count_spin
        self._controls['text_input'] = text_input
        
        result = {
            'mode_group': mode_group,
            'count_radio': count_radio,
            'text_radio': text_radio,
            'count_spin': count_spin,
            'text_input': text_input
        }
        if full_span_check:
            result['full_span_check'] = full_span_check
        
        return result
    
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
        uniform_scale = QSlider(Qt.Horizontal)
        uniform_scale.setRange(1, 100)  # 0.01 to 1.0 (multiply by 100)
        uniform_scale.setValue(int(default_scale * 100))
        uniform_spin = QDoubleSpinBox()
        uniform_spin.setRange(0.01, 1.0)
        uniform_spin.setSingleStep(0.01)
        uniform_spin.setValue(default_scale)
        uniform_spin.setMaximumWidth(80)
        uniform_scale.valueChanged.connect(lambda v: uniform_spin.setValue(v/100))
        uniform_spin.valueChanged.connect(lambda v: uniform_scale.setValue(int(v*100)))
        uniform_layout.addWidget(uniform_label)
        uniform_layout.addWidget(uniform_scale)
        uniform_layout.addWidget(uniform_spin)
        layout.addLayout(uniform_layout)
        
        # Start scale
        start_layout = QHBoxLayout()
        start_label = QLabel("Start Scale:")
        start_scale = QSlider(Qt.Horizontal)
        start_scale.setRange(1, 100)
        start_scale.setValue(int(default_scale * 100))
        start_spin = QDoubleSpinBox()
        start_spin.setRange(0.01, 1.0)
        start_spin.setSingleStep(0.01)
        start_spin.setValue(default_scale)
        start_spin.setMaximumWidth(80)
        start_scale.valueChanged.connect(lambda v: start_spin.setValue(v/100))
        start_spin.valueChanged.connect(lambda v: start_scale.setValue(int(v*100)))
        start_layout.addWidget(start_label)
        start_layout.addWidget(start_scale)
        start_layout.addWidget(start_spin)
        layout.addLayout(start_layout)
        
        # End scale
        end_layout = QHBoxLayout()
        end_label = QLabel("End Scale:")
        end_scale = QSlider(Qt.Horizontal)
        end_scale.setRange(1, 100)
        end_scale.setValue(int(default_scale * 100))
        end_spin = QDoubleSpinBox()
        end_spin.setRange(0.01, 1.0)
        end_spin.setSingleStep(0.01)
        end_spin.setValue(default_scale)
        end_spin.setMaximumWidth(80)
        end_scale.valueChanged.connect(lambda v: end_spin.setValue(v/100))
        end_spin.valueChanged.connect(lambda v: end_scale.setValue(int(v*100)))
        end_layout.addWidget(end_label)
        end_layout.addWidget(end_scale)
        end_layout.addWidget(end_spin)
        layout.addLayout(end_layout)
        
        # Initially hide gradient controls
        start_label.setVisible(enable_gradient)
        start_scale.setVisible(enable_gradient)
        start_spin.setVisible(enable_gradient)
        end_label.setVisible(enable_gradient)
        end_scale.setVisible(enable_gradient)
        end_spin.setVisible(enable_gradient)
        uniform_label.setVisible(not enable_gradient)
        uniform_scale.setVisible(not enable_gradient)
        uniform_spin.setVisible(not enable_gradient)
        
        # Connect checkbox
        def on_gradient_toggled(checked):
            start_label.setVisible(checked)
            start_scale.setVisible(checked)
            start_spin.setVisible(checked)
            end_label.setVisible(checked)
            end_scale.setVisible(checked)
            end_spin.setVisible(checked)
            uniform_label.setVisible(not checked)
            uniform_scale.setVisible(not checked)
            uniform_spin.setVisible(not checked)
        
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
        base_rotation = QSlider(Qt.Horizontal)
        base_rotation.setRange(0, 359)
        base_rotation.setValue(int(default_rotation))
        rotation_spin = QDoubleSpinBox()
        rotation_spin.setRange(0.0, 359.9)
        rotation_spin.setSingleStep(1.0)
        rotation_spin.setValue(default_rotation)
        rotation_spin.setMaximumWidth(80)
        base_rotation.valueChanged.connect(lambda v: rotation_spin.setValue(float(v)))
        rotation_spin.valueChanged.connect(lambda v: base_rotation.setValue(int(v)))
        rotation_layout.addWidget(rotation_label)
        rotation_layout.addWidget(base_rotation)
        rotation_layout.addWidget(rotation_spin)
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
        start_angle = QSlider(Qt.Horizontal)
        start_angle.setRange(0, 359)
        start_angle.setValue(int(default_start))
        start_spin = QDoubleSpinBox()
        start_spin.setRange(0.0, 359.9)
        start_spin.setSingleStep(1.0)
        start_spin.setValue(default_start)
        start_spin.setMaximumWidth(80)
        start_angle.valueChanged.connect(lambda v: start_spin.setValue(float(v)))
        start_spin.valueChanged.connect(lambda v: start_angle.setValue(int(v)))
        start_layout.addWidget(start_label)
        start_layout.addWidget(start_angle)
        start_layout.addWidget(start_spin)
        layout.addLayout(start_layout)
        
        end_layout = QHBoxLayout()
        end_label = QLabel("End Angle (°):")
        end_angle = QSlider(Qt.Horizontal)
        end_angle.setRange(0, 359)
        end_angle.setValue(int(default_end))
        end_spin = QDoubleSpinBox()
        end_spin.setRange(0.0, 359.9)
        end_spin.setSingleStep(1.0)
        end_spin.setValue(default_end)
        end_spin.setMaximumWidth(80)
        end_angle.valueChanged.connect(lambda v: end_spin.setValue(float(v)))
        end_spin.valueChanged.connect(lambda v: end_angle.setValue(int(v)))
        end_layout.addWidget(end_label)
        end_layout.addWidget(end_angle)
        end_layout.addWidget(end_spin)
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
        start_percent = QSlider(Qt.Horizontal)
        start_percent.setRange(0, 100)
        start_percent.setValue(int(default_start))
        start_spin = QDoubleSpinBox()
        start_spin.setRange(0.0, 100.0)
        start_spin.setSingleStep(1.0)
        start_spin.setValue(default_start)
        start_spin.setMaximumWidth(80)
        start_percent.valueChanged.connect(lambda v: start_spin.setValue(float(v)))
        start_spin.valueChanged.connect(lambda v: start_percent.setValue(int(v)))
        start_layout.addWidget(start_label)
        start_layout.addWidget(start_percent)
        start_layout.addWidget(start_spin)
        layout.addLayout(start_layout)
        
        end_layout = QHBoxLayout()
        end_label = QLabel("End Position (%):")
        end_percent = QSlider(Qt.Horizontal)
        end_percent.setRange(0, 100)
        end_percent.setValue(int(default_end))
        end_spin = QDoubleSpinBox()
        end_spin.setRange(0.0, 100.0)
        end_spin.setSingleStep(1.0)
        end_spin.setValue(default_end)
        end_spin.setMaximumWidth(80)
        end_percent.valueChanged.connect(lambda v: end_spin.setValue(float(v)))
        end_spin.valueChanged.connect(lambda v: end_percent.setValue(int(v)))
        end_layout.addWidget(end_label)
        end_layout.addWidget(end_percent)
        end_layout.addWidget(end_spin)
        layout.addLayout(end_layout)
        
        self._controls['start_percent'] = start_percent
        self._controls['end_percent'] = end_percent
        
        return {
            'start_percent': start_percent,
            'end_percent': end_percent
        }
