from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, QTabWidget, QPushButton, QLineEdit, QSlider, QDialog, QGridLayout, QColorDialog, QCheckBox
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QPixmap, QIcon


class PropertySidebar(QFrame):
	"""Right properties sidebar with Base, Layers, and Properties tabs"""
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setMinimumWidth(250)
		self.setMaximumWidth(400)
		self.layers = []  # List of layer data dicts
		self.selected_layer_indices = set()  # Set of selected layer indices for multi-select
		self.last_selected_index = None  # Track for range selection with Shift+Click
		self.layer_buttons = []  # Keep track of layer buttons
		self.canvas_widget = None  # Reference to canvas for updates
		self.canvas_area = None  # Reference to canvas area for transform widget
		self.main_window = None  # Reference to main window for history
		self.drag_start_index = None
		self.drag_start_pos = None
		self.drop_zones = []  # Drop zone widgets for drag-drop
		self.active_drop_zone = None  # Currently highlighted drop zone
		self._setup_ui()
	
	# Selection helper methods
	def get_selected_indices(self) -> list:
		"""Get sorted list of selected layer indices"""
		return sorted(list(self.selected_layer_indices))
	
	def set_selected_indices(self, indices: set):
		"""Update selection state with new indices"""
		self.selected_layer_indices = set(indices) if not isinstance(indices, set) else indices
		self._update_layer_selection()
	
	def is_selected(self, index: int) -> bool:
		"""Check if index is in selection"""
		return index in self.selected_layer_indices
	
	def clear_selection(self):
		"""Clear selection and update UI"""
		self.selected_layer_indices.clear()
		self._update_layer_selection()
		# Update transform widget to hide
		if self.canvas_area:
			self.canvas_area.update_transform_widget_for_layer(None)
		# Switch to layers tab and disable properties tab
		self.tab_widget.setTabEnabled(2, False)
		if self.tab_widget.currentIndex() == 2:
			self.tab_widget.setCurrentIndex(1)  # Switch to Layers tab
	
	# Mixed value detection helpers (Phase 4)
	def get_property_value(self, property_name):
		"""Get property value from selected layers. Returns actual value if all same, 'Mixed' if different.
		
		Args:
			property_name: String key for layer property (e.g., 'pos_x', 'scale_x', 'rotation')
		
		Returns:
			- Actual value if all selected layers have the same value
			- 'Mixed' string if values differ
			- None if no layers selected
		"""
		selected_indices = self.get_selected_indices()
		if not selected_indices:
			return None
		
		# Single selection - return actual value
		if len(selected_indices) == 1:
			idx = selected_indices[0]
			if idx < len(self.layers):
				return self.layers[idx].get(property_name)
			return None
		
		# Multi-selection - check if all values are the same
		values = []
		for idx in selected_indices:
			if idx < len(self.layers):
				val = self.layers[idx].get(property_name)
				values.append(val)
		
		if not values:
			return None
		
		# Check if all values are equal
		first_val = values[0]
		if all(v == first_val for v in values):
			return first_val
		
		return 'Mixed'
	
	def has_mixed_values(self, property_name):
		"""Check if a property has mixed values across selected layers"""
		return self.get_property_value(property_name) == 'Mixed'
	
	def _setup_ui(self):
		"""Setup the property sidebar UI"""
		layout = QVBoxLayout(self)
		layout.setContentsMargins(5, 5, 5, 5)
		
		# Header
		header = QLabel("Properties")
		header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
		layout.addWidget(header)
		
		# Create tab widget
		self.tab_widget = QTabWidget()
		self.tab_widget.setStyleSheet("""
			QTabWidget::pane {
				border: 1px solid rgba(255, 255, 255, 40);
			}
			QTabBar::tab {
				padding: 6px 10px;
				border-radius: 3px;
				margin-right: 4px;
				margin-bottom: 2px;
				font-size: 11px;
				border: 1px solid transparent;
			}
			QTabBar::tab:selected {
				border: 2px solid #5a8dbf;
				padding: 5px 9px;
			}
			QTabBar::tab:hover {
				background-color: rgba(255, 255, 255, 30);
			}
		""")
		
		# Create tabs
		base_tab = self._create_base_tab()
		self.tab_widget.addTab(base_tab, "Base")
		
		layers_tab = self._create_layers_tab()
		self.tab_widget.addTab(layers_tab, "Layers")
		
		properties_tab = self._create_properties_tab()
		self.tab_widget.addTab(properties_tab, "Properties")
		
		# Disable properties tab initially (no layer selected)
		self.tab_widget.setTabEnabled(2, False)
		
		# Set Base tab as default
		self.tab_widget.setCurrentIndex(0)
		
		layout.addWidget(self.tab_widget)
	
	def _create_base_tab(self):
		"""Create the Base properties tab"""
		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		
		content = QWidget()
		content_layout = QVBoxLayout(content)
		content_layout.setAlignment(Qt.AlignTop)
		content_layout.setSpacing(10)
		
		# CoA Root Properties
		self._add_property_section(content_layout, "Coat of Arms")
		
		# Color swatches inline
		self.base_color_layout = QHBoxLayout()
		self.base_color_layout.setSpacing(5)
		self.base_color_layout.setContentsMargins(5, 5, 5, 5)
		
		self.color_buttons = []
		# Default base colors: black, yellow, black
		for i, color in enumerate(["#191713", "#BF8630", "#191713"], 1):
			color_btn = QPushButton()
			color_btn.setFixedSize(60, 60)
			color_btn.setProperty("colorValue", color)
			color_btn.setStyleSheet(f"""
				QPushButton {{
					background-color: {color};
					border-radius: 4px;
				}}
			""")
			color_btn.clicked.connect(lambda checked, btn=color_btn: self._show_color_picker(btn))
			self.color_buttons.append(color_btn)
			self.base_color_layout.addWidget(color_btn)
		
		self.base_color_layout.addStretch()
		content_layout.addLayout(self.base_color_layout)
		
		content_layout.addStretch()
		scroll.setWidget(content)
		return scroll
	
	def _create_layers_tab(self):
		"""Create the Layers tab"""
		container = QWidget()
		container_layout = QVBoxLayout(container)
		container_layout.setContentsMargins(0, 0, 0, 0)
		container_layout.setSpacing(0)
		
		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		
		content = QWidget()
		content.setAcceptDrops(True)
		# Store reference for drag-drop
		self.layers_container = content
		content.dragEnterEvent = self._drag_enter_event
		content.dragMoveEvent = self._drag_move_event
		content.dropEvent = self._drop_event
		# Add mouse press event to deselect on empty area click
		content.mousePressEvent = self._layers_container_mouse_press
		
		self.layers_layout = QVBoxLayout(content)
		self.layers_layout.setAlignment(Qt.AlignTop)
		self.layers_layout.setSpacing(5)
		self.layers_layout.setContentsMargins(5, 5, 5, 5)
		
		self.layers_layout.addStretch()
		scroll.setWidget(content)
		container_layout.addWidget(scroll)
		
		# Layer control buttons at bottom
		button_layout = QHBoxLayout()
		button_layout.setContentsMargins(5, 5, 5, 5)
		button_layout.setSpacing(5)
		
		button_style = """
			QPushButton {
				padding: 8px;
				font-size: 14px;
				font-weight: bold;
				border-radius: 3px;
				min-width: 32px;
			}
			QPushButton:hover {
				background-color: rgba(255, 255, 255, 30);
			}
		"""
		
		# Plus button (add layer)
		self.plus_btn = QPushButton("+")
		self.plus_btn.setToolTip("Add Layer")
		self.plus_btn.setStyleSheet(button_style)
		self.plus_btn.clicked.connect(self._add_layer)
		button_layout.addWidget(self.plus_btn)
		
		# Up button (move layer up)
		self.up_btn = QPushButton("↑")
		self.up_btn.setToolTip("Move Layer Up")
		self.up_btn.setStyleSheet(button_style)
		self.up_btn.clicked.connect(self._move_layer_up)
		button_layout.addWidget(self.up_btn)
		
		# Down button (move layer down)
		self.down_btn = QPushButton("↓")
		self.down_btn.setToolTip("Move Layer Down")
		self.down_btn.setStyleSheet(button_style)
		self.down_btn.clicked.connect(self._move_layer_down)
		button_layout.addWidget(self.down_btn)
		
		# Delete button
		self.delete_btn = QPushButton("×")
		self.delete_btn.setToolTip("Delete Layer")
		self.delete_btn.setStyleSheet(button_style)
		self.delete_btn.clicked.connect(self._delete_layer)
		button_layout.addWidget(self.delete_btn)
		
		# Copy/Duplicate button
		self.copy_btn = QPushButton("⎘")
		self.copy_btn.setToolTip("Duplicate Layer")
		self.copy_btn.setStyleSheet(button_style)
		self.copy_btn.clicked.connect(self._duplicate_layer)
		button_layout.addWidget(self.copy_btn)
		
		container_layout.addLayout(button_layout)
		
		return container
	
	def _create_properties_tab(self):
		"""Create the Properties tab"""
		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		
		content = QWidget()
		content_layout = QVBoxLayout(content)
		content_layout.setAlignment(Qt.AlignTop)
		content_layout.setSpacing(10)
		
		# Multi-selection indicator label (hidden by default)
		self.multi_select_label = QLabel()
		self.multi_select_label.setStyleSheet("""
			QLabel {
				font-size: 12px;
				font-weight: bold;
				padding: 8px;
				background-color: rgba(90, 141, 191, 30);
				border: 1px solid #5a8dbf;
				border-radius: 4px;
				color: #ffffff;
			}
		""")
		self.multi_select_label.setAlignment(Qt.AlignCenter)
		self.multi_select_label.setVisible(False)
		content_layout.addWidget(self.multi_select_label)
		
		# Single layer name label (hidden by default)
		self.single_layer_label = QLabel()
		self.single_layer_label.setStyleSheet("""
			QLabel {
				font-size: 12px;
				font-weight: bold;
				padding: 6px;
				color: #ddd;
			}
		""")
		self.single_layer_label.setAlignment(Qt.AlignCenter)
		content_layout.addWidget(self.single_layer_label)
		
		# Emblem Properties
		self._add_property_section(content_layout, "Properties")
		
		# Color swatches for emblem
		self.emblem_color_layout = QHBoxLayout()
		self.emblem_color_layout.setSpacing(5)
		self.emblem_color_layout.setContentsMargins(5, 5, 5, 5)
		
		self.emblem_color_buttons = []
		# Default emblem colors: yellow, red, red
		for i, color in enumerate(["#BF8630", "#732216", "#732216"], 1):
			color_btn = QPushButton()
			color_btn.setFixedSize(60, 60)
			color_btn.setProperty("colorValue", color)
			color_btn.setStyleSheet(f"""
				QPushButton {{
					background-color: {color};
					border-radius: 4px;
				}}
			""")
			color_btn.clicked.connect(lambda checked, btn=color_btn: self._show_color_picker(btn))
			self.emblem_color_buttons.append(color_btn)
			self.emblem_color_layout.addWidget(color_btn)
		self.emblem_color_layout.addStretch()
		content_layout.addLayout(self.emblem_color_layout)
		
		# Instance Properties
		self._add_property_section(content_layout, "Instance")
		self.pos_x_slider, self.pos_x_input = self._add_slider_field(content_layout, "Position X", 0.5, 0.0, 1.0)
		self.pos_y_slider, self.pos_y_input = self._add_slider_field(content_layout, "Position Y", 0.5, 0.0, 1.0)
		
		# Scale sliders (unified or separate)
		self.scale_x_label, self.scale_x_slider, self.scale_x_input = self._add_slider_field_with_label(content_layout, "Scale", 0.5, 0.0, 1.0)
		self.scale_y_label, self.scale_y_slider, self.scale_y_input = self._add_slider_field_with_label(content_layout, "Scale Y", 0.5, 0.0, 1.0)
		self.scale_y_label.setVisible(False)
		self.scale_y_slider.setVisible(False)
		self.scale_y_input.setVisible(False)
		
		# Unified scale and flip checkboxes together
		options_layout = QHBoxLayout()
		self.unified_scale_check = QCheckBox("Unified Scale")
		self.unified_scale_check.setChecked(True)
		self.unified_scale_check.stateChanged.connect(self._toggle_unified_scale)
		self.flip_x_check = QCheckBox("Flip X")
		self.flip_y_check = QCheckBox("Flip Y")
		self.flip_x_check.stateChanged.connect(lambda: self._update_layer_scale())
		self.flip_y_check.stateChanged.connect(lambda: self._update_layer_scale())
		options_layout.addWidget(self.unified_scale_check)
		options_layout.addWidget(self.flip_x_check)
		options_layout.addWidget(self.flip_y_check)
		options_layout.addStretch()
		content_layout.addLayout(options_layout)
		
		self.rotation_slider, self.rotation_input = self._add_slider_field(content_layout, "Rotation", 0, 0, 360, is_int=True)
		
		# Connect slider changes to update current layer
		self.pos_x_slider.valueChanged.connect(lambda: self._update_layer_property_and_widget('pos_x', self.pos_x_slider.value() / 100.0))
		self.pos_y_slider.valueChanged.connect(lambda: self._update_layer_property_and_widget('pos_y', self.pos_y_slider.value() / 100.0))
		self.scale_x_slider.valueChanged.connect(lambda: self._update_layer_scale_and_widget())
		self.scale_y_slider.valueChanged.connect(lambda: self._update_layer_scale_and_widget())
		self.rotation_slider.valueChanged.connect(lambda: self._update_layer_property_and_widget('rotation', self.rotation_slider.value()))
		scroll.setWidget(content)
		return scroll
	
	def _add_property_section(self, layout, title):
		"""Add a section header to properties"""
		section_label = QLabel(title)
		section_label.setStyleSheet("""
			font-size: 12px; 
			font-weight: bold; 
			padding: 10px 5px 5px 5px;
			border-bottom: 1px solid;
		""")
		layout.addWidget(section_label)
	
	def _add_property_field(self, layout, label, value):
		"""Add a property label and value field"""
		prop_label = QLabel(f"{label}:")
		prop_label.setStyleSheet("padding: 2px 5px; font-size: 11px;")
		layout.addWidget(prop_label)
		
		prop_input = QLineEdit(value)
		prop_input.setStyleSheet("""
			QLineEdit {
				padding: 6px;
				border-radius: 3px;
			}
		""")
		layout.addWidget(prop_input)
	
	def _add_slider_field(self, layout, label, value, min_val, max_val, is_int=False):
		"""Add a slider with a small input box to its left"""
		label_widget, slider, input_box = self._add_slider_field_with_label(layout, label, value, min_val, max_val, is_int)
		return slider, input_box
	
	def _add_slider_field_with_label(self, layout, label, value, min_val, max_val, is_int=False):
		"""Add a slider with a small input box to its left, returning label widget too"""
		# Label
		prop_label = QLabel(f"{label}:")
		prop_label.setStyleSheet("padding: 2px 5px; font-size: 11px;")
		layout.addWidget(prop_label)
		
		# Horizontal layout for slider and input box
		slider_layout = QHBoxLayout()
		slider_layout.setSpacing(5)
		
		# Small input box
		value_input = QLineEdit()
		value_input.setFixedWidth(50)
		if is_int:
			value_input.setText(str(int(value)))
		else:
			value_input.setText(f"{value:.2f}")
		value_input.setStyleSheet("""
			QLineEdit {
				padding: 4px;
				border-radius: 3px;
				font-size: 10px;
			}
		""")
		slider_layout.addWidget(value_input)
		
		# Slider
		slider = QSlider(Qt.Horizontal)
		if is_int:
			slider.setMinimum(int(min_val))
			slider.setMaximum(int(max_val))
			slider.setValue(int(value))
		else:
			# For float values, use integer slider with 100x multiplier
			slider.setMinimum(int(min_val * 100))
			slider.setMaximum(int(max_val * 100))
			slider.setValue(int(value * 100))
		
		slider.setStyleSheet("""
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
		
		# Connect slider to input box
		if is_int:
			slider.valueChanged.connect(lambda v: value_input.setText(str(v)))
			value_input.textChanged.connect(lambda t: slider.setValue(int(t)) if t.isdigit() else None)
		else:
			slider.valueChanged.connect(lambda v: value_input.setText(f"{v/100:.2f}"))
			value_input.textChanged.connect(lambda t: slider.setValue(int(float(t) * 100)) if t.replace('.','').replace('-','').isdigit() else None)
		
		slider_layout.addWidget(slider)
		layout.addLayout(slider_layout)
		
		return prop_label, slider, value_input
	
	def _show_color_picker(self, button):
		"""Show custom color picker dialog with presets"""
		dialog = QDialog(self)
		dialog.setWindowTitle("Choose Color")
		dialog.setModal(True)
		
		layout = QVBoxLayout(dialog)
		layout.setSpacing(10)
		layout.setContentsMargins(15, 15, 15, 15)
		
		# Label
		label = QLabel("Select a color:")
		label.setStyleSheet("font-size: 12px; font-weight: bold;")
		layout.addWidget(label)
		
		# CK3 CoA color palette - Official colors from game/common/named_colors/default_colors.txt
		# Accurate hex values converted from HSV using color_conversions.txt
		presets = [
			("#722116", "red", "Red"),
			("#4C0707", "red_dark", "Red Dark"),
			("#993A00", "orange", "Orange"),
			("#BF852F", "yellow", "Yellow"),
			("#FFAD32", "yellow_light", "Yellow Light"),
			("#CCC9C7", "white", "White"),
			("#7F7F7F", "grey", "Grey"),
			("#191613", "black", "Black"),
			("#723B1D", "brown", "Brown"),
			("#1E4C23", "green", "Green"),
			("#336638", "green_light", "Green Light"),
			("#2A5D8C", "blue_light", "Blue Light"),
			("#143E66", "blue", "Blue"),
			("#072B4C", "blue_dark", "Blue Dark"),
			("#591A40", "purple", "Purple")
		]
		
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
			preset_btn.clicked.connect(lambda checked, c=color_hex, cid=color_id, b=button: self._apply_color(b, c, dialog, cid))
			# 7 colors in first row, 6 in second row
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
		custom_btn.clicked.connect(lambda: self._show_custom_color_dialog(button, dialog))
		layout.addWidget(custom_btn)
		
		dialog.exec_()
	
	def _apply_color(self, button, color_hex, dialog, color_name=None):
		"""Apply selected color to button
		
		Args:
			button: The color button being updated
			color_hex: Hex color value
			dialog: Parent dialog to close
			color_name: CK3 color name if from swatch, None if custom
		"""
		button.setProperty("colorValue", color_hex)
		button.setProperty("colorName", color_name)  # Track if from swatch
		button.setStyleSheet(f"""
			QPushButton {{
				background-color: {color_hex};
				border-radius: 4px;
			}}
		""")
		dialog.accept()
		
		# Update canvas with new colors
		if button in self.color_buttons:
			# Base color changed
			if self.canvas_widget:
				colors = self.get_base_colors()
				self.canvas_widget.set_base_colors(colors)
				# Store color names on canvas for serialization
				for i, btn in enumerate(self.color_buttons):
					color_name_prop = btn.property("colorName")
					setattr(self.canvas_widget, f'base_color{i+1}_name', color_name_prop)
				# Save to history
				if self.main_window and hasattr(self.main_window, '_save_state'):
					self.main_window._save_state("Change base color")
		elif button in self.emblem_color_buttons:
			# Emblem color changed - apply to ALL selected layers
			selected_indices = self.get_selected_indices()
			if selected_indices and self.canvas_widget:
				color_idx = self.emblem_color_buttons.index(button)
				color = QColor(color_hex)
				color_rgb = [color.redF(), color.greenF(), color.blueF()]
				
				# Apply to all selected layers
				for idx in selected_indices:
					if 0 <= idx < len(self.layers):
						self.layers[idx][f'color{color_idx+1}'] = color_rgb
						self.layers[idx][f'color{color_idx+1}_name'] = color_name  # Store name or None
				
				self.canvas_widget.set_layers(self.layers)
				# Save to history
				if self.main_window and hasattr(self.main_window, '_save_state'):
					self.main_window._save_state("Change emblem color")
	
	def _show_custom_color_dialog(self, button, parent_dialog):
		"""Show Qt's standard color picker"""
		current_color = QColor(button.property("colorValue"))
		color = QColorDialog.getColor(current_color, self, "Choose Custom Color")
		
		if color.isValid():
			color_hex = color.name()
			self._apply_color(button, color_hex, parent_dialog, None)  # None = custom color
	
	def set_base_color_count(self, count):
		"""Show/hide base color swatches based on asset color count (1, 2, or 3)"""
		if not hasattr(self, 'color_buttons'):
			return
		
		for i, btn in enumerate(self.color_buttons):
			if i < count:
				btn.show()
			else:
				btn.hide()
	
	def get_base_colors(self):
		"""Get base colors as RGB float arrays [0.0-1.0]"""
		colors = []
		for btn in self.color_buttons:
			color_hex = btn.property("colorValue")
			color = QColor(color_hex)
			colors.append([color.redF(), color.greenF(), color.blueF()])
		return colors
	
	def set_base_colors(self, colors, color_names=None):
		"""Set base colors from RGB float arrays [0.0-1.0]
		Args:
			colors: List of [r, g, b] values (0.0-1.0)
			color_names: Optional list of color names ('black', 'yellow', etc.) to store on canvas
		"""
		for i, color_rgb in enumerate(colors):
			if i < len(self.color_buttons):
				# Convert RGB float to hex
				r = int(color_rgb[0] * 255)
				g = int(color_rgb[1] * 255)
				b = int(color_rgb[2] * 255)
				color_hex = f"#{r:02x}{g:02x}{b:02x}"
				
				# Update button
				btn = self.color_buttons[i]
				btn.setProperty("colorValue", color_hex)
				
				# Set color name if provided, otherwise clear it
				if color_names and i < len(color_names):
					btn.setProperty("colorName", color_names[i])
					# Also store on canvas for serialization
					if self.canvas_widget:
						setattr(self.canvas_widget, f'base_color{i+1}_name', color_names[i])
				else:
					btn.setProperty("colorName", None)
					if self.canvas_widget:
						setattr(self.canvas_widget, f'base_color{i+1}_name', None)
				
				btn.setStyleSheet(f"""
					QPushButton {{
						background-color: {color_hex};
						border-radius: 4px;
					}}
				""")
	
	def set_emblem_color_count(self, count):
		"""Show/hide emblem color swatches based on asset color count (1, 2, or 3)"""
		if not hasattr(self, 'emblem_color_buttons'):
			return
		
		for i, btn in enumerate(self.emblem_color_buttons):
			if i < count:
				btn.show()
			else:
				btn.hide()
	
	def _add_layer(self):
		"""Add empty layer button (placeholder until asset selected)"""
		layer = {
			'filename': 'Empty Layer',
			'path': None,
			'colors': 1,
			'pos_x': 0.5,
			'pos_y': 0.5,
			'scale_x': 0.5,
			'scale_y': 0.5,
			'rotation': 0,
			'color1': [0.750, 0.525, 0.188],   # yellow (CK3 default)
			'color2': [0.450, 0.133, 0.090],    # red (CK3 default)
			'color3': [0.450, 0.133, 0.090]     # red (CK3 default)
		}
		self.layers.append(layer)
		self._rebuild_layer_list()
		new_index = len(self.layers) - 1
		self.selected_layer_indices = {new_index}
		self.last_selected_index = new_index  # Set for shift+click range selection
		self._update_layer_selection()
		self._load_layer_properties()
		if self.canvas_widget:
			self.canvas_widget.set_layers(self.layers)
	
	def _delete_layer(self):
		"""Delete all selected layers"""
		selected_indices = self.get_selected_indices()
		if not selected_indices:
			return
		
		# Validate all indices are in range
		valid_indices = [idx for idx in selected_indices if 0 <= idx < len(self.layers)]
		if not valid_indices:
			return
		
		# Get top-most deleted position for later selection (before deletion)
		top_most_index = min(valid_indices)
		
		# Delete layers from highest index to lowest to avoid index shifting issues
		for idx in sorted(valid_indices, reverse=True):
			self.layers.pop(idx)
		
		# Select layer at top-most deleted position if exists, otherwise clear
		if len(self.layers) > 0:
			# If top-most deleted was beyond the end, select last layer
			if top_most_index >= len(self.layers):
				self.selected_layer_indices = {len(self.layers) - 1}
			else:
				self.selected_layer_indices = {top_most_index}
			self.last_selected_index = list(self.selected_layer_indices)[0]
		else:
			self.clear_selection()
			self.last_selected_index = None
		
		self._rebuild_layer_list()
		self._update_layer_selection()
		# Update transform widget for selection
		if self.canvas_area:
			self.canvas_area.update_transform_widget_for_layer()
		if self.canvas_widget:
			self.canvas_widget.set_layers(self.layers)
		# Save to history
		if self.main_window and hasattr(self.main_window, '_save_state'):
			layer_word = "layers" if len(valid_indices) > 1 else "layer"
			self.main_window._save_state(f"Delete {len(valid_indices)} {layer_word}")
	
	def _move_layer_up(self):
		"""Move all selected layers up in the list as a group"""
		selected_indices = self.get_selected_indices()
		if not selected_indices:
			return
		
		# Can't move up if any selected layer is at the top (index 0)
		if min(selected_indices) == 0:
			return
		
		# Extract selected layers maintaining order
		selected_layers = [(idx, self.layers[idx]) for idx in selected_indices]
		
		# Remove selected layers from their current positions (highest to lowest)
		for idx in sorted(selected_indices, reverse=True):
			self.layers.pop(idx)
		
		# Calculate new indices: each moves up by 1
		new_indices = [idx - 1 for idx in selected_indices]
		
		# Insert layers at new positions (lowest to highest)
		for new_idx, (old_idx, layer) in zip(sorted(new_indices), sorted(selected_layers)):
			self.layers.insert(new_idx, layer)
		
		# Update selection to new indices
		self.selected_layer_indices = set(new_indices)
		self.last_selected_index = max(new_indices) if new_indices else None
		
		self._rebuild_layer_list()
		self._update_layer_selection()
		if self.canvas_widget:
			self.canvas_widget.set_layers(self.layers)
		# Save to history
		if self.main_window and hasattr(self.main_window, '_save_state'):
			layer_word = "layers" if len(selected_indices) > 1 else "layer"
			self.main_window._save_state(f"Move {len(selected_indices)} {layer_word} up")
	
	def _move_layer_down(self):
		"""Move all selected layers down in the list as a group"""
		selected_indices = self.get_selected_indices()
		if not selected_indices:
			return
		
		# Can't move down if any selected layer is at the bottom (last index)
		if max(selected_indices) >= len(self.layers) - 1:
			return
		
		# Extract selected layers maintaining order
		selected_layers = [(idx, self.layers[idx]) for idx in selected_indices]
		
		# Remove selected layers from their current positions (highest to lowest)
		for idx in sorted(selected_indices, reverse=True):
			self.layers.pop(idx)
		
		# Calculate new indices: each moves down by 1
		new_indices = [idx + 1 for idx in selected_indices]
		
		# Insert layers at new positions (lowest to highest)
		for new_idx, (old_idx, layer) in zip(sorted(new_indices), sorted(selected_layers)):
			self.layers.insert(new_idx, layer)
		
		# Update selection to new indices
		self.selected_layer_indices = set(new_indices)
		self.last_selected_index = max(new_indices) if new_indices else None
		
		self._rebuild_layer_list()
		self._update_layer_selection()
		if self.canvas_widget:
			self.canvas_widget.set_layers(self.layers)
		# Save to history
		if self.main_window and hasattr(self.main_window, '_save_state'):
			layer_word = "layers" if len(selected_indices) > 1 else "layer"
			self.main_window._save_state(f"Move {len(selected_indices)} {layer_word} down")
	
	def _duplicate_layer(self):
		"""Duplicate all selected layers with offset"""
		selected_indices = self.get_selected_indices()
		if not selected_indices:
			return
		
		# Validate all indices are in range
		valid_indices = [idx for idx in selected_indices if 0 <= idx < len(self.layers)]
		if not valid_indices:
			return
		
		# Create duplicates with offset position
		new_layers = []
		for idx in valid_indices:
			layer_copy = self.layers[idx].copy()
			# Apply offset (0.02 in normalized coordinates as per design decision)
			layer_copy['pos_x'] = min(1.0, layer_copy.get('pos_x', 0.5) + 0.02)
			layer_copy['pos_y'] = min(1.0, layer_copy.get('pos_y', 0.5) + 0.02)
			new_layers.append(layer_copy)
		
		# Add all duplicates at the end (front-most)
		self.layers.extend(new_layers)
		
		# Clear old selection and select all newly created layers
		new_indices = list(range(len(self.layers) - len(new_layers), len(self.layers)))
		self.selected_layer_indices = set(new_indices)
		self.last_selected_index = new_indices[-1] if new_indices else None
		
		self._rebuild_layer_list()
		self._update_layer_selection()
		self._load_layer_properties()
		# Enable properties tab but don't switch to it
		self.tab_widget.setTabEnabled(2, True)
		if self.canvas_widget:
			self.canvas_widget.set_layers(self.layers)
		# Update transform widget for new selection
		if self.canvas_area:
			self.canvas_area.update_transform_widget_for_layer()
		# Save to history
		if self.main_window and hasattr(self.main_window, '_save_state'):
			layer_word = "layers" if len(valid_indices) > 1 else "layer"
			self.main_window._save_state(f"Duplicate {len(valid_indices)} {layer_word}")
	
	def _delete_layer_at_index(self, index):
		"""Delete a specific layer by index"""
		if 0 <= index < len(self.layers):
			self.layers.pop(index)
			# Adjust selected index if needed
			selected_indices = self.get_selected_indices()
			if selected_indices:
				if selected_indices[0] == index:
					# Deleted the selected layer
					if index >= len(self.layers):
						new_idx = len(self.layers) - 1 if self.layers else None
						self.selected_layer_indices = {new_idx} if new_idx is not None else set()
					else:
						self.selected_layer_indices = {index}
				elif selected_indices[0] > index:
					# Shift selection down if layer below was deleted
					self.selected_layer_indices = {selected_indices[0] - 1}
			self._rebuild_layer_list()
			self._update_layer_selection()
			# Update transform widget
			if self.canvas_area:
				self.canvas_area.update_transform_widget_for_layer()
			if self.canvas_widget:
				self.canvas_widget.set_layers(self.layers)
	
	def _duplicate_layer_at_index(self, index):
		"""Duplicate a specific layer by index"""
		if 0 <= index < len(self.layers):
			layer_copy = self.layers[index].copy()
			self.layers.insert(index + 1, layer_copy)
			# Select the new duplicate
			new_index = index + 1
			self.selected_layer_indices = {new_index}
			self.last_selected_index = new_index  # Set for shift+click range selection
			self._rebuild_layer_list()
			self._update_layer_selection()
			self._load_layer_properties()
			# Enable properties tab but don't switch to it
			self.tab_widget.setTabEnabled(2, True)
			if self.canvas_area:
				self.canvas_area.update_transform_widget_for_layer()
			if self.canvas_widget:
				self.canvas_widget.set_layers(self.layers)
	
	def _layers_container_mouse_press(self, event):
		"""Handle mouse press on empty area of layers container to deselect"""
		from PyQt5.QtCore import Qt
		if event.button() == Qt.LeftButton:
			# Check if click is on empty area (not on a layer button)
			child = self.layers_container.childAt(event.pos())
			if child is None or child not in self.layer_buttons:
				# Deselect layer
				self.clear_selection()
		QWidget.mousePressEvent(self.layers_container, event)
	
	def _layer_mouse_press(self, event, index, button):
		"""Handle mouse press on layer button for drag start"""
		from PyQt5.QtCore import Qt
		if event.button() == Qt.LeftButton:
			self.drag_start_index = index
			self.drag_start_pos = event.pos()
		# Call original handler
		QPushButton.mousePressEvent(button, event)
	
	def _layer_mouse_move(self, event, index, button):
		"""Handle mouse move on layer button for drag operation"""
		from PyQt5.QtCore import Qt, QMimeData, QByteArray
		from PyQt5.QtGui import QDrag
		import json
		
		if not (event.buttons() & Qt.LeftButton):
			return
		
		if self.drag_start_index is None:
			return
		
		# Check if dragged far enough
		if (event.pos() - self.drag_start_pos).manhattanLength() < 10:
			return
		
		# Get selected indices (for multi-layer drag)
		selected_indices = self.get_selected_indices()
		
		# If dragged layer is not in selection, make it the only selection
		if index not in selected_indices:
			selected_indices = [index]
			self.selected_layer_indices = {index}
			self._update_layer_selection()
		
		# Start drag with selected indices
		drag = QDrag(button)
		mime_data = QMimeData()
		# Store all selected indices as JSON array
		mime_data.setData('application/x-layer-indices', QByteArray(json.dumps(selected_indices).encode('utf-8')))
		drag.setMimeData(mime_data)
		
		# Set drag cursor
		drag.exec_(Qt.MoveAction)
		self.drag_start_index = None
	
	def _drag_enter_event(self, event):
		"""Handle drag enter on layer list"""
		if event.mimeData().hasFormat('application/x-layer-indices'):
			event.accept()
		else:
			event.ignore()
	
	def _drag_move_event(self, event):
		"""Handle drag move over layer list and highlight drop zones"""
		if event.mimeData().hasFormat('application/x-layer-indices'):
			# Find which drop zone is closest to cursor
			drop_pos = event.pos()
			closest_zone = None
			min_distance = float('inf')
			
			for zone in self.drop_zones:
				zone_center = zone.geometry().center()
				distance = abs(drop_pos.y() - zone_center.y())
				if distance < min_distance:
					min_distance = distance
					closest_zone = zone
			
			# Highlight the closest zone
			if closest_zone != self.active_drop_zone:
				# Clear previous highlight
				if self.active_drop_zone:
					self.active_drop_zone.setProperty('highlighted', 'false')
					self.active_drop_zone.style().unpolish(self.active_drop_zone)
					self.active_drop_zone.style().polish(self.active_drop_zone)
				
				# Set new highlight
				if closest_zone:
					closest_zone.setProperty('highlighted', 'true')
					closest_zone.style().unpolish(closest_zone)
					closest_zone.style().polish(closest_zone)
				
				self.active_drop_zone = closest_zone
			
			event.accept()
		else:
			event.ignore()
	
	def _drop_event(self, event):
		"""Handle drop on layer list to reorder (supports multi-layer)"""
		# Clear drop zone highlight
		if self.active_drop_zone:
			self.active_drop_zone.setProperty('highlighted', 'false')
			self.active_drop_zone.style().unpolish(self.active_drop_zone)
			self.active_drop_zone.style().polish(self.active_drop_zone)
			self.active_drop_zone = None
		
		if event.mimeData().hasFormat('application/x-layer-indices'):
			import json
			
			# Get dragged indices
			dragged_indices_json = bytes(event.mimeData().data('application/x-layer-indices')).decode('utf-8')
			dragged_indices = json.loads(dragged_indices_json)
			
			if not dragged_indices:
				event.ignore()
				return
			
			# Find which drop zone is closest to cursor
			drop_pos = event.pos()
			closest_zone = None
			min_distance = float('inf')
			
			for zone in self.drop_zones:
				zone_center = zone.geometry().center()
				distance = abs(drop_pos.y() - zone_center.y())
				if distance < min_distance:
					min_distance = distance
					closest_zone = zone
			
			if not closest_zone:
				event.ignore()
				return
			
			# Get the target index from the drop zone
			target_index = closest_zone.property('drop_index')
			
			# Extract layers to be moved (maintain their array order)
			sorted_indices = sorted(dragged_indices)
			dragged_layers = [self.layers[idx] for idx in sorted_indices]
			
			# Remove dragged layers from list (highest to lowest)
			for idx in sorted(dragged_indices, reverse=True):
				self.layers.pop(idx)
			
			# Adjust target index after removals
			adjusted_target = target_index
			for idx in sorted_indices:
				if idx < target_index:
					adjusted_target -= 1
			
			# Insert layers at target position
			for i, layer in enumerate(dragged_layers):
				insert_pos = adjusted_target + i
				# Clamp to valid range
				insert_pos = max(0, min(len(self.layers), insert_pos))
				self.layers.insert(insert_pos, layer)
			
			# Update selection to new indices
			new_indices = list(range(adjusted_target, adjusted_target + len(dragged_layers)))
			self.selected_layer_indices = set(new_indices)
			self.last_selected_index = new_indices[-1] if new_indices else None
			
			self._rebuild_layer_list()
			self._update_layer_selection()
			
			# Update canvas
			if self.canvas_widget:
				self.canvas_widget.set_layers(self.layers)
			
			# Save to history
			if self.main_window and hasattr(self.main_window, '_save_state'):
				layer_word = "layers" if len(dragged_indices) > 1 else "layer"
				self.main_window._save_state(f"Reorder {len(dragged_indices)} {layer_word}")
			
			event.accept()
		else:
			event.ignore()
	
	def _add_drop_zone(self, drop_index, layout_position):
		"""Add a drop zone separator at the specified position"""
		drop_zone = QWidget()
		drop_zone.setFixedHeight(8)
		drop_zone.setProperty('drop_index', drop_index)
		drop_zone.setStyleSheet("""
			QWidget {
				background-color: transparent;
				border: none;
			}
			QWidget[highlighted="true"] {
				background-color: rgba(100, 150, 255, 150);
				border-radius: 2px;
			}
		""")
		self.drop_zones.append(drop_zone)
		self.layers_layout.insertWidget(layout_position, drop_zone)
	
	def _get_preview_path(self, dds_path):
		"""Convert .dds filename to .png preview path"""
		import os
		from .asset_sidebar import TEXTURE_PREVIEW_MAP
		
		# Check if it's already a full path (from asset sidebar)
		if os.path.exists(dds_path):
			return dds_path
		
		# Extract just the filename if it's a full path
		filename = os.path.basename(dds_path) if '/' in dds_path or '\\' in dds_path else dds_path
		
		# Look up in the global texture preview map
		return TEXTURE_PREVIEW_MAP.get(filename)
	
	def _rebuild_layer_list(self):
		"""Rebuild the layer list UI with drop zones"""
		# Clear existing layer buttons and drop zones
		for btn in self.layer_buttons:
			btn.deleteLater()
		self.layer_buttons.clear()
		
		for zone in self.drop_zones:
			zone.deleteLater()
		self.drop_zones.clear()
		
		# Remove all widgets except the stretch
		while self.layers_layout.count() > 1:
			item = self.layers_layout.takeAt(0)
			if item.widget():
				item.widget().deleteLater()
		
		# Add drop zone at top (inserts at end of array, appears at top of display)
		layout_pos = 0
		self._add_drop_zone(len(self.layers), layout_pos)
		layout_pos += 1
		
		# Add layer buttons in reverse order (top layer = frontmost = last index)
		for i, layer in enumerate(reversed(self.layers)):
			# Calculate actual layer index (reversed)
			actual_index = len(self.layers) - 1 - i
			layer_btn = QPushButton()
			layer_btn.setCheckable(True)
			layer_btn.setFixedHeight(60)
			layer_btn.setProperty('layer_index', actual_index)
			layer_btn.clicked.connect(lambda checked, idx=actual_index: self._select_layer(idx))
			
			# Enable drag functionality
			layer_btn.mousePressEvent = lambda event, idx=actual_index, btn=layer_btn: self._layer_mouse_press(event, idx, btn)
			layer_btn.mouseMoveEvent = lambda event, idx=actual_index, btn=layer_btn: self._layer_mouse_move(event, idx, btn)
			
			# Create layout for layer button content
			btn_layout = QHBoxLayout(layer_btn)
			btn_layout.setContentsMargins(5, 5, 5, 5)
			btn_layout.setSpacing(8)
			
			# Add preview icon
			icon_label = QLabel()
			icon_label.setFixedSize(48, 48)
			icon_label.setStyleSheet("border: 1px solid rgba(255, 255, 255, 40); border-radius: 3px;")
			
			layer_path = layer.get('path')
			if layer_path:
				# Convert .dds path to .png preview path
				preview_path = self._get_preview_path(layer_path)
				if preview_path:
					pixmap = QPixmap(preview_path)
					if not pixmap.isNull():
						icon_label.setPixmap(pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
			
			btn_layout.addWidget(icon_label)
			
			# Add layer name
			name_label = QLabel(layer.get('filename', 'Empty Layer'))
			name_label.setWordWrap(True)
			name_label.setStyleSheet("border: none; font-size: 11px;")
			btn_layout.addWidget(name_label, stretch=1)
			
			# Add inline delete and duplicate buttons
			button_container = QWidget()
			button_container.setStyleSheet("border: none;")
			inline_layout = QVBoxLayout(button_container)
			inline_layout.setContentsMargins(0, 0, 0, 0)
			inline_layout.setSpacing(2)
			
			# Duplicate button
			duplicate_btn = QPushButton("⎘")
			duplicate_btn.setFixedSize(20, 20)
			duplicate_btn.setToolTip("Duplicate Layer")
			duplicate_btn.setStyleSheet("""
				QPushButton {
					border: 1px solid rgba(255, 255, 255, 60);
					border-radius: 2px;
					background-color: rgba(255, 255, 255, 10);
					font-size: 10px;
					padding: 0px;
					text-align: center;
				}
				QPushButton:hover {
					background-color: rgba(90, 141, 191, 100);
				}
			""")
			duplicate_btn.clicked.connect(lambda checked, idx=actual_index: self._duplicate_layer_at_index(idx))
			inline_layout.addWidget(duplicate_btn)
			
			# Delete button
			delete_btn = QPushButton("×")
			delete_btn.setFixedSize(20, 20)
			delete_btn.setToolTip("Delete Layer")
			delete_btn.setStyleSheet("""
				QPushButton {
					border: 1px solid rgba(255, 100, 100, 60);
					border-radius: 2px;
					background-color: rgba(255, 255, 255, 10);
					font-size: 14px;
					font-weight: bold;
					padding: 0px;
					text-align: center;
				}
				QPushButton:hover {
					background-color: rgba(191, 90, 90, 100);
				}
			""")
			delete_btn.clicked.connect(lambda checked, idx=actual_index: self._delete_layer_at_index(idx))
			inline_layout.addWidget(delete_btn)
			
			btn_layout.addWidget(button_container)
			
			layer_btn.setStyleSheet("""
				QPushButton {
					text-align: left;
					border: 1px solid rgba(255, 255, 255, 40);
					border-radius: 4px;
					background-color: rgba(255, 255, 255, 10);
				}
				QPushButton:hover {
					background-color: rgba(255, 255, 255, 20);
					border: 1px solid rgba(255, 255, 255, 60);
				}
				QPushButton:checked {
					border: 2px solid #5a8dbf;
					background-color: rgba(90, 141, 191, 30);
				}
			""")
			
			self.layers_layout.insertWidget(layout_pos, layer_btn)
			self.layer_buttons.append(layer_btn)
			layout_pos += 1
			
			# Add drop zone after this layer (inserts before this layer in array)
			self._add_drop_zone(actual_index, layout_pos)
			layout_pos += 1
	
	def _update_layer_property(self, prop_name, value):
		"""Update a property of all selected layers"""
		selected_indices = self.get_selected_indices()
		if not selected_indices:
			return
		
		# Apply to ALL selected layers
		for idx in selected_indices:
			if 0 <= idx < len(self.layers):
				self.layers[idx][prop_name] = value
		
		if self.canvas_widget:
			self.canvas_widget.set_layers(self.layers)
		
		# Save to history with debouncing (to avoid spam during slider drags)
		if self.main_window and hasattr(self.main_window, 'save_property_change_debounced'):
			self.main_window.save_property_change_debounced(f"Change {prop_name}")
	
	def _update_layer_property_and_widget(self, prop_name, value):
		"""Update a property and sync transform widget"""
		self._update_layer_property(prop_name, value)
		if self.canvas_area and hasattr(self.canvas_area, 'transform_widget'):
			selected_indices = self.get_selected_indices()
			if selected_indices and 0 <= selected_indices[0] < len(self.layers):
				layer = self.layers[selected_indices[0]]
				# Update transform widget with current layer state
				self.canvas_area.transform_widget.set_transform(
					layer.get('pos_x', 0.5),
					layer.get('pos_y', 0.5),
					abs(layer.get('scale_x', 0.5)),
					abs(layer.get('scale_y', 0.5)),
					layer.get('rotation', 0)
				)
	
	def _toggle_unified_scale(self, state):
		"""Toggle between unified and separate scale sliders"""
		is_unified = self.unified_scale_check.isChecked()
		
		if is_unified:
			# Update label to just "Scale"
			self.scale_x_label.setText("Scale:")
			# Hide Y slider
			self.scale_y_label.setVisible(False)
			self.scale_y_slider.setVisible(False)
			self.scale_y_input.setVisible(False)
			# Sync Y to X when switching to unified
			selected_indices = self.get_selected_indices()
			if selected_indices:
				self.scale_y_slider.blockSignals(True)
				self.scale_y_slider.setValue(self.scale_x_slider.value())
				self.scale_y_slider.blockSignals(False)
				self._update_layer_scale()
		else:
			# Update label back to "Scale X"
			self.scale_x_label.setText("Scale X:")
			# Show both sliders
			self.scale_y_label.setVisible(True)
			self.scale_y_slider.setVisible(True)
			self.scale_y_input.setVisible(True)
	
	def _update_layer_scale(self):
		"""Update layer scale with flip multipliers applied to all selected layers"""
		selected_indices = self.get_selected_indices()
		if not selected_indices:
			return
		
		# If unified scale, sync Y to X first
		if self.unified_scale_check.isChecked():
			self.scale_y_slider.blockSignals(True)
			self.scale_y_slider.setValue(self.scale_x_slider.value())
			self.scale_y_slider.blockSignals(False)
		
		# Get scale values
		scale_x = self.scale_x_slider.value() / 100.0
		scale_y = self.scale_y_slider.value() / 100.0
		
		# Apply flip multipliers
		if self.flip_x_check.isChecked():
			scale_x = -scale_x
		if self.flip_y_check.isChecked():
			scale_y = -scale_y
		
		# Apply to ALL selected layers
		for idx in selected_indices:
			if 0 <= idx < len(self.layers):
				self.layers[idx]['scale_x'] = scale_x
				self.layers[idx]['scale_y'] = scale_y
		
		if self.canvas_widget:
			self.canvas_widget.set_layers(self.layers)
		
		# Save to history with debouncing
		if self.main_window and hasattr(self.main_window, 'save_property_change_debounced'):
			self.main_window.save_property_change_debounced("Change scale")
	
	def _update_layer_scale_and_widget(self):
		"""Update layer scale and sync transform widget"""
		self._update_layer_scale()
		if self.canvas_area and hasattr(self.canvas_area, 'transform_widget'):
			selected_indices = self.get_selected_indices()
			if selected_indices and 0 <= selected_indices[0] < len(self.layers):
				layer = self.layers[selected_indices[0]]
				# Update transform widget with current layer state
				self.canvas_area.transform_widget.set_transform(
					layer.get('pos_x', 0.5),
					layer.get('pos_y', 0.5),
					abs(layer.get('scale_x', 0.5)),
					abs(layer.get('scale_y', 0.5)),
					layer.get('rotation', 0)
				)
	
	def _load_layer_properties(self):
		"""Load the selected layer's properties into the UI controls"""
		selected_indices = self.get_selected_indices()
		if not selected_indices:
			return
		
		# Block signals while updating to avoid triggering changes
		self.pos_x_slider.blockSignals(True)
		self.pos_y_slider.blockSignals(True)
		self.scale_x_slider.blockSignals(True)
		self.scale_y_slider.blockSignals(True)
		self.rotation_slider.blockSignals(True)
		self.flip_x_check.blockSignals(True)
		self.flip_y_check.blockSignals(True)
		
		# Get property values (may be 'Mixed' for multi-select)
		pos_x = self.get_property_value('pos_x')
		pos_y = self.get_property_value('pos_y')
		scale_x_raw = self.get_property_value('scale_x')
		scale_y_raw = self.get_property_value('scale_y')
		rotation = self.get_property_value('rotation')
		
		# Position X
		if pos_x == 'Mixed':
			self.pos_x_input.setText('—')
			self.pos_x_slider.setValue(50)  # Neutral position
		else:
			pos_x_val = int((pos_x or 0.5) * 100)
			self.pos_x_slider.setValue(pos_x_val)
			self.pos_x_input.setText(f"{pos_x_val/100:.2f}")
		
		# Position Y
		if pos_y == 'Mixed':
			self.pos_y_input.setText('—')
			self.pos_y_slider.setValue(50)  # Neutral position
		else:
			pos_y_val = int((pos_y or 0.5) * 100)
			self.pos_y_slider.setValue(pos_y_val)
			self.pos_y_input.setText(f"{pos_y_val/100:.2f}")
		
		# Scale X with flip detection
		if scale_x_raw == 'Mixed':
			self.scale_x_input.setText('—')
			self.scale_x_slider.setValue(50)  # Neutral position
			self.flip_x_check.setChecked(False)
			self.flip_x_check.setEnabled(False)  # Disable mixed flip
		else:
			scale_x = scale_x_raw or 0.5
			self.flip_x_check.setChecked(scale_x < 0)
			self.flip_x_check.setEnabled(True)
			scale_x_val = int(abs(scale_x) * 100)
			self.scale_x_slider.setValue(scale_x_val)
			self.scale_x_input.setText(f"{scale_x_val/100:.2f}")
		
		# Scale Y with flip detection
		if scale_y_raw == 'Mixed':
			self.scale_y_input.setText('—')
			self.scale_y_slider.setValue(50)  # Neutral position
			self.flip_y_check.setChecked(False)
			self.flip_y_check.setEnabled(False)  # Disable mixed flip
		else:
			scale_y = scale_y_raw or 0.5
			self.flip_y_check.setChecked(scale_y < 0)
			self.flip_y_check.setEnabled(True)
			scale_y_val = int(abs(scale_y) * 100)
			self.scale_y_slider.setValue(scale_y_val)
			self.scale_y_input.setText(f"{scale_y_val/100:.2f}")
		
		# Rotation
		if rotation == 'Mixed':
			self.rotation_input.setText('—')
			self.rotation_slider.setValue(0)  # Neutral position
		else:
			rotation_val = int(rotation or 0)
			self.rotation_slider.setValue(rotation_val)
			self.rotation_input.setText(str(rotation_val))
		
		# Check if X and Y scales are different or mixed
		if scale_x_raw == 'Mixed' or scale_y_raw == 'Mixed':
			self.unified_scale_check.setChecked(False)
		elif scale_x_raw is not None and scale_y_raw is not None:
			if abs(abs(scale_x_raw) - abs(scale_y_raw)) > 0.01:
				self.unified_scale_check.setChecked(False)
		
		self.pos_x_slider.blockSignals(False)
		self.pos_y_slider.blockSignals(False)
		self.scale_x_slider.blockSignals(False)
		self.scale_y_slider.blockSignals(False)
		self.rotation_slider.blockSignals(False)
		self.flip_x_check.blockSignals(False)
		self.flip_y_check.blockSignals(False)
		
		# Update transform widget
		if self.canvas_area:
			self.canvas_area.update_transform_widget_for_layer()
		
		# Update emblem color buttons - show mixed state if colors differ
		for i, btn in enumerate(self.emblem_color_buttons):
			color_key = f'color{i+1}'
			color_value = self.get_property_value(color_key)
			
			if color_value == 'Mixed':
				# Show mixed state
				btn.setStyleSheet(f"""
					QPushButton {{
						background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
							stop:0 #888, stop:0.5 #bbb, stop:1 #888);
						border: 2px solid #555;
						border-radius: 4px;
					}}
				""")
				btn.setProperty("colorValue", None)
				btn.setProperty("colorName", None)
			elif color_value is not None:
				# Single value - show color
				color_rgb = color_value
				color_hex = '#{:02x}{:02x}{:02x}'.format(
					int(color_rgb[0] * 255),
					int(color_rgb[1] * 255),
					int(color_rgb[2] * 255)
				)
				btn.setProperty("colorValue", color_hex)
				# Get color name if available
				color_name = self.get_property_value(f'color{i+1}_name')
				btn.setProperty("colorName", color_name if color_name != 'Mixed' else None)
				btn.setStyleSheet(f"""
				QPushButton {{
					background-color: {color_hex};
					border-radius: 4px;
				}}
			""")
	
	def _select_layer(self, index):
		"""Handle layer selection with modifier key support"""
		# Get current keyboard modifiers
		from PyQt5.QtWidgets import QApplication
		from PyQt5.QtCore import Qt
		modifiers = QApplication.keyboardModifiers()
		ctrl_pressed = modifiers & Qt.ControlModifier
		shift_pressed = modifiers & Qt.ShiftModifier
		
		if shift_pressed and self.last_selected_index is not None:
			# Shift+Click: Range selection
			start = min(index, self.last_selected_index)
			end = max(index, self.last_selected_index)
			# Select all indices in range (inclusive)
			self.selected_layer_indices = set(range(start, end + 1))
			# Don't update last_selected_index - keep anchor for next shift-click
		elif ctrl_pressed:
			# Ctrl+Click: Toggle selection
			if index in self.selected_layer_indices:
				self.selected_layer_indices.discard(index)
				if not self.selected_layer_indices:
					# No selection left - disable properties tab
					self.tab_widget.setTabEnabled(2, False)
			else:
				self.selected_layer_indices.add(index)
				# Enable properties tab
				self.tab_widget.setTabEnabled(2, True)
			self.last_selected_index = index
		else:
			# Regular click: Single selection (clear others)
			if index in self.selected_layer_indices and len(self.selected_layer_indices) == 1:
				# Clicking the only selected layer - deselect it
				self._deselect_layer()
				return
			else:
				# Select only this layer
				self.selected_layer_indices = {index}
				self.last_selected_index = index
				# Enable properties tab
				self.tab_widget.setTabEnabled(2, True)
		
		# Update UI
		self._update_layer_selection()
		
		# Load properties for selected layers
		selected_indices = self.get_selected_indices()
		if selected_indices:
			self._load_layer_properties()
			# Update transform widget in canvas area
			if self.canvas_area:
				self.canvas_area.update_transform_widget_for_layer()
	
	def _deselect_layer(self):
		"""Deselect the current layer"""
		self.clear_selection()
	
	def _update_layer_selection(self):
		"""Update which layer button is checked and multi-select indicator"""
		# Buttons are in reversed order (top layer = last index = button 0)
		for i, btn in enumerate(self.layer_buttons):
			actual_layer_index = len(self.layers) - 1 - i
			btn.setChecked(actual_layer_index in self.selected_layer_indices)
		
		# Update selection indicator labels
		selected_count = len(self.selected_layer_indices)
		if hasattr(self, 'multi_select_label') and hasattr(self, 'single_layer_label'):
			if selected_count > 1:
				# Show multi-select indicator
				self.multi_select_label.setText(f"Multiple Layers Selected ({selected_count} layers)")
				self.multi_select_label.setVisible(True)
				self.single_layer_label.setVisible(False)
			elif selected_count == 1:
				# Show single layer name
				idx = list(self.selected_layer_indices)[0]
				if 0 <= idx < len(self.layers):
					layer_name = self.layers[idx].get('filename', 'Unknown Layer')
					self.single_layer_label.setText(f"Layer: {layer_name}")
					self.single_layer_label.setVisible(True)
				self.multi_select_label.setVisible(False)
			else:
				# No selection
				self.multi_select_label.setVisible(False)
				self.single_layer_label.setVisible(False)
