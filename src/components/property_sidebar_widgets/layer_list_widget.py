"""
CK3 Coat of Arms Editor - Layer List Widget

Extracted from property_sidebar.py to improve organization.
Handles layer display, selection, drag-drop reordering, and inline actions.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, 
                             QHBoxLayout, QApplication)
from PyQt5.QtCore import Qt, QMimeData, QByteArray, QSize
from PyQt5.QtGui import QPixmap, QDrag
import json


class LayerListWidget(QWidget):
	"""Widget for displaying and managing the layer list with drag-drop support"""
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.layers = []  # Reference to layers list (will be set externally)
		self.selected_layer_indices = set()
		self.last_selected_index = None
		self.layer_buttons = []
		self.drop_zones = []
		self.active_drop_zone = None
		self.drag_start_index = None
		self.drag_start_pos = None
		
		# Callbacks (set by parent)
		self.on_selection_changed = None
		self.on_layers_reordered = None
		self.on_duplicate_layer = None
		self.on_delete_layer = None
		
		self._setup_ui()
	
	def _setup_ui(self):
		"""Setup the layer list UI"""
		self.layers_layout = QVBoxLayout(self)
		self.layers_layout.setContentsMargins(0, 0, 0, 0)
		self.layers_layout.setSpacing(2)
		self.layers_layout.addStretch()
		
		# Enable drag and drop
		self.setAcceptDrops(True)
	
	def set_layers(self, layers):
		"""Set the layers list reference"""
		self.layers = layers
	
	def rebuild(self):
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
		for i in range(len(self.layers)):
			# Calculate actual layer index (reversed)
			actual_index = len(self.layers) - 1 - i
			layer_btn = self._create_layer_button(actual_index)
			
			self.layers_layout.insertWidget(layout_pos, layer_btn)
			self.layer_buttons.append(layer_btn)
			layout_pos += 1
			
			# Add drop zone after this layer
			self._add_drop_zone(actual_index, layout_pos)
			layout_pos += 1
	
	def _create_layer_button(self, actual_index):
		"""Create a layer button widget"""
		layer = self.layers[actual_index]
		layer_btn = QPushButton()
		layer_btn.setCheckable(True)
		layer_btn.setFixedHeight(60)
		layer_btn.setProperty('layer_index', actual_index)
		layer_btn.clicked.connect(lambda checked: self._select_layer(actual_index))
		
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
		
		# Add inline duplicate and delete buttons
		button_container = self._create_inline_buttons(actual_index)
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
		
		return layer_btn
	
	def _create_inline_buttons(self, actual_index):
		"""Create inline duplicate and delete buttons for a layer"""
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
		duplicate_btn.clicked.connect(lambda checked: self._handle_duplicate(actual_index))
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
		delete_btn.clicked.connect(lambda checked: self._handle_delete(actual_index))
		inline_layout.addWidget(delete_btn)
		
		return button_container
	
	def _layer_mouse_press(self, event, index, button):
		"""Handle mouse press on layer button for drag start"""
		if event.button() == Qt.LeftButton:
			self.drag_start_index = index
			self.drag_start_pos = event.pos()
		QPushButton.mousePressEvent(button, event)
	
	def _layer_mouse_move(self, event, index, button):
		"""Handle mouse move on layer button for drag operation"""
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
			self.update_selection_visuals()
		
		# Start drag with selected indices
		drag = QDrag(button)
		mime_data = QMimeData()
		mime_data.setData('application/x-layer-indices', QByteArray(json.dumps(selected_indices).encode('utf-8')))
		drag.setMimeData(mime_data)
		
		drag.exec_(Qt.MoveAction)
		self.drag_start_index = None
	
	def dragEnterEvent(self, event):
		"""Handle drag enter on layer list"""
		if event.mimeData().hasFormat('application/x-layer-indices'):
			event.accept()
		else:
			event.ignore()
	
	def dragMoveEvent(self, event):
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
	
	def dropEvent(self, event):
		"""Handle drop on layer list to reorder (supports multi-layer)"""
		# Clear drop zone highlight
		if self.active_drop_zone:
			self.active_drop_zone.setProperty('highlighted', 'false')
			self.active_drop_zone.style().unpolish(self.active_drop_zone)
			self.active_drop_zone.style().polish(self.active_drop_zone)
			self.active_drop_zone = None
		
		if event.mimeData().hasFormat('application/x-layer-indices'):
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
				insert_pos = max(0, min(len(self.layers), insert_pos))
				self.layers.insert(insert_pos, layer)
			
			# Update selection to new indices
			new_indices = list(range(adjusted_target, adjusted_target + len(dragged_layers)))
			self.selected_layer_indices = set(new_indices)
			self.last_selected_index = new_indices[-1] if new_indices else None
			
			self.rebuild()
			self.update_selection_visuals()
			
			# Notify parent of reorder
			if self.on_layers_reordered:
				self.on_layers_reordered(len(dragged_indices))
			
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
		from ..asset_sidebar import TEXTURE_PREVIEW_MAP
		
		# Check if it's already a full path
		if os.path.exists(dds_path):
			return dds_path
		
		# Extract just the filename
		filename = os.path.basename(dds_path) if '/' in dds_path or '\\' in dds_path else dds_path
		
		# Look up in the global texture preview map
		return TEXTURE_PREVIEW_MAP.get(filename)
	
	def _select_layer(self, index):
		"""Handle layer selection with modifier key support"""
		modifiers = QApplication.keyboardModifiers()
		ctrl_pressed = modifiers & Qt.ControlModifier
		shift_pressed = modifiers & Qt.ShiftModifier
		
		if shift_pressed and self.last_selected_index is not None:
			# Shift+Click: Range selection
			start = min(index, self.last_selected_index)
			end = max(index, self.last_selected_index)
			self.selected_layer_indices = set(range(start, end + 1))
		elif ctrl_pressed:
			# Ctrl+Click: Toggle selection
			if index in self.selected_layer_indices:
				self.selected_layer_indices.discard(index)
			else:
				self.selected_layer_indices.add(index)
			self.last_selected_index = index
		else:
			# Regular click: Single selection
			if index in self.selected_layer_indices and len(self.selected_layer_indices) == 1:
				# Clicking the only selected layer - deselect it
				self.selected_layer_indices.clear()
				self.last_selected_index = None
			else:
				self.selected_layer_indices = {index}
				self.last_selected_index = index
		
		# Update UI
		self.update_selection_visuals()
		
		# Notify parent
		if self.on_selection_changed:
			self.on_selection_changed()
	
	def update_selection_visuals(self):
		"""Update which layer buttons are checked"""
		for i, btn in enumerate(self.layer_buttons):
			actual_layer_index = len(self.layers) - 1 - i
			btn.setChecked(actual_layer_index in self.selected_layer_indices)
	
	def get_selected_indices(self):
		"""Get sorted list of selected layer indices"""
		return sorted(list(self.selected_layer_indices))
	
	def set_selected_indices(self, indices):
		"""Update selection state with new indices"""
		self.selected_layer_indices = set(indices) if not isinstance(indices, set) else indices
		self.update_selection_visuals()
		if self.on_selection_changed:
			self.on_selection_changed()
	
	def clear_selection(self):
		"""Clear selection and update UI"""
		self.selected_layer_indices.clear()
		self.last_selected_index = None
		self.update_selection_visuals()
		if self.on_selection_changed:
			self.on_selection_changed()
	
	def _handle_duplicate(self, index):
		"""Handle duplicate button click"""
		if self.on_duplicate_layer:
			self.on_duplicate_layer(index)
	
	def _handle_delete(self, index):
		"""Handle delete button click"""
		if self.on_delete_layer:
			self.on_delete_layer(index)
