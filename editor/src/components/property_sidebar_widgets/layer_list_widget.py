"""
CK3 Coat of Arms Editor - Layer List Widget

Extracted from property_sidebar.py to improve organization.
Handles layer display, selection, drag-drop reordering, and inline actions.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, 
                             QHBoxLayout, QApplication, QLineEdit)
from PyQt5.QtCore import Qt, QMimeData, QByteArray, QSize
from PyQt5.QtGui import QPixmap, QDrag
import json
import math
from utils.atlas_compositor import composite_emblem_atlas, get_atlas_path
from constants import HIGH_CONTRAST_DARK, HIGH_CONTRAST_LIGHT


class LayerListWidget(QWidget):
	"""Widget for displaying and managing the layer list with drag-drop support"""
	
	def __init__(self, parent=None):
		super().__init__(parent)
		#COA INTEGRATION ACTION: Step 3 - Add CoA model reference (set externally)
		self.coa = None  # Reference to CoA model (will be set by MainWindow)
		self.selected_layer_uuids = set()  # Track selection by UUID
		self.last_selected_uuid = None
		self.layer_buttons = []  # List of (uuid, button) tuples
		self.container_markers = []  # List of (container_uuid, marker_widget) tuples
		self.collapsed_containers = set()  # Track which containers are collapsed (UI state only)
		self.drop_zones = []
		self.active_drop_zone = None
		self.drag_start_uuid = None
		self.drag_start_pos = None
		self.thumbnail_cache = {}  # uuid -> QPixmap cache
		self.property_sidebar = None  # Reference to parent PropertySidebar (for accessing base colors)
		self.main_window = None  # Reference to main window (for history snapshots)
		
		# Callbacks (set by parent)
		self.on_selection_changed = None
		self.on_layers_reordered = None
		self.on_duplicate_layer = None
		self.on_delete_layer = None
		self.on_color_changed = None
		self.on_visibility_toggled = None
		
		self._setup_ui()
	
	def _setup_ui(self):
		"""Setup the layer list UI"""
		main_layout = QVBoxLayout(self)
		main_layout.setContentsMargins(0, 0, 0, 0)
		main_layout.setSpacing(2)
		
		# Add "Group into Container" button (hidden by default)
		self.group_container_btn = QPushButton("📦 Group into Container")
		self.group_container_btn.setFixedHeight(30)
		self.group_container_btn.setStyleSheet("""
			QPushButton {
				background-color: rgba(100, 150, 100, 100);
				border: 1px solid rgba(150, 200, 150, 100);
				border-radius: 4px;
				color: white;
				font-weight: bold;
			}
			QPushButton:hover {
				background-color: rgba(120, 170, 120, 120);
			}
		""")
		self.group_container_btn.clicked.connect(self._create_container_from_selection)
		self.group_container_btn.hide()  # Hidden by default
		main_layout.addWidget(self.group_container_btn)
		
		# Create container for layers
		layers_container = QWidget()
		self.layers_layout = QVBoxLayout(layers_container)
		self.layers_layout.setContentsMargins(0, 0, 0, 0)
		self.layers_layout.setSpacing(2)
		self.layers_layout.addStretch()
		main_layout.addWidget(layers_container)
		
		# Enable drag and drop
		self.setAcceptDrops(True)
	
	def set_layers(self, layers):
		"""DEPRECATED: Kept for compatibility. Widget now reads from CoA directly."""
		pass
	
	def rebuild(self):
		"""Rebuild the layer list UI from CoA model with container support"""
		if not self.coa:
			return
		
		# Clear existing layer buttons, container markers, and drop zones
		for uuid, btn in self.layer_buttons:
			btn.deleteLater()
		self.layer_buttons.clear()
		
		for container_uuid, marker in self.container_markers:
			marker.deleteLater()
		self.container_markers.clear()
		
		for zone in self.drop_zones:
			zone.deleteLater()
		self.drop_zones.clear()
		
		# Clear all widgets from layout
		while self.layers_layout.count() > 0:
			item = self.layers_layout.takeAt(0)
			if item.widget():
				item.widget().deleteLater()
			elif item.spacerItem():
				pass
		
		# Get all layer UUIDs and containers
		all_uuids = self.coa.get_all_layer_uuids()
		all_containers = self.coa.get_all_containers()
		
		# Build container structure: map container_uuid -> [layer_uuids in that container]
		container_map = {}
		root_layers = []
		
		for uuid in all_uuids:
			container_uuid = self.coa.get_layer_container(uuid)
			if container_uuid is None:
				root_layers.append(uuid)
			else:
				if container_uuid not in container_map:
					container_map[container_uuid] = []
				container_map[container_uuid].append(uuid)
		
		# Determine display order: containers and root layers interleaved by layer position
		# Build display items list: each item is either ('root', uuid) or ('container', container_uuid)
		display_items = []
		for uuid in all_uuids:
			container_uuid = self.coa.get_layer_container(uuid)
			if container_uuid is None:
				# Root layer
				display_items.append(('root', uuid))
			else:
				# Check if this is the first layer in the container (add container marker once)
				container_layers = container_map.get(container_uuid, [])
				if container_layers and uuid == container_layers[0]:
					# First layer in container - add container marker here
					display_items.append(('container', container_uuid))
		
		# Reverse for display (top to bottom)
		display_items.reverse()
		
		# Add drop zone at top
		layout_pos = 0
		self._add_drop_zone(len(all_uuids), layout_pos)
		layout_pos += 1
		
		# Add display items (containers with their layers, and root layers)
		for item_type, item_id in display_items:
			if item_type == 'root':
				# Add root layer
				uuid = item_id
				layer_btn = self._create_layer_button(uuid, indented=False)
				self.layers_layout.insertWidget(layout_pos, layer_btn)
				self.layer_buttons.append((uuid, layer_btn))
				layout_pos += 1
				
				# Add drop zone after this layer
				actual_index = all_uuids.index(uuid)
				self._add_drop_zone(actual_index, layout_pos)
				layout_pos += 1
				
			elif item_type == 'container':
				# Add container marker
				container_uuid = item_id
				container_marker = self._create_container_marker(container_uuid)
				self.layers_layout.insertWidget(layout_pos, container_marker)
				self.container_markers.append((container_uuid, container_marker))
				layout_pos += 1
				
				# Check if container is collapsed
				is_collapsed = container_uuid in self.collapsed_containers
				
				if not is_collapsed:
					# Add container's layers (indented)
					container_layers = container_map.get(container_uuid, [])
					# Reverse the container layers for display
					container_layers_reversed = list(reversed(container_layers))
					
					for layer_uuid in container_layers_reversed:
						layer_btn = self._create_layer_button(layer_uuid, indented=True)
						self.layers_layout.insertWidget(layout_pos, layer_btn)
						self.layer_buttons.append((layer_uuid, layer_btn))
						layout_pos += 1
						
						# Add drop zone after each sub-layer
						actual_index = all_uuids.index(layer_uuid)
						self._add_drop_zone(actual_index, layout_pos, indented=True)
						layout_pos += 1
		
		# Re-add stretch at the end
		self.layers_layout.addStretch()
	
	def _create_layer_button(self, uuid, indented=False):
		"""Create a layer button widget from UUID"""
		if not self.coa:
			return QPushButton()
		
		# Query properties from CoA using UUID
		filename = self.coa.get_layer_filename(uuid)
		instance_count = self.coa.get_layer_instance_count(uuid)
		
		# Create container widget for indentation
		container_widget = QWidget()
		container_layout = QHBoxLayout(container_widget)
		container_layout.setContentsMargins(0, 0, 0, 0)
		container_layout.setSpacing(0)
		
		# Add indentation if this is a sub-layer
		if indented:
			indent_spacer = QWidget()
			indent_spacer.setFixedWidth(20)  # 20px indent
			container_layout.addWidget(indent_spacer)
		
		layer_btn = QPushButton()
		layer_btn.setCheckable(True)
		layer_btn.setFixedHeight(60)
		layer_btn.setProperty('layer_uuid', uuid)
		layer_btn.clicked.connect(lambda checked: self._select_layer_by_uuid(uuid))
		
		# Enable drag functionality
		layer_btn.mousePressEvent = lambda event, u=uuid, btn=layer_btn: self._layer_mouse_press(event, u, btn)
		layer_btn.mouseMoveEvent = lambda event, u=uuid, btn=layer_btn: self._layer_mouse_move(event, u, btn)
		
		# Create layout for layer button content
		btn_layout = QHBoxLayout(layer_btn)
		btn_layout.setContentsMargins(5, 5, 5, 5)
		btn_layout.setSpacing(8)
		
		# Add preview icon with dynamic coloring and badge overlay
		icon_container = QWidget()
		icon_container.setFixedSize(48, 48)
		icon_container_layout = QVBoxLayout(icon_container)
		icon_container_layout.setContentsMargins(0, 0, 0, 0)
		icon_container_layout.setSpacing(0)
		
		icon_label = QLabel()
		icon_label.setFixedSize(48, 48)
		icon_label.setStyleSheet("border: 1px solid rgba(255, 255, 255, 40); border-radius: 3px;")
		
		# Generate colored thumbnail
		thumbnail = self._generate_layer_thumbnail(uuid, size=48)
		if thumbnail and not thumbnail.isNull():
			icon_label.setPixmap(thumbnail)
		
		icon_container_layout.addWidget(icon_label)
		
		# Add instance count badge for multi-instance layers
		if instance_count > 1:
			badge = QLabel(str(instance_count))
			badge.setStyleSheet("""
				QLabel {
					background-color: #5a8dbf;
					color: white;
					border: 1px solid rgba(255, 255, 255, 60);
					border-radius: 3px;
					font-size: 9px;
					font-weight: bold;
					padding: 2px 4px;
				}
			""")
			badge.setAlignment(Qt.AlignCenter)
			badge.setFixedSize(18, 16)  # Fixed size to prevent stretching
			# Position badge in top-right corner
			badge.setParent(icon_container)
			badge.move(28, 2)  # Adjusted position to be in corner
			badge.raise_()
		
		btn_layout.addWidget(icon_container)
		
		# Add layer name - query from CoA by UUID using get_layer_name()
		layer_name = self.coa.get_layer_name(uuid) if self.coa else 'Empty Layer'
		
		# Create editable name label
		name_widget = QWidget()
		name_widget.setStyleSheet("border: none;")
		name_layout = QVBoxLayout(name_widget)
		name_layout.setContentsMargins(0, 0, 0, 0)
		name_layout.setSpacing(0)
		
		name_label = QLabel(layer_name)
		name_label.setWordWrap(True)
		name_label.setStyleSheet("border: none; font-size: 11px;")
		name_label.setProperty('layer_uuid', uuid)
		
		# Enable double-click to edit
		name_label.mouseDoubleClickEvent = lambda event, u=uuid, lbl=name_label: self._start_name_edit(event, u, lbl, name_widget, name_layout)
		
		# Add tooltip for multi-instance layers
		if instance_count > 1:
			instance_word = "instances" if instance_count > 1 else "instance"
			name_label.setToolTip(f"Multi-instance layer ({instance_count} {instance_word}). Double-click to rename.")
		else:
			name_label.setToolTip("Double-click to rename")
		
		name_layout.addWidget(name_label)
		btn_layout.addWidget(name_widget, stretch=1)
		
		# Add inline color, duplicate and delete buttons
		button_container = self._create_inline_buttons(uuid)
		btn_layout.addWidget(button_container)
		
		# Check if multi-instance for blue tint
		is_multi_instance = instance_count > 1
		
		if is_multi_instance:
			# Blue tint for multi-instance layers
			layer_btn.setStyleSheet("""
				QPushButton {
					text-align: left;
					border: 1px solid rgba(90, 141, 191, 60);
					border-radius: 4px;
					background-color: rgba(90, 141, 191, 20);
				}
				QPushButton:hover {
					background-color: rgba(90, 141, 191, 35);
					border: 1px solid rgba(90, 141, 191, 80);
				}
				QPushButton:checked {
					border: 2px solid #5a8dbf;
					background-color: rgba(90, 141, 191, 45);
				}
			""")
		else:
			# Normal style for single-instance layers
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
		
		# Add button to container layout and return container
		container_layout.addWidget(layer_btn)
		return container_widget
	
	def _create_container_marker(self, container_uuid):
		"""Create a container marker widget"""
		if not self.coa:
			return QWidget()
		
		# Parse container name from container_uuid
		# Format: "container_{uuid}_{name}"
		parts = container_uuid.split('_', 2)
		container_name = parts[2] if len(parts) >= 3 else "Container"
		
		# Check if collapsed
		is_collapsed = container_uuid in self.collapsed_containers
		
		marker_btn = QPushButton()
		marker_btn.setCheckable(True)  # Make it selectable
		marker_btn.setFixedHeight(40)
		marker_btn.setProperty('container_uuid', container_uuid)
		marker_btn.clicked.connect(lambda checked: self._select_container(container_uuid))
		
		# Enable drag functionality for container marker
		marker_btn.mousePressEvent = lambda event, c_uuid=container_uuid, btn=marker_btn: \
			self._container_mouse_press(event, c_uuid, btn)
		marker_btn.mouseMoveEvent = lambda event, c_uuid=container_uuid, btn=marker_btn: \
			self._container_mouse_move(event, c_uuid, btn)
		
		# Create layout
		btn_layout = QHBoxLayout(marker_btn)
		btn_layout.setContentsMargins(5, 5, 5, 5)
		btn_layout.setSpacing(8)
		
		# Add expand/collapse button
		toggle_btn = QPushButton("[+]" if is_collapsed else "[-]")
		toggle_btn.setFixedSize(24, 24)
		toggle_btn.setToolTip("Expand/Collapse Container")
		toggle_btn.setStyleSheet("""
			QPushButton {
				border: 1px solid rgba(255, 255, 255, 60);
				border-radius: 2px;
				background-color: rgba(255, 255, 255, 10);
				font-size: 10px;
				font-weight: bold;
				padding: 0px;
			}
			QPushButton:hover {
				background-color: rgba(255, 255, 255, 30);
			}
		""")
		toggle_btn.clicked.connect(lambda: self._toggle_container_collapse(container_uuid))
		btn_layout.addWidget(toggle_btn)
		
		# Add folder icon (📁)
		icon_label = QLabel("📁")
		icon_label.setFixedSize(24, 24)
		icon_label.setStyleSheet("border: none; font-size: 18px;")
		btn_layout.addWidget(icon_label)
		
		# Add container name (editable)
		name_widget = QWidget()
		name_widget.setStyleSheet("border: none;")
		name_layout = QVBoxLayout(name_widget)
		name_layout.setContentsMargins(0, 0, 0, 0)
		
		name_label = QLabel(container_name)
		name_label.setStyleSheet("border: none; font-size: 11px; font-weight: bold;")
		name_label.setProperty('container_uuid', container_uuid)
		name_label.setToolTip("Double-click to rename container")
		
		# Enable double-click to edit
		name_label.mouseDoubleClickEvent = lambda event, c_uuid=container_uuid, lbl=name_label: \
			self._start_container_name_edit(event, c_uuid, lbl, name_widget, name_layout)
		
		name_layout.addWidget(name_label)
		btn_layout.addWidget(name_widget, stretch=1)
		
		# Add container action buttons
		action_container = self._create_container_buttons(container_uuid)
		btn_layout.addWidget(action_container)
		
		# Styling
		marker_btn.setStyleSheet("""
			QPushButton {
				text-align: left;
				border: 1px solid rgba(200, 200, 100, 60);
				border-radius: 4px;
				background-color: rgba(200, 200, 100, 15);
			}
			QPushButton:hover {
				background-color: rgba(200, 200, 100, 25);
				border: 1px solid rgba(200, 200, 100, 80);
			}
			QPushButton:checked {
				border: 2px solid #c8c864;
				background-color: rgba(200, 200, 100, 35);
			}
		""")
		
		return marker_btn
	
	def _create_inline_buttons(self, uuid):
		"""Create inline duplicate, delete, and color buttons for a layer"""
		button_container = QWidget()
		button_container.setStyleSheet("border: none;")
		inline_layout = QHBoxLayout(button_container)
		inline_layout.setContentsMargins(0, 0, 0, 0)
		inline_layout.setSpacing(2)
		
		# Color buttons container (stacked vertically like traffic lights)
		# Query metadata for color count based on texture filename
		from utils.metadata_cache import get_texture_color_count
		filename = self.coa.get_layer_filename(uuid)
		num_colors = get_texture_color_count(filename)
		
		color_container = QWidget()
		color_container.setStyleSheet("border: none;")
		color_layout = QVBoxLayout(color_container)
		color_layout.setContentsMargins(0, 0, 0, 0)
		color_layout.setSpacing(1)
		
		# Create color buttons based on layer's color count
		for color_idx in range(1, num_colors + 1):
			color_btn = QPushButton()
			color_btn.setFixedSize(16, 16)
			color_btn.setToolTip(f"Color {color_idx}")
			
			# Get current color from CoA by UUID
			color_rgb = self.coa.get_layer_color(uuid, color_idx) or [1.0, 1.0, 1.0]
			r, g, b = int(color_rgb[0] * 255), int(color_rgb[1] * 255), int(color_rgb[2] * 255)
			
			color_btn.setStyleSheet(f"""
				QPushButton {{
					border: 1px solid rgba(255, 255, 255, 80);
					border-radius: 2px;
					background-color: rgb({r}, {g}, {b});
					padding: 0px;
				}}
				QPushButton:hover {{
					border: 2px solid rgba(255, 255, 255, 150);
				}}
			""")
			color_btn.clicked.connect(lambda checked, u=uuid, c_idx=color_idx: self._handle_color_pick(u, c_idx))
			color_layout.addWidget(color_btn)
		
		# Add stretch if less than 3 colors to maintain vertical spacing
		if num_colors < 3:
			color_layout.addStretch()
		
		inline_layout.addWidget(color_container)
		
		# Add small gap between color and action buttons
		inline_layout.addSpacing(3)
		
		# Action buttons container (visibility/duplicate/delete)
		action_container = QWidget()
		action_container.setStyleSheet("border: none;")
		action_layout = QVBoxLayout(action_container)
		action_layout.setContentsMargins(0, 0, 0, 0)
		action_layout.setSpacing(2)
		
		# Visibility toggle button - query from CoA by UUID
		visible = self.coa.get_layer_visible(uuid)
		if visible is None:
			visible = True
		visibility_btn = QPushButton("👁" if visible else "🚫")
		visibility_btn.setFixedSize(20, 20)
		visibility_btn.setToolTip("Toggle Visibility")
		visibility_btn.setStyleSheet("""
			QPushButton {
				border: 1px solid rgba(255, 255, 255, 60);
				border-radius: 2px;
				background-color: rgba(255, 255, 255, 10);
				font-size: 10px;
				padding: 0px;
				text-align: center;
			}
			QPushButton:hover {
				background-color: rgba(141, 191, 90, 100);
			}
		""")
		visibility_btn.clicked.connect(lambda checked: self._handle_visibility_toggle(uuid))
		action_layout.addWidget(visibility_btn)
		
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
		duplicate_btn.clicked.connect(lambda checked: self._handle_duplicate(uuid))
		action_layout.addWidget(duplicate_btn)
		
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
		delete_btn.clicked.connect(lambda checked: self._handle_delete(uuid))
		action_layout.addWidget(delete_btn)
		
		inline_layout.addWidget(action_container)
		
		return button_container
	
	def _create_container_buttons(self, container_uuid):
		"""Create action buttons for container (visibility/duplicate/delete)"""
		button_container = QWidget()
		button_container.setStyleSheet("border: none;")
		action_layout = QVBoxLayout(button_container)
		action_layout.setContentsMargins(0, 0, 0, 0)
		action_layout.setSpacing(2)
		
		# Visibility toggle button - aggregate state from all layers
		container_layers = self.coa.get_layers_by_container(container_uuid)
		any_visible = any(self.coa.get_layer_visible(uuid) for uuid in container_layers)
		
		visibility_btn = QPushButton("👁" if any_visible else "🚫")
		visibility_btn.setFixedSize(20, 20)
		visibility_btn.setToolTip("Toggle Container Visibility")
		visibility_btn.setStyleSheet("""
			QPushButton {
				border: 1px solid rgba(255, 255, 255, 60);
				border-radius: 2px;
				background-color: rgba(255, 255, 255, 10);
				font-size: 10px;
				padding: 0px;
				text-align: center;
			}
			QPushButton:hover {
				background-color: rgba(141, 191, 90, 100);
			}
		""")
		visibility_btn.clicked.connect(lambda: self._handle_container_visibility_toggle(container_uuid))
		action_layout.addWidget(visibility_btn)
		
		# Duplicate button
		duplicate_btn = QPushButton("⎘")
		duplicate_btn.setFixedSize(20, 20)
		duplicate_btn.setToolTip("Duplicate Container")
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
		duplicate_btn.clicked.connect(lambda: self._handle_container_duplicate(container_uuid))
		action_layout.addWidget(duplicate_btn)
		
		# Delete button
		delete_btn = QPushButton("×")
		delete_btn.setFixedSize(20, 20)
		delete_btn.setToolTip("Delete Container")
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
		delete_btn.clicked.connect(lambda: self._handle_container_delete(container_uuid))
		action_layout.addWidget(delete_btn)
		
		return button_container
	
	def _start_name_edit(self, event, uuid, label, name_widget, name_layout):
		"""Start inline editing of layer name"""
		if not self.coa:
			return
		
		# Get current name
		current_name = self.coa.get_layer_name(uuid)
		
		# Hide label
		label.hide()
		
		# Create line edit
		line_edit = QLineEdit(current_name)
		line_edit.setStyleSheet("""
			QLineEdit {
				border: 1px solid #5a8dbf;
				border-radius: 2px;
				background-color: rgba(255, 255, 255, 200);
				color: black;
				font-size: 11px;
				padding: 2px;
			}
		""")
		line_edit.setProperty('layer_uuid', uuid)
		line_edit.setProperty('original_label', label)
		
		# Connect signals
		line_edit.editingFinished.connect(lambda: self._finish_name_edit(uuid, line_edit, label, name_widget))
		line_edit.returnPressed.connect(lambda: self._finish_name_edit(uuid, line_edit, label, name_widget))
		
		# Add to layout and focus
		name_layout.addWidget(line_edit)
		line_edit.setFocus()
		line_edit.selectAll()
	
	def _finish_name_edit(self, uuid, line_edit, label, name_widget):
		"""Finish inline editing of layer name"""
		if not self.coa:
			return
		
		# Get old name for comparison
		old_name = self.coa.get_layer_name(uuid)
		
		# Get new name
		new_name = line_edit.text().strip()
		
		# If empty, revert to default (texture filename)
		if not new_name:
			# Setting empty string triggers default in Layer.name property
			new_name = ''
		
		# Update CoA model
		self.coa.set_layer_name(uuid, new_name)
		
		# Update label text with actual name (might be defaulted)
		actual_name = self.coa.get_layer_name(uuid)
		label.setText(actual_name)
		
		# Create snapshot if name actually changed
		if old_name != actual_name and self.main_window:
			self.main_window._save_state(f"Rename layer to '{actual_name}'")
		
		# Remove line edit and show label again
		line_edit.deleteLater()
		label.show()
	
	def _layer_mouse_press(self, event, uuid, button):
		"""Handle mouse press on layer button for drag start"""
		if event.button() == Qt.LeftButton:
			self.drag_start_uuid = uuid
			self.drag_start_pos = event.pos()
		QPushButton.mousePressEvent(button, event)
	
	def _layer_mouse_move(self, event, uuid, button):
		"""Handle mouse move on layer button for drag operation"""
		if not (event.buttons() & Qt.LeftButton):
			return
		
		if self.drag_start_uuid is None:
			return
		
		# Check if dragged far enough
		if (event.pos() - self.drag_start_pos).manhattanLength() < 10:
			return
		
		# Get selected indices (for multi-layer drag)
		selected_indices = self.get_selected_indices()
		
		# If dragged layer is not in selection, make it the only selection
		# Convert button position (idx in layer_buttons) to CoA index
		button_idx = None
		for idx, (btn_uuid, _) in enumerate(self.layer_buttons):
			if btn_uuid == uuid:
				button_idx = idx
				break
		
		if button_idx is None:
			return
		
		if button_idx not in selected_indices:
			selected_indices = [button_idx]
			self.selected_layer_uuids = {uuid}
			self.update_selection_visuals()
		
		# Start drag with selected UUIDs (convert from indices)
		selected_uuids = [self.layer_buttons[idx][0] for idx in selected_indices if idx < len(self.layer_buttons)]
		
		# Sort UUIDs by CoA layer order (bottom to top) to preserve stacking
		if selected_uuids and self.coa:
			selected_uuids.sort(key=lambda uuid: self.coa.get_layer_index_by_uuid(uuid) or 0)
		
		drag = QDrag(button)
		mime_data = QMimeData()
		mime_data.setData('application/x-layer-uuids', QByteArray(json.dumps(selected_uuids).encode('utf-8')))
		drag.setMimeData(mime_data)
		
		drag.exec_(Qt.MoveAction)
		self.drag_start_uuid = None
	
	def _container_mouse_press(self, event, container_uuid, button):
		"""Handle mouse press on container marker for drag start"""
		if event.button() == Qt.LeftButton:
			self.drag_start_uuid = container_uuid  # Store container UUID
			self.drag_start_pos = event.pos()
		QPushButton.mousePressEvent(button, event)
	
	def _container_mouse_move(self, event, container_uuid, button):
		"""Handle mouse move on container marker for drag operation"""
		if not (event.buttons() & Qt.LeftButton):
			return
		
		if self.drag_start_uuid is None:
			return
		
		# Check if dragged far enough
		if (event.pos() - self.drag_start_pos).manhattanLength() < 10:
			return
		
		# Start drag with container UUID
		drag = QDrag(button)
		mime_data = QMimeData()
		# Use different format to distinguish from layer drag
		mime_data.setData('application/x-container-uuid', QByteArray(container_uuid.encode('utf-8')))
		drag.setMimeData(mime_data)
		
		drag.exec_(Qt.MoveAction)
		self.drag_start_uuid = None
	
	def dragEnterEvent(self, event):
		"""Handle drag enter on layer list"""
		if event.mimeData().hasFormat('application/x-layer-uuids') or \
		   event.mimeData().hasFormat('application/x-container-uuid'):
			event.accept()
		else:
			event.ignore()
	
	def dragMoveEvent(self, event):
		"""Handle drag move over layer list and highlight drop zones"""
		if event.mimeData().hasFormat('application/x-layer-uuids') or \
		   event.mimeData().hasFormat('application/x-container-uuid'):
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
	
	def dropEvent(self, event):
		"""Handle drop on layer list to reorder layers or containers"""
		# Clear drop zone highlight
		if self.active_drop_zone:
			self.active_drop_zone.setProperty('highlighted', 'false')
			self.active_drop_zone.style().unpolish(self.active_drop_zone)
			self.active_drop_zone.style().polish(self.active_drop_zone)
			self.active_drop_zone = None
		
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
		
		# Get drop zone properties
		target_index = closest_zone.property('drop_index')
		is_indented = closest_zone.property('indented') or False
		
		# Handle layer drag
		if event.mimeData().hasFormat('application/x-layer-uuids'):
			dragged_uuids_json = bytes(event.mimeData().data('application/x-layer-uuids')).decode('utf-8')
			dragged_uuids = json.loads(dragged_uuids_json)
			
			if not dragged_uuids:
				event.ignore()
				return
			
			# Determine target container based on drop zone
			target_container = None
			if is_indented:
				# Dropping in sub-zone - find which container this zone belongs to
				target_uuid = self.coa.get_layer_uuid_by_index(target_index) if target_index < self.coa.get_layer_count() else None
				if target_uuid:
					target_container = self.coa.get_layer_container(target_uuid)
			# else: root zone, target_container stays None
			
			# Move layers
			if target_index == 0:
				self.coa.move_layer_to_bottom(dragged_uuids)
			elif target_index >= self.coa.get_layer_count():
				self.coa.move_layer_to_top(dragged_uuids)
			else:
				target_uuid = self.coa.get_layer_uuid_by_index(target_index)
				self.coa.move_layer_above(dragged_uuids, target_uuid)
			
			# Update container assignment for all dragged layers
			for uuid in dragged_uuids:
				self.coa.set_layer_container(uuid, target_container)
			
			# Update selection
			self.selected_layer_uuids = set(dragged_uuids)
			self.last_selected_uuid = dragged_uuids[-1] if dragged_uuids else None
			
			self.rebuild()
			self.update_selection_visuals()
			
			if self.on_layers_reordered:
				self.on_layers_reordered(len(dragged_uuids))
			
			event.accept()
		
		# Handle container drag
		elif event.mimeData().hasFormat('application/x-container-uuid'):
			container_uuid = bytes(event.mimeData().data('application/x-container-uuid')).decode('utf-8')
			
			if not container_uuid:
				event.ignore()
				return
			
			# Reject drop on indented zones (no nesting)
			if is_indented:
				event.ignore()
				return
			
			# Get all layers in the container
			container_layers = self.coa.get_layers_by_container(container_uuid)
			if not container_layers:
				event.ignore()
				return
			
			# Move all container layers as a unit
			if target_index == 0:
				self.coa.move_layer_to_bottom(container_layers)
			elif target_index >= self.coa.get_layer_count():
				self.coa.move_layer_to_top(container_layers)
			else:
				target_uuid = self.coa.get_layer_uuid_by_index(target_index)
				self.coa.move_layer_above(container_layers, target_uuid)
			
			# Rebuild and maintain selection
			self.rebuild()
			self.selected_layer_uuids = set(container_layers)
			self.update_selection_visuals()
			
			if self.on_layers_reordered:
				self.on_layers_reordered(len(container_layers))
			
			event.accept()
		
		else:
			event.ignore()
	
	def _add_drop_zone(self, drop_index, layout_position, indented=False):
		"""Add a drop zone separator at the specified position"""
		# Create container for indentation support
		container = QWidget()
		container_layout = QHBoxLayout(container)
		container_layout.setContentsMargins(0, 0, 0, 0)
		container_layout.setSpacing(0)
		
		# Add indentation if needed
		if indented:
			indent_spacer = QWidget()
			indent_spacer.setFixedWidth(20)  # 20px indent
			container_layout.addWidget(indent_spacer)
		
		drop_zone = QWidget()
		drop_zone.setFixedHeight(8)
		drop_zone.setProperty('drop_index', drop_index)
		drop_zone.setProperty('indented', indented)
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
		
		container_layout.addWidget(drop_zone)
		self.drop_zones.append(drop_zone)
		self.layers_layout.insertWidget(layout_position, container)
	
	def _get_preview_path(self, dds_path):
		"""Convert .dds filename to .png preview path"""
		import os
		from ..asset_sidebar import TEXTURE_PREVIEW_MAP
		
		# Check if it's already a full path
		if os.path.exists(dds_path):
			return dds_path
		
		# Extract just the filename
		filename = os.path.basename(dds_path) if '/' in dds_path or '\\' in dds_path else dds_path
		
		# Look up in the global texture preview map
		return TEXTURE_PREVIEW_MAP.get(filename)
	
	def _select_layer_by_uuid(self, uuid):
		"""Handle layer selection by UUID with modifier key support"""
		modifiers = QApplication.keyboardModifiers()
		ctrl_pressed = modifiers & Qt.ControlModifier
		shift_pressed = modifiers & Qt.ShiftModifier
		
		if shift_pressed and self.last_selected_uuid is not None:
			# Shift+Click: Range selection - need to select all UUIDs between last and current
			# Get indices of both UUIDs to determine range
			current_idx = None
			last_idx = None
			for idx, (btn_uuid, _) in enumerate(self.layer_buttons):
				if btn_uuid == uuid:
					current_idx = idx
				if btn_uuid == self.last_selected_uuid:
					last_idx = idx
			
			if current_idx is not None and last_idx is not None:
				start = min(current_idx, last_idx)
				end = max(current_idx, last_idx)
				# Select all UUIDs in range
				self.selected_layer_uuids = set()
				for idx in range(start, end + 1):
					if idx < len(self.layer_buttons):
						self.selected_layer_uuids.add(self.layer_buttons[idx][0])
		elif ctrl_pressed:
			# Ctrl+Click: Toggle selection
			if uuid in self.selected_layer_uuids:
				self.selected_layer_uuids.discard(uuid)
			else:
				self.selected_layer_uuids.add(uuid)
			self.last_selected_uuid = uuid
		else:
			# Regular click: Single selection
			if uuid in self.selected_layer_uuids and len(self.selected_layer_uuids) == 1:
				# Clicking the only selected layer - deselect it
				self.selected_layer_uuids.clear()
				self.last_selected_uuid = None
			else:
				self.selected_layer_uuids = {uuid}
				self.last_selected_uuid = uuid
		
		# Update UI
		self.update_selection_visuals()
		
		# Notify parent
		if self.on_selection_changed:
			self.on_selection_changed()
	
	def _select_container(self, container_uuid):
		"""Handle container selection - multi-selects all contained layers"""
		if not self.coa:
			return
		
		modifiers = QApplication.keyboardModifiers()
		ctrl_pressed = modifiers & Qt.ControlModifier
		
		# Get all layers in this container
		container_layers = set(self.coa.get_layers_by_container(container_uuid))
		
		if ctrl_pressed:
			# Ctrl+Click: Toggle all layers in container
			if container_layers.issubset(self.selected_layer_uuids):
				# All layers selected, deselect them
				self.selected_layer_uuids -= container_layers
			else:
				# Add all layers to selection
				self.selected_layer_uuids.update(container_layers)
		else:
			# Regular click: Select only these layers
			self.selected_layer_uuids = container_layers.copy()
		
		# Update last selected (use first layer in container)
		if container_layers:
			self.last_selected_uuid = next(iter(container_layers))
		
		# Update UI
		self.update_selection_visuals()
		
		# Notify parent
		if self.on_selection_changed:
			self.on_selection_changed()
	
	def _select_layer(self, index):
		"""Handle layer selection with modifier key support (DEPRECATED - use _select_layer_by_uuid)"""
		# Convert index to UUID and delegate
		if index < len(self.layer_buttons):
			uuid = self.layer_buttons[index][0]
			self._select_layer_by_uuid(uuid)
	
	def update_selection_visuals(self):
		"""Update which layer buttons and container markers are checked"""
		# Update layer buttons
		for uuid, btn in self.layer_buttons:
			btn.setChecked(uuid in self.selected_layer_uuids)
		
		# Update container markers (checked if all layers in container are selected)
		for container_uuid, marker in self.container_markers:
			container_layers = set(self.coa.get_layers_by_container(container_uuid)) if self.coa else set()
			all_selected = container_layers and container_layers.issubset(self.selected_layer_uuids)
			marker.setChecked(all_selected)
		
		# Show/hide "Group into Container" button
		# Show if 2+ layers selected and they're not all from the same container
		if len(self.selected_layer_uuids) >= 2:
			# Check if all selected layers have same container_uuid
			container_uuids = set()
			for uuid in self.selected_layer_uuids:
				container_uuid = self.coa.get_layer_container(uuid) if self.coa else None
				container_uuids.add(container_uuid)
			
			# Show button if mixed containers or all at root
			if len(container_uuids) > 1 or (len(container_uuids) == 1 and None in container_uuids):
				self.group_container_btn.show()
			else:
				self.group_container_btn.hide()
		else:
			self.group_container_btn.hide()
		
		if self.on_selection_changed:
			self.on_selection_changed()
	
	def get_selected_uuids(self):
		"""Get list of selected layer UUIDs (primary selection API)"""
		return list(self.selected_layer_uuids)
	
	def get_selected_indices(self):
		"""Get sorted list of selected layer indices (DEPRECATED - converts from UUIDs)"""
		indices = []
		for idx, (btn_uuid, _) in enumerate(self.layer_buttons):
			if btn_uuid in self.selected_layer_uuids:
				indices.append(idx)
		return sorted(indices)
	
	def set_selected_indices(self, indices):
		"""Update selection state with new indices (converts to UUIDs)"""
		self.selected_layer_uuids.clear()
		for idx in indices:
			if idx < len(self.layer_buttons):
				self.selected_layer_uuids.add(self.layer_buttons[idx][0])
		self.update_selection_visuals()
		if self.on_selection_changed:
			self.on_selection_changed()
	
	def clear_selection(self):
		"""Clear selection and update UI"""
		self.selected_layer_uuids.clear()
		self.last_selected_uuid = None
		self.update_selection_visuals()
		if self.on_selection_changed:
			self.on_selection_changed()
	
	def mousePressEvent(self, event):
		"""Handle mouse press on empty space to clear selection"""
		if event.button() == Qt.LeftButton:
			# Check if we clicked on empty space (not on any child widget)
			child = self.childAt(event.pos())
			if child is None or child == self:
				# Clicked on empty space - clear selection
				self.clear_selection()
		super().mousePressEvent(event)
	
	def _handle_duplicate(self, uuid):
		"""Handle duplicate button click"""
		if self.on_duplicate_layer:
			# Pass UUID directly instead of converting to index
			self.on_duplicate_layer(uuid)
	
	def _handle_delete(self, uuid):
		"""Handle delete button click"""
		if self.on_delete_layer:
			# Pass UUID directly instead of converting to index
			self.on_delete_layer(uuid)
	
	def _handle_visibility_toggle(self, uuid):
		"""Handle visibility toggle button click"""
		if self.on_visibility_toggled:
			# Pass UUID directly instead of converting to index
			self.on_visibility_toggled(uuid)
	
	def _handle_color_pick(self, uuid, color_index):
		"""Handle color button click - open color picker"""
		if self.on_color_changed:
			# Pass UUID directly instead of converting to index
			self.on_color_changed(uuid, color_index)
	
	def _toggle_container_collapse(self, container_uuid):
		"""Toggle container expand/collapse state"""
		if container_uuid in self.collapsed_containers:
			self.collapsed_containers.remove(container_uuid)
		else:
			self.collapsed_containers.add(container_uuid)
		# Rebuild to reflect new state
		self.rebuild()
	
	def _handle_container_visibility_toggle(self, container_uuid):
		"""Toggle visibility for all layers in container"""
		if not self.coa:
			return
		
		container_layers = self.coa.get_layers_by_container(container_uuid)
		
		# Determine new visibility state (toggle based on current aggregate)
		any_visible = any(self.coa.get_layer_visible(uuid) for uuid in container_layers)
		new_visibility = not any_visible
		
		# Set visibility for all layers in container
		for uuid in container_layers:
			self.coa.set_layer_visible(uuid, new_visibility)
		
		# Rebuild UI to reflect changes
		self.rebuild()
		
		# Trigger callback if exists
		if self.on_visibility_toggled:
			# Notify with first layer UUID (or could notify all)
			if container_layers:
				self.on_visibility_toggled(container_layers[0])
	
	def _handle_container_duplicate(self, container_uuid):
		"""Duplicate entire container"""
		if not self.coa or not self.main_window:
			return
		
		# Create snapshot for undo
		self.main_window._save_state("Duplicate Container")
		
		# Duplicate the container (creates new layers with new container_uuid)
		new_container_uuid = self.coa.duplicate_container(container_uuid)
		
		# Rebuild UI to show new container
		self.rebuild()
		
		# Select the new container's layers
		new_container_layers = set(self.coa.get_layers_by_container(new_container_uuid))
		self.selected_layer_uuids = new_container_layers
		self.update_selection_visuals()
		
		# Trigger callback
		if self.on_selection_changed:
			self.on_selection_changed()
	
	def _handle_container_delete(self, container_uuid):
		"""Delete container (moves layers to root)"""
		if not self.coa or not self.main_window:
			return
		
		# Create snapshot for undo
		self.main_window._save_state("Delete Container")
		
		# Set all layers in container to None (moves to root)
		container_layers = self.coa.get_layers_by_container(container_uuid)
		for uuid in container_layers:
			self.coa.set_layer_container(uuid, None)
		
		# Rebuild UI
		self.rebuild()
		
		# Trigger callback if selection changes
		if self.on_selection_changed:
			self.on_selection_changed()
	
	def _start_container_name_edit(self, event, container_uuid, label, name_widget, name_layout):
		"""Start inline editing of container name"""
		if not self.coa:
			return
		
		# Parse current name from container_uuid
		parts = container_uuid.split('_', 2)
		current_name = parts[2] if len(parts) >= 3 else "Container"
		
		# Hide label
		label.hide()
		
		# Create line edit
		line_edit = QLineEdit(current_name)
		line_edit.setStyleSheet("""
			QLineEdit {
				border: 1px solid #5a8dbf;
				border-radius: 2px;
				background-color: rgba(255, 255, 255, 200);
				color: black;
				font-size: 11px;
				padding: 2px;
			}
		""")
		line_edit.setProperty('container_uuid', container_uuid)
		line_edit.setProperty('original_label', label)
		
		# Connect signals
		line_edit.returnPressed.connect(lambda: self._finish_container_name_edit(line_edit, name_widget, name_layout))
		line_edit.editingFinished.connect(lambda: self._finish_container_name_edit(line_edit, name_widget, name_layout))
		
		# Add to layout and focus
		name_layout.addWidget(line_edit)
		line_edit.setFocus()
		line_edit.selectAll()
	
	def _finish_container_name_edit(self, line_edit, name_widget, name_layout):
		"""Finish editing container name"""
		if not self.coa or not self.main_window:
			return
		
		new_name = line_edit.text().strip()
		old_container_uuid = line_edit.property('container_uuid')
		original_label = line_edit.property('original_label')
		
		if not new_name:
			# Empty name, cancel edit
			line_edit.deleteLater()
			original_label.show()
			return
		
		# Parse old UUID portion
		parts = old_container_uuid.split('_', 2)
		if len(parts) >= 2:
			uuid_portion = parts[1]
			
			# Build new container_uuid
			new_container_uuid = f"container_{uuid_portion}_{new_name}"
			
			# Create snapshot for undo
			self.main_window._save_state("Rename Container")
			
			# Update all layers with old container_uuid to new one
			container_layers = self.coa.get_layers_by_container(old_container_uuid)
			for layer_uuid in container_layers:
				self.coa.set_layer_container(layer_uuid, new_container_uuid)
			
			# Update label text
			original_label.setText(new_name)
			original_label.setProperty('container_uuid', new_container_uuid)
			
			# Update collapsed state tracking
			if old_container_uuid in self.collapsed_containers:
				self.collapsed_containers.remove(old_container_uuid)
				self.collapsed_containers.add(new_container_uuid)
		
		# Clean up and show label
		line_edit.deleteLater()
		original_label.show()
		
		# Rebuild to reflect changes
		self.rebuild()
	
	def _create_container_from_selection(self):
		"""Create a new container from selected layers"""
		if not self.coa or not self.main_window:
			return
		
		if len(self.selected_layer_uuids) < 2:
			return
		
		# Create snapshot for undo
		self.main_window._save_state("Create Container")
		
		# Create container
		layer_list = list(self.selected_layer_uuids)
		new_container_uuid = self.coa.create_container_from_layers(layer_list, name="Container")
		
		# Rebuild UI
		self.rebuild()
		
		# Keep selection on the newly grouped layers
		self.selected_layer_uuids = set(layer_list)
		self.update_selection_visuals()
		
		# Trigger callback
		if self.on_selection_changed:
			self.on_selection_changed()
	
	def _uuid_to_index(self, uuid):
		"""Convert UUID to index by searching layer_buttons list"""
		for idx, (btn_uuid, _) in enumerate(self.layer_buttons):
			if btn_uuid == uuid:
				return idx
		return None
	
	def _generate_layer_thumbnail(self, uuid, size=48):
		"""Generate a dynamically colored thumbnail for a layer
		
		Args:
			uuid: UUID of layer in CoA model
			size: Thumbnail size (square)
		
		Returns:
			QPixmap thumbnail or None
		"""
		# Check cache first
		cache_key = (uuid, size)
		if cache_key in self.thumbnail_cache:
			return self.thumbnail_cache[cache_key]
		
		# Query layer properties from CoA by UUID
		filename = self.coa.get_layer_filename(uuid)
		
		if not filename:
			return None
		
		from utils.color_utils import get_contrasting_background
		
		# Get actual layer colors (in 0-1 range) - query from CoA
		emblem_color1 = self.coa.get_layer_color(uuid, 1) or [0.75, 0.525, 0.188]
		
		# Get base background color from property sidebar (not from layer data)
		if self.property_sidebar and hasattr(self.property_sidebar, 'get_base_colors'):
			base_colors = self.property_sidebar.get_base_colors()
			base_background_color1 = base_colors[0] if len(base_colors) > 0 else [0.45, 0.133, 0.090]
		else:
			base_background_color1 = [0.45, 0.133, 0.090]
		
		# Choose background color with smart contrast
		background_color = get_contrasting_background(emblem_color1, base_background_color1)
		
		# Extract colors from CoA (already in 0-1 range)
		colors = {
			'color1': tuple(self.coa.get_layer_color(uuid, 1) or [0.75, 0.525, 0.188]),
			'color2': tuple(self.coa.get_layer_color(uuid, 2) or [0.45, 0.133, 0.090]),
			'color3': tuple(self.coa.get_layer_color(uuid, 3) or [0.45, 0.133, 0.090]),
			'background1': background_color
		}
		
		try:
			# Try atlas compositor first
			atlas_path = get_atlas_path(filename, 'emblem')
			if atlas_path.exists():
				thumbnail = composite_emblem_atlas(str(atlas_path), colors, size=size)
				if thumbnail and not thumbnail.isNull():
					self.thumbnail_cache[cache_key] = thumbnail
					return thumbnail
		except Exception as e:
			pass
		
		# Fallback to static preview
		preview_path = self._get_preview_path(filename)
		if preview_path:
			pixmap = QPixmap(preview_path)
			if not pixmap.isNull():
				thumbnail = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
				self.thumbnail_cache[cache_key] = thumbnail
				return thumbnail
		
		return None
	
	def invalidate_thumbnail(self, uuid):
		"""Invalidate cached thumbnail for a specific layer by UUID"""
		# Remove all size variants for this layer UUID
		keys_to_remove = [k for k in self.thumbnail_cache.keys() if k[0] == uuid]
		for key in keys_to_remove:
			del self.thumbnail_cache[key]
	
	def clear_thumbnail_cache(self):
		"""Clear all cached thumbnails"""
		self.thumbnail_cache.clear()
	
	def update_layer_button(self, uuid):
		"""Update a single layer button's display by querying all data from UUID
		
		This method is called when external property changes occur (color, visibility, etc.)
		It queries fresh data from CoA and metadata, then updates the UI.
		
		Args:
			uuid: UUID of the layer to update
		"""
		if not self.coa:
			return
		
		# Find the button for this UUID
		button = None
		for btn_uuid, btn in self.layer_buttons:
			if btn_uuid == uuid:
				button = btn
				break
		
		if not button:
			return
		
		# Query fresh properties from CoA
		filename = self.coa.get_layer_filename(uuid)
		instance_count = self.coa.get_layer_instance_count(uuid)
		# Query metadata for color count based on texture filename
		from utils.metadata_cache import get_texture_color_count
		num_colors = get_texture_color_count(filename)
		visible = self.coa.get_layer_visible(uuid)
		if visible is None:
			visible = True
		
		# Find the UI components within the button
		layout = button.layout()
		if not layout:
			return
		
		# Update icon/thumbnail (component 0 = icon_container)
		if layout.count() > 0:
			icon_container = layout.itemAt(0).widget()
			if icon_container:
				# Find the icon label
				icon_layout = icon_container.layout()
				if icon_layout and icon_layout.count() > 0:
					icon_label = icon_layout.itemAt(0).widget()
					if isinstance(icon_label, QLabel):
						# Invalidate and regenerate thumbnail
						self.invalidate_thumbnail(uuid)
						thumbnail = self._generate_layer_thumbnail(uuid, size=48)
						if thumbnail and not thumbnail.isNull():
							icon_label.setPixmap(thumbnail)
				
				# Update instance count badge
				# Remove old badge if it exists
				for child in icon_container.children():
					if isinstance(child, QLabel) and child != icon_layout.itemAt(0).widget():
						child.deleteLater()
				
				# Add new badge if needed
				if instance_count > 1:
					badge = QLabel(str(instance_count))
					badge.setStyleSheet("""
						QLabel {
							background-color: #5a8dbf;
							color: white;
							border: 1px solid rgba(255, 255, 255, 60);
							border-radius: 3px;
							font-size: 9px;
							font-weight: bold;
							padding: 2px 4px;
						}
					""")
					badge.setAlignment(Qt.AlignCenter)
					badge.setFixedSize(18, 16)  # Fixed size to prevent stretching
					badge.setParent(icon_container)
					badge.move(28, 2)  # Adjusted position to be in corner
					badge.raise_()
		
		# Update name label (component 1)
		if layout.count() > 1:
			name_label = layout.itemAt(1).widget()
			if isinstance(name_label, QLabel):
				layer_name = filename or 'Empty Layer'
				if layer_name.lower().endswith('.dds'):
					layer_name = layer_name[:-4]
				name_label.setText(layer_name)
				
				# Update tooltip
				if instance_count > 1:
					instance_word = "instances" if instance_count > 1 else "instance"
					name_label.setToolTip(f"Multi-instance layer ({instance_count} {instance_word})")
				else:
					name_label.setToolTip("")
		
		# Update inline buttons (component 2 = button_container)
		if layout.count() > 2:
			button_container = layout.itemAt(2).widget()
			if button_container:
				inline_layout = button_container.layout()
				if inline_layout:
					# Find color_container (first widget)
					if inline_layout.count() > 0:
						color_container = inline_layout.itemAt(0).widget()
						if color_container:
							color_layout = color_container.layout()
							if color_layout:
								# Remove all existing color buttons
								while color_layout.count():
									item = color_layout.takeAt(0)
									if item.widget():
										item.widget().deleteLater()
								
								# Create new color buttons based on current color count
								for color_idx in range(1, num_colors + 1):
									color_btn = QPushButton()
									color_btn.setFixedSize(16, 16)
									color_btn.setToolTip(f"Color {color_idx}")
									
									# Get current color from CoA by UUID
									color_rgb = self.coa.get_layer_color(uuid, color_idx) or [1.0, 1.0, 1.0]
									r, g, b = int(color_rgb[0] * 255), int(color_rgb[1] * 255), int(color_rgb[2] * 255)
									
									color_btn.setStyleSheet(f"""
										QPushButton {{
											border: 1px solid rgba(255, 255, 255, 80);
											border-radius: 2px;
											background-color: rgb({r}, {g}, {b});
											padding: 0px;
										}}
										QPushButton:hover {{
											border: 2px solid rgba(255, 255, 255, 150);
										}}
									""")
									color_btn.clicked.connect(lambda checked, u=uuid, c_idx=color_idx: self._handle_color_pick(u, c_idx))
									color_layout.addWidget(color_btn)
								
								# Add stretch if less than 3 colors
								if num_colors < 3:
									color_layout.addStretch()
		
		# Update button style based on instance count
		is_multi_instance = instance_count > 1
		if is_multi_instance:
			button.setStyleSheet("""
				QPushButton {
					text-align: left;
					border: 1px solid rgba(90, 141, 191, 60);
					border-radius: 4px;
					background-color: rgba(90, 141, 191, 20);
				}
				QPushButton:hover {
					background-color: rgba(90, 141, 191, 35);
					border: 1px solid rgba(90, 141, 191, 80);
				}
				QPushButton:checked {
					border: 2px solid #5a8dbf;
					background-color: rgba(90, 141, 191, 45);
				}
			""")
		else:
			button.setStyleSheet("""
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
	

	def update_all_buttons(self):
		"""Update all layer buttons by querying fresh data from CoA
		
		This method is called when external bulk property changes occur.
		It updates all visible buttons without full rebuild.
		"""
		for uuid, _ in self.layer_buttons:
			self.update_layer_button(uuid)
