"""Zoom toolbar widget with zoom controls."""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QToolButton, QComboBox, QLabel
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QIcon
import os


class ZoomToolbar(QWidget):
	"""Toolbar with zoom in/out buttons and zoom level dropdown"""
	
	zoom_changed = pyqtSignal(int)  # Emits zoom percentage (25-500)
	
	# Standard zoom presets
	ZOOM_PRESETS = [25, 50, 100, 150, 200, 300, 400, 500]
	
	def __init__(self, parent=None):
		super().__init__(parent)
		
		layout = QHBoxLayout()
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(4)
		
		# Zoom out button
		self.zoom_out_btn = QToolButton()
		self.zoom_out_btn.setText("−")
		self.zoom_out_btn.setToolTip("Zoom Out (Ctrl+-)")
		self.zoom_out_btn.clicked.connect(self._on_zoom_out)
		layout.addWidget(self.zoom_out_btn)
		
		# Zoom level dropdown
		self.zoom_combo = QComboBox()
		self.zoom_combo.setEditable(False)
		self.zoom_combo.setMinimumWidth(80)
		for preset in self.ZOOM_PRESETS:
			self.zoom_combo.addItem(f"🔍 {preset}%", preset)
		self.zoom_combo.setCurrentIndex(self.ZOOM_PRESETS.index(100))  # Default to 100%
		self.zoom_combo.currentIndexChanged.connect(self._on_combo_changed)
		layout.addWidget(self.zoom_combo)
		
		# Zoom in button
		self.zoom_in_btn = QToolButton()
		self.zoom_in_btn.setText("+")
		self.zoom_in_btn.setToolTip("Zoom In (Ctrl++)")
		self.zoom_in_btn.clicked.connect(self._on_zoom_in)
		layout.addWidget(self.zoom_in_btn)
		
		self.setLayout(layout)
	
	def _on_zoom_in(self):
		"""Handle zoom in button click"""
		current_zoom = self.zoom_combo.currentData()
		# Find next preset
		for preset in self.ZOOM_PRESETS:
			if preset > current_zoom:
				self.set_zoom_percent(preset)
				return
		# Already at max, just use 125% of current
		new_zoom = min(500, int(current_zoom * 1.25))
		self.set_zoom_percent(new_zoom)
	
	def _on_zoom_out(self):
		"""Handle zoom out button click"""
		current_zoom = self.zoom_combo.currentData()
		# Find previous preset
		for preset in reversed(self.ZOOM_PRESETS):
			if preset < current_zoom:
				self.set_zoom_percent(preset)
				return
		# Already at min, just use 80% of current
		new_zoom = max(25, int(current_zoom / 1.25))
		self.set_zoom_percent(new_zoom)
	
	def _on_combo_changed(self, index):
		"""Handle combo box selection change"""
		if index >= 0:
			zoom_value = self.zoom_combo.itemData(index)
			self.zoom_changed.emit(zoom_value)
	
	def set_zoom_percent(self, percent):
		"""Set zoom level (updates combo box without triggering signal)"""
		# Block signals to prevent recursive updates
		self.zoom_combo.blockSignals(True)
		
		# Try to find exact match in presets
		try:
			index = self.ZOOM_PRESETS.index(percent)
			self.zoom_combo.setCurrentIndex(index)
		except ValueError:
			# Not a preset, find closest or add custom entry
			for i, preset in enumerate(self.ZOOM_PRESETS):
				if preset >= percent:
					self.zoom_combo.setCurrentIndex(i)
					break
			else:
				self.zoom_combo.setCurrentIndex(len(self.ZOOM_PRESETS) - 1)
		
		self.zoom_combo.blockSignals(False)
		
		# Emit signal
		self.zoom_changed.emit(percent)
	
	def get_zoom_percent(self):
		"""Get current zoom percentage"""
		return self.zoom_combo.currentData()
