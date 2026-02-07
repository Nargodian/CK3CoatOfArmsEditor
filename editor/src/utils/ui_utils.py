"""
UI Utility Widgets - Universal reusable UI components

Contains standardized widgets that maintain consistent styling across 
the application (generators, symmetry transforms, properties, etc.)
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QLineEdit
from PyQt5.QtCore import Qt, pyqtSignal


class NumberSliderWidget(QWidget):
    """Universal number input with synchronized slider and text input.
    
    Provides consistent UI for numeric parameters across generators,
    symmetry transforms, and property panels. Matches PropertySlider styling
    from property sidebar.
    
    Usage:
        # Integer range
        widget = NumberSliderWidget("Count", 10, min_val=1, max_val=100, is_int=True)
        widget.valueChanged.connect(lambda v: print(f"Count: {v}"))
        
        # Float range
        widget = NumberSliderWidget("Scale", 0.5, min_val=0.01, max_val=1.0)
        widget.valueChanged.connect(lambda v: print(f"Scale: {v:.2f}"))
    """
    
    valueChanged = pyqtSignal(float)  # Always emits float (cast to int if needed)
    
    def __init__(self, label, value=0.5, min_val=0.0, max_val=1.0, 
                 step=0.01, decimals=2, is_int=False, parent=None):
        """Initialize NumberSliderWidget.
        
        Args:
            label: Display label text
            value: Initial value
            min_val: Minimum value
            max_val: Maximum value
            step: Step size (not used, kept for API compatibility)
            decimals: Number of decimal places for float display
            is_int: If True, display as integer; if False, display as float
            parent: Parent widget
        """
        super().__init__(parent)
        self.is_int = is_int
        self.min_val = min_val
        self.max_val = max_val
        self.decimals = decimals
        
        # Block signal recursion during programmatic updates
        self._updating = False
        
        self._setup_ui(label, value)
    
    def _setup_ui(self, label, value):
        """Setup the widget UI - matches PropertySlider styling."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Label (small font, on top)
        self.label = QLabel(f"{label}:")
        self.label.setStyleSheet("padding: 2px 5px; font-size: 11px;")
        layout.addWidget(self.label)
        
        # Horizontal layout for input and slider
        slider_layout = QHBoxLayout()
        slider_layout.setSpacing(5)
        
        # Small text input (QLineEdit like PropertySlider)
        self.value_input = QLineEdit()
        self.value_input.setFixedWidth(50)
        if self.is_int:
            self.value_input.setText(str(int(value)))
        else:
            self.value_input.setText(f"{value:.{self.decimals}f}")
        self.value_input.setStyleSheet("""
            QLineEdit {
                padding: 4px;
                border-radius: 3px;
                font-size: 10px;
            }
        """)
        self.value_input.textChanged.connect(self._on_input_changed)
        slider_layout.addWidget(self.value_input)
        
        # Slider (styled to match PropertySlider)
        self.slider = QSlider(Qt.Horizontal)
        if self.is_int:
            self.slider.setMinimum(int(self.min_val))
            self.slider.setMaximum(int(self.max_val))
            self.slider.setValue(int(value))
        else:
            # For floats, scale to 0-100 range for smooth sliding
            self.slider.setMinimum(int(self.min_val * 100))
            self.slider.setMaximum(int(self.max_val * 100))
            self.slider.setValue(int(value * 100))
        
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                border-radius: 3px;
                background-color: rgba(255, 255, 255, 20);
            }
            QSlider::handle:horizontal {
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
                background-color: #5a8dbf;
            }
            QSlider::handle:horizontal:hover {
                background-color: #6a9dcf;
            }
        """)
        self.slider.valueChanged.connect(self._on_slider_changed)
        slider_layout.addWidget(self.slider)
        
        layout.addLayout(slider_layout)
    
    def _on_slider_changed(self, slider_value):
        """Handle slider value change."""
        if self._updating:
            return
        
        self._updating = True
        
        if self.is_int:
            value = slider_value
            self.value_input.setText(str(value))
        else:
            # Scale from slider range (0-100*max) to actual range
            value = slider_value / 100.0
            self.value_input.setText(f"{value:.{self.decimals}f}")
        
        self._updating = False
        self.valueChanged.emit(float(value))
    
    def _on_input_changed(self, text):
        """Handle text input change."""
        if self._updating:
            return
        
        # Validate and parse input
        try:
            if self.is_int:
                if text and text.lstrip('-').isdigit():
                    value = int(text)
                    if self.min_val <= value <= self.max_val:
                        self._updating = True
                        self.slider.setValue(value)
                        self._updating = False
                        self.valueChanged.emit(float(value))
            else:
                if text and text.replace('.', '').replace('-', '').isdigit():
                    value = float(text)
                    if self.min_val <= value <= self.max_val:
                        self._updating = True
                        slider_pos = int(value * 100)
                        self.slider.setValue(slider_pos)
                        self._updating = False
                        self.valueChanged.emit(value)
        except (ValueError, AttributeError):
            pass  # Ignore invalid input during typing
    
    def value(self):
        """Get current value.
        
        Returns:
            Current value (int or float depending on mode)
        """
        try:
            val = float(self.value_input.text())
            return int(val) if self.is_int else val
        except ValueError:
            return int(self.min_val) if self.is_int else self.min_val
    
    def setValue(self, value):
        """Set value programmatically.
        
        Args:
            value: New value to set
        """
        self._updating = True
        
        if self.is_int:
            self.value_input.setText(str(int(value)))
            self.slider.setValue(int(value))
        else:
            self.value_input.setText(f"{value:.{self.decimals}f}")
            self.slider.setValue(int(value * 100))
        
        self._updating = False
    
    def setEnabled(self, enabled):
        """Enable/disable the widget.
        
        Args:
            enabled: True to enable, False to disable
        """
        super().setEnabled(enabled)
        self.label.setEnabled(enabled)
        self.slider.setEnabled(enabled)
        self.value_input.setEnabled(enabled)
