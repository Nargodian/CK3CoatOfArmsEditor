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
from constants import (
    DEFAULT_BASE_COLOR1, DEFAULT_BASE_COLOR2, DEFAULT_BASE_COLOR3,
    DEFAULT_EMBLEM_COLOR1, DEFAULT_EMBLEM_COLOR2, DEFAULT_EMBLEM_COLOR3,
    CK3_NAMED_COLORS
)


class PropertySidebar(QFrame):
	"""Right properties sidebar with Base, Layers, and Properties tabs"""
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setMinimumWidth(250)
		self.setMaximumWidth(400)
		#COA INTEGRATION ACTION: Step 3 - Add CoA model reference (set by MainWindow)
		self.coa = None  # Reference to CoA model (will be set externally)
		# NO MORE self.layers dict list - access via property that proxies to coa._layers
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
	
	def get_layer_count(self):
		"""Get number of layers from CoA model"""
		if self.coa is None:
			return 0
		return self.coa.get_layer_count()
	
	def get_layer_by_index(self, index):
		"""Get layer UUID by index"""
		if self.coa is None:
			return None
		return self.coa.get_uuid_at_index(index)
	
	# ========================================
	# Selection Management
	# ========================================
	
	def get_selected_uuids(self) -> list:
		"""Get list of selected layer UUIDs (primary selection API)"""
		return list(self.layer_list_widget.selected_layer_uuids)
	
	def get_selected_indices(self) -> list:
		"""Get sorted list of selected layer indices (DEPRECATED - use get_selected_uuids)"""
		return self.layer_list_widget.get_selected_indices()
	
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
		
		For instance properties (pos_x, pos_y, scale_x, scale_y, rotation), returns the value
		from the selected instance within each layer.
		
		Args:
			property_name: String key for layer property (e.g., 'pos_x', 'scale_x', 'rotation')
		
		Returns:
			- Actual value if all selected layers have the same value
			- 'Mixed' string if values differ
			- None if no layers selected
		"""
		selected_uuids = self.get_selected_uuids()
		if not selected_uuids:
			return None
		
		# Map property names to CoA getter methods
		property_getters = {
			'pos_x': 'get_layer_pos_x',
			'pos_y': 'get_layer_pos_y',
			'scale_x': 'get_layer_scale_x',
			'scale_y': 'get_layer_scale_y',
			'rotation': 'get_layer_rotation',
			'flip_x': 'get_layer_flip_x',
			'flip_y': 'get_layer_flip_y',
		}
		
		# Handle color properties with index parameter
		if property_name.startswith('color') and property_name[5:6].isdigit():
			color_index = int(property_name[5])
			if property_name.endswith('_name'):
				# color1_name, color2_name, color3_name
				values = []
				for uuid in selected_uuids:
					val = self.main_window.coa.get_layer_color_name(uuid, color_index)
					if val is not None:
						values.append(val)
			else:
				# color1, color2, color3
				values = []
				for uuid in selected_uuids:
					val = self.main_window.coa.get_layer_color(uuid, color_index)
					if val is not None:
						values.append(val)
		else:
			# Standard properties
			getter_method_name = property_getters.get(property_name)
			if not getter_method_name:
				raise ValueError(f"No getter method for property '{property_name}'")
			
			getter_method = getattr(self.main_window.coa, getter_method_name)
			
			# Collect values from all selected layers
			values = []
			for uuid in selected_uuids:
				val = getter_method(uuid)
				if val is not None:
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
		
		# Initialize mask colors after UI is built (delayed to ensure everything is ready)
		from PyQt5.QtCore import QTimer
		QTimer.singleShot(100, self.update_mask_colors_from_base)
	
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
		# Default base colors: red, yellow, black
		default_base_colors = [
			CK3_NAMED_COLORS[DEFAULT_BASE_COLOR1]['hex'],
			CK3_NAMED_COLORS[DEFAULT_BASE_COLOR2]['hex'],
			CK3_NAMED_COLORS[DEFAULT_BASE_COLOR3]['hex']
		]
		for i, color in enumerate(default_base_colors, 1):
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
		#COA INTEGRATION ACTION: Step 3 - Pass CoA reference to layer list widget
		# This is set later when MainWindow initializes references
		self.layer_list_widget.property_sidebar = self  # Give layer list access to base colors
		# Layer list widget now queries CoA directly via UUIDs - no need to pass layers
		
		# Setup callbacks
		self.layer_list_widget.on_selection_changed = self._on_layer_selection_changed
		self.layer_list_widget.on_layers_reordered = self._on_layer_reorder
		self.layer_list_widget.on_duplicate_layer = self._duplicate_layer
		self.layer_list_widget.on_delete_layer = self._delete_layer
		self.layer_list_widget.on_color_changed = self._on_layer_color_changed
		self.layer_list_widget.on_visibility_toggled = self._on_layer_visibility_toggle
		
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
		default_emblem_colors = [
			CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR1]['hex'],
			CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR2]['hex'],
			CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR3]['hex']
		]
		for i, color in enumerate(default_emblem_colors, 1):
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
		
		# Multi-instance indicator (shown when editing multi-instance layer)
		self.instance_selector_widget = QWidget()
		instance_selector_layout = QHBoxLayout(self.instance_selector_widget)
		instance_selector_layout.setContentsMargins(5, 5, 5, 5)
		instance_selector_layout.setSpacing(5)
		
		self.instance_label = QLabel("Editing Instance:")
		self.instance_label.setStyleSheet("font-size: 11px; color: #5a8dbf;")
		instance_selector_layout.addWidget(self.instance_label)
		
		self.instance_prev_btn = QPushButton("<")
		self.instance_prev_btn.setFixedSize(24, 24)
		self.instance_prev_btn.clicked.connect(self._prev_instance)
		instance_selector_layout.addWidget(self.instance_prev_btn)
		
		self.instance_display = QLabel("1 of 1")
		self.instance_display.setStyleSheet("font-size: 11px; color: #5a8dbf; font-weight: bold;")
		self.instance_display.setAlignment(Qt.AlignCenter)
		self.instance_display.setMinimumWidth(50)
		instance_selector_layout.addWidget(self.instance_display)
		
		self.instance_next_btn = QPushButton(">")
		self.instance_next_btn.setFixedSize(24, 24)
		self.instance_next_btn.clicked.connect(self._next_instance)
		instance_selector_layout.addWidget(self.instance_next_btn)
		
		instance_selector_layout.addStretch()
		self.instance_selector_widget.setStyleSheet("""
			QWidget {
				background-color: rgba(90, 141, 191, 15);
				border: 1px solid rgba(90, 141, 191, 50);
				border-radius: 4px;
			}
		""")
		self.instance_selector_widget.setVisible(False)
		content_layout.addWidget(self.instance_selector_widget)
		
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
		
		# Pattern Mask
		self._add_property_section(content_layout, "Pattern Mask")
		
		# Mask channel selection checkboxes
		mask_layout = QHBoxLayout()
		mask_layout.setSpacing(8)
		mask_layout.setContentsMargins(10, 5, 10, 5)
		
		# Create checkboxes for 3 mask channels
		self.mask_checkboxes = []
		
		for i in range(3):
			channel_widget = QWidget()
			channel_layout = QVBoxLayout(channel_widget)
			channel_layout.setContentsMargins(0, 0, 0, 0)
			channel_layout.setSpacing(2)
			
			# Color indicator (will be updated with pattern colors)
			color_indicator = QLabel()
			color_indicator.setFixedSize(24, 24)
			color_indicator.setStyleSheet("""
				QLabel {
					background-color: #888888;
					border: 2px solid rgba(255, 255, 255, 100);
					border-radius: 4px;
				}
			""")
			color_indicator.setAlignment(Qt.AlignCenter)
			channel_layout.addWidget(color_indicator, alignment=Qt.AlignCenter)
			
			# Checkbox
			checkbox = QCheckBox(f"Ch {i+1}")
			checkbox.setChecked(False)
			checkbox.stateChanged.connect(lambda state, ch=i: self._update_mask_from_ui())
			channel_layout.addWidget(checkbox, alignment=Qt.AlignCenter)
			
			self.mask_checkboxes.append({
				'checkbox': checkbox,
				'color_indicator': color_indicator,
				'widget': channel_widget
			})
			mask_layout.addWidget(channel_widget)
		
		mask_layout.addStretch()
		content_layout.addLayout(mask_layout)
		
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
				
				# Update mask channel color indicators
				self.update_mask_colors_from_base()
				
				# Clear layer thumbnail cache since background colors changed
				if hasattr(self, 'layer_list_widget') and self.layer_list_widget:
					self.layer_list_widget.clear_thumbnail_cache()
					self._rebuild_layer_list()
				
				# Update asset sidebar pattern previews with new background colors
				if self.main_window and hasattr(self.main_window, 'left_sidebar'):
					self.main_window.left_sidebar.update_asset_colors()
				
				# Save to history
				if self.main_window and hasattr(self.main_window, '_save_state'):
					self.main_window._save_state("Change base color")
		elif button in self.emblem_color_buttons:
			# Emblem color changed - apply to ALL selected layers
			selected_uuids = self.get_selected_uuids()
			if selected_uuids and self.canvas_widget:
				color_idx = self.emblem_color_buttons.index(button)
				color = QColor(color_hex)
				color_rgb = [color.redF(), color.greenF(), color.blueF()]
				
				# Apply to all selected layers
				for uuid in selected_uuids:
					self.main_window.coa.set_layer_color(uuid, color_idx+1, color_rgb, color_name)
					# Invalidate thumbnail cache for this layer
					self.layer_list_widget.invalidate_thumbnail(uuid)
				if self.main_window and hasattr(self.main_window, 'left_sidebar'):
					self.main_window.left_sidebar.update_asset_colors()
				
				# Save to history
				if self.main_window and hasattr(self.main_window, '_save_state'):
					self.main_window._save_state(f"Change emblem color {color_idx+1}")
			
			# Rebuild layer list to update thumbnails
			self._rebuild_layer_list()
	
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
		
		# Update mask channel color indicators
		self.update_mask_colors_from_base()
	
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
			DEFAULT_FLIP_X, DEFAULT_FLIP_Y,
			DEFAULT_ROTATION,
			DEFAULT_EMBLEM_TEXTURE,
			DEFAULT_EMBLEM_COLOR1, DEFAULT_EMBLEM_COLOR2, DEFAULT_EMBLEM_COLOR3,
			CK3_NAMED_COLORS
		)
		from models.coa import Layer
		
		# Create layer data dict
		layer_data = {
			'filename': DEFAULT_EMBLEM_TEXTURE,
			'path': DEFAULT_EMBLEM_TEXTURE,
			'colors': 1,
			'instances': [{
				'pos_x': DEFAULT_POSITION_X,
				'pos_y': DEFAULT_POSITION_Y,
				'scale_x': DEFAULT_SCALE_X,
				'scale_y': DEFAULT_SCALE_Y,
				'rotation': DEFAULT_ROTATION,
				'depth': 0.0
			}],
			'selected_instance': 0,
			'flip_x': DEFAULT_FLIP_X,
			'flip_y': DEFAULT_FLIP_Y,
			'color1': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR1]['rgb'],
			'color2': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR2]['rgb'],
			'color3': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR3]['rgb'],
			'color1_name': DEFAULT_EMBLEM_COLOR1,
			'color2_name': DEFAULT_EMBLEM_COLOR2,
			'color3_name': DEFAULT_EMBLEM_COLOR3
		}
		
		# Create Layer object from data
		layer = Layer(layer_data, caller='property_sidebar._add_layer')
		
		# Check for selection to add above
		selected_uuids = self.get_selected_uuids()
		target_uuid = selected_uuids[0] if selected_uuids else None
		
		if target_uuid:
			# Add below selected layer (in front of it)
			self.coa.add_layer_object(layer, target_uuid=target_uuid)
		else:
			# No selection, add at front
			self.coa.add_layer_object(layer)
		
		self._rebuild_layer_list()
		
		# Auto-select the newly added layer using UUID from CoA
		new_uuid = self.coa.get_last_added_uuid()
		if new_uuid:
			self.layer_list_widget.selected_layer_uuids = {new_uuid}
			self.layer_list_widget.last_selected_uuid = new_uuid
			self.layer_list_widget.update_selection_visuals()
		
		if self.canvas_widget:
			self.canvas_widget.set_coa(self.main_window.coa)
		
		# Trigger selection change callback to update properties and transform widget
		self._on_layer_selection_changed()
	
	def _prev_instance(self):
		"""Switch to previous instance in multi-instance layer"""
		selected_uuids = self.get_selected_uuids()
		if len(selected_uuids) != 1:
			return
		
		uuid = selected_uuids[0]
		instance_count = self.main_window.coa.get_layer_instance_count(uuid)
		if instance_count <= 1:
			return
		
		selected_inst = self.main_window.selected_instance_per_layer.get(uuid, 0)
		new_inst = (selected_inst - 1) % instance_count
		self.main_window.selected_instance_per_layer[uuid] = new_inst
		
		# Reload properties and update transform widget
		self._load_layer_properties()
		if self.canvas_area:
			self.canvas_area.update_transform_widget_for_layer()
	
	def _next_instance(self):
		"""Switch to next instance in multi-instance layer"""
		selected_uuids = self.get_selected_uuids()
		if len(selected_uuids) != 1:
			return
		
		uuid = selected_uuids[0]
		instance_count = self.main_window.coa.get_layer_instance_count(uuid)
		if instance_count <= 1:
			return
		
		selected_inst = self.main_window.selected_instance_per_layer.get(uuid, 0)
		new_inst = (selected_inst + 1) % instance_count
		self.main_window.selected_instance_per_layer[uuid] = new_inst
		
		# Reload properties and update transform widget
		self._load_layer_properties()
		if self.canvas_area:
			self.canvas_area.update_transform_widget_for_layer()
	
	def _delete_layer(self):
		"""Delete all selected layers"""
		selected_uuids = self.get_selected_uuids()
		if not selected_uuids:
			return
		
		# Delete layers by UUID (order doesn't matter)
		for uuid in selected_uuids:
			self.coa.remove_layer(uuid)
		
		# Clear thumbnail cache
		if hasattr(self, 'layer_list_widget'):
			self.layer_list_widget.clear_thumbnail_cache()
		
		# Clear selection
		self.clear_selection()
		self.last_selected_index = None
		
		self._rebuild_layer_list()
		self._update_layer_selection()
		# Update transform widget for selection
		if self.canvas_area:
			self.canvas_area.update_transform_widget_for_layer()
		if self.canvas_widget:
			self.canvas_widget.set_coa(self.main_window.coa)
		# Save to history
		if self.main_window and hasattr(self.main_window, '_save_state'):
			layer_word = "layers" if len(selected_uuids) > 1 else "layer"
			self.main_window._save_state(f"Delete {len(selected_uuids)} {layer_word}")
	
	def _move_layer_up(self):
		"""Move all selected layers up in the list as a group"""
		selected_indices = self.get_selected_indices()
		if not selected_indices:
			return
		
		# Can't move up if any selected layer is at the top (index 0)
		if min(selected_indices) == 0:
			return
		
		# Extract selected layers maintaining order
		selected_layers = [(idx, self.get_layer_by_index(idx)) for idx in selected_indices]
		
		# Remove selected layers from their current positions (highest to lowest)
		for idx in sorted(selected_indices, reverse=True):
			layer_uuid = self.coa.get_layer_uuid_by_index(idx)
			self.coa.remove_layer(layer_uuid)
		
		# Calculate new indices: each moves up by 1
		new_indices = [idx - 1 for idx in selected_indices]
		
		# Insert layers at new positions (lowest to highest)
		for new_idx, (old_idx, layer) in zip(sorted(new_indices), sorted(selected_layers)):
			self.coa.insert_layer_at_index(new_idx, layer)
		
		# Update selection to new indices
		self.selected_layer_indices = set(new_indices)
		self.last_selected_index = max(new_indices) if new_indices else None
		
		self._rebuild_layer_list()
		self._update_layer_selection()
		if self.canvas_widget:
			self.canvas_widget.set_coa(self.main_window.coa)
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
		if max(selected_indices) >= self.get_layer_count() - 1:
			return
		
		# Extract selected layers maintaining order
		selected_layers = [(idx, self.get_layer_by_index(idx)) for idx in selected_indices]
		
		# Remove selected layers from their current positions (highest to lowest)
		for idx in sorted(selected_indices, reverse=True):
			layer_uuid = self.coa.get_layer_uuid_by_index(idx)
			self.coa.remove_layer(layer_uuid)
		
		# Calculate new indices: each moves down by 1
		new_indices = [idx + 1 for idx in selected_indices]
		
		# Insert layers at new positions (lowest to highest)
		for new_idx, (old_idx, layer) in zip(sorted(new_indices), sorted(selected_layers)):
			self.coa.insert_layer_at_index(new_idx, layer)
		
		# Update selection to new indices
		self.selected_layer_indices = set(new_indices)
		self.last_selected_index = max(new_indices) if new_indices else None
		
		self._rebuild_layer_list()
		self._update_layer_selection()
		if self.canvas_widget:
			self.canvas_widget.set_coa(self.main_window.coa)
		# Save to history
		if self.main_window and hasattr(self.main_window, '_save_state'):
			layer_word = "layers" if len(selected_indices) > 1 else "layer"
			self.main_window._save_state(f"Move {len(selected_indices)} {layer_word} down")
	
	def _duplicate_layer(self, uuid=None):
		"""Duplicate specific layer or all selected layers with offset"""
		if uuid:
			selected_uuids = [uuid]
		else:
			selected_uuids = self.get_selected_uuids()
		if not selected_uuids:
			return
		
		# Duplicate using CoA model
		new_uuids = []
		for uuid in selected_uuids:
			new_uuid = self.main_window.coa.duplicate_layer(uuid)
			new_uuids.append(new_uuid)
		
		# Select the new layers by UUID
		if new_uuids:
			self.layer_list_widget.selected_layer_uuids = set(new_uuids)
			# Note: No need to track indices anymore, selection is UUID-based
		
		self._rebuild_layer_list()
		self._update_layer_selection()
		self._load_layer_properties()
		# Enable properties tab but don't switch to it
		self.tab_widget.setTabEnabled(2, True)
		if self.canvas_widget:
			self.canvas_widget.set_coa(self.main_window.coa)
		# Update transform widget for new selection
		if self.canvas_area:
			self.canvas_area.update_transform_widget_for_layer()
		# Save to history
		if self.main_window and hasattr(self.main_window, '_save_state'):
			layer_word = "layers" if len(selected_uuids) > 1 else "layer"
			self.main_window._save_state(f"Duplicate {len(selected_uuids)} {layer_word}")
	
	# ========================================
	# Layer List Widget Callbacks
	# ========================================
	
	def _on_layer_color_changed(self, uuid, color_index):
		"""Handle color button click from layer list - open color picker for that layer's color"""
		color_key = f'color{color_index}'
		color_name_key = f'color{color_index}_name'
		
		# Get current color using CoA API with parameterized method
		current_color_rgb = self.coa.get_layer_color(uuid, color_index)
		if not current_color_rgb:
			current_color_rgb = [1.0, 1.0, 1.0]
		r, g, b = int(current_color_rgb[0] * 255), int(current_color_rgb[1] * 255), int(current_color_rgb[2] * 255)
		current_color_hex = f'#{r:02x}{g:02x}{b:02x}'
		
		# Show color picker
		color_hex, color_name = ColorPickerDialog.get_color(self, current_color_hex)
		
		if color_hex:
			# Convert hex to RGB float
			from PyQt5.QtGui import QColor
			color = QColor(color_hex)
			color_rgb = [color.redF(), color.greenF(), color.blueF()]
			
			# Update layer using CoA API
			self.coa.set_layer_color(uuid, color_index, color_rgb, color_name)
			
			# Invalidate thumbnail cache for this layer (by UUID)
			self.layer_list_widget.invalidate_thumbnail(uuid)
				
			
			# Update only this layer button (no full rebuild needed)
			self.layer_list_widget.update_layer_button(uuid)
			
			# Update canvas
			if self.canvas_widget:
				self.canvas_widget.set_coa(self.main_window.coa)
			
			# Update asset sidebar previews with new colors
			if self.main_window and hasattr(self.main_window, 'left_sidebar'):
				self.main_window.left_sidebar.update_asset_colors()
			
			
			# Save to history
			if self.main_window and hasattr(self.main_window, '_save_state'):
				self.main_window._save_state(f"Change layer color {color_index}")
	
	def _on_layer_visibility_toggle(self, uuid):
		current_visibility = self.coa.get_layer_visible(uuid)
		if current_visibility is None:
			current_visibility = True
		self.coa.set_layer_visible(uuid, not current_visibility)
		
		# Invalidate thumbnail cache for this layer (by UUID)
		
		# Update canvas to hide/show layer
		if self.canvas_widget:
			self.canvas_widget.set_coa(self.main_window.coa)
		
		# Save to history
		if self.main_window and hasattr(self.main_window, '_save_state'):
			current_visibility = self.coa.get_layer_visible(uuid) or False
			visibility_state = "visible" if current_visibility else "hidden"
			self.main_window._save_state(f"Toggle layer visibility to {visibility_state}")
	


	def _on_layer_selection_changed(self):
		"""Handle layer selection change from layer list widget"""
		# layer_list_widget manages selection via UUIDs - we just query when needed
		# No need to sync to self.selected_layer_indices (deprecated)
		
		# Update selection UI (this also calls _update_menu_actions via main_window)
		self._update_layer_selection()
		
		# Update asset sidebar emblem previews if viewing emblems
		# (patterns use base colors which don't change with layer selection)
		if self.main_window and hasattr(self.main_window, 'left_sidebar'):
			if self.main_window.left_sidebar.current_mode == "emblems":
				self.main_window.left_sidebar.update_asset_colors()
		
		# Update alignment action states in main window
		if self.main_window and hasattr(self.main_window, '_update_alignment_actions'):
			self.main_window._update_alignment_actions()
		
		# Update transform action states in main window
		if self.main_window and hasattr(self.main_window, '_update_transform_actions'):
			self.main_window._update_transform_actions()
		
		# Update move to action states in main window
		if self.main_window and hasattr(self.main_window, '_update_move_to_actions'):
			self.main_window._update_move_to_actions()
		
		# Update properties tab state
		selected_uuids = self.get_selected_uuids()
		if selected_uuids:
			self.tab_widget.setTabEnabled(2, True)
			# Always load properties (including color count) when selection changes
			self._load_layer_properties()
			if self.canvas_area:
				self.canvas_area.update_transform_widget_for_layer()
		else:
			self.tab_widget.setTabEnabled(2, False)
			if self.tab_widget.currentIndex() == 2:
				self.tab_widget.setCurrentIndex(1)
			if self.canvas_area:
				self.canvas_area.update_transform_widget_for_layer(None)
	
	def _on_layer_reorder(self, count):
		"""Handle layer reordering from drag-drop
		
		Note: The layer_list_widget already reordered self.layers directly.
		This callback just updates the canvas and saves state.
		
		Args:
			count: Number of layers that were reordered
		"""
		# Layers were already reordered by layer_list_widget
		# Selection was also already updated by layer_list_widget
		# Just sync canvas and save state
		
		# Clear thumbnail cache since indices have changed
		self.layer_list_widget.clear_thumbnail_cache()
		
		# Update canvas
		if self.canvas_widget:
			self.canvas_widget.set_coa(self.main_window.coa)
		
		# Save state
		if self.main_window and hasattr(self.main_window, '_save_state'):
			layer_word = "layers" if count > 1 else "layer"
			self.main_window._save_state(f"Reorder {count} {layer_word}")
	
	# ========================================
	# Property Updates and Layer Management
	# ========================================
	
	def _rebuild_layer_list(self):
		"""Rebuild the layer list UI (delegates to LayerListWidget)"""
		if hasattr(self, 'layer_list_widget'):
			# Pass CoA model layers directly via public method
			layers = []
			if self.main_window and self.main_window.coa:
				layers = [self.coa.get_layer_by_index(i) for i in range(self.coa.get_layer_count())]
			self.layer_list_widget.set_layers(layers)
			self.layer_list_widget.rebuild()
			# Selection state is managed by layer_list_widget itself (UUID-based)
	
	def _update_layer_property(self, prop_name, value):
		"""Update a property of all selected layers
		
		For instance properties (pos_x, pos_y, scale_x, scale_y, rotation), updates
		the selected instance within each layer.
		"""
		selected_uuids = self.get_selected_uuids()
		if not selected_uuids:
			return
		
		# Instance properties are stored within instances list
		instance_properties = ['pos_x', 'pos_y', 'scale_x', 'scale_y', 'rotation', 'depth']
		
		# Apply to ALL selected layers using CoA API
		for uuid in selected_uuids:
			# Route to appropriate CoA setter based on property name
			if prop_name in ('pos_x', 'pos_y'):
				current_x = self.main_window.coa.get_layer_pos_x(uuid) or 0.0
				current_y = self.main_window.coa.get_layer_pos_y(uuid) or 0.0
				if prop_name == 'pos_x':
					self.main_window.coa.set_layer_position(uuid, value, current_y)
				else:
					self.main_window.coa.set_layer_position(uuid, current_x, value)
			elif prop_name in ('scale_x', 'scale_y'):
				current_sx = self.main_window.coa.get_layer_scale_x(uuid) or 1.0
				current_sy = self.main_window.coa.get_layer_scale_y(uuid) or 1.0
				if prop_name == 'scale_x':
					self.main_window.coa.set_layer_scale(uuid, value, current_sy)
				else:
					self.main_window.coa.set_layer_scale(uuid, current_sx, value)
			elif prop_name == 'rotation':
				self.main_window.coa.set_layer_rotation(uuid, value)
			else:
				# Other properties - log warning
				import logging
				logging.warning(f"Unhandled property {prop_name} in _update_layer_property")
		
		if self.canvas_widget:
			self.canvas_widget.set_coa(self.main_window.coa)
		
		# Save to history with debouncing (to avoid spam during slider drags)
		if self.main_window and hasattr(self.main_window, 'save_property_change_debounced'):
			self.main_window.save_property_change_debounced(f"Change {prop_name}")
	
	def _update_layer_property_and_widget(self, prop_name, value):
		"""Update a property and sync transform widget"""
		self._update_layer_property(prop_name, value)
		if self.canvas_area:
			# Use update_transform_widget_for_layer to properly handle multi-selection
			self.canvas_area.update_transform_widget_for_layer()
	
	
	def _update_layer_scale_and_widget(self):
		"""Update layer scale with flip multipliers applied to all selected layers"""
		selected_uuids = self.get_selected_uuids()
		if not selected_uuids:
			return
		
		# Get scale values and flip states separately
		scale_x, scale_y, flip_x, flip_y = self.scale_editor.get_scale_values()
		
		# Apply to ALL selected layers using CoA API
		for uuid in selected_uuids:
			# Use CoA setters
			self.main_window.coa.set_layer_scale(uuid, scale_x, scale_y)
			self.main_window.coa.set_layer_flip(uuid, flip_x, flip_y)
		
		if self.canvas_widget:
			self.canvas_widget.set_coa(self.main_window.coa)
		
		# Update transform widget - use update_transform_widget_for_layer for multi-selection
		if self.canvas_area:
			self.canvas_area.update_transform_widget_for_layer()
		
		# Save to history with debouncing
		if self.main_window and hasattr(self.main_window, 'save_property_change_debounced'):
			self.main_window.save_property_change_debounced("Change scale")
	
	# ========================================
	# Layer Property Loading and Selection UI
	# ========================================
	
	def _load_layer_properties(self):
		"""Load the selected layer's properties into the UI controls"""
		from utils.metadata_cache import get_texture_color_count
		
		selected_uuids = self.get_selected_uuids()
		if not selected_uuids:
			return
		
		# Query metadata for color count based on layer's texture filename
		# For multi-select, use the maximum color count across all selected layers
		color_counts = []
		for uuid in selected_uuids:
			filename = self.main_window.coa.get_layer_filename(uuid)
			color_count = get_texture_color_count(filename)
			color_counts.append(color_count)
		
		if color_counts:
			max_color_count = max(color_counts)
			self.set_emblem_color_count(max_color_count)
		
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
		flip_x_raw = self.get_property_value('flip_x')
		flip_y_raw = self.get_property_value('flip_y')
		
		if scale_x_raw == 'Mixed' or scale_y_raw == 'Mixed' or flip_x_raw == 'Mixed' or flip_y_raw == 'Mixed':
			self.scale_editor.scale_x_slider.value_input.setText('—')
			self.scale_editor.scale_y_slider.value_input.setText('—')
			self.scale_editor.set_scale_values(0.5, 0.5, False, False)
			self.scale_editor.flip_x_check.setEnabled(False)
			self.scale_editor.flip_y_check.setEnabled(False)
		else:
			scale_x = scale_x_raw or 0.5
			scale_y = scale_y_raw or 0.5
			flip_x = flip_x_raw if isinstance(flip_x_raw, bool) else False
			flip_y = flip_y_raw if isinstance(flip_y_raw, bool) else False
			self.scale_editor.set_scale_values(scale_x, scale_y, flip_x, flip_y)
			self.scale_editor.flip_x_check.setEnabled(True)
			self.scale_editor.flip_y_check.setEnabled(True)
		
		# Rotation
		if rotation == 'Mixed':
			self.rotation_editor.value_input.setText('—')
			self.rotation_editor.setValue(0)
		else:
			self.rotation_editor.setValue(rotation or 0)
		
		# Check if X and Y scales are different or mixed - update unified checkbox
		# Block unified_check signals to prevent triggering valueChanged during UI load
		self.scale_editor.unified_check.blockSignals(True)
		if scale_x_raw == 'Mixed' or scale_y_raw == 'Mixed':
			self.scale_editor.unified_check.setChecked(False)
		elif scale_x_raw is not None and scale_y_raw is not None:
			if abs(abs(scale_x_raw) - abs(scale_y_raw)) > 0.01:
				self.scale_editor.unified_check.setChecked(False)
		self.scale_editor.unified_check.blockSignals(False)
		
		# Restore signals
		self.pos_x_editor.blockSignals(False)
		self.pos_y_editor.blockSignals(False)
		self.scale_editor.blockSignals(False)
		self.rotation_editor.blockSignals(False)
		
		# Update instance selector for single-selection multi-instance layers
		if len(selected_uuids) == 1:
			instance_count = self.main_window.coa.get_layer_instance_count(selected_uuids[0])
			if instance_count > 1:
				selected_inst = self.main_window.selected_instance_per_layer.get(selected_uuids[0], 0)
				self.instance_display.setText(f"{selected_inst + 1} of {instance_count}")
				self.instance_selector_widget.setVisible(True)
			else:
				self.instance_selector_widget.setVisible(False)
		else:
			self.instance_selector_widget.setVisible(False)
		
		# Update mask UI
		self._update_mask_ui()
		
		# DON'T update transform widget here - it uses abs() which destroys flip state
		# Transform widget is updated when layer selection changes, not when UI loads
		
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
		# NOTE: Don't sync to layer_list_widget here - it manages its own UUID-based selection
		# The layer_list_widget.selected_layer_uuids is the source of truth
		
		# Get current selection from layer_list_widget (UUID-based)
		selected_uuids = self.get_selected_uuids()
		selected_count = len(selected_uuids)
		
		# Update selection indicator labels
		if hasattr(self, 'multi_select_label') and hasattr(self, 'single_layer_label'):
			if selected_count > 1:
				# Show multi-select indicator
				self.multi_select_label.setText(f"Multiple Layers Selected ({selected_count} layers)")
				self.multi_select_label.setVisible(True)
				self.single_layer_label.setVisible(False)
			elif selected_count == 1:
				# Show single layer name
				if selected_uuids:
					layer_name = self.main_window.coa.get_layer_filename(selected_uuids[0]) or 'Unknown Layer'
					self.single_layer_label.setText(f"Layer: {layer_name}")
					self.single_layer_label.setVisible(True)
				self.multi_select_label.setVisible(False)
			else:
				# No selection
				self.multi_select_label.setVisible(False)
				self.single_layer_label.setVisible(False)
		
		# Load properties for newly selected layers
		self._load_layer_properties()
		
		# Update main window menu actions (split/merge enable state)
		if self.main_window and hasattr(self.main_window, '_update_menu_actions'):
			self.main_window._update_menu_actions()	
	# ========================================
	# Pattern Mask Management
	# ========================================
	
	def _update_mask_from_ui(self):
		"""Update mask field in selected layers based on checkbox states"""
		selected_uuids = self.get_selected_uuids()
		if not selected_uuids:
			return
		
		# Build mask list from checkbox states [ch1, ch2, ch3]
		mask = []
		for i, mask_item in enumerate(self.mask_checkboxes):
			if mask_item['checkbox'].isChecked():
				mask.append(i + 1)  # Channels are 1-indexed
			else:
				mask.append(0)
		
		# If all unchecked, set to None (render everywhere)
		if all(v == 0 for v in mask):
			mask = None
		
		# Apply to all selected layers using CoA API
		for uuid in selected_uuids:
			self.main_window.coa.set_layer_mask(uuid, mask)
		# Save to history
		if self.main_window and hasattr(self.main_window, '_save_state'):
			self.main_window._save_state("Change pattern mask")
	
	def _update_mask_ui(self):
		"""Update mask checkboxes based on selected layer's mask value"""
		selected_uuids = self.get_selected_uuids()
		if not selected_uuids:
			# No selection - uncheck all
			for mask_item in self.mask_checkboxes:
				mask_item['checkbox'].blockSignals(True)
				mask_item['checkbox'].setChecked(False)
				mask_item['checkbox'].blockSignals(False)
			return
		
		# Get mask value from first selected layer using CoA API
		mask = self.main_window.coa.get_layer_mask(selected_uuids[0])
		
		# Update checkboxes based on mask value
		if mask is None:
			# No mask - uncheck all
			for mask_item in self.mask_checkboxes:
				mask_item['checkbox'].blockSignals(True)
				mask_item['checkbox'].setChecked(False)
				mask_item['checkbox'].blockSignals(False)
		else:
			# Check boxes for non-zero values in mask list
			for i, mask_item in enumerate(self.mask_checkboxes):
				mask_item['checkbox'].blockSignals(True)
				if i < len(mask) and mask[i] != 0:
					mask_item['checkbox'].setChecked(True)
				else:
					mask_item['checkbox'].setChecked(False)
				mask_item['checkbox'].blockSignals(False)
	
	def update_mask_colors_from_base(self):
		"""Update mask channel color indicators to match base pattern colors"""
		if not hasattr(self, 'mask_checkboxes'):
			return
		
		# Get base colors from canvas
		base_colors = self.get_base_colors()
		
		# Update each mask channel indicator with corresponding base color
		for i, mask_item in enumerate(self.mask_checkboxes):
			if i < len(base_colors):
				color_rgb = base_colors[i]
				color_hex = '#{:02x}{:02x}{:02x}'.format(
					int(color_rgb[0] * 255),
					int(color_rgb[1] * 255),
					int(color_rgb[2] * 255)
				)
				mask_item['color_indicator'].setStyleSheet(f"""
					QLabel {{
						background-color: {color_hex};
						border: 2px solid rgba(255, 255, 255, 100);
						border-radius: 4px;
					}}
				""")