"""
CK3 Coat of Arms Editor - Color Picker Widget

Extracted from property_sidebar.py to improve organization.
Handles color selection with CK3 named color presets and custom colors.
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QPushButton, QLabel, QColorDialog
from PyQt5.QtGui import QColor
from constants import CK3_NAMED_COLORS, CK3_COLOR_NAMES_ORDERED


class ColorPickerDialog(QDialog):
	"""Dialog for selecting colors from CK3 palette or custom colors"""
	
	def __init__(self, parent=None, current_color="#000000"):
		super().__init__(parent)
		self.setWindowTitle("Choose Color")
		self.setModal(True)
		self.selected_color = None
		self.selected_color_name = None
		self.current_color = current_color
		
		self._setup_ui()
	
	def _setup_ui(self):
		"""Setup the color picker UI"""
		layout = QVBoxLayout(self)
		layout.setSpacing(10)
		layout.setContentsMargins(15, 15, 15, 15)
		
		# Label
		label = QLabel("Select a color:")
		label.setStyleSheet("font-size: 12px; font-weight: bold;")
		layout.addWidget(label)
		
		# Build presets from constants (in UI order)
		presets = []
		for color_id in CK3_COLOR_NAMES_ORDERED:
			color_data = CK3_NAMED_COLORS[color_id]
			color_hex = color_data['hex']
			# Convert color_id to display name (e.g., "red_dark" → "Red Dark")
			display_name = ' '.join(word.capitalize() for word in color_id.split('_'))
			presets.append((color_hex, color_id, display_name))
		
		grid_layout = QGridLayout()
		grid_layout.setSpacing(8)
		
		for i, (color_hex, color_id, color_name) in enumerate(presets):
			preset_btn = QPushButton()
			preset_btn.setFixedSize(60, 60)
			preset_btn.setToolTip(color_name)
			preset_btn.setStyleSheet(f"""
				QPushButton {{
					background-color: {color_hex};
					border-radius: 4px;
					border: 1px solid rgba(255, 255, 255, 30);
				}}
			""")
			preset_btn.clicked.connect(lambda checked, c=color_hex, cid=color_id: self._select_preset(c, cid))
			# 7 colors in first row, 8 in second row
			if i < 7:
				row = 0
				col = i
			else:
				row = 1
				col = i - 7
			grid_layout.addWidget(preset_btn, row, col)
		
		layout.addLayout(grid_layout)
		
		# Custom color button
		custom_btn = QPushButton("Custom Color...")
		custom_btn.setStyleSheet("""
			QPushButton {
				padding: 8px;
				border-radius: 4px;
			}
		""")
		custom_btn.clicked.connect(self._show_custom_color_dialog)
		layout.addWidget(custom_btn)
	
	def _select_preset(self, color_hex, color_name):
		"""Select a preset color"""
		self.selected_color = color_hex
		self.selected_color_name = color_name
		self.accept()
	
	def _show_custom_color_dialog(self):
		"""Show Qt's standard color picker"""
		current_color = QColor(self.current_color)
		color = QColorDialog.getColor(current_color, self, "Choose Custom Color")
		
		if color.isValid():
			self.selected_color = color.name()
			self.selected_color_name = None  # Custom colors don't have a CK3 name
			self.accept()
	
	@staticmethod
	def get_color(parent=None, current_color="#000000"):
		"""Show color picker dialog and return selected color
		
		Args:
			parent: Parent widget
			current_color: Current color hex value
			
		Returns:
			Tuple of (color_hex, color_name) or (None, None) if cancelled
		"""
		dialog = ColorPickerDialog(parent, current_color)
		if dialog.exec_():
			return dialog.selected_color, dialog.selected_color_name
		return None, None


def create_color_button(color_hex="#000000", color_name=None):
	"""Create a color swatch button
	
	Args:
		color_hex: Hex color value
		color_name: CK3 color name (if from preset) or None (if custom)
		
	Returns:
		QPushButton configured as color swatch
	"""
	btn = QPushButton()
	btn.setFixedSize(40, 40)
	btn.setProperty("colorValue", color_hex)
	btn.setProperty("colorName", color_name)
	btn.setStyleSheet(f"""
		QPushButton {{
			background-color: {color_hex};
			border-radius: 4px;
		}}
	""")
	return btn
