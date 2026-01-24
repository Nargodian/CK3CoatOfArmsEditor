# PyQt5 imports
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, 
    QTabWidget, QPushButton, QLineEdit, QSlider, QCheckBox
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QPixmap, QIcon

# Local widget imports
from .property_sidebar_widgets import (
    LayerListWidget, ColorPickerDialog, create_color_button, 
    PropertySlider, ScaleEditor
)


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
	
	# ========================================
	# Selection Management
	# ========================================
	
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
	
	# ========================================
	# Property Value Helpers (Multi-Select Support)
	# ========================================
	
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
	
	# ========================================
	# UI Setup and Tab Creation
	# ========================================
	
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
		
		# Use LayerListWidget
		self.layer_list_widget = LayerListWidget()
		self.layer_list_widget.set_layers(self.layers)
		
		# Setup callbacks
		self.layer_list_widget.on_selection_changed = self._on_layer_selection_changed
		self.layer_list_widget.on_layers_reordered = self._on_layers_reordered
		self.layer_list_widget.on_duplicate_layer = self._duplicate_layer_at_index
		self.layer_list_widget.on_delete_layer = self._delete_layer_at_index
		self.layer_list_widget.on_color_changed = self._on_layer_color_changed
		
		scroll.setWidget(self.layer_list_widget)
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
		
		# Position sliders using PropertySlider
		self.pos_x_editor = PropertySlider("Position X", 0.5, 0.0, 1.0)
		self.pos_x_editor.valueChanged.connect(lambda v: self._update_layer_property_and_widget('pos_x', v))
		content_layout.addWidget(self.pos_x_editor)
		
		self.pos_y_editor = PropertySlider("Position Y", 0.5, 0.0, 1.0)
		self.pos_y_editor.valueChanged.connect(lambda v: self._update_layer_property_and_widget('pos_y', v))
		content_layout.addWidget(self.pos_y_editor)
		
		# Scale editor with unified/separate and flip options
		self.scale_editor = ScaleEditor()
		self.scale_editor.valueChanged.connect(self._update_layer_scale_and_widget)
		content_layout.addWidget(self.scale_editor)
		
		# Rotation slider
		self.rotation_editor = PropertySlider("Rotation", 0, 0, 360, is_int=True)
		self.rotation_editor.valueChanged.connect(lambda v: self._update_layer_property_and_widget('rotation', v))
		content_layout.addWidget(self.rotation_editor)
		
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
	
	
	def _show_color_picker(self, button):
		"""Show custom color picker dialog with presets"""
		current_color = button.property("colorValue")
		color_hex, color_name = ColorPickerDialog.get_color(self, current_color)
		
		if color_hex:
			self._apply_color(button, color_hex, color_name)
	
	def _apply_color(self, button, color_hex, color_name=None):
		"""Apply selected color to button
		
		Args:
			button: The color button being updated
			color_hex: Hex color value
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
	
	# ========================================
	# Color Management (Base & Emblem)
	# ========================================
	
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
	
	# ========================================
	# Layer Operations (Add, Delete, Move, Duplicate)
	# ========================================
	
	def _add_layer(self):
		"""Add empty layer button (placeholder until asset selected)"""
		from constants import (
			DEFAULT_POSITION_X, DEFAULT_POSITION_Y,
			DEFAULT_SCALE_X, DEFAULT_SCALE_Y,
			DEFAULT_ROTATION,
			DEFAULT_EMBLEM_TEXTURE,
			DEFAULT_EMBLEM_COLOR1, DEFAULT_EMBLEM_COLOR2, DEFAULT_EMBLEM_COLOR3,
			CK3_NAMED_COLORS
		)
		
		layer = {
			'filename': DEFAULT_EMBLEM_TEXTURE,
			'path': DEFAULT_EMBLEM_TEXTURE,
			'colors': 1,
			'pos_x': DEFAULT_POSITION_X,
			'pos_y': DEFAULT_POSITION_Y,
			'scale_x': DEFAULT_SCALE_X,
			'scale_y': DEFAULT_SCALE_Y,
			'rotation': DEFAULT_ROTATION,
			'color1': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR1]['rgb'],
			'color2': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR2]['rgb'],
			'color3': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR3]['rgb'],
			'color1_name': DEFAULT_EMBLEM_COLOR1,
			'color2_name': DEFAULT_EMBLEM_COLOR2,
			'color3_name': DEFAULT_EMBLEM_COLOR3
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
			self.last_selected_index = new_index
			self._rebuild_layer_list()
			self._update_layer_selection()
			self._load_layer_properties()
			# Enable properties tab but don't switch to it
			self.tab_widget.setTabEnabled(2, True)
			if self.canvas_area:
				self.canvas_area.update_transform_widget_for_layer()
			if self.canvas_widget:
				self.canvas_widget.set_layers(self.layers)
	
	# ========================================
	# Layer List Widget Callbacks
	# ========================================
	
	def _on_layer_color_changed(self, layer_index, color_index):
		"""Handle color button click from layer list - open color picker for that layer's color"""
		if 0 <= layer_index < len(self.layers):
			layer = self.layers[layer_index]
			color_key = f'color{color_index}'
			color_name_key = f'color{color_index}_name'
			
			# Get current color
			current_color_rgb = layer.get(color_key, [1.0, 1.0, 1.0])
			r, g, b = int(current_color_rgb[0] * 255), int(current_color_rgb[1] * 255), int(current_color_rgb[2] * 255)
			current_color_hex = f'#{r:02x}{g:02x}{b:02x}'
			
			# Show color picker
			color_hex, color_name = ColorPickerDialog.get_color(self, current_color_hex)
			
			if color_hex:
				# Convert hex to RGB float
				from PyQt5.QtGui import QColor
				color = QColor(color_hex)
				color_rgb = [color.redF(), color.greenF(), color.blueF()]
				
				# Update layer
				layer[color_key] = color_rgb
				layer[color_name_key] = color_name  # Store name or None
				
				# Rebuild layer list to update color button display
				self._rebuild_layer_list()
				
				# Update canvas
				if self.canvas_widget:
					self.canvas_widget.set_layers(self.layers)
				
				# Save to history
				if self.main_window and hasattr(self.main_window, '_save_state'):
					self.main_window._save_state(f"Change layer color {color_index}")
	
	def _on_layer_selection_changed(self):
		"""Handle layer selection change from layer list widget"""
		# Sync selection state
		self.selected_layer_indices = self.layer_list_widget.selected_layer_indices
		self.last_selected_index = self.layer_list_widget.last_selected_index
		
		# Update properties tab state
		selected_indices = self.get_selected_indices()
		if selected_indices:
			self.tab_widget.setTabEnabled(2, True)
			self._load_layer_properties()
			if self.canvas_area:
				self.canvas_area.update_transform_widget_for_layer()
		else:
			self.tab_widget.setTabEnabled(2, False)
			if self.tab_widget.currentIndex() == 2:
				self.tab_widget.setCurrentIndex(1)
			if self.canvas_area:
				self.canvas_area.update_transform_widget_for_layer(None)
	
	def _on_layers_reordered(self, count):
		"""Handle layers reordered from layer list widget"""
		# Update canvas
		if self.canvas_widget:
			self.canvas_widget.set_layers(self.layers)
		
		# Save to history
		if self.main_window and hasattr(self.main_window, '_save_state'):
			layer_word = "layers" if count > 1 else "layer"
			self.main_window._save_state(f"Reorder {count} {layer_word}")
	
	# ========================================
	# Property Updates and Layer Management
	# ========================================
	
	def _rebuild_layer_list(self):
		"""Rebuild the layer list UI (delegates to LayerListWidget)"""
		if hasattr(self, 'layer_list_widget'):
			self.layer_list_widget.set_layers(self.layers)
			self.layer_list_widget.rebuild()
			# Sync selection state
			self.layer_list_widget.selected_layer_indices = self.selected_layer_indices
			self.layer_list_widget.last_selected_index = self.last_selected_index
			self.layer_list_widget.update_selection_visuals()
	
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
	
	
	def _update_layer_scale_and_widget(self):
		"""Update layer scale with flip multipliers applied to all selected layers"""
		selected_indices = self.get_selected_indices()
		if not selected_indices:
			return
		
		# Get scale values with flip applied
		scale_x, scale_y = self.scale_editor.get_scale_values()
		
		# Apply to ALL selected layers
		for idx in selected_indices:
			if 0 <= idx < len(self.layers):
				self.layers[idx]['scale_x'] = scale_x
				self.layers[idx]['scale_y'] = scale_y
		
		if self.canvas_widget:
			self.canvas_widget.set_layers(self.layers)
		
		# Update transform widget
		if self.canvas_area and hasattr(self.canvas_area, 'transform_widget'):
			if selected_indices and 0 <= selected_indices[0] < len(self.layers):
				layer = self.layers[selected_indices[0]]
				self.canvas_area.transform_widget.set_transform(
					layer.get('pos_x', 0.5),
					layer.get('pos_y', 0.5),
					abs(layer.get('scale_x', 0.5)),
					abs(layer.get('scale_y', 0.5)),
					layer.get('rotation', 0)
				)
		
		# Save to history with debouncing
		if self.main_window and hasattr(self.main_window, 'save_property_change_debounced'):
			self.main_window.save_property_change_debounced("Change scale")
	
	# ========================================
	# Layer Property Loading and Selection UI
	# ========================================
	
	def _load_layer_properties(self):
		"""Load the selected layer's properties into the UI controls"""
		selected_indices = self.get_selected_indices()
		if not selected_indices:
			return
		
		# Block signals while updating to avoid triggering changes
		self.pos_x_editor.blockSignals(True)
		self.pos_y_editor.blockSignals(True)
		self.scale_editor.blockSignals(True)
		self.rotation_editor.blockSignals(True)
		
		# Get property values (may be 'Mixed' for multi-select)
		pos_x = self.get_property_value('pos_x')
		pos_y = self.get_property_value('pos_y')
		scale_x_raw = self.get_property_value('scale_x')
		scale_y_raw = self.get_property_value('scale_y')
		rotation = self.get_property_value('rotation')
		
		# Position X
		if pos_x == 'Mixed':
			self.pos_x_editor.value_input.setText('—')
			self.pos_x_editor.setValue(0.5)
		else:
			self.pos_x_editor.setValue(pos_x or 0.5)
		
		# Position Y
		if pos_y == 'Mixed':
			self.pos_y_editor.value_input.setText('—')
			self.pos_y_editor.setValue(0.5)
		else:
			self.pos_y_editor.setValue(pos_y or 0.5)
		
		# Scale X and Y with flip detection
		if scale_x_raw == 'Mixed' or scale_y_raw == 'Mixed':
			self.scale_editor.scale_x_slider.value_input.setText('—')
			self.scale_editor.scale_y_slider.value_input.setText('—')
			self.scale_editor.set_scale_values(0.5, 0.5)
			self.scale_editor.flip_x_check.setEnabled(False)
			self.scale_editor.flip_y_check.setEnabled(False)
		else:
			scale_x = scale_x_raw or 0.5
			scale_y = scale_y_raw or 0.5
			self.scale_editor.set_scale_values(scale_x, scale_y)
			self.scale_editor.flip_x_check.setEnabled(True)
			self.scale_editor.flip_y_check.setEnabled(True)
		
		# Rotation
		if rotation == 'Mixed':
			self.rotation_editor.value_input.setText('—')
			self.rotation_editor.setValue(0)
		else:
			self.rotation_editor.setValue(rotation or 0)
		
		# Check if X and Y scales are different or mixed - update unified checkbox
		if scale_x_raw == 'Mixed' or scale_y_raw == 'Mixed':
			self.scale_editor.unified_check.setChecked(False)
		elif scale_x_raw is not None and scale_y_raw is not None:
			if abs(abs(scale_x_raw) - abs(scale_y_raw)) > 0.01:
				self.scale_editor.unified_check.setChecked(False)
		
		# Restore signals
		self.pos_x_editor.blockSignals(False)
		self.pos_y_editor.blockSignals(False)
		self.scale_editor.blockSignals(False)
		self.rotation_editor.blockSignals(False)
		
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
		# Delegate to layer list widget which handles the selection logic
		if hasattr(self, 'layer_list_widget'):
			# The widget will call _on_layer_selection_changed which syncs back to us
			self.layer_list_widget._select_layer(index)
		else:
			# Fallback for old code paths
			from PyQt5.QtWidgets import QApplication
			from PyQt5.QtCore import Qt
			modifiers = QApplication.keyboardModifiers()
			ctrl_pressed = modifiers & Qt.ControlModifier
			shift_pressed = modifiers & Qt.ShiftModifier
			
			if shift_pressed and self.last_selected_index is not None:
				start = min(index, self.last_selected_index)
				end = max(index, self.last_selected_index)
				self.selected_layer_indices = set(range(start, end + 1))
			elif ctrl_pressed:
				if index in self.selected_layer_indices:
					self.selected_layer_indices.discard(index)
					if not self.selected_layer_indices:
						self.tab_widget.setTabEnabled(2, False)
				else:
					self.selected_layer_indices.add(index)
					self.tab_widget.setTabEnabled(2, True)
				self.last_selected_index = index
			else:
				if index in self.selected_layer_indices and len(self.selected_layer_indices) == 1:
					self._deselect_layer()
					return
				else:
					self.selected_layer_indices = {index}
					self.last_selected_index = index
					self.tab_widget.setTabEnabled(2, True)
			
			self._update_layer_selection()
			
			selected_indices = self.get_selected_indices()
			if selected_indices:
				self._load_layer_properties()
				if self.canvas_area:
					self.canvas_area.update_transform_widget_for_layer()
	
	def _deselect_layer(self):
		"""Deselect the current layer"""
		self.clear_selection()
	
	def _update_layer_selection(self):
		"""Update which layer button is checked and multi-select indicator"""
		# Sync selection state to layer list widget first
		if hasattr(self, 'layer_list_widget'):
			self.layer_list_widget.selected_layer_indices = self.selected_layer_indices
			self.layer_list_widget.last_selected_index = self.last_selected_index
			self.layer_list_widget.update_selection_visuals()
		
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
