"""
CK3 Coat of Arms Editor - Property Editors

Extracted from property_sidebar.py to improve organization.
Reusable property editor widgets for position, scale, rotation, etc.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QLineEdit, QCheckBox
from PyQt5.QtCore import Qt, pyqtSignal


class PropertySlider(QWidget):
	"""Slider with synchronized input box for property editing"""
	
	valueChanged = pyqtSignal(float)  # Emits normalized float value
	
	def __init__(self, label, value=0.5, min_val=0.0, max_val=1.0, is_int=False, parent=None):
		super().__init__(parent)
		self.is_int = is_int
		self.min_val = min_val
		self.max_val = max_val
		self._setup_ui(label, value)
	
	def _setup_ui(self, label, value):
		"""Setup the slider UI"""
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(2)
		
		# Label
		self.label = QLabel(f"{label}:")
		self.label.setStyleSheet("padding: 2px 5px; font-size: 11px;")
		layout.addWidget(self.label)
		
		# Horizontal layout for input and slider
		slider_layout = QHBoxLayout()
		slider_layout.setSpacing(5)
		
		# Small input box
		self.value_input = QLineEdit()
		self.value_input.setFixedWidth(50)
		if self.is_int:
			self.value_input.setText(str(int(value)))
		else:
			self.value_input.setText(f"{value:.2f}")
		self.value_input.setStyleSheet("""
			QLineEdit {
				padding: 4px;
				border-radius: 3px;
				font-size: 10px;
			}
		""")
		slider_layout.addWidget(self.value_input)
		
		# Slider
		self.slider = QSlider(Qt.Horizontal)
		if self.is_int:
			self.slider.setMinimum(int(self.min_val))
			self.slider.setMaximum(int(self.max_val))
			self.slider.setValue(int(value))
		else:
			# For float values, use integer slider with 100x multiplier
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
		slider_layout.addWidget(self.slider)
		
		layout.addLayout(slider_layout)
		
		# Connect signals
		if self.is_int:
			self.slider.valueChanged.connect(self._on_slider_changed)
			self.value_input.textChanged.connect(self._on_input_changed)
		else:
			self.slider.valueChanged.connect(self._on_slider_changed_float)
			self.value_input.textChanged.connect(self._on_input_changed_float)
	
	def _on_slider_changed(self, value):
		"""Handle slider change (int mode)"""
		self.value_input.setText(str(value))
		self.valueChanged.emit(float(value))
	
	def _on_slider_changed_float(self, value):
		"""Handle slider change (float mode)"""
		float_val = value / 100.0
		self.value_input.setText(f"{float_val:.2f}")
		self.valueChanged.emit(float_val)
	
	def _on_input_changed(self, text):
		"""Handle input change (int mode)"""
		if text.isdigit():
			self.slider.blockSignals(True)
			self.slider.setValue(int(text))
			self.slider.blockSignals(False)
	
	def _on_input_changed_float(self, text):
		"""Handle input change (float mode)"""
		if text.replace('.', '').replace('-', '').isdigit():
			try:
				float_val = float(text)
				self.slider.blockSignals(True)
				self.slider.setValue(int(float_val * 100))
				self.slider.blockSignals(False)
			except ValueError:
				pass
	
	def setValue(self, value):
		"""Set the slider value"""
		self.slider.blockSignals(True)
		self.value_input.blockSignals(True)
		
		if self.is_int:
			self.slider.setValue(int(value))
			self.value_input.setText(str(int(value)))
		else:
			self.slider.setValue(int(value * 100))
			self.value_input.setText(f"{value:.2f}")
		
		self.slider.blockSignals(False)
		self.value_input.blockSignals(False)
	
	def value(self):
		"""Get the current value"""
		if self.is_int:
			return self.slider.value()
		else:
			return self.slider.value() / 100.0
	
	def blockSignals(self, block):
		"""Block/unblock signals from slider and input"""
		self.slider.blockSignals(block)
		self.value_input.blockSignals(block)
	
	def setVisible(self, visible):
		"""Override setVisible to hide/show all components"""
		super().setVisible(visible)
		self.label.setVisible(visible)


class ScaleEditor(QWidget):
	"""Unified or separate scale editor with flip options"""
	
	valueChanged = pyqtSignal()  # Emitted when any scale value changes
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.unified_mode = True
		self._setup_ui()
	
	def _setup_ui(self):
		"""Setup the scale editor UI"""
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(2)
		
		# Scale X slider (shows as "Scale" in unified mode)
		self.scale_x_slider = PropertySlider("Scale", 0.5, 0.0, 1.0)
		self.scale_x_slider.valueChanged.connect(self._on_scale_x_changed)
		layout.addWidget(self.scale_x_slider)
		
		# Scale Y slider (hidden in unified mode)
		self.scale_y_slider = PropertySlider("Scale Y", 0.5, 0.0, 1.0)
		self.scale_y_slider.valueChanged.connect(self._on_scale_y_changed)
		self.scale_y_slider.setVisible(False)
		layout.addWidget(self.scale_y_slider)
		
		# Options: Unified scale and flip checkboxes
		options_layout = QHBoxLayout()
		self.unified_check = QCheckBox("Unified Scale")
		self.unified_check.setChecked(True)
		self.unified_check.stateChanged.connect(self._toggle_unified_scale)
		
		self.flip_x_check = QCheckBox("Flip X")
		self.flip_y_check = QCheckBox("Flip Y")
		self.flip_x_check.stateChanged.connect(lambda: self.valueChanged.emit())
		self.flip_y_check.stateChanged.connect(lambda: self.valueChanged.emit())
		
		options_layout.addWidget(self.unified_check)
		options_layout.addWidget(self.flip_x_check)
		options_layout.addWidget(self.flip_y_check)
		options_layout.addStretch()
		layout.addLayout(options_layout)
	
	def _toggle_unified_scale(self, state):
		"""Toggle between unified and separate scale sliders"""
		self.unified_mode = self.unified_check.isChecked()
		
		if self.unified_mode:
			# Update label to just "Scale"
			self.scale_x_slider.label.setText("Scale:")
			# Hide separate Y slider
			self.scale_y_slider.setVisible(False)
			# Sync Y to X
			self.scale_y_slider.blockSignals(True)
			self.scale_y_slider.setValue(self.scale_x_slider.value())
			self.scale_y_slider.blockSignals(False)
		else:
			# Update label to "Scale X"
			self.scale_x_slider.label.setText("Scale X:")
			# Show separate Y slider
			self.scale_y_slider.setVisible(True)
		
		self.valueChanged.emit()
	
	def _on_scale_x_changed(self, value):
		"""Handle scale X change"""
		if self.unified_mode:
			# In unified mode, sync Y to X
			self.scale_y_slider.blockSignals(True)
			self.scale_y_slider.setValue(value)
			self.scale_y_slider.blockSignals(False)
		self.valueChanged.emit()
	
	def _on_scale_y_changed(self, value):
		"""Handle scale Y change"""
		self.valueChanged.emit()
	
	def get_scale_values(self):
		"""Get scale X and Y values (always positive) and flip states
		
		Returns:
			Tuple of (scale_x, scale_y, flip_x, flip_y)
		"""
		scale_x = self.scale_x_slider.value()
		scale_y = self.scale_y_slider.value()
		flip_x = self.flip_x_check.isChecked()
		flip_y = self.flip_y_check.isChecked()
		
		return scale_x, scale_y, flip_x, flip_y
	
	def set_scale_values(self, scale_x, scale_y, flip_x=False, flip_y=False):
		"""Set scale values and flip states separately
		
		Args:
			scale_x: Scale X value (should be positive)
			scale_y: Scale Y value (should be positive)
			flip_x: Flip X state (bool)
			flip_y: Flip Y state (bool)
		"""
		# Block signals during update
		self.scale_x_slider.blockSignals(True)
		self.scale_y_slider.blockSignals(True)
		self.flip_x_check.blockSignals(True)
		self.flip_y_check.blockSignals(True)
		
		# Use absolute values and set flip states separately
		self.scale_x_slider.setValue(abs(scale_x))
		self.scale_y_slider.setValue(abs(scale_y))
		self.flip_x_check.setChecked(flip_x)
		self.flip_y_check.setChecked(flip_y)
		
		# Restore signals
		self.scale_x_slider.blockSignals(False)
		self.scale_y_slider.blockSignals(False)
		self.flip_x_check.blockSignals(False)
		self.flip_y_check.blockSignals(False)
	
	def blockSignals(self, block):
		"""Block/unblock signals from all components"""
		self.scale_x_slider.blockSignals(block)
		self.scale_y_slider.blockSignals(block)
		self.flip_x_check.blockSignals(block)
		self.flip_y_check.blockSignals(block)
