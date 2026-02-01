import sys
import os
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Output to console
    ]
)

# DEBUG MODE: Set to True to get full tracebacks instead of popup error messages
DEBUG_MODE = True

# Add editor/src to path so imports work when running directly
if __name__ == "__main__":
	# Get the directory containing this file (editor/src)
	current_dir = os.path.dirname(os.path.abspath(__file__))
	# Add it to the Python path
	if current_dir not in sys.path:
		sys.path.insert(0, current_dir)

# PyQt5 import/s
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QSplitter, QApplication, QFileDialog, QMessageBox, QStatusBar, QLabel
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPalette, QColor

# Component imports
from components.asset_sidebar import AssetSidebar
from components.canvas_area import CanvasArea
from components.property_sidebar import PropertySidebar

#COA INTEGRATION ACTION: Import CoA model for integration Step 1
from models.coa import CoA, Layer

# Utility imports
from utils.history_manager import HistoryManager
from utils.color_utils import color_name_to_rgb, rgb_to_color_name
from utils.logger import loggerRaise

# Constants
from constants import DEFAULT_BASE_CATEGORY

# Service imports
from services.file_operations import (
    save_coa_to_file, load_coa_from_file, 
    coa_to_clipboard_text, is_layer_subblock
)
from services.layer_operations import (
    serialize_layer_to_text, parse_layer_from_text,
    parse_multiple_layers_from_text
)
from constants import (
    DEFAULT_EMBLEM_COLOR1, DEFAULT_EMBLEM_COLOR2, DEFAULT_EMBLEM_COLOR3,
    DEFAULT_BASE_COLOR1, DEFAULT_BASE_COLOR2, DEFAULT_BASE_COLOR3,
    CK3_NAMED_COLORS, DEFAULT_SCALE_X, DEFAULT_SCALE_Y,
    DEFAULT_FLIP_X, DEFAULT_FLIP_Y, DEFAULT_ROTATION, MAX_HISTORY_ENTRIES
)

# Action imports
from actions.file_actions import FileActions
from actions.clipboard_actions import ClipboardActions
from actions.layer_transform_actions import LayerTransformActions

# Layer generator imports
from services.layer_generator import GeneratorPopup
from services.layer_generator.generators import (
    CircularGenerator, LineGenerator, SpiralGenerator, ShapeGenerator,
    GridGenerator, DiamondGenerator, FibonacciGenerator,
    RadialGenerator, StarGenerator, VanillaGenerator
)


class CoatOfArmsEditor(QMainWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("Coat Of Arms Designer")
		self.resize(1280, 720)
		self.setMinimumSize(1280, 720)
		
		#COA INTEGRATION ACTION: Initialize CoA model instance (Step 1 - MainWindow initialization)
		# This is the single source of truth for all CoA data going forward
		self.coa = CoA()
		# Set as active instance for global access
		CoA.set_active(self.coa)
		
		# Initialize history manager
		self.history_manager = HistoryManager(max_history=MAX_HISTORY_ENTRIES)
		self.history_manager.add_listener(self._on_history_changed)
		
		# Debounce timer for property changes (avoid spamming history on slider drags)
		self.property_change_timer = QTimer()
		self.property_change_timer.setSingleShot(True)
		self.property_change_timer.timeout.connect(self._save_property_change)
		self._pending_property_change = None
		
		# Flag to prevent saving state during undo/redo
		self._is_applying_history = False
		
		# Track current file and saved state
		self.current_file_path = None
		self.is_saved = True
		
		# Recent files and autosave
		self.recent_files = []
		self.max_recent_files = 10
		self.config_dir = os.path.join(os.path.expanduser("~"), ".ck3coa")
		self.config_file = os.path.join(self.config_dir, "config.json")
		self.autosave_file = os.path.join(self.config_dir, "autosave.txt")
		self._load_config()
		
		# Autosave timer (every 2 minutes)
		self.autosave_timer = QTimer()
		self.autosave_timer.timeout.connect(self._autosave)
		self.autosave_timer.start(120000)  # 2 minutes in milliseconds
		
		# Install event filter on application to catch arrow keys globally
		QApplication.instance().installEventFilter(self)
		
		# Initialize global logger with main window reference
		from utils.logger import set_main_window
		set_main_window(self)
		
		# Initialize action handlers (composition pattern)
		self.file_actions = FileActions(self)
		self.clipboard_actions = ClipboardActions(self)
		self.transform_actions = LayerTransformActions(self)
		
		# Initialize layer generator - preload shapes before UI setup
		self.generator_popup = None  # Created on demand
		try:
			self._preload_shapes()
		except Exception as e:
			print(f"Warning: Failed to preload shapes: {e}")
		
		self.setup_ui()
		
		# Initialize menu action states
		QTimer.singleShot(100, self._update_menu_actions)
		
		# Check for autosave recovery after UI is set up
		# QTimer.singleShot(500, self._check_autosave_recovery)  # TODO: Fix autosave recovery
	
	def setup_ui(self):
		# Create menu bar
		self._create_menu_bar()
		
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
		#COA INTEGRATION ACTION: Step 4-5 - Pass CoA reference to canvas area and canvas widget
		self.canvas_area.coa = self.coa
		self.canvas_area.canvas_widget.coa = self.coa
		splitter.addWidget(self.canvas_area)
		
		# Right properties sidebar
		self.right_sidebar = PropertySidebar(self)
		self.right_sidebar.main_window = self
		#COA INTEGRATION ACTION: Step 3 - Pass CoA reference to property sidebar and layer list
		self.right_sidebar.coa = self.coa
		self.right_sidebar.layer_list_widget.coa = self.coa
		self.right_sidebar.layer_list_widget.main_window = self  # For history snapshots
		splitter.addWidget(self.right_sidebar)
		
		# Connect sidebars together
		self.left_sidebar.right_sidebar = self.right_sidebar
		
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
	
	def _create_menu_bar(self):
		"""Create the menu bar with File, Edit, Help menus"""
		menubar = self.menuBar()
		
		# File Menu
		file_menu = menubar.addMenu("&File")
		
		new_action = file_menu.addAction("&New")
		new_action.setShortcut("Ctrl+N")
		new_action.triggered.connect(self.file_actions.new_coa)
		
		open_action = file_menu.addAction("&Open...")
		open_action.setShortcut("Ctrl+O")
		open_action.triggered.connect(self.file_actions.load_coa)
		
		# Recent Files submenu
		self.recent_menu = file_menu.addMenu("Recent Files")
		self._update_recent_files_menu()
		
		file_menu.addSeparator()
		
		save_action = file_menu.addAction("&Save")
		save_action.setShortcut("Ctrl+S")
		save_action.triggered.connect(self.file_actions.save_coa)
		
		save_as_action = file_menu.addAction("Save &As...")
		save_as_action.setShortcut("Ctrl+Shift+S")
		save_as_action.triggered.connect(self.file_actions.save_coa_as)
		
		file_menu.addSeparator()
		
		export_png_action = file_menu.addAction("Export as &PNG...")
		export_png_action.setShortcut("Ctrl+E")
		export_png_action.triggered.connect(self.file_actions.export_png)
		
		file_menu.addSeparator()
		
		copy_coa_action = file_menu.addAction("&Copy CoA to Clipboard")
		copy_coa_action.setShortcut("Ctrl+Shift+C")
		copy_coa_action.triggered.connect(self.clipboard_actions.copy_coa)
		
		paste_coa_action = file_menu.addAction("&Paste CoA from Clipboard")
		paste_coa_action.setShortcut("Ctrl+Shift+V")
		paste_coa_action.triggered.connect(self.clipboard_actions.paste_coa)
		
		file_menu.addSeparator()
		
		exit_action = file_menu.addAction("E&xit")
		exit_action.setShortcut("Alt+F4")
		exit_action.triggered.connect(self.close)
		
		# Edit Menu
		self.edit_menu = menubar.addMenu("&Edit")
		
		self.undo_action = self.edit_menu.addAction("&Undo")
		self.undo_action.setShortcut("Ctrl+Z")
		self.undo_action.triggered.connect(self.undo)
		self.undo_action.setEnabled(False)
		
		self.redo_action = self.edit_menu.addAction("&Redo")
		self.redo_action.setShortcut("Ctrl+Y")
		self.redo_action.triggered.connect(self.redo)
		self.redo_action.setEnabled(False)
		
		self.edit_menu.addSeparator()
		
		# Transform submenu
		transform_menu = self.edit_menu.addMenu("&Transform")
		
		self.flip_x_action = transform_menu.addAction("Flip &Horizontal")
		self.flip_x_action.setShortcut("F")
		self.flip_x_action.triggered.connect(self._flip_x)
		
		self.flip_y_action = transform_menu.addAction("Flip &Vertical")
		self.flip_y_action.setShortcut("Ctrl+F")
		self.flip_y_action.triggered.connect(self._flip_y)
		
		transform_menu.addSeparator()
		
		self.rotate_90_action = transform_menu.addAction("Rotate &90°")
		self.rotate_90_action.triggered.connect(lambda: self._rotate_layers(90))
		
		self.rotate_180_action = transform_menu.addAction("Rotate &180°")
		self.rotate_180_action.triggered.connect(lambda: self._rotate_layers(180))
		
		self.rotate_minus_90_action = transform_menu.addAction("Rotate &-90°")
		self.rotate_minus_90_action.triggered.connect(lambda: self._rotate_layers(-90))
		
		# Store transform actions for enabling/disabling
		self.transform_action_list = [
			self.flip_x_action,
			self.flip_y_action,
			self.rotate_90_action,
			self.rotate_180_action,
			self.rotate_minus_90_action
		]
		
		# Initially disable transform actions
		self._update_transform_actions()
		
		self.edit_menu.addSeparator()
		
		# Align submenu
		align_menu = self.edit_menu.addMenu("&Align Layers")
		
		self.align_left_action = align_menu.addAction("Align &Left")
		self.align_left_action.triggered.connect(lambda: self._align_layers('left'))
		
		self.align_center_action = align_menu.addAction("Align &Center")
		self.align_center_action.triggered.connect(lambda: self._align_layers('center'))
		
		self.align_right_action = align_menu.addAction("Align &Right")
		self.align_right_action.triggered.connect(lambda: self._align_layers('right'))
		
		align_menu.addSeparator()
		
		self.align_top_action = align_menu.addAction("Align &Top")
		self.align_top_action.triggered.connect(lambda: self._align_layers('top'))
		
		self.align_middle_action = align_menu.addAction("Align &Middle")
		self.align_middle_action.triggered.connect(lambda: self._align_layers('middle'))
		
		self.align_bottom_action = align_menu.addAction("Align &Bottom")
		self.align_bottom_action.triggered.connect(lambda: self._align_layers('bottom'))
		
		# Store alignment actions for enabling/disabling
		self.alignment_actions = [
			self.align_left_action,
			self.align_center_action,
			self.align_right_action,
			self.align_top_action,
			self.align_middle_action,
			self.align_bottom_action
		]
		
		# Initially disable alignment actions
		self._update_alignment_actions()
		
		# Move to submenu (move to fixed positions)
		move_to_menu = self.edit_menu.addMenu("&Move to")
		
		self.move_to_left_action = move_to_menu.addAction("&Left")
		self.move_to_left_action.triggered.connect(lambda: self._move_to('left'))
		
		self.move_to_center_action = move_to_menu.addAction("&Center")
		self.move_to_center_action.triggered.connect(lambda: self._move_to('center'))
		
		self.move_to_right_action = move_to_menu.addAction("&Right")
		self.move_to_right_action.triggered.connect(lambda: self._move_to('right'))
		
		move_to_menu.addSeparator()
		
		self.move_to_top_action = move_to_menu.addAction("&Top")
		self.move_to_top_action.triggered.connect(lambda: self._move_to('top'))
		
		self.move_to_middle_action = move_to_menu.addAction("&Middle")
		self.move_to_middle_action.triggered.connect(lambda: self._move_to('middle'))
		
		self.move_to_bottom_action = move_to_menu.addAction("&Bottom")
		self.move_to_bottom_action.triggered.connect(lambda: self._move_to('bottom'))
		
		# Store move to actions for enabling/disabling
		self.move_to_actions = [
			self.move_to_left_action,
			self.move_to_center_action,
			self.move_to_right_action,
			self.move_to_top_action,
			self.move_to_middle_action,
			self.move_to_bottom_action
		]
		
		# Initially disable move to actions
		self._update_move_to_actions()
		
		self.edit_menu.addSeparator()
		
		select_all_action = self.edit_menu.addAction("Select &All Layers")
		select_all_action.setShortcut("Ctrl+A")
		select_all_action.triggered.connect(self._select_all_layers)
		
		# Layers Menu
		self.layers_menu = menubar.addMenu("&Layers")
		
		copy_layer_action = self.layers_menu.addAction("&Copy Layer")
		copy_layer_action.setShortcut("Ctrl+C")
		copy_layer_action.triggered.connect(self.clipboard_actions.copy_layer)
		
		paste_layer_action = self.layers_menu.addAction("&Paste Layer")
		paste_layer_action.setShortcut("Ctrl+V")
		paste_layer_action.triggered.connect(self.clipboard_actions.paste_layer_smart)
		
		duplicate_layer_action = self.layers_menu.addAction("&Duplicate Layer")
		duplicate_layer_action.setShortcut("Ctrl+D")
		duplicate_layer_action.triggered.connect(self.clipboard_actions.duplicate_selected_layer)
		
		self.layers_menu.addSeparator()
		
		# Group/Ungroup Container action
		self.group_container_action = self.layers_menu.addAction("Group")
		self.group_container_action.triggered.connect(self._group_or_ungroup_container)
		self.group_container_action.setEnabled(False)  # Enabled based on selection
		
		self.layers_menu.addSeparator()
		
		# Instance section (label + actions)
		instance_label = self.layers_menu.addAction("Instance")
		instance_label.setEnabled(False)  # Make it non-clickable like a label
		
		self.split_instances_action = self.layers_menu.addAction("    Split")
		self.split_instances_action.triggered.connect(self._split_selected_layer)
		self.split_instances_action.setEnabled(False)  # Enabled only for multi-instance layers
		
		self.merge_as_instances_action = self.layers_menu.addAction("    Merge")
		self.merge_as_instances_action.triggered.connect(self._merge_selected_layers)
		self.merge_as_instances_action.setEnabled(False)  # Enabled only for multi-selection
		
		# Generate Menu
		self.generate_menu = menubar.addMenu("&Generate")
		
		# Path submenu
		path_menu = self.generate_menu.addMenu("&Path")
		
		circular_action = path_menu.addAction("&Circular")
		circular_action.triggered.connect(lambda: self._open_generator('circular'))
		
		line_action = path_menu.addAction("&Line")
		line_action.triggered.connect(lambda: self._open_generator('line'))
		
		spiral_action = path_menu.addAction("&Spiral")
		spiral_action.triggered.connect(lambda: self._open_generator('spiral'))
		
		path_menu.addSeparator()
		
		# Shape submenu (dynamically populated with loaded SVGs)
		self.shape_menu = path_menu.addMenu("S&hape")
		self._populate_shape_menu()
		
		# Grid submenu
		grid_patterns_menu = self.generate_menu.addMenu("&Grid")
		
		grid_action = grid_patterns_menu.addAction("&Grid Pattern")
		grid_action.triggered.connect(lambda: self._open_generator('grid'))
		
		diamond_action = grid_patterns_menu.addAction("&Diamond Grid")
		diamond_action.triggered.connect(lambda: self._open_generator('diamond'))
		
		# Misc submenu
		misc_menu = self.generate_menu.addMenu("&Misc")
		
		fibonacci_action = misc_menu.addAction("&Fibonacci Spiral (Sunflower)")
		fibonacci_action.triggered.connect(lambda: self._open_generator('fibonacci'))
		
		radial_action = misc_menu.addAction("&Radial")
		radial_action.triggered.connect(lambda: self._open_generator('radial'))
		
		star_action = misc_menu.addAction("&Star Path")
		star_action.triggered.connect(lambda: self._open_generator('star'))
		
		# Vanilla submenu
		vanilla_menu = self.generate_menu.addMenu("&Vanilla")
		vanilla_action = vanilla_menu.addAction("CK3 Official &Layouts")
		vanilla_action.triggered.connect(lambda: self._open_generator('vanilla'))
		
		# View Menu
		view_menu = menubar.addMenu("&View")
		
		# Grid submenu
		grid_menu = view_menu.addMenu("Show &Grid")
		
		self.grid_2x2_action = grid_menu.addAction("&2x2")
		self.grid_2x2_action.setCheckable(True)
		self.grid_2x2_action.triggered.connect(lambda: self._set_grid_size(2))
		
		self.grid_4x4_action = grid_menu.addAction("&4x4")
		self.grid_4x4_action.setCheckable(True)
		self.grid_4x4_action.setChecked(True)
		self.grid_4x4_action.triggered.connect(lambda: self._set_grid_size(4))
		
		self.grid_8x8_action = grid_menu.addAction("&8x8")
		self.grid_8x8_action.setCheckable(True)
		self.grid_8x8_action.triggered.connect(lambda: self._set_grid_size(8))
		
		self.grid_16x16_action = grid_menu.addAction("1&6x16")
		self.grid_16x16_action.setCheckable(True)
		self.grid_16x16_action.triggered.connect(lambda: self._set_grid_size(16))
		
		grid_menu.addSeparator()
		
		self.grid_off_action = grid_menu.addAction("&Off")
		self.grid_off_action.setCheckable(True)
		self.grid_off_action.triggered.connect(lambda: self._set_grid_size(0))
		
		# Group grid actions
		from PyQt5.QtWidgets import QActionGroup
		self.grid_action_group = QActionGroup(self)
		self.grid_action_group.addAction(self.grid_2x2_action)
		self.grid_action_group.addAction(self.grid_4x4_action)
		self.grid_action_group.addAction(self.grid_8x8_action)
		self.grid_action_group.addAction(self.grid_16x16_action)
		self.grid_action_group.addAction(self.grid_off_action)
		self.grid_off_action.setChecked(True)  # Start with grid off
		
		# Help Menu
		help_menu = menubar.addMenu("&Help")
		
		about_action = help_menu.addAction("&About")
		about_action.triggered.connect(self._show_about)
	
	def _select_all_layers(self):
		"""Select all layers"""
		layer_count = self.coa.get_layer_count()
		if layer_count > 0:
			all_indices = set(range(layer_count))
			self.right_sidebar.set_selected_indices(all_indices)
			if self.canvas_area:
				self.canvas_area.update_transform_widget_for_layer()
			self.right_sidebar.tab_widget.setTabEnabled(2, True)
			self._update_menu_actions()
	
	def _show_about(self):
		"""Show about dialog"""
		from PyQt5.QtWidgets import QMessageBox
		QMessageBox.about(self, "About Coat of Arms Designer",
			"<h3>Coat of Arms Designer</h3>"
			"<p>A tool for creating and editing Crusader Kings 3 coats of arms.</p>"
			"<p>Version 1.0</p>"
			"<hr>"
			"<p><b>AI Disclosure:</b> This tool was developed with heavy AI assistance. "
			"I respect that people have valid concerns about AI, and I do not wish to claim ownership over the output. "
			"This tool is provided for its own sake as a useful utility, "
			"free for anyone to use or modify.</p>")
	
	def _zoom_in(self):
		"""Zoom in on canvas"""
		if hasattr(self.canvas_area, 'canvas_widget'):
			self.canvas_area.canvas_widget.zoom_in()
			# Update transform widget position after zoom change
			if hasattr(self.canvas_area, 'update_transform_widget_for_layer'):
				self.canvas_area.update_transform_widget_for_layer()
	
	def _zoom_out(self):
		"""Zoom out on canvas"""
		if hasattr(self.canvas_area, 'canvas_widget'):
			self.canvas_area.canvas_widget.zoom_out()
			# Update transform widget position after zoom change
			if hasattr(self.canvas_area, 'update_transform_widget_for_layer'):
				self.canvas_area.update_transform_widget_for_layer()
	
	def _zoom_reset(self):
		"""Reset canvas zoom to 100%"""
		if hasattr(self.canvas_area, 'canvas_widget'):
			self.canvas_area.canvas_widget.zoom_reset()
			# Update transform widget position after zoom change
			if hasattr(self.canvas_area, 'update_transform_widget_for_layer'):
				self.canvas_area.update_transform_widget_for_layer()
	
	def _set_grid_size(self, divisions):
		"""Set grid size (0 = off, 2/4/8/16 = grid divisions)"""
		if hasattr(self.canvas_area, 'canvas_widget'):
			if divisions == 0:
				self.canvas_area.canvas_widget.set_show_grid(False)
			else:
				self.canvas_area.canvas_widget.set_show_grid(True)
				self.canvas_area.canvas_widget.set_grid_divisions(divisions)
	
	def _update_menu_actions(self):
		"""Update menu action states based on current selections"""
		self._update_alignment_actions()
		self._update_transform_actions()
		self._update_move_to_actions()
		self._update_instance_actions()
	
	def _update_instance_actions(self):
		"""Enable or disable instance menu actions based on selection"""
		if not hasattr(self, 'right_sidebar'):
			self.merge_as_instances_action.setEnabled(False)
			self.split_instances_action.setEnabled(False)
			self.group_container_action.setEnabled(False)
			return
		
		selected_uuids = self.right_sidebar.get_selected_uuids()
		
		# Merge: enabled for 2+ selections
		self.merge_as_instances_action.setEnabled(len(selected_uuids) >= 2)
		
		# Group/Ungroup: Check if a container was explicitly selected
		layer_list = self.right_sidebar.layer_list_widget
		is_container_selected = len(layer_list.selected_container_uuids) > 0
		
		if is_container_selected:
			self.group_container_action.setText("Ungroup")
			self.group_container_action.setEnabled(True)
		elif len(selected_uuids) >= 2:
			self.group_container_action.setText("Group")
			self.group_container_action.setEnabled(True)
		else:
			self.group_container_action.setText("Group")
			self.group_container_action.setEnabled(False)
		
		# Split: enabled for single selection with 2+ instances
		if len(selected_uuids) == 1:
			instance_count = self.coa.get_layer_instance_count(selected_uuids[0])
			self.split_instances_action.setEnabled(instance_count >= 2)
		else:
			self.split_instances_action.setEnabled(False)
	
	def _update_alignment_actions(self):
		"""Enable or disable alignment actions based on selection count"""
		if not hasattr(self, 'right_sidebar'):
			# Right sidebar not yet initialized, disable all alignment actions
			for action in self.alignment_actions:
				action.setEnabled(False)
			return
		
		selected_count = len(self.right_sidebar.get_selected_indices())
		enabled = selected_count >= 2
		
		for action in self.alignment_actions:
			action.setEnabled(enabled)
	
	def _update_transform_actions(self):
		"""Enable or disable transform actions based on selection count"""
		if not hasattr(self, 'right_sidebar'):
			# Right sidebar not yet initialized, disable all transform actions
			for action in self.transform_action_list:
				action.setEnabled(False)
			return
		
		# Enable transform actions if at least one layer is selected
		# Works for single layers, multi-selection, and multi-instance layers
		selected_count = len(self.right_sidebar.get_selected_indices())
		enabled = selected_count >= 1
		
		for action in self.transform_action_list:
			action.setEnabled(enabled)
	
	def _align_layers(self, alignment):
		"""Align selected layers"""
		self.transform_actions.align_layers(alignment)
	
	def _update_move_to_actions(self):
		"""Enable or disable move to actions based on selection count"""
		if not hasattr(self, 'right_sidebar'):
			# Right sidebar not yet initialized, disable all move to actions
			for action in self.move_to_actions:
				action.setEnabled(False)
			return
		
		selected_count = len(self.right_sidebar.get_selected_indices())
		enabled = selected_count >= 1
		
		for action in self.move_to_actions:
			action.setEnabled(enabled)
	
	def _move_to(self, position):
		"""Move selected layers to fixed position"""
		self.transform_actions.move_to(position)
	
	def _flip_x(self):
		"""Flip selected layers horizontally"""
		self.transform_actions.flip_x()
	
	def _flip_y(self):
		"""Flip selected layers vertically"""
		self.transform_actions.flip_y()
	
	def _rotate_layers(self, degrees):
		"""Rotate selected layers by specified degrees"""
		self.transform_actions.rotate_layers(degrees)
	
	def export_png(self):
		"""Export current CoA as PNG with transparency"""
		try:
			# Open save file dialog
			filename, _ = QFileDialog.getSaveFileName(
				self,
				"Export as PNG",
				"",
				"PNG Files (*.png);;All Files (*)"
			)
			
			if not filename:
				return
			
			# Ensure .png extension
			if not filename.lower().endswith('.png'):
				filename += '.png'
			
			# Get the canvas widget's pixmap/image
			if hasattr(self.canvas_area, 'canvas_widget'):
				success = self.canvas_area.canvas_widget.export_to_png(filename)
				if success:
					QMessageBox.information(self, "Export Successful", f"CoA exported to:\n{filename}")
				else:
					QMessageBox.warning(self, "Export Failed", "Failed to export PNG.")
		except Exception as e:
			loggerRaise(e, "Failed to export PNG")
	
	def _update_window_title(self):
		"""Update window title with current file name"""
		if self.current_file_path:
			filename = os.path.basename(self.current_file_path)
			modified = "" if self.is_saved else "*"
			self.setWindowTitle(f"{filename}{modified} - Coat Of Arms Designer")
		else:
			modified = "" if self.is_saved else "*"
			self.setWindowTitle(f"Untitled{modified} - Coat Of Arms Designer")
	
	def _prompt_save_if_needed(self):
		"""Prompt user to save if there are unsaved changes
		
		Returns:
			True if it's safe to proceed (saved or discarded)
			False if user cancelled
		"""
		if not self.is_saved:
			reply = QMessageBox.question(
				self,
				"Unsaved Changes",
				"Do you want to save your changes?",
				QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
				QMessageBox.Save
			)
			
			if reply == QMessageBox.Save:
				self.save_coa()
				# Check if save was successful (user might have cancelled save dialog)
				return self.is_saved
			elif reply == QMessageBox.Cancel:
				return False
			# Discard falls through
		
		return True
	
	def closeEvent(self, event):
		"""Handle window close event - prompt to save if needed"""
		if self._prompt_save_if_needed():
			# Save config before closing
			self._save_config()
			event.accept()
		else:
			event.ignore()
	
	def _load_config(self):
		"""Load recent files and settings from config file"""
		try:
			if os.path.exists(self.config_file):
				with open(self.config_file, 'r', encoding='utf-8') as f:
					config = json.load(f)
					self.recent_files = config.get('recent_files', [])
					# Filter out files that no longer exist
					self.recent_files = [f for f in self.recent_files if os.path.exists(f)]
		except Exception as e:
			loggerRaise(e, "Error loading config")
	
	def _save_config(self):
		"""Save recent files and settings to config file"""
		try:
			# Create config directory if it doesn't exist
			os.makedirs(self.config_dir, exist_ok=True)
			
			config = {
				'recent_files': self.recent_files[:self.max_recent_files]
			}
			
			with open(self.config_file, 'w', encoding='utf-8') as f:
				json.dump(config, f, indent=2)
		except Exception as e:
			loggerRaise(e, "Error saving config")
	
	def _add_to_recent_files(self, filepath):
		"""Add a file to the recent files list"""
		# Remove if already in list
		if filepath in self.recent_files:
			self.recent_files.remove(filepath)
		
		# Add to front of list
		self.recent_files.insert(0, filepath)
		
		# Trim to max size
		self.recent_files = self.recent_files[:self.max_recent_files]
		
		# Update menu
		if hasattr(self, 'recent_menu'):
			self._update_recent_files_menu()
		
		# Save config
		self._save_config()
	
	def _update_recent_files_menu(self):
		"""Update the Recent Files submenu"""
		self.recent_menu.clear()
		
		if not self.recent_files:
			no_recent = self.recent_menu.addAction("No recent files")
			no_recent.setEnabled(False)
		else:
			for filepath in self.recent_files:
				if os.path.exists(filepath):
					filename = os.path.basename(filepath)
					action = self.recent_menu.addAction(filename)
					action.setToolTip(filepath)
					# Use lambda with default argument to capture filepath
					action.triggered.connect(lambda checked, f=filepath: self._open_recent_file(f))
			
			self.recent_menu.addSeparator()
			clear_action = self.recent_menu.addAction("Clear Recent Files")
			clear_action.triggered.connect(self._clear_recent_files)
	
	def _clear_recent_files(self):
		"""Clear the recent files list"""
		self.recent_files = []
		self._update_recent_files_menu()
		self._save_config()
	
	def _open_recent_file(self, filepath):
		"""Open a file from the recent files list"""
		if not os.path.exists(filepath):
			QMessageBox.warning(self, "File Not Found", f"The file no longer exists:\n{filepath}")
			# Remove from recent files
			self.recent_files.remove(filepath)
			self._update_recent_files_menu()
			self._save_config()
			return
		
		# Prompt to save current changes
		if not self._prompt_save_if_needed():
			return
		
		try:
			# Read file
			with open(filepath, 'r', encoding='utf-8') as f:
				coa_text = f.read()
			
			# Clear and parse into existing CoA instance
			self.coa.clear()
			self.coa.parse(coa_text)
			
			# Apply to UI - update from model
			# Set base texture and colors
			self.canvas_area.canvas_widget.set_base_texture(self.coa.pattern)
			self.canvas_area.canvas_widget.set_base_colors([self.coa.pattern_color1, self.coa.pattern_color2, self.coa.pattern_color3])
			self.canvas_area.canvas_widget.base_color1_name = self.coa.pattern_color1_name
			self.canvas_area.canvas_widget.base_color2_name = self.coa.pattern_color2_name
			self.canvas_area.canvas_widget.base_color3_name = self.coa.pattern_color3_name
			
			base_color_names = [self.coa.pattern_color1_name, self.coa.pattern_color2_name, self.coa.pattern_color3_name]
			self.right_sidebar.set_base_colors([self.coa.pattern_color1, self.coa.pattern_color2, self.coa.pattern_color3], base_color_names)
			
			# Update UI - switch to Layers tab and rebuild
			self.right_sidebar.tab_widget.setCurrentIndex(1)
			self.right_sidebar._rebuild_layer_list()
			if self.coa.get_layer_count() > 0:
				self.right_sidebar._select_layer(0)
			
			# Update canvas
			self.canvas_area.canvas_widget.update()
			
			# OLD CODE (will remove in Step 10):
			# coa_data = load_coa_from_file(filepath)
			# self._apply_coa_data(coa_data)
			
			# Set current file path and mark as saved
			self.current_file_path = filepath
			self.is_saved = True
			self._update_window_title()
			
			# Add to recent files (moves to top)
			self._add_to_recent_files(filepath)
			
			# Clear history and save initial state
			self.history_manager.clear()
			self._save_state("Load CoA")
		except Exception as e:
			loggerRaise(e, "Failed to load coat of arms")
		self._update_recent_files_menu()
		self._save_config()
	
	def _autosave(self):
		"""Perform autosave to temporary file"""
		try:
			# Only autosave if there are unsaved changes
			if not self.is_saved:
				#COA INTEGRATION ACTION: Step 2 - Use CoA model for autosave
				# Create config directory if it doesn't exist
				os.makedirs(self.config_dir, exist_ok=True)
				
				# Save using model
				coa_string = self.coa.to_string()
				with open(self.autosave_file, 'w', encoding='utf-8') as f:
					f.write(coa_string)
				
				# OLD CODE (will remove in Step 9):
				# canvas = self.canvas_area.canvas_widget
				# base_colors = self.right_sidebar.get_base_colors()
				# base_color_names = [
				# 	getattr(canvas, 'base_color1_name', 'black'),
				# 	getattr(canvas, 'base_color2_name', 'yellow'),
				# 	getattr(canvas, 'base_color3_name', 'black')
				# ]
				# coa_data = build_coa_for_save(
				# 	base_colors,
				# 	canvas.base_texture,
				# 	self.right_sidebar.layers,
				# 	base_color_names
				# )
				# save_coa_to_file(coa_data, self.autosave_file)
				
				print("Autosaved")
		except Exception as e:
			loggerRaise(e, "Autosave failed")
			if os.path.exists(self.autosave_file):
				reply = QMessageBox.question(
					self,
					"Recover Autosave",
					"An autosave file was found. Would you like to recover it?",
					QMessageBox.Yes | QMessageBox.No,
					QMessageBox.Yes
				)
				
				if reply == QMessageBox.Yes:
					#COA INTEGRATION ACTION: Step 2 - Use CoA model for autosave recovery
					# Read and parse into existing CoA instance
					with open(self.autosave_file, 'r', encoding='utf-8') as f:
						coa_text = f.read()
					self.coa.clear()
					self.coa.parse(coa_text)
					
					# Apply to UI - update from model
					# Set base texture and colors
					self.canvas_area.canvas_widget.set_base_texture(self.coa.pattern)
				self.canvas_area.canvas_widget.set_base_colors([self.coa.pattern_color1, self.coa.pattern_color2, self.coa.pattern_color3])
				self.canvas_area.canvas_widget.base_color1_name = self.coa.pattern_color1_name
				self.canvas_area.canvas_widget.base_color2_name = self.coa.pattern_color2_name
				self.canvas_area.canvas_widget.base_color3_name = self.coa.pattern_color3_name
				
				base_color_names = [self.coa.pattern_color1_name, self.coa.pattern_color2_name, self.coa.pattern_color3_name]
				self.right_sidebar.set_base_colors([self.coa.pattern_color1, self.coa.pattern_color2, self.coa.pattern_color3], base_color_names)
				
				# Update UI
				self.right_sidebar.tab_widget.setCurrentIndex(1)
				# OLD CODE (will remove in Step 10):
				# coa_data = load_coa_from_file(self.autosave_file)
				# self._apply_coa_data(coa_data)
				
				# Mark as unsaved (since it's recovered from autosave)
				self.current_file_path = None
				self.is_saved = False
				self._update_window_title()
				
				# Clear history and save state
				self.history_manager.clear()
				self._save_state("Recover autosave")
				
				# Remove autosave file after prompt
				os.remove(self.autosave_file)
		except Exception as e:
			loggerRaise(e, "Error checking autosave")
			pass


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
			# Hide transform widget when on Base tab
			if hasattr(self, 'canvas_area') and self.canvas_area.transform_widget:
				self.canvas_area.transform_widget.set_visible(False)
		else:
			self.left_sidebar.switch_mode("emblems")
			# Update transform widget visibility for current layer selection
			if hasattr(self, 'canvas_area'):
				self.canvas_area.update_transform_widget_for_layer()
	
	# ========================================
	# Asset Selection Handlers
	# ========================================
	
	def _on_asset_selected(self, asset_data):
		"""
		Handle asset selection from sidebar.
		- Base tab: Updates base pattern texture
		- Layers/Properties tab: Updates selected layer or creates new layer
		"""
		color_count = asset_data.get("colors", 1)
		filename = asset_data.get("filename")
		dds_filename = asset_data.get('dds_filename', filename)
		current_tab = self.right_sidebar.tab_widget.currentIndex()
		
		if current_tab == 0:  # Base tab
			self._apply_base_texture(filename, color_count)
		else:  # Layers or Properties tab
			self._apply_emblem_texture(dds_filename, color_count)
	
	def _apply_base_texture(self, filename, color_count):
		"""Apply texture to base pattern"""
		self.right_sidebar.set_base_color_count(color_count)
		if filename:
			self.canvas_area.canvas_widget.set_base_texture(filename)
			self._save_state("Change base texture")
	
	def _apply_emblem_texture(self, dds_filename, color_count):
		"""Apply texture to selected layer(s) or create new layer"""
		self.right_sidebar.set_emblem_color_count(color_count)
		selected_uuids = self.right_sidebar.get_selected_uuids()
		
		if selected_uuids:
			# Update all selected layers
			for uuid in selected_uuids:
				self._update_layer_texture(uuid, dds_filename, color_count)
		else:
			self._create_layer_with_texture(dds_filename, color_count)
	
	def _update_layer_texture(self, uuid, dds_filename, color_count):
		"""Update existing layer's texture while preserving other properties"""
		layer = self.coa.get_layer_by_uuid(uuid)
		if layer:
			# Update Layer object attributes
			layer.filename = dds_filename
			layer.path = dds_filename
			layer.colors = color_count
			
			# Invalidate thumbnail cache and update button for this layer (by UUID)
			if hasattr(self.right_sidebar, 'layer_list_widget') and self.right_sidebar.layer_list_widget:
				self.right_sidebar.layer_list_widget.invalidate_thumbnail(layer.uuid)
				self.right_sidebar.layer_list_widget.update_layer_button(layer.uuid)
			
			# Update UI and canvas (no full rebuild needed)
			self.right_sidebar._update_layer_selection()
			self.canvas_area.canvas_widget.update()
			self._save_state("Change layer texture")
	
	def _create_layer_with_texture(self, dds_filename, color_count):
		"""Create new layer with selected texture"""
		# Check for selection to add above
		selected_uuids = self.right_sidebar.get_selected_uuids()
		target_uuid = selected_uuids[0] if selected_uuids else None
		
		# Use CoA model to add layer
		if target_uuid:
			# Add below selected layer (in front of it)
			layer_uuid = self.coa.add_layer(
				emblem_path=dds_filename,
				pos_x=0.5,
				pos_y=0.5,
				colors=color_count,
				target_uuid=target_uuid
			)
		else:
			# No selection, add at front
			layer_uuid = self.coa.add_layer(
				emblem_path=dds_filename,
				pos_x=0.5,
				pos_y=0.5,
				colors=color_count
			)
		
		# Auto-select the newly added layer using UUID from CoA
		new_uuid = self.coa.get_last_added_uuid()
		if new_uuid:
			self.right_sidebar.layer_list_widget.selected_layer_uuids = {new_uuid}
			self.right_sidebar.layer_list_widget.last_selected_uuid = new_uuid
			self.right_sidebar.layer_list_widget.update_selection_visuals()
		
		# Update UI
		self.right_sidebar._rebuild_layer_list()
		
		# Update canvas
		self.canvas_area.canvas_widget.update()
		
		# Trigger selection change callback to update properties and transform widget
		self.right_sidebar._on_layer_selection_changed()
		
		self._save_state("Create layer")
	
	# ========================================
	# Window Events
	# ========================================
	
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
	
	def eventFilter(self, obj, event):
		"""Filter events to capture arrow keys and context menus before child widgets consume them"""
		# Handle context menu events globally
		if event.type() == event.ContextMenu:
			# Get the widget under the cursor
			global_pos = event.globalPos()
			widget_under_cursor = QApplication.widgetAt(global_pos)
			
			# Traverse up to find the relevant widget
			while widget_under_cursor:
				# Check if we're over the canvas area or canvas widget
				if widget_under_cursor == self.canvas_area or widget_under_cursor == self.canvas_area.canvas_widget:
					menu = QtWidgets.QMenu(self)
					for action in self.edit_menu.actions():
						if action.isSeparator():
							menu.addSeparator()
						else:
							menu.addAction(action)
					menu.exec_(global_pos)
					return True
				
				# Check if we're over the layer list
				elif widget_under_cursor == self.right_sidebar.layer_list_widget or widget_under_cursor.parent() == self.right_sidebar.layer_list_widget:
					menu = QtWidgets.QMenu(self)
					for action in self.layers_menu.actions():
						if action.isSeparator():
							menu.addSeparator()
						else:
							menu.addAction(action)
					menu.exec_(global_pos)
					return True
				
				widget_under_cursor = widget_under_cursor.parent()
			
		if event.type() == event.KeyPress:
			# Intercept arrow keys when layers are selected
			if event.key() in [Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down]:
				selected_uuids = self.right_sidebar.get_selected_uuids()
				if selected_uuids:
					# Handle arrow key movement
					from constants import ARROW_KEY_MOVE_NORMAL, ARROW_KEY_MOVE_FINE
					move_amount = ARROW_KEY_MOVE_FINE if event.modifiers() & Qt.ShiftModifier else ARROW_KEY_MOVE_NORMAL
					
					for uuid in selected_uuids:
						current_x, current_y = self.coa.get_layer_position(uuid)
						
						if event.key() == Qt.Key_Left:
							new_x = current_x - move_amount
							self.coa.set_layer_position(uuid, new_x, current_y)
						elif event.key() == Qt.Key_Right:
							new_x = current_x + move_amount
							self.coa.set_layer_position(uuid, new_x, current_y)
						elif event.key() == Qt.Key_Up:
							new_y = current_y - move_amount
							self.coa.set_layer_position(uuid, current_x, new_y)
						elif event.key() == Qt.Key_Down:
							new_y = current_y + move_amount
							self.coa.set_layer_position(uuid, current_x, new_y)
					
					# Update UI
					self.right_sidebar._load_layer_properties()
					self.canvas_area.canvas_widget.update()
					self.canvas_area.update_transform_widget_for_layer()
					
					# Save to history
					self.save_property_change_debounced("Move layer with arrow keys")
					
					# Consume the event so child widgets don't process it
					return True
		
		# Let all other events pass through
		return False
	
	def keyPressEvent(self, event):
		"""Handle keyboard shortcuts"""
		# Ctrl+S for save
		if event.key() == Qt.Key_S and event.modifiers() == Qt.ControlModifier:
			self.save_coa()
			event.accept()
		# Ctrl+D for duplicate layer
		elif event.key() == Qt.Key_D and event.modifiers() == Qt.ControlModifier:
			if self.right_sidebar.get_selected_indices():
				self.clipboard_actions.duplicate_selected_layer()
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
				self.clipboard_actions.copy_layer()
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
					self.clipboard_actions.paste_layer_at_position(mouse_pos, canvas_geometry)
					event.accept()
					return
			# Otherwise, paste at center
			self.clipboard_actions.paste_layer()
			event.accept()
		# Delete key for delete layer
		elif event.key() == Qt.Key_Delete:
			if self.right_sidebar.get_selected_indices():
				self.right_sidebar._delete_layer()
				event.accept()
			else:
				super().keyPressEvent(event)
		# Ctrl+A for select all layers
		elif event.key() == Qt.Key_A and event.modifiers() & Qt.ControlModifier:
			layer_count = self.coa.get_layer_count()
			if layer_count > 0:
				# Select all layer indices
				all_indices = set(range(layer_count))
				self.right_sidebar.set_selected_indices(all_indices)
				# Update transform widget for multi-selection
				if self.canvas_area:
					self.canvas_area.update_transform_widget_for_layer()
				# Enable properties tab
				self.right_sidebar.tab_widget.setTabEnabled(2, True)
				event.accept()
			else:
				super().keyPressEvent(event)
		# M key for toggle minimal transform widget
		elif event.key() == Qt.Key_M and not event.modifiers():
			self.canvas_area.minimal_transform_btn.toggle()
			event.accept()
		# R key for rotate -45 degrees
		elif event.key() == Qt.Key_R and not event.modifiers():
			if self.right_sidebar.get_selected_indices():
				self._rotate_selected_layers(-45)
				event.accept()
			else:
				super().keyPressEvent(event)
		# Shift+R for rotate +45 degrees
		elif event.key() == Qt.Key_R and event.modifiers() == Qt.ShiftModifier:
			if self.right_sidebar.get_selected_indices():
				self._rotate_selected_layers(45)
				event.accept()
			else:
				super().keyPressEvent(event)
		else:
			super().keyPressEvent(event)
	
	def _rotate_selected_layers(self, angle_delta):
		"""Rotate selected layers by the specified angle."""
		selected_indices = self.right_sidebar.get_selected_indices()
		if not selected_indices:
			return
		
		# Rotate each selected layer
		for idx in selected_indices:
			if 0 <= idx < self.coa.get_layer_count():
				layer = self.coa.get_layer_by_index(idx)
				layer.rotation = (layer.rotation + angle_delta) % 360
		
		# Update canvas
		self.canvas_area.canvas_widget.update()
		
		# Update transform widget (which updates properties panel)
		self.canvas_area.update_transform_widget_for_layer()
		
		# Save to history
		self._save_state(f"Rotate {'+' if angle_delta > 0 else ''}{angle_delta}°")
	
	def _capture_current_state(self):
		"""Capture the current state for history"""
		#COA INTEGRATION ACTION: Step 9 - Use CoA model snapshot for undo/redo
		# NEW CODE: Use model's snapshot for CoA data
		state = {
			'coa_snapshot': self.coa.get_snapshot(),
			'selected_layer_uuids': set(self.right_sidebar.get_selected_uuids()),  # UI state
			'selected_container_uuids': set(self.right_sidebar.layer_list_widget.selected_container_uuids),  # Container selection state
		}
		
		return state
	
	def _restore_state(self, state):
		"""Restore a state from history"""
		if not state:
			return
		
		self._is_applying_history = True
		try:
			#COA INTEGRATION ACTION: Step 9 - Restore from CoA model snapshot
			# NEW CODE: Restore CoA from snapshot
			self.coa.set_snapshot(state['coa_snapshot'])
			
			# Rebuild layer list from restored CoA
			self.right_sidebar._rebuild_layer_list()
			
			# Restore UI selection state (filter out UUIDs that no longer exist)
			saved_selection = set(state.get('selected_layer_uuids', set()))
			valid_uuids = {uuid for uuid in saved_selection if self.coa.has_layer_uuid(uuid)}
			self.right_sidebar.layer_list_widget.selected_layer_uuids = valid_uuids
			if valid_uuids:
				self.right_sidebar.layer_list_widget.last_selected_uuid = next(iter(valid_uuids))
			
			# Restore container selection state
			saved_container_selection = set(state.get('selected_container_uuids', set()))
			self.right_sidebar.layer_list_widget.selected_container_uuids = saved_container_selection
			
			# Always update canvas and base colors (regardless of selection)
			self.canvas_area.canvas_widget.base_color1_name = self.coa.pattern_color1_name
			self.canvas_area.canvas_widget.base_color2_name = self.coa.pattern_color2_name
			self.canvas_area.canvas_widget.base_color3_name = self.coa.pattern_color3_name
			
			# Update property sidebar base colors
			base_color_names = [self.coa.pattern_color1_name, self.coa.pattern_color2_name, self.coa.pattern_color3_name]
			self.right_sidebar.set_base_colors([self.coa.pattern_color1, self.coa.pattern_color2, self.coa.pattern_color3], base_color_names)
			
			# Restore canvas layers - ALWAYS update, not just when selection exists
			self.canvas_area.canvas_widget.update()
			
			# Update layer properties and transform widget if layers are selected
			if valid_uuids:
				self.right_sidebar._load_layer_properties()
				self.canvas_area.update_transform_widget_for_layer()
				self.right_sidebar.tab_widget.setTabEnabled(2, True)
			else:
				self.right_sidebar.tab_widget.setTabEnabled(2, False)
				self.canvas_area.transform_widget.set_visible(False)
		except Exception as e:
			loggerRaise(e, "Error restoring history state")
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
		
		# Mark as unsaved (except for initial "New CoA" and "Load CoA" states)
		if description not in ["New CoA", "Load CoA"]:
			self.is_saved = False
			self._update_window_title()
	
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
		if hasattr(self, 'undo_action'):
			self.undo_action.setEnabled(can_undo)
		if hasattr(self, 'redo_action'):
			self.redo_action.setEnabled(can_redo)
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
		layer_count = self.coa.get_layer_count() if hasattr(self, 'right_sidebar') else 0
		selected_indices = self.right_sidebar.get_selected_indices() if hasattr(self, 'right_sidebar') else []
		
		if selected_indices:
			if len(selected_indices) == 1:
				right_msg = f"Layers: {layer_count} | Selected: Layer {selected_indices[0] + 1}"
			else:
				right_msg = f"Layers: {layer_count} | Selected: {len(selected_indices)} layers"
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
	
	def redo(self):
		"""Redo the last undone action"""
		state = self.history_manager.redo()
		if state:
			self._restore_state(state)
	
	def new_coa(self):
		"""Clear everything and start with default empty CoA"""
		try:
			# Prompt to save if there are unsaved changes
			if not self._prompt_save_if_needed():
				return
			
			# Clear selection (layers will be empty via CoA model)
			self.right_sidebar.clear_selection()
			
			# Reset base to default pattern and colors
			from constants import DEFAULT_PATTERN_TEXTURE, DEFAULT_BASE_COLOR1, DEFAULT_BASE_COLOR2, DEFAULT_BASE_COLOR3
			default_pattern = DEFAULT_PATTERN_TEXTURE
			default_color_names = [DEFAULT_BASE_COLOR1, DEFAULT_BASE_COLOR2, DEFAULT_BASE_COLOR3]
			default_colors = [
				color_name_to_rgb(DEFAULT_BASE_COLOR1),
				color_name_to_rgb(DEFAULT_BASE_COLOR2),
				color_name_to_rgb(DEFAULT_BASE_COLOR3)
			]
			
			self.canvas_area.canvas_widget.set_base_texture(default_pattern)
			self.canvas_area.canvas_widget.set_base_colors(default_colors)
			
			# Create new empty CoA
			self.coa = CoA(pattern=default_pattern, pattern_color1=default_color_names[0], pattern_color2=default_color_names[1], pattern_color3=default_color_names[2])
			self.canvas_area.canvas_widget.update()
			
			# Reset property sidebar base colors with color names
			self.right_sidebar.set_base_colors(default_colors, default_color_names)
			
			# Reset asset sidebar to patterns mode with default category
			if hasattr(self, 'left_sidebar'):
				self.left_sidebar.current_mode = "patterns"
				self.left_sidebar.current_category = DEFAULT_BASE_CATEGORY
				self.left_sidebar.display_assets()
			
			# Switch to Base tab
			self.right_sidebar.tab_widget.setCurrentIndex(0)
			
			# Clear file path and mark as saved
			self.current_file_path = None
			self.is_saved = True
			self._update_window_title()
			
			# Clear history and save initial state
			self.history_manager.clear()
			self._save_state("New CoA")
		except Exception as e:
			loggerRaise(e, "Error creating new CoA")
			# Save to existing file
			self._save_to_file(self.current_file_path)
		else:
			# No file path yet, use Save As
			self.save_coa_as()
	
	def save_coa_as(self):
		"""Save current CoA to a new file (always prompts for location)"""
		try:
			# Open save file dialog
			filename, _ = QFileDialog.getSaveFileName(
				self,
				"Save Coat of Arms",
				"",
				"Text Files (*.txt);;All Files (*)"
			)
			
			if filename:
				self._save_to_file(filename)
		except Exception as e:
			loggerRaise(e, "Failed to save coat of arms")
		try:
			#COA INTEGRATION ACTION: Step 2 - Use CoA.to_string() for save operations
			# New model-based save path
			coa_string = self.coa.to_string()
			
			# Write directly to file
			with open(filename, 'w', encoding='utf-8') as f:
				f.write(coa_string)
			
			# OLD CODE (kept for now, will remove in Step 9):
			# Get current state
			# canvas = self.canvas_area.canvas_widget
			# base_colors = self.right_sidebar.get_base_colors()
			# base_color_names = [
			# 	getattr(canvas, 'base_color1_name', 'black'),
			# 	getattr(canvas, 'base_color2_name', 'yellow'),
			# 	getattr(canvas, 'base_color3_name', 'black')
			# ]
			# coa_data = build_coa_for_save(
			# 	base_colors, 
			# 	canvas.base_texture, 
			# 	self.right_sidebar.layers,
			# 	base_color_names
			# )
			# save_coa_to_file(coa_data, filename)
			
			# Update current file path and mark as saved
			self.current_file_path = filename
			self.is_saved = True
			self._update_window_title()
			
			# Add to recent files
			self._add_to_recent_files(filename)
			
			# Clear autosave file since we just saved
			if os.path.exists(self.autosave_file):
				os.remove(self.autosave_file)
		except Exception as e:
			loggerRaise(e, "Failed to save coat of arms")
	
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
			
			# Build clipboard text using CoA model's to_string method
			coa_text = self.coa.to_string()
			
			# Copy to clipboard
			QApplication.clipboard().setText(coa_text)
		except Exception as e:
			loggerRaise(e, "Failed to copy coat of arms")
	
	def paste_coa(self):
		"""Paste CoA from clipboard as text"""
		try:
			# Get clipboard text
			coa_text = QApplication.clipboard().text()
			if not coa_text.strip():
				QMessageBox.warning(self, "Paste Error", "Clipboard is empty.")
				return
			
			# Smart detection: check if this is a layer sub-block or full CoA
			if is_layer_subblock(coa_text):
				# This is a layer, paste as layer instead
				self.clipboard_actions.paste_layer()
				return
			
			# Parse using CoA model
			self.coa.clear()
			self.coa.parse(coa_text)
			
			# Update UI from CoA model
			self.canvas_area.canvas_widget.set_base_texture(self.coa.pattern)
			self.canvas_area.canvas_widget.set_base_colors([self.coa.pattern_color1, self.coa.pattern_color2, self.coa.pattern_color3])
			self.canvas_area.canvas_widget.base_color1_name = self.coa.pattern_color1_name
			self.canvas_area.canvas_widget.base_color2_name = self.coa.pattern_color2_name
			self.canvas_area.canvas_widget.base_color3_name = self.coa.pattern_color3_name
			
			base_color_names = [self.coa.pattern_color1_name, self.coa.pattern_color2_name, self.coa.pattern_color3_name]
			self.right_sidebar.set_base_colors([self.coa.pattern_color1, self.coa.pattern_color2, self.coa.pattern_color3], base_color_names)
			
			# Update UI
			self.right_sidebar.tab_widget.setCurrentIndex(1)
			self.right_sidebar._rebuild_layer_list()
			if self.coa.get_layer_count() > 0:
				self.right_sidebar._select_layer(0)
			
			# Update canvas
			self.canvas_area.canvas_widget.update()
			
			# Save to history after pasting
			self._save_state("Paste CoA")
		except Exception as e:
			loggerRaise(e, "Failed to paste coat of arms - clipboard may not contain valid data")
	
	def copy_layer(self):
		"""Copy selected layer(s) to clipboard"""
		try:
			# Check if layers are selected
			selected_indices = self.right_sidebar.get_selected_indices()
			if not selected_indices:
				return
			
			# Serialize all selected layers using service
			layer_texts = []
			for layer_idx in selected_indices:
				if 0 <= layer_idx < self.coa.get_layer_count():
					layer = self.coa.get_layer_by_index(layer_idx)
					layer_text = serialize_layer_to_text(layer)
					layer_texts.append(layer_text)
			
			if layer_texts:
				full_text = '\n\n'.join(layer_texts)
				QApplication.clipboard().setText(full_text)
		except Exception as e:
			loggerRaise(e, "Failed to copy layer")
	
	def paste_layer(self):
		"""Paste layer(s) from clipboard"""
		try:
			# Check if layers are selected
			selected_indices = self.right_sidebar.get_selected_indices()
			if not selected_indices:
				return
			
			# Sort indices to maintain order
			sorted_indices = sorted(selected_indices)
			
			# Duplicate all selected layers using CoA model
			new_uuids = []
			for layer_idx in sorted_indices:
				if layer_idx < self.coa.get_layer_count():
					layer = self.coa.get_layer_by_index(layer_idx)
					new_uuid = self.coa.duplicate_layer(layer.uuid)
					new_uuids.append(new_uuid)
			
			if not new_uuids:
				return
			
			# Select the newly duplicated layers by UUID
			self.right_sidebar.layer_list_widget.selected_layer_uuids = set(new_uuids)
			self.right_sidebar.layer_list_widget.last_selected_uuid = new_uuids[-1] if new_uuids else None
			
			# Clear layer thumbnail cache since indices have shifted
			if hasattr(self.right_sidebar, 'layer_list_widget') and self.right_sidebar.layer_list_widget:
				self.right_sidebar.layer_list_widget.clear_thumbnail_cache()
			
			# Rebuild the layer list UI
			self.right_sidebar._rebuild_layer_list()
			
			# Update canvas and transform widget
			self.canvas_area.canvas_widget.update()
			if self.canvas_area:
				self.canvas_area.update_transform_widget_for_layer()
			
			# Force immediate canvas redraw and window preview update
			self.canvas_area.canvas_widget.repaint()
			self.repaint()  # Update main window and taskbar preview
			
			# Save to history
			layer_word = "layers" if len(new_uuids) > 1 else "layer"
			self._save_state(f"Duplicate {len(new_uuids)} {layer_word}")
		except Exception as e:
			loggerRaise(e, "Failed to duplicate layer")
			# Check if a single layer is selected (multi-layer ctrl+drag not supported)
			selected_indices = self.right_sidebar.get_selected_indices()
			if not selected_indices or len(selected_indices) != 1:
				return
			
			layer_idx = selected_indices[0]
			if layer_idx >= self.coa.get_layer_count():
				return
			
			# Get layer and duplicate using CoA model
			layer = self.coa.get_layer_by_index(layer_idx)
			new_uuid = self.coa.duplicate_layer(layer.uuid)
			
			# CoA.duplicate_layer inserts AFTER original, but we need it BEFORE
			# So move it from layer_idx+1 to layer_idx
			self.coa.move_layer(new_uuid, layer_idx)
			
			# Keep the ORIGINAL layer selected (which is now at layer_idx + 1)
			self.right_sidebar.selected_layer_indices = {layer_idx + 1}
			self.right_sidebar.last_selected_index = layer_idx + 1
			
			# Clear layer thumbnail cache since indices have shifted
			if hasattr(self.right_sidebar, 'layer_list_widget') and self.right_sidebar.layer_list_widget:
				self.right_sidebar.layer_list_widget.clear_thumbnail_cache()
			
			# Rebuild the layer list UI
			self.right_sidebar._rebuild_layer_list()
			
			# Update canvas layers (but don't update transform widget - that would kill the drag)
			self.canvas_area.canvas_widget.update()
			
			# Force immediate canvas redraw
			self.canvas_area.canvas_widget.repaint()
			self.repaint()
			
			# Save to history
			self._save_state("Duplicate layer below")
		except Exception as e:
			loggerRaise(e, "Error duplicating layer below")
	
	def _split_selected_layer(self):
		"""Split selected layer's instances into separate layers"""
		try:
			# Require single layer selection
			selected_uuids = self.right_sidebar.get_selected_uuids()
			if not selected_uuids or len(selected_uuids) != 1:
				QMessageBox.information(self, "Split Instances", 
					"Please select a single layer to split.")
				return
			
			uuid = selected_uuids[0]
			
			# Check if it's multi-instance
			instance_count = self.coa.get_layer_instance_count(uuid)
			if instance_count <= 1:
				QMessageBox.information(self, "Split Instances", 
					"Selected layer only has one instance.")
				return
			
			# Split the layer using CoA method (returns new UUIDs)
			new_uuids = self.coa.split_layer(uuid)
			
			# Clear thumbnail cache
			if hasattr(self.right_sidebar, 'layer_list_widget') and self.right_sidebar.layer_list_widget:
				self.right_sidebar.layer_list_widget.clear_thumbnail_cache()
			
			# Rebuild UI
			self.right_sidebar._rebuild_layer_list()
			self.canvas_area.canvas_widget.update()
			
			# Select the new layers
			if new_uuids:
				self.right_sidebar.layer_list_widget.selected_layer_uuids = set(new_uuids)
				self.right_sidebar.layer_list_widget.last_selected_uuid = new_uuids[0]
				self.right_sidebar.layer_list_widget.update_selection_visuals()
			
			# Force repaint
			self.canvas_area.canvas_widget.repaint()
			self.repaint()
			
			# Save to history
			self._save_state(f"Split {len(new_uuids)} instances")
		except Exception as e:
			loggerRaise(e, "Failed to split layer")
	
	def _merge_selected_layers(self):
		"""Merge selected layers as instances into one layer"""
		try:
			from services.layer_operations import merge_layers_as_instances
			from PyQt5.QtWidgets import QMessageBox
			
			# Require multi-selection
			selected_uuids = list(self.right_sidebar.get_selected_uuids())
			if not selected_uuids or len(selected_uuids) < 2:
				QMessageBox.information(self, "Merge as Instances", 
					"Please select multiple layers to merge.")
				return
			
			# Check compatibility using CoA method
			is_compatible, differences = self.coa.check_merge_compatibility(selected_uuids)
			use_topmost = False
			if not is_compatible:
				# Show warning dialog
				diff_list = []
				for prop, indices in differences.items():
					diff_list.append(f"  • {prop}: differs on layers {', '.join(str(i) for i in indices)}")
				diff_text = "\n".join(diff_list)
				
				msg = QMessageBox(self)
				msg.setIcon(QMessageBox.Warning)
				msg.setWindowTitle("Incompatible Layers")
				msg.setText("The selected layers have different properties:")
				msg.setInformativeText(f"{diff_text}\n\nMerge anyway using properties from topmost layer?")
				msg.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
				msg.setDefaultButton(QMessageBox.Cancel)
				
				result = msg.exec_()
				if result != QMessageBox.Yes:
					return
				use_topmost = True
			
			# Merge layers (get Layer objects for merge function)
			layers_to_merge = [self.coa.get_layer_by_uuid(uuid) for uuid in selected_uuids]
		
			# Merge all layers into the first one (it keeps its UUID and position)
			merged_uuid = self.coa.merge_layers_into_first(selected_uuids)
			
			# Update selection to the merged layer
			self.right_sidebar.layer_list_widget.selected_layer_uuids = {merged_uuid}
			self.right_sidebar.layer_list_widget.clear_thumbnail_cache()
			
			# Rebuild UI and update selection
			self.right_sidebar._rebuild_layer_list()
			self.right_sidebar.layer_list_widget.update_selection_visuals()  # Ensure UI highlights selection
			self.right_sidebar._update_layer_selection()
			self.right_sidebar._load_layer_properties()  # Load properties for merged layer
			self.canvas_area.canvas_widget.update()
			self.canvas_area.update_transform_widget_for_layer()
			
			# Save to history
			merged_layer = self.coa.get_layer_by_uuid(merged_uuid)
			instance_count = merged_layer.instance_count
			self._save_state(f"Merge {len(layers_to_merge)} layers ({instance_count} instances)")
		except Exception as e:
			loggerRaise(e, "Failed to merge layers")
	
	def _group_or_ungroup_container(self):
		"""Group selected layers into a container or ungroup if full container selected"""
		try:
			selected_uuids = self.right_sidebar.get_selected_uuids()
			if len(selected_uuids) < 2:
				return
			
			# Check if a container was explicitly selected
			layer_list = self.right_sidebar.layer_list_widget
			is_container_selected = len(layer_list.selected_container_uuids) > 0
			
			if is_container_selected:
				# Ungroup: remove container
				self._save_state("Ungroup Container")
				for uuid in selected_uuids:
					self.coa.set_layer_container(uuid, None)
				layer_list.selected_container_uuids.clear()
				self.right_sidebar._rebuild_layer_list()
				self.right_sidebar.layer_list_widget.update_selection_visuals()
			else:
				# Group: create container
				if hasattr(self.right_sidebar, 'layer_list_widget'):
					self.right_sidebar.layer_list_widget._create_container_from_selection()
		except Exception as e:
			loggerRaise(e, "Failed to group/ungroup layers")
	
	def paste_layer_smart(self):
		"""Smart paste - delegates to clipboard_actions"""
		self.clipboard_actions.paste_layer_smart()
	
	def paste_layer_at_position(self, mouse_pos, canvas_geometry):
		"""Paste layers at mouse position - delegates to clipboard_actions"""
		self.clipboard_actions.paste_layer_at_position(mouse_pos, canvas_geometry)
	
	def _apply_coa_data(self, coa_data):
		"""Apply parsed CoA data to editor
		
		DEPRECATED: This function is legacy code from the dict-based system.
		Use CoA.from_string() directly instead to parse into the CoA model.
		"""
		raise NotImplementedError("_apply_coa_data is deprecated. Use CoA.from_string() instead.")

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
	
	# ===========================================
	# Layer Generator Methods
	# ===========================================
	
	def _preload_shapes(self):
		"""Preload all SVG shapes at startup."""
		# Get path to SVG directory
		editor_dir = os.path.dirname(os.path.abspath(__file__))
		svg_dir = os.path.join(os.path.dirname(editor_dir), 'assets', 'svg')
		
		# Preload shapes into ShapeGenerator
		ShapeGenerator.preload_shapes(svg_dir)
	
	def _populate_shape_menu(self):
		"""Populate the Shape submenu with loaded SVG shapes."""
		shape_names = ShapeGenerator.get_shape_names()
		
		if not shape_names:
			# No shapes available
			no_shapes_action = self.shape_menu.addAction("(No shapes available)")
			no_shapes_action.setEnabled(False)
			return
		
		# Add menu item for each shape
		for shape_name in shape_names:
			action = self.shape_menu.addAction(shape_name)
			action.triggered.connect(lambda checked, name=shape_name: self._open_generator('shape', name))
	
	def _open_generator(self, generator_type: str, shape_name: str = None):
		"""Open the generator popup with specified generator type.
		
		Args:
			generator_type: Type of generator ('circular', 'line', 'spiral', 'shape', 
			                'grid', 'diamond', 'fibonacci', 'radial', 'star')
			shape_name: For 'shape' type, the name of the shape to use
		"""
		# Create generator instance based on type
		generator = None
		
		if generator_type == 'circular':
			generator = CircularGenerator()
		elif generator_type == 'line':
			generator = LineGenerator()
		elif generator_type == 'spiral':
			generator = SpiralGenerator()
		elif generator_type == 'shape':
			generator = ShapeGenerator(initial_shape=shape_name)
		elif generator_type == 'grid':
			generator = GridGenerator()
		elif generator_type == 'diamond':
			generator = DiamondGenerator()
		elif generator_type == 'fibonacci':
			generator = FibonacciGenerator()
		elif generator_type == 'radial':
			generator = RadialGenerator()
		elif generator_type == 'star':
			generator = StarGenerator()
		elif generator_type == 'vanilla':
			generator = VanillaGenerator()
		else:
			print(f"Unknown generator type: {generator_type}")
			return
		
		# Create popup if it doesn't exist
		if not self.generator_popup:
			self.generator_popup = GeneratorPopup(self)
		
		# Load generator into popup
		self.generator_popup.load_generator(generator)
		
		# Show popup
		result = self.generator_popup.exec_()
		
		# If user clicked Generate, create the layer
		if result == self.generator_popup.Accepted:
			# Check if text mode is active
			if self.generator_popup.is_text_mode():
				# Text mode: will create multiple layers (one per character)
				text_data = self.generator_popup.get_text_and_positions()
				if text_data:
					text, positions = text_data
					# Show warning dialog
					from PyQt5.QtWidgets import QMessageBox
					reply = QMessageBox.question(
						self,
						'Text Mode Warning',
						'Text mode will create multiple layers (one per character), not a single multi-instance layer.\n\nContinue?',
						QMessageBox.Yes | QMessageBox.No,
						QMessageBox.No
					)
					if reply == QMessageBox.Yes:
						self._create_text_layers(text, positions)
			else:
				# Count mode: create single multi-instance layer
				generated_instances = self.generator_popup.get_generated_instances()
				if generated_instances is not None and len(generated_instances) > 0:
					self._create_generated_layer(generated_instances)
	
	def _open_generator_with_asset(self, asset_texture: str, generator_type: str = 'circular'):
		"""Open generator popup with pre-selected asset.
		
		Args:
			asset_texture: Texture filename (.dds) of the asset to use
			generator_type: Type of generator to open ('circular', 'line', 'spiral', 'grid', 'diamond', 'fibonacci', 'radial', 'star', 'vanilla')
		"""
		# Import and create appropriate generator based on type
		generator = None
		
		if generator_type == 'circular':
			from services.layer_generator.generators.circular_generator import CircularGenerator
			generator = CircularGenerator()
		elif generator_type == 'line':
			from services.layer_generator.generators.line_generator import LineGenerator
			generator = LineGenerator()
		elif generator_type == 'spiral':
			from services.layer_generator.generators.spiral_generator import SpiralGenerator
			generator = SpiralGenerator()
		elif generator_type == 'grid':
			from services.layer_generator.generators.grid_generator import GridGenerator
			generator = GridGenerator()
		elif generator_type == 'diamond':
			from services.layer_generator.generators.diamond_generator import DiamondGenerator
			generator = DiamondGenerator()
		elif generator_type == 'fibonacci':
			from services.layer_generator.generators.fibonacci_generator import FibonacciGenerator
			generator = FibonacciGenerator()
		elif generator_type == 'radial':
			from services.layer_generator.generators.radial_generator import RadialGenerator
			generator = RadialGenerator()
		elif generator_type == 'star':
			from services.layer_generator.generators.star_generator import StarGenerator
			generator = StarGenerator()
		elif generator_type == 'vanilla':
			from services.layer_generator.generators.vanilla_generator import VanillaGenerator
			generator = VanillaGenerator()
		
		if not generator:
			return
		
		# Create popup if it doesn't exist
		if not self.generator_popup:
			self.generator_popup = GeneratorPopup(self)
		
		# Load generator into popup
		self.generator_popup.load_generator(generator)
		
		# Show popup
		result = self.generator_popup.exec_()
		
		# If user clicked Generate, create the layer with selected asset
		if result == self.generator_popup.Accepted:
			# Check if text mode is active
			if self.generator_popup.is_text_mode():
				# Text mode: will create multiple layers (one per character) in a container
				text_data = self.generator_popup.get_text_and_positions()
				if text_data:
					text, positions = text_data
					self._create_text_layers(text, positions, emblem_texture=asset_texture)
			else:
				# Count mode: create single multi-instance layer
				generated_instances = self.generator_popup.get_generated_instances()
				if generated_instances is not None and len(generated_instances) > 0:
					self._create_generated_layer(generated_instances, emblem_texture=asset_texture)
	
	def _create_generated_layer(self, instances: 'np.ndarray', emblem_texture: str = None):
		"""Create a layer from generated instance transforms.
		
		Args:
			instances: 5xN numpy array [[x, y, scale_x, scale_y, rotation], ...]
			emblem_texture: Optional custom emblem texture (.dds filename)
		"""
		try:
			import numpy as np
			from services.layer_generator.layer_string_builder import build_layer_string
			
			default_emblem = emblem_texture if emblem_texture else "ce_fleur.dds"
			
			# Apply frame scale compensation to prevent growth on drag
			# Get current frame scale
			frame_scale, _ = self.canvas_area.canvas_widget.get_frame_transform()
			frame_scale_x, frame_scale_y = frame_scale
			
			# Compensate instance scales by dividing by frame scale
			compensated_instances = instances.copy()
			compensated_instances[:, 2] /= frame_scale_x  # scale_x
			compensated_instances[:, 3] /= frame_scale_y  # scale_y
			
			# Build layer string
			layer_string = build_layer_string(compensated_instances, default_emblem)
			
			# Check for selection to insert above
			selected_uuids = self.right_sidebar.get_selected_uuids()
			target_uuid = selected_uuids[0] if selected_uuids else None
			
			# Parse directly into main CoA (parser handles insertion)
			new_uuids = self.coa.parse(layer_string, target_uuid=target_uuid)
			
			# Update UI
			self.right_sidebar._rebuild_layer_list()
			self.canvas_area.canvas_widget.update()
			
			# Select the newly created layer
			if new_uuids:
				self.right_sidebar.layer_list_widget.selected_layer_uuids = set(new_uuids)
				self.right_sidebar.layer_list_widget.last_selected_uuid = new_uuids[0]
				self.right_sidebar.layer_list_widget.update_selection_visuals()
			
			# Save to history
			count = len(instances)
			self._save_state(f"Generate layer ({count} instances)")
			
			self.status_left.setText(f"Generated layer with {count} instances")
			
		except Exception as e:
			loggerRaise(e, f"Failed to create generated layer: {str(e)}")
	
	def _create_text_layers(self, text: str, positions: 'np.ndarray', emblem_texture: str = None):
		"""Create multiple layers for text mode (one layer per character).
		
		Args:
			text: Text string to render
			positions: 6xN numpy array [[x, y, scale_x, scale_y, rotation, label_code], ...]
			emblem_texture: Optional custom emblem texture (ignored for text - uses letter emblems)
		"""
		try:
			from services.layer_generator.text_emblem_mapper import get_emblem_for_char, label_code_to_char
			from services.layer_generator.layer_string_builder import build_layer_string
			
			# Reconstruct filtered text from label codes (6th column)
			# This ensures we match exactly what the generator used
			if positions.shape[1] < 6:
				print("Error: positions array missing label codes (6th column)")
				return
			
			label_codes = positions[:, 5].astype(int)
			filtered_text = ''.join(label_code_to_char(code) for code in label_codes)
			
			if len(filtered_text) == 0:
				print("No valid characters in text")
				return
			
			# Generate container UUID for all text layers
			container_name = f"text ({filtered_text})"
			container_uuid = self.coa.generate_container_uuid(container_name)
			
			# Check for selection to insert above
			selected_uuids = self.right_sidebar.get_selected_uuids()
			target_uuid = selected_uuids[0] if selected_uuids else None
			
			created_uuids = []
			
			# Create layers in reverse order so layer list reads correctly top-to-bottom
			for i in range(len(filtered_text) - 1, -1, -1):
				char = filtered_text[i]
				if char == ' ':
					continue  # Skip spaces - no layer created
				
				# Get emblem for this character
				from services.layer_generator.text_emblem_mapper import get_emblem_for_char
				emblem = get_emblem_for_char(char)
				if not emblem:
					continue  # Skip invalid characters
				
				# Build layer string (single instance, use first 5 columns)
				layer_string = build_layer_string(positions[i], emblem, container_uuid=container_uuid)
				
				# Parse directly into main CoA (parser handles insertion)
				new_uuids = self.coa.parse(layer_string, target_uuid=target_uuid)
				
				# Stack subsequent layers on top
				if new_uuids:
					target_uuid = new_uuids[0]
					created_uuids.extend(new_uuids)
			
			# Update UI
			self.right_sidebar._rebuild_layer_list()
			self.canvas_area.canvas_widget.update()
			
			# Select the newly created container and collapse it
			if created_uuids:
				self.right_sidebar.layer_list_widget.selected_layer_uuids = set(created_uuids)
				self.right_sidebar.layer_list_widget.selected_container_uuids = {container_uuid}
				self.right_sidebar.layer_list_widget.collapsed_containers.add(container_uuid)  # Start collapsed
				self.right_sidebar.layer_list_widget.last_selected_uuid = created_uuids[-1]
				self.right_sidebar.layer_list_widget.update_selection_visuals()
			
			# Save to history
			char_count = len(created_uuids)
			self._save_state(f"Generate text layers ({char_count} characters)")
			
			self.status_left.setText(f"Generated {char_count} text layers in container")
			
		except Exception as e:
			loggerRaise(e, f"Failed to create text layers: {str(e)}")


def main():
	"""Main entry point for the Coat of Arms Designer application"""
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
