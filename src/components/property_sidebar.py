from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                              QScrollArea, QWidget, QTabWidget, QPushButton,
                              QLineEdit, QSlider, QDialog, QGridLayout, QColorDialog, QCheckBox)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QPixmap, QIcon


class PropertySidebar(QFrame):
	"""Right properties sidebar with Base, Layers, and Properties tabs"""
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setMinimumWidth(250)
		self.setMaximumWidth(400)
		self.layers = []  # List of layer data dicts
		self.selected_layer_index = None
		self.layer_buttons = []  # Keep track of layer buttons
		self.canvas_widget = None  # Reference to canvas for updates
		self.drag_start_index = None
		self.drag_start_pos = None
		self._setup_ui()
	
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
		
		# Emblem Properties
		self._add_property_section(content_layout, "Selected Emblem")
		
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
		self.pos_x_slider.valueChanged.connect(lambda: self._update_layer_property('pos_x', self.pos_x_slider.value() / 100.0))
		self.pos_y_slider.valueChanged.connect(lambda: self._update_layer_property('pos_y', self.pos_y_slider.value() / 100.0))
		self.scale_x_slider.valueChanged.connect(lambda: self._update_layer_scale())
		self.scale_y_slider.valueChanged.connect(lambda: self._update_layer_scale())
		self.rotation_slider.valueChanged.connect(lambda: self._update_layer_property('rotation', self.rotation_slider.value()))
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
		elif button in self.emblem_color_buttons:
			# Emblem color changed
			if self.selected_layer_index is not None and self.canvas_widget:
				idx = self.selected_layer_index
				if 0 <= idx < len(self.layers):
					# Update layer colors
					color_idx = self.emblem_color_buttons.index(button)
					color = QColor(color_hex)
					color_rgb = [color.redF(), color.greenF(), color.blueF()]
					self.layers[idx][f'color{color_idx+1}'] = color_rgb
					self.layers[idx][f'color{color_idx+1}_name'] = color_name  # Store name or None
					self.canvas_widget.set_layers(self.layers)
	
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
			'scale_x': 1.0,
			'scale_y': 1.0,
			'rotation': 0,
			'color1': [0.750, 0.525, 0.188],   # yellow (CK3 default)
			'color2': [0.450, 0.133, 0.090],    # red (CK3 default)
			'color3': [0.450, 0.133, 0.090]     # red (CK3 default)
		}
		self.layers.append(layer)
		self._rebuild_layer_list()
		self.selected_layer_index = len(self.layers) - 1
		self._update_layer_selection()
		self._load_layer_properties()
		if self.canvas_widget:
			self.canvas_widget.set_layers(self.layers)
	
	def _delete_layer(self):
		"""Delete the selected layer"""
		if self.selected_layer_index is not None and 0 <= self.selected_layer_index < len(self.layers):
			self.layers.pop(self.selected_layer_index)
			if self.selected_layer_index >= len(self.layers):
				self.selected_layer_index = len(self.layers) - 1 if self.layers else None
			self._rebuild_layer_list()
			self._update_layer_selection()
			if self.canvas_widget:
				self.canvas_widget.set_layers(self.layers)
	
	def _move_layer_up(self):
		"""Move selected layer up in the list"""
		if self.selected_layer_index is not None and self.selected_layer_index > 0:
			idx = self.selected_layer_index
			self.layers[idx], self.layers[idx - 1] = self.layers[idx - 1], self.layers[idx]
			self.selected_layer_index = idx - 1
			self._rebuild_layer_list()
			self._update_layer_selection()
			if self.canvas_widget:
				self.canvas_widget.set_layers(self.layers)
	
	def _move_layer_down(self):
		"""Move selected layer down in the list"""
		if self.selected_layer_index is not None and self.selected_layer_index < len(self.layers) - 1:
			idx = self.selected_layer_index
			self.layers[idx], self.layers[idx + 1] = self.layers[idx + 1], self.layers[idx]
			self.selected_layer_index = idx + 1
			self._rebuild_layer_list()
			self._update_layer_selection()
			if self.canvas_widget:
				self.canvas_widget.set_layers(self.layers)
	
	def _duplicate_layer(self):
		"""Duplicate the selected layer"""
		if self.selected_layer_index is not None and 0 <= self.selected_layer_index < len(self.layers):
			layer_copy = self.layers[self.selected_layer_index].copy()
			self.layers.insert(self.selected_layer_index + 1, layer_copy)
			self.selected_layer_index += 1
			self._rebuild_layer_list()
			self._update_layer_selection()
			if self.canvas_widget:
				self.canvas_widget.set_layers(self.layers)
	
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
		
		if not (event.buttons() & Qt.LeftButton):
			return
		
		if self.drag_start_index is None:
			return
		
		# Check if dragged far enough
		if (event.pos() - self.drag_start_pos).manhattanLength() < 10:
			return
		
		# Start drag
		drag = QDrag(button)
		mime_data = QMimeData()
		mime_data.setData('application/x-layer-index', QByteArray.number(index))
		drag.setMimeData(mime_data)
		
		# Set drag cursor
		drag.exec_(Qt.MoveAction)
		self.drag_start_index = None
	
	def _drag_enter_event(self, event):
		"""Handle drag enter on layer list"""
		if event.mimeData().hasFormat('application/x-layer-index'):
			event.accept()
		else:
			event.ignore()
	
	def _drag_move_event(self, event):
		"""Handle drag move over layer list"""
		if event.mimeData().hasFormat('application/x-layer-index'):
			event.accept()
		else:
			event.ignore()
	
	def _drop_event(self, event):
		"""Handle drop on layer list to reorder"""
		if event.mimeData().hasFormat('application/x-layer-index'):
			from_index = int(event.mimeData().data('application/x-layer-index'))
			
			# Determine drop position
			drop_pos = event.pos()
			to_index = None
			
			# Find which layer button the drop is over
			for i, btn in enumerate(self.layer_buttons):
				btn_center = btn.geometry().center()
				if abs(drop_pos.y() - btn_center.y()) < 30:
					to_index = i
					break
			
			if to_index is None and len(self.layer_buttons) > 0:
				# Check if dropped below last button
				last_btn = self.layer_buttons[-1]
				if drop_pos.y() > last_btn.geometry().bottom():
					to_index = len(self.layers) - 1
			
			if to_index is not None and from_index != to_index:
				# Reorder layers
				layer = self.layers.pop(from_index)
				self.layers.insert(to_index, layer)
				
				# Update selected index
				if self.selected_layer_index == from_index:
					self.selected_layer_index = to_index
				elif from_index < self.selected_layer_index <= to_index:
					self.selected_layer_index -= 1
				elif to_index <= self.selected_layer_index < from_index:
					self.selected_layer_index += 1
				
				self._rebuild_layer_list()
				self._update_layer_selection()
				
				# Update canvas
				if self.canvas_widget:
					self.canvas_widget.set_layers(self.layers)
				
				event.accept()
			else:
				event.ignore()
		else:
			event.ignore()
	
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
		"""Rebuild the layer list UI"""
		# Clear existing layer buttons
		for btn in self.layer_buttons:
			btn.deleteLater()
		self.layer_buttons.clear()
		
		# Remove all widgets except the stretch
		while self.layers_layout.count() > 1:
			item = self.layers_layout.takeAt(0)
			if item.widget():
				item.widget().deleteLater()
		
		# Add layer buttons
		for i, layer in enumerate(self.layers):
			layer_btn = QPushButton()
			layer_btn.setCheckable(True)
			layer_btn.setFixedHeight(60)
			layer_btn.setProperty('layer_index', i)
			layer_btn.clicked.connect(lambda checked, idx=i: self._select_layer(idx))
			
			# Enable drag functionality
			layer_btn.mousePressEvent = lambda event, idx=i, btn=layer_btn: self._layer_mouse_press(event, idx, btn)
			layer_btn.mouseMoveEvent = lambda event, idx=i, btn=layer_btn: self._layer_mouse_move(event, idx, btn)
			
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
			
			self.layers_layout.insertWidget(i, layer_btn)
			self.layer_buttons.append(layer_btn)
	
	def _update_layer_property(self, prop_name, value):
		"""Update a property of the currently selected layer"""
		if self.selected_layer_index is not None and 0 <= self.selected_layer_index < len(self.layers):
			self.layers[self.selected_layer_index][prop_name] = value
			if self.canvas_widget:
				self.canvas_widget.set_layers(self.layers)
	
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
			if self.selected_layer_index is not None:
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
		"""Update layer scale with flip multipliers applied"""
		if self.selected_layer_index is not None and 0 <= self.selected_layer_index < len(self.layers):
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
			
			self.layers[self.selected_layer_index]['scale_x'] = scale_x
			self.layers[self.selected_layer_index]['scale_y'] = scale_y
			if self.canvas_widget:
				self.canvas_widget.set_layers(self.layers)
	
	def _load_layer_properties(self):
		"""Load the selected layer's properties into the UI controls"""
		if self.selected_layer_index is not None and 0 <= self.selected_layer_index < len(self.layers):
			layer = self.layers[self.selected_layer_index]
			
			# Block signals while updating to avoid triggering changes
			self.pos_x_slider.blockSignals(True)
			self.pos_y_slider.blockSignals(True)
			self.scale_x_slider.blockSignals(True)
			self.scale_y_slider.blockSignals(True)
			self.rotation_slider.blockSignals(True)
			self.flip_x_check.blockSignals(True)
			self.flip_y_check.blockSignals(True)
			
			self.pos_x_slider.setValue(int(layer.get('pos_x', 0.5) * 100))
			self.pos_y_slider.setValue(int(layer.get('pos_y', 0.5) * 100))
			
			# Handle scale with flip detection
			scale_x = layer.get('scale_x', 0.5)
			scale_y = layer.get('scale_y', 0.5)
			
			# Set flip checkboxes based on sign
			self.flip_x_check.setChecked(scale_x < 0)
			self.flip_y_check.setChecked(scale_y < 0)
			
			# Set slider values to absolute values
			self.scale_x_slider.setValue(int(abs(scale_x) * 100))
			self.scale_y_slider.setValue(int(abs(scale_y) * 100))
			self.rotation_slider.setValue(int(layer.get('rotation', 0)))
			
			self.pos_x_slider.blockSignals(False)
			self.pos_y_slider.blockSignals(False)
			self.scale_x_slider.blockSignals(False)
			self.scale_y_slider.blockSignals(False)
			self.rotation_slider.blockSignals(False)
			self.flip_x_check.blockSignals(False)
			self.flip_y_check.blockSignals(False)
			
			# Update emblem color buttons from layer colors
			for i, btn in enumerate(self.emblem_color_buttons):
				color_key = f'color{i+1}'
				if color_key in layer:
					color_rgb = layer[color_key]
					color_hex = '#{:02x}{:02x}{:02x}'.format(
						int(color_rgb[0] * 255),
						int(color_rgb[1] * 255),
						int(color_rgb[2] * 255)
					)
					btn.setProperty("colorValue", color_hex)
					btn.setStyleSheet(f"""
						QPushButton {{
							background-color: {color_hex};
							border-radius: 4px;
						}}
					""")
	
	def _select_layer(self, index):
		"""Select a layer"""
		self.selected_layer_index = index
		self._update_layer_selection()
		self._load_layer_properties()
	
	def _update_layer_selection(self):
		"""Update which layer button is checked"""
		for i, btn in enumerate(self.layer_buttons):
			btn.setChecked(i == self.selected_layer_index)
