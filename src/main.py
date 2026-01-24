import re
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QSplitter, QApplication, QFileDialog, QMessageBox, QStatusBar, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPalette, QColor

from components.toolbar import create_toolbar
from components.asset_sidebar import AssetSidebar
from components.canvas_area import CanvasArea
from components.property_sidebar import PropertySidebar
from utils.coa_parser import parse_coa_string, serialize_coa_to_string
from utils.history_manager import HistoryManager
from utils.color_utils import color_name_to_rgb, rgb_to_color_name
from services.file_operations import (
    save_coa_to_file, load_coa_from_file, 
    build_coa_for_save, coa_to_clipboard_text, is_layer_subblock
)
from services.layer_operations import (
    duplicate_layer, serialize_layer_to_text, parse_layer_from_text,
    parse_multiple_layers_from_text
)


class CoatOfArmsEditor(QMainWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("Coat Of Arms Designer")
		self.resize(1280, 720)
		self.setMinimumSize(1280, 720)
		
		# Initialize history manager
		self.history_manager = HistoryManager(max_history=50)
		self.history_manager.add_listener(self._on_history_changed)
		
		# Debounce timer for property changes (avoid spamming history on slider drags)
		self.property_change_timer = QTimer()
		self.property_change_timer.setSingleShot(True)
		self.property_change_timer.timeout.connect(self._save_property_change)
		self._pending_property_change = None
		
		# Flag to prevent saving state during undo/redo
		self._is_applying_history = False
		
		self.setup_ui()
	
	def setup_ui(self):
		# Create top toolbar
		create_toolbar(self)
		
		# Create central widget with splitter
		central_widget = QWidget()
		self.setCentralWidget(central_widget)
		
		main_layout = QHBoxLayout(central_widget)
		main_layout.setContentsMargins(0, 0, 0, 0)
		main_layout.setSpacing(0)
		
		# Create splitter for resizable panels
		splitter = QSplitter(Qt.Horizontal)
		
		# Left sidebar - scrollable assets
		self.left_sidebar = AssetSidebar(self)
		splitter.addWidget(self.left_sidebar)
		
		# Center canvas area
		self.canvas_area = CanvasArea(self)
		splitter.addWidget(self.canvas_area)
		
		# Right properties sidebar
		self.right_sidebar = PropertySidebar(self)
		self.right_sidebar.main_window = self
		splitter.addWidget(self.right_sidebar)
		
		# Connect canvas to property sidebar for layer updates
		self.right_sidebar.canvas_widget = self.canvas_area.canvas_widget
		self.right_sidebar.canvas_area = self.canvas_area
		
		# Connect canvas area to property sidebar for transform widget
		self.canvas_area.set_property_sidebar(self.right_sidebar)
		self.canvas_area.main_window = self
		
		# Initialize base colors in canvas from property sidebar
		base_colors = self.right_sidebar.get_base_colors()
		self.canvas_area.canvas_widget.set_base_colors(base_colors)
		
		# Connect property tab changes to asset sidebar mode
		self.right_sidebar.tab_widget.currentChanged.connect(self._on_property_tab_changed)
		
		# Connect asset selection to update color swatches
		self.left_sidebar.asset_selected.connect(self._on_asset_selected)
		
		# Set initial sizes (left: 250px, center: flex, right: 300px)
		splitter.setSizes([250, 730, 300])
		splitter.setCollapsible(0, False)
		splitter.setCollapsible(1, False)
		splitter.setCollapsible(2, False)
		
		main_layout.addWidget(splitter)
		
		# Add status bar at bottom with left and right sections
		self.status_left = QLabel("Ready")
		self.status_right = QLabel("")
		self.statusBar().addWidget(self.status_left, 1)  # stretch=1 for left
		self.statusBar().addPermanentWidget(self.status_right)  # permanent widget for right
		self.statusBar().setStyleSheet("QStatusBar { border-top: 1px solid rgba(255, 255, 255, 40); padding: 4px; }")
		
		# Update status bar with initial stats
		self._update_status_bar()
		
		# Note: Cannot set frame/base here - OpenGL not initialized yet
		# Will be set after show() triggers initializeGL()
	
	def _on_property_tab_changed(self, index):
		"""Handle property tab changes to switch asset sidebar mode"""
		# Index 0 = Base tab (show patterns), other tabs (show emblems)
		if index == 0:
			self.left_sidebar.switch_mode("patterns")
		else:
			self.left_sidebar.switch_mode("emblems")
	
	def _on_asset_selected(self, asset_data):
		"""Handle asset selection - update color swatches based on asset color count"""
		print(f"[_on_asset_selected] Asset selected: {asset_data}")
		
		color_count = asset_data.get("colors", 1)
		filename = asset_data.get("filename")
		
		print(f"[_on_asset_selected] filename: {filename}, color_count: {color_count}")
		
		# Update color swatches based on which tab is active
		current_tab = self.right_sidebar.tab_widget.currentIndex()
		print(f"[_on_asset_selected] current_tab: {current_tab}")
		
		if current_tab == 0:  # Base tab
			print(f"[_on_asset_selected] Base tab - setting base texture: {filename}")
			self.right_sidebar.set_base_color_count(color_count)
			# Base is not a layer, update canvas base texture
			if filename:
				self.canvas_area.canvas_widget.set_base_texture(filename)
				# Save to history (base texture changed)
				self._save_state("Change base texture")
		else:  # Layers or Properties tab
			print(f"[_on_asset_selected] Layers/Properties tab - setting emblem color count")
			self.right_sidebar.set_emblem_color_count(color_count)
			
			# If a layer is selected, update it with the new asset
			selected_indices = self.right_sidebar.get_selected_indices()
			print(f"[_on_asset_selected] selected_indices: {selected_indices}")
			if selected_indices:
				idx = selected_indices[0]
				print(f"[_on_asset_selected] Updating layer {idx}")
				if 0 <= idx < len(self.right_sidebar.layers):
					# Preserve existing properties when updating asset
					old_layer = self.right_sidebar.layers[idx]
					print(f"[_on_asset_selected] Old layer: {old_layer}")
					
					# Use DDS filename for both filename and path (texture system expects DDS)
					dds_filename = asset_data.get('dds_filename', asset_data.get('filename', ''))
					print(f"[_on_asset_selected] Using DDS filename: {dds_filename}")
					
					new_layer = {
						'filename': dds_filename,
						'path': dds_filename,
						'colors': color_count,
						'depth': old_layer.get('depth', idx),  # Preserve depth
						'pos_x': old_layer.get('pos_x', 0.5),
						'pos_y': old_layer.get('pos_y', 0.5),
					'scale_x': old_layer.get('scale_x', 1.0),
					'scale_y': old_layer.get('scale_y', 1.0),
					'rotation': old_layer.get('rotation', 0),
					'color1': old_layer.get('color1', [0.750, 0.525, 0.188]),
					'color2': old_layer.get('color2', [0.450, 0.133, 0.090]),
					'color3': old_layer.get('color3', [0.450, 0.133, 0.090]),
						'color1_name': old_layer.get('color1_name'),
						'color2_name': old_layer.get('color2_name'),
						'color3_name': old_layer.get('color3_name')
					}
					self.right_sidebar.layers[idx] = new_layer
					print(f"[_on_asset_selected] New layer: {new_layer}")
					
					print(f"[_on_asset_selected] Rebuilding layer list")
					self.right_sidebar._rebuild_layer_list()
					self.right_sidebar._update_layer_selection()
					
					print(f"[_on_asset_selected] Updating canvas with {len(self.right_sidebar.layers)} layers")
					# Update canvas with new layers
					self.canvas_area.canvas_widget.set_layers(self.right_sidebar.layers)
					print(f"[_on_asset_selected] Canvas updated successfully")
					
					# Save to history (layer texture changed)
					self._save_state("Change layer texture")
			else:
				# No layer selected - create a new layer at the top with this asset
				print(f"[_on_asset_selected] No layer selected - creating new layer at top")
				dds_filename = asset_data.get('dds_filename', asset_data.get('filename', ''))
				
				new_layer = {
					'filename': dds_filename,
					'path': dds_filename,
					'colors': color_count,
					'depth': 0,
					'pos_x': 0.5,
					'pos_y': 0.5,
					'scale_x': 0.5,
					'scale_y': 0.5,
					'rotation': 0,
					'color1': [0.750, 0.525, 0.188],
					'color2': [0.450, 0.133, 0.090],
					'color3': [0.450, 0.133, 0.090],
					'color1_name': None,
					'color2_name': None,
					'color3_name': None
				}
				
				# Insert at the beginning (top of stack)
				self.right_sidebar.layers.insert(0, new_layer)
				
				# Select the new layer
				self.right_sidebar.selected_layer_indices = {0}
				
				# Update UI
				self.right_sidebar._rebuild_layer_list()
				self.right_sidebar._update_layer_selection()
				self.right_sidebar._load_layer_properties()
				
				# Enable Properties tab
				self.right_sidebar.tab_widget.setTabEnabled(2, True)
				
				# Update canvas and transform widget
				self.canvas_area.canvas_widget.set_layers(self.right_sidebar.layers)
				if self.canvas_area:
					self.canvas_area.update_transform_widget_for_layer(0)
				
				# Save to history (new layer created)
				self._save_state("Create layer")
				
				print(f"[_on_asset_selected] New layer created and selected at index 0")
	
	def resizeEvent(self, event):
		"""Handle window resize to recalculate grid columns in asset sidebar"""
		super().resizeEvent(event)
		if hasattr(self, 'left_sidebar'):
			self.left_sidebar.handle_resize()
	
	def showEvent(self, event):
		"""Handle window show - save initial state after UI is set up"""
		super().showEvent(event)
		# Save initial state on first show (after OpenGL is initialized)
		if not hasattr(self, '_initial_state_saved'):
			self._initial_state_saved = True
			# Use a timer to ensure everything is fully initialized
			QTimer.singleShot(100, lambda: self._save_state("Initial state"))
	
	def keyPressEvent(self, event):
		"""Handle keyboard shortcuts"""
		# Ctrl+S for save
		if event.key() == Qt.Key_S and event.modifiers() == Qt.ControlModifier:
			self.save_coa()
			event.accept()
		# Ctrl+D for duplicate layer
		elif event.key() == Qt.Key_D and event.modifiers() == Qt.ControlModifier:
			if self.right_sidebar.get_selected_indices():
				self.duplicate_selected_layer()
				event.accept()
			else:
				super().keyPressEvent(event)
		# Ctrl+Z for undo
		elif event.key() == Qt.Key_Z and event.modifiers() == Qt.ControlModifier:
			self.undo()
			event.accept()
		# Ctrl+Y for redo
		elif event.key() == Qt.Key_Y and event.modifiers() == Qt.ControlModifier:
			self.redo()
			event.accept()
		# Ctrl+C for copy layer
		elif event.key() == Qt.Key_C and event.modifiers() == Qt.ControlModifier:
			if self.right_sidebar.get_selected_indices():
				self.copy_layer()
				event.accept()
			else:
				super().keyPressEvent(event)
		# Ctrl+V for paste layer - will be handled by canvas_area if over canvas
		elif event.key() == Qt.Key_V and event.modifiers() == Qt.ControlModifier:
			# Check if mouse is over canvas
			if hasattr(self, 'canvas_area'):
				mouse_pos = self.canvas_area.mapFromGlobal(self.cursor().pos())
				canvas_geometry = self.canvas_area.canvas_widget.geometry()
				if canvas_geometry.contains(mouse_pos):
					# Mouse is over canvas, paste at mouse position
					self.paste_layer_at_position(mouse_pos, canvas_geometry)
					event.accept()
					return
			# Otherwise, paste at center
			self.paste_layer()
			event.accept()
		else:
			super().keyPressEvent(event)
	
	def _capture_current_state(self):
		"""Capture the current state for history"""
		canvas = self.canvas_area.canvas_widget
		
		state = {
			'layers': [dict(layer) for layer in self.right_sidebar.layers],  # Deep copy
			'selected_layer_indices': set(self.right_sidebar.selected_layer_indices),  # Copy set
			'base_texture': canvas.base_texture,
			'base_colors': canvas.base_colors[:],  # Copy list
			'base_color1_name': getattr(canvas, 'base_color1_name', None),
			'base_color2_name': getattr(canvas, 'base_color2_name', None),
			'base_color3_name': getattr(canvas, 'base_color3_name', None),
			# TODO: Add frame and splendor level when implemented
		}
		return state
	
	def _restore_state(self, state):
		"""Restore a state from history"""
		if not state:
			return
		
		self._is_applying_history = True
		try:
			# Restore layers
			self.right_sidebar.layers = [dict(layer) for layer in state['layers']]
			self.right_sidebar.selected_layer_indices = set(state.get('selected_layer_indices', set()))
			self.right_sidebar._rebuild_layer_list()
			self.right_sidebar._update_layer_selection()
			
			# Restore base
			self.canvas_area.canvas_widget.set_base_texture(state['base_texture'])
			self.canvas_area.canvas_widget.set_base_colors(state['base_colors'])
			self.canvas_area.canvas_widget.base_color1_name = state.get('base_color1_name')
			self.canvas_area.canvas_widget.base_color2_name = state.get('base_color2_name')
			self.canvas_area.canvas_widget.base_color3_name = state.get('base_color3_name')
			
			# Update property sidebar base colors
			base_color_names = [
				state.get('base_color1_name'),
				state.get('base_color2_name'),
				state.get('base_color3_name')
			]
			self.right_sidebar.set_base_colors(state['base_colors'], base_color_names)
			
			# Restore canvas layers
			self.canvas_area.canvas_widget.set_layers(self.right_sidebar.layers)
			
			# Update layer properties if a layer is selected
			selected_indices = list(state.get('selected_layer_indices', set()))
			if selected_indices:
				self.right_sidebar._load_layer_properties()
				self.canvas_area.update_transform_widget_for_layer(selected_indices[0])
				self.right_sidebar.tab_widget.setTabEnabled(2, True)
			else:
				self.right_sidebar.tab_widget.setTabEnabled(2, False)
				self.canvas_area.transform_widget.set_visible(False)
		finally:
			self._is_applying_history = False
			# Update status bar after state is fully restored
			self._update_status_bar()
	
	def _save_state(self, description):
		"""Save current state to history"""
		if self._is_applying_history:
			return  # Don't save state during undo/redo
		
		state = self._capture_current_state()
		self.history_manager.save_state(state, description)
	
	def _save_property_change(self):
		"""Called by timer to save property change to history (debounced)"""
		if self._pending_property_change:
			self._save_state(self._pending_property_change)
			self._pending_property_change = None
	
	def save_property_change_debounced(self, description):
		"""
		Schedule a property change to be saved after a delay.
		This prevents spamming the history when dragging sliders.
		"""
		self._pending_property_change = description
		self.property_change_timer.stop()
		self.property_change_timer.start(500)  # 500ms delay
	
	def _on_history_changed(self, can_undo, can_redo):
		"""Called when history state changes to update UI"""
		if hasattr(self, 'undo_btn'):
			self.undo_btn.setEnabled(can_undo)
		if hasattr(self, 'redo_btn'):
			self.redo_btn.setEnabled(can_redo)
		# Update status bar with current action
		self._update_status_bar()
	
	def _update_status_bar(self):
		"""Update status bar with current action and stats"""
		# Left side: Last action
		current_desc = self.history_manager.get_current_description()
		if current_desc:
			left_msg = f"Last action: {current_desc}"
		else:
			left_msg = "Ready"
		
		# Right side: Stats
		layer_count = len(self.right_sidebar.layers) if hasattr(self, 'right_sidebar') else 0
		selected_indices = self.right_sidebar.get_selected_indices() if hasattr(self, 'right_sidebar') else []
		
		if selected_indices:
			right_msg = f"Layers: {layer_count} | Selected: Layer {selected_indices[0] + 1}"
		else:
			right_msg = f"Layers: {layer_count} | No selection"
		
		# Update labels
		if hasattr(self, 'status_left'):
			self.status_left.setText(left_msg)
		if hasattr(self, 'status_right'):
			self.status_right.setText(right_msg)
	
	def undo(self):
		"""Undo the last action"""
		state = self.history_manager.undo()
		if state:
			self._restore_state(state)
			print(f"Undid: {self.history_manager.get_current_description()}")
	
	def redo(self):
		"""Redo the last undone action"""
		state = self.history_manager.redo()
		if state:
			self._restore_state(state)
			print(f"Redid: {self.history_manager.get_current_description()}")
	
	def new_coa(self):
		"""Clear everything and start with default empty CoA"""
		try:
			# Confirm with user
			reply = QMessageBox.question(
				self,
				"New Coat of Arms",
				"Are you sure you want to create a new coat of arms?\n\nAll unsaved changes will be lost.",
				QMessageBox.Yes | QMessageBox.No,
				QMessageBox.No
			)
			
			if reply == QMessageBox.No:
				return
			
			# Clear all layers
			self.right_sidebar.layers = []
			self.right_sidebar.clear_selection()
			self.right_sidebar._rebuild_layer_list()
			
			# Reset base to default pattern and colors (CK3 defaults: black, yellow, black)
			default_pattern = "pattern__solid.dds"
			default_color_names = ['black', 'yellow', 'black']
			default_colors = [
				color_name_to_rgb('black'),
				color_name_to_rgb('yellow'),
				color_name_to_rgb('black')
			]
			
			self.canvas_area.canvas_widget.set_base_texture(default_pattern)
			self.canvas_area.canvas_widget.set_base_colors(default_colors)
			self.canvas_area.canvas_widget.set_layers([])
			
			# Reset property sidebar base colors with color names
			self.right_sidebar.set_base_colors(default_colors, default_color_names)
			
			# Switch to Base tab
			self.right_sidebar.tab_widget.setCurrentIndex(0)
			
			# Clear history and save initial state
			self.history_manager.clear()
			self._save_state("New CoA")
			
			print("New CoA created - reset to defaults")
		except Exception as e:
			print(f"Error creating new CoA: {e}")
			import traceback
			traceback.print_exc()
	
	def save_coa(self):
		"""Save current CoA to .txt file"""
		try:
			# Get current state
			canvas = self.canvas_area.canvas_widget
			base_colors = self.right_sidebar.get_base_colors()
			base_color_names = [
				getattr(canvas, 'base_color1_name', 'black'),
				getattr(canvas, 'base_color2_name', 'yellow'),
				getattr(canvas, 'base_color3_name', 'black')
			]
			
			# Build CoA data structure using service
			coa_data = build_coa_for_save(
				base_colors, 
				canvas.base_texture, 
				self.right_sidebar.layers,
				base_color_names
			)
			
			# Open save file dialog
			filename, _ = QFileDialog.getSaveFileName(
				self,
				"Save Coat of Arms",
				"",
				"Text Files (*.txt);;All Files (*)"
			)
			
			if filename:
				save_coa_to_file(coa_data, filename)
			
		except Exception as e:
			print(f"Error saving CoA: {e}")
			import traceback
			traceback.print_exc()
			QMessageBox.critical(self, "Save Error", f"Failed to save coat of arms:\n{str(e)}")
	
	def load_coa(self):
		"""Load CoA from .txt file"""
		try:
			# Open file dialog
			filename, _ = QFileDialog.getOpenFileName(
				self,
				"Load Coat of Arms",
				"",
				"Text Files (*.txt);;All Files (*)"
			)
			
			if not filename:
				return
			
			# Load and parse file using service
			coa_data = load_coa_from_file(filename)
			
			# Apply to editor
			self._apply_coa_data(coa_data)
			
			# Clear history and save initial state after loading
			self.history_manager.clear()
			self._save_state("Load CoA")
			
		except Exception as e:
			print(f"Error loading CoA: {e}")
			import traceback
			traceback.print_exc()
			QMessageBox.critical(self, "Load Error", f"Failed to load coat of arms:\n{str(e)}\n\nThe file may not contain valid coat of arms data.")
	
	def copy_coa(self):
		"""Copy current CoA to clipboard as text"""
		try:
			# Get current state
			canvas = self.canvas_area.canvas_widget
			base_colors = self.right_sidebar.get_base_colors()
			base_color_names = [
				getattr(canvas, 'base_color1_name', 'black'),
				getattr(canvas, 'base_color2_name', 'yellow'),
				getattr(canvas, 'base_color3_name', 'black')
			]
			
			# Build clipboard text using service
			coa_text = coa_to_clipboard_text(
				base_colors,
				canvas.base_texture,
				self.right_sidebar.layers,
				base_color_names
			)
			
			# Copy to clipboard
			QApplication.clipboard().setText(coa_text)
			print("CoA copied to clipboard")
			
		except Exception as e:
			print(f"Error copying CoA: {e}")
			import traceback
			traceback.print_exc()
	
	def paste_coa(self):
		"""Paste CoA from clipboard and apply to editor"""
		try:
			# Get clipboard text
			coa_text = QApplication.clipboard().text()
			if not coa_text.strip():
				print("Clipboard is empty")
				QMessageBox.warning(self, "Paste Error", "Clipboard is empty.")
				return
			
			# Smart detection: check if this is a layer sub-block or full CoA
			if is_layer_subblock(coa_text):
				# This is a layer, paste as layer instead
				self.paste_layer()
				return
			
			# Parse CoA data
			coa_data = parse_coa_string(coa_text)
			if not coa_data:
				raise ValueError("Failed to parse coat of arms data - not a valid CK3 format")
			
			# Apply to editor
			self._apply_coa_data(coa_data)
			
			# Save to history after pasting
			self._save_state("Paste CoA")
			
		except Exception as e:
			print(f"Error pasting CoA: {e}")
			import traceback
			traceback.print_exc()
			QMessageBox.critical(self, "Paste Error", f"Failed to paste coat of arms:\n{str(e)}\n\nThe clipboard may not contain valid coat of arms data.")
	
	def copy_layer(self):
		"""Copy all selected layers to clipboard as CoA sub-blocks"""
		try:
			# Check if layers are selected
			selected_indices = self.right_sidebar.get_selected_indices()
			if not selected_indices:
				print("No layer selected to copy")
				return
			
			# Serialize all selected layers using service
			layer_texts = []
			for layer_idx in selected_indices:
				if 0 <= layer_idx < len(self.right_sidebar.layers):
					layer = self.right_sidebar.layers[layer_idx]
					layer_text = serialize_layer_to_text(layer)
					layer_texts.append(layer_text)
			
			if not layer_texts:
				print("No valid layers to copy")
				return
			
			# Join all layer texts (each is already a complete colored_emblem block)
			full_text = '\n\n'.join(layer_texts)
			
			# Copy to clipboard
			QApplication.clipboard().setText(full_text)
			layer_word = "layers" if len(selected_indices) > 1 else "layer"
			print(f"{len(selected_indices)} {layer_word} copied to clipboard")
			
		except Exception as e:
			print(f"Error copying layer: {e}")
			import traceback
			traceback.print_exc()
	
	def duplicate_selected_layer(self):
		"""Duplicate the currently selected layer (called by Ctrl+drag on transform widget)"""
		try:
			# Check if a layer is selected
			selected_indices = self.right_sidebar.get_selected_indices()
			if not selected_indices:
				print("No layer selected to duplicate")
				return
			
			layer_idx = selected_indices[0]
			layer = self.right_sidebar.layers[layer_idx]
			
			# Create a duplicate using service
			duplicated_layer = duplicate_layer(layer)
			
			# Insert at the top (index 0) - most in front
			self.right_sidebar.layers.insert(0, duplicated_layer)
			
			# Select the new duplicated layer
			self.right_sidebar.selected_layer_indices = {0}
			
			# Update UI
			self.right_sidebar._rebuild_layer_list()
			self.right_sidebar._update_layer_selection()
			self.right_sidebar._load_layer_properties()
			
			# Enable Properties tab
			self.right_sidebar.tab_widget.setTabEnabled(2, True)
			
			# Update canvas and transform widget
			self.canvas_area.canvas_widget.set_layers(self.right_sidebar.layers)
			if self.canvas_area:
				self.canvas_area.update_transform_widget_for_layer(0)
			
			# Save to history
			self._save_state("Duplicate layer")
			
			print(f"Layer '{duplicated_layer.get('filename', 'Unknown')}' duplicated successfully")
			
		except Exception as e:
			print(f"Error duplicating layer: {e}")
			import traceback
			traceback.print_exc()
	
	def paste_layer(self):
		"""Paste layers from clipboard (as CoA sub-blocks) and add to layers"""
		try:
			# Get clipboard text
			layer_text = QApplication.clipboard().text()
			if not layer_text.strip():
				print("Paste layer failed: Clipboard is empty")
				return
			
			# Parse layers from clipboard using service
			layers_data = parse_multiple_layers_from_text(layer_text)
			
			if not layers_data:
				raise ValueError("Clipboard does not contain valid layer data")
			
			# Apply small offset to pasted layers (0.02 as per design decision)
			for layer_data in layers_data:
				layer_data['pos_x'] = min(1.0, layer_data.get('pos_x', 0.5) + 0.02)
				layer_data['pos_y'] = min(1.0, layer_data.get('pos_y', 0.5) + 0.02)
			
			# Add all layers at the end (front-most)
			start_index = len(self.right_sidebar.layers)
			self.right_sidebar.layers.extend(layers_data)
			
			# Select all newly pasted layers
			new_indices = list(range(start_index, len(self.right_sidebar.layers)))
			self.right_sidebar.selected_layer_indices = set(new_indices)
			self.right_sidebar.last_selected_index = new_indices[-1] if new_indices else None
			
			# Update UI
			self.right_sidebar._rebuild_layer_list()
			self.right_sidebar._update_layer_selection()
			self.right_sidebar._load_layer_properties()
			
			# Enable Properties tab
			self.right_sidebar.tab_widget.setTabEnabled(2, True)
			
			# Update canvas and transform widget
			self.canvas_area.canvas_widget.set_layers(self.right_sidebar.layers)
			if self.canvas_area:
				self.canvas_area.update_transform_widget_for_layer()
			
			# Save to history
			layer_word = "layers" if len(layers_data) > 1 else "layer"
			self._save_state(f"Paste {len(layers_data)} {layer_word}")
			
			print(f"{len(layers_data)} {layer_word} pasted successfully")
			
		except Exception as e:
			print(f"Paste layer failed: {e}")
			if hasattr(self, 'status_left'):
				self.status_left.setText("Paste layer failed")
			import traceback
			traceback.print_exc()
	
	def paste_layer_at_position(self, mouse_pos, canvas_geometry):
		"""Paste layer at mouse position on canvas with clamping to legal positions"""
		try:
			# Get clipboard text
			layer_text = QApplication.clipboard().text()
			if not layer_text.strip():
				print("Paste layer failed: Clipboard is empty")
				return
			
			# Parse layer from clipboard using service
			layer_data = parse_layer_from_text(layer_text)
			if not layer_data:
				raise ValueError("Clipboard does not contain valid layer data")
			
			# Convert mouse position to normalized coordinates [0-1]
			# Canvas uses 0.5 as center, so we need to map from widget coords
			canvas_size = min(canvas_geometry.width(), canvas_geometry.height())
			canvas_offset_x = (canvas_geometry.width() - canvas_size) / 2
			canvas_offset_y = (canvas_geometry.height() - canvas_size) / 2
			
			# Get mouse position relative to canvas widget
			local_x = mouse_pos.x() - canvas_geometry.x()
			local_y = mouse_pos.y() - canvas_geometry.y()
			
			# Convert to canvas center coords [-size/2, size/2]
			canvas_x = local_x - canvas_offset_x - canvas_size / 2
			canvas_y = local_y - canvas_offset_y - canvas_size / 2
			
			# Convert to normalized coords [0-1] (canvas uses 1.1 scale factor)
			norm_x = (canvas_x / (canvas_size / 2) / 1.1) + 0.5
			norm_y = (canvas_y / (canvas_size / 2) / 1.1) + 0.5
			
			# Clamp to legal positions [0-1]
			norm_x = max(0.0, min(1.0, norm_x))
			norm_y = max(0.0, min(1.0, norm_y))
			
			# Update layer position
			layer_data['pos_x'] = norm_x
			layer_data['pos_y'] = norm_y
			
			# Add layer at the top (end of list = frontmost)
			self.right_sidebar.layers.append(layer_data)
			
			# Select the new layer
			new_index = len(self.right_sidebar.layers) - 1
			self.right_sidebar.selected_layer_indices = {new_index}
			self.right_sidebar.last_selected_index = new_index  # Set for shift+click range selection
			
			# Update UI
			self.right_sidebar._rebuild_layer_list()
			self.right_sidebar._update_layer_selection()
			self.right_sidebar._load_layer_properties()
			
			# Enable Properties tab
			self.right_sidebar.tab_widget.setTabEnabled(2, True)
			
			# Update canvas and transform widget
			self.canvas_area.canvas_widget.set_layers(self.right_sidebar.layers)
			if self.canvas_area:
				self.canvas_area.update_transform_widget_for_layer()
			
			# Save to history
			self._save_state("Paste layer at position")
			
			print(f"Layer '{layer_data.get('filename', 'Unknown')}' pasted at ({norm_x:.2f}, {norm_y:.2f})")
			
		except Exception as e:
			print(f"Paste layer at position failed: {e}")
			if hasattr(self, 'status_left'):
				self.status_left.setText("Paste layer failed")
			import traceback
			traceback.print_exc()
		
	def _apply_coa_data(self, coa_data):
		"""Apply parsed CoA data to editor"""
		
		# Get the CoA object (first key)
		coa_id = list(coa_data.keys())[0]
		coa = coa_data[coa_id]
		
		# Apply base pattern
		if 'pattern' in coa:
			self.canvas_area.canvas_widget.set_base_texture(coa['pattern'])
		
		# Apply base colors (CK3 defaults: black, yellow, black)
		color1_name = coa.get('color1', 'black')
		color2_name = coa.get('color2', 'yellow')
		color3_name = coa.get('color3', 'black')
		
		base_colors = [
			color_name_to_rgb(color1_name),
			color_name_to_rgb(color2_name),
			color_name_to_rgb(color3_name)
		]
		base_color_names = [color1_name, color2_name, color3_name]
		
		self.canvas_area.canvas_widget.set_base_colors(base_colors)
		self.right_sidebar.set_base_colors(base_colors, base_color_names)
		
		# Clear existing layers
		self.right_sidebar.layers = []
		
		# Collect all emblem instances with their depth values
		emblem_instances = []
		for emblem in coa.get('colored_emblem', []):
			filename = emblem.get('texture', '')
			
			# Get instances, or create default if none exist
			instances = emblem.get('instance', [])
			if not instances:
				# No instance block means default values
				instances = [{'position': [0.5, 0.5], 'scale': [1.0, 1.0], 'rotation': 0}]
			
			for instance in instances:
				# Get depth value (default to 0 if not specified)
				depth = instance.get('depth', 0)
				
				# Get color names and RGB values
				color1_name = emblem.get('color1', 'yellow')
				color2_name = emblem.get('color2', 'red')
				color3_name = emblem.get('color3', 'red')
				
				layer_data = {
					'filename': filename,
					'path': filename,  # Use filename as path - texture system and preview lookup both use this
					'colors': 3,  # Assume 3 colors for all emblems
					'pos_x': instance.get('position', [0.5, 0.5])[0],
					'pos_y': instance.get('position', [0.5, 0.5])[1],
					'scale_x': instance.get('scale', [1.0, 1.0])[0],
					'scale_y': instance.get('scale', [1.0, 1.0])[1],
					'rotation': instance.get('rotation', 0),
					'color1': color_name_to_rgb(color1_name),
					'color2': color_name_to_rgb(color2_name),
					'color3': color_name_to_rgb(color3_name),
					'color1_name': color1_name,
					'color2_name': color2_name,
					'color3_name': color3_name,
					'depth': depth
				}
				emblem_instances.append(layer_data)
		
		# Sort by depth (higher depth = further back = first in list for rendering)
		emblem_instances.sort(key=lambda x: x['depth'], reverse=True)
		
		# Add sorted layers to sidebar
		for layer_data in emblem_instances:
			# Remove depth from layer data (it's only used for sorting)
			del layer_data['depth']
			self.right_sidebar.layers.append(layer_data)
			print(f"Added layer: {layer_data['filename']} (depth order)")
		
		# Update UI - switch to Layers tab and rebuild
		self.right_sidebar.tab_widget.setCurrentIndex(1)  # Switch to Layers tab
		self.right_sidebar._rebuild_layer_list()
		if len(self.right_sidebar.layers) > 0:
			self.right_sidebar._select_layer(0)
		
		# Update canvas
		self.canvas_area.canvas_widget.set_layers(self.right_sidebar.layers)
		print(f"CoA loaded - {len(self.right_sidebar.layers)} layers created")

	def _find_asset_path(self, filename):
		"""Find the display path for an asset by filename"""
		if not filename:
			return ''
		# Try to find in the asset sidebar's loaded data
		if hasattr(self.left_sidebar, 'emblem_data'):
			for asset in self.left_sidebar.emblem_data:
				if asset.get('filename') == filename:
					return asset.get('path', '')
		return ''


def main():
	print("Starting Coat of Arms Designer...")
	app = QtWidgets.QApplication([])
	
	# Use Fusion style with dark palette
	app.setStyle("Fusion")
	
	dark_palette = QPalette()
	dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
	dark_palette.setColor(QPalette.WindowText, Qt.white)
	dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
	dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
	dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
	dark_palette.setColor(QPalette.ToolTipText, Qt.white)
	dark_palette.setColor(QPalette.Text, Qt.white)
	dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
	dark_palette.setColor(QPalette.ButtonText, Qt.white)
	dark_palette.setColor(QPalette.BrightText, Qt.red)
	dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
	dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
	dark_palette.setColor(QPalette.HighlightedText, Qt.black)
	
	app.setPalette(dark_palette)
	
	window = CoatOfArmsEditor()
	window.show()
	app.exec_()


if __name__ == "__main__":
	main()
