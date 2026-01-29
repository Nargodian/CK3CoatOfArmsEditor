import sys
import os
import json

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

# Utility imports
from utils.coa_parser import parse_coa_string, serialize_coa_to_string
from utils.history_manager import HistoryManager
from utils.color_utils import color_name_to_rgb, rgb_to_color_name

# Service imports
from services.file_operations import (
    save_coa_to_file, load_coa_from_file, 
    build_coa_for_save, coa_to_clipboard_text, is_layer_subblock
)
from services.layer_operations import (
    duplicate_layer, serialize_layer_to_text, parse_layer_from_text,
    parse_multiple_layers_from_text
)
from services.coa_serializer import parse_coa_for_editor
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


class CoatOfArmsEditor(QMainWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("Coat Of Arms Designer")
		self.resize(1280, 720)
		self.setMinimumSize(1280, 720)
		
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
		
		# Initialize action handlers (composition pattern)
		self.file_actions = FileActions(self)
		self.clipboard_actions = ClipboardActions(self)
		self.transform_actions = LayerTransformActions(self)
		
		self.setup_ui()
		
		# Check for autosave recovery after UI is set up
		QTimer.singleShot(500, self._check_autosave_recovery)
	
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
		splitter.addWidget(self.canvas_area)
		
		# Right properties sidebar
		self.right_sidebar = PropertySidebar(self)
		self.right_sidebar.main_window = self
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
		new_action.triggered.connect(self.new_coa)
		
		open_action = file_menu.addAction("&Open...")
		open_action.setShortcut("Ctrl+O")
		open_action.triggered.connect(self.load_coa)
		
		# Recent Files submenu
		self.recent_menu = file_menu.addMenu("Recent Files")
		self._update_recent_files_menu()
		
		file_menu.addSeparator()
		
		save_action = file_menu.addAction("&Save")
		save_action.setShortcut("Ctrl+S")
		save_action.triggered.connect(self.save_coa)
		
		save_as_action = file_menu.addAction("Save &As...")
		save_as_action.setShortcut("Ctrl+Shift+S")
		save_as_action.triggered.connect(self.save_coa_as)
		
		file_menu.addSeparator()
		
		export_png_action = file_menu.addAction("Export as &PNG...")
		export_png_action.setShortcut("Ctrl+E")
		export_png_action.triggered.connect(self.export_png)
		
		file_menu.addSeparator()
		
		copy_coa_action = file_menu.addAction("&Copy CoA to Clipboard")
		copy_coa_action.setShortcut("Ctrl+Shift+C")
		copy_coa_action.triggered.connect(self.copy_coa)
		
		paste_coa_action = file_menu.addAction("&Paste CoA from Clipboard")
		paste_coa_action.setShortcut("Ctrl+Shift+V")
		paste_coa_action.triggered.connect(self.paste_coa)
		
		file_menu.addSeparator()
		
		copy_layer_action = file_menu.addAction("Copy &Layer")
		copy_layer_action.setShortcut("Ctrl+C")
		copy_layer_action.triggered.connect(self.copy_layer)
		
		paste_layer_action = file_menu.addAction("Paste Layer")
		paste_layer_action.setShortcut("Ctrl+V")
		paste_layer_action.triggered.connect(self.paste_layer_smart)
		
		duplicate_layer_action = file_menu.addAction("&Duplicate Layer")
		duplicate_layer_action.setShortcut("Ctrl+D")
		duplicate_layer_action.triggered.connect(self.duplicate_selected_layer)
		
		file_menu.addSeparator()
		
		exit_action = file_menu.addAction("E&xit")
		exit_action.setShortcut("Alt+F4")
		exit_action.triggered.connect(self.close)
		
		# Edit Menu
		edit_menu = menubar.addMenu("&Edit")
		
		self.undo_action = edit_menu.addAction("&Undo")
		self.undo_action.setShortcut("Ctrl+Z")
		self.undo_action.triggered.connect(self.undo)
		self.undo_action.setEnabled(False)
		
		self.redo_action = edit_menu.addAction("&Redo")
		self.redo_action.setShortcut("Ctrl+Y")
		self.redo_action.triggered.connect(self.redo)
		self.redo_action.setEnabled(False)
		
		edit_menu.addSeparator()
		
		# Transform submenu
		transform_menu = edit_menu.addMenu("&Transform")
		
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
		
		edit_menu.addSeparator()
		
		# Align submenu
		align_menu = edit_menu.addMenu("&Align Layers")
		
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
		move_to_menu = edit_menu.addMenu("&Move to")
		
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
		
		edit_menu.addSeparator()
		
		select_all_action = edit_menu.addAction("Select &All Layers")
		select_all_action.setShortcut("Ctrl+A")
		select_all_action.triggered.connect(self._select_all_layers)
		
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
		if self.right_sidebar.layers:
			all_indices = set(range(len(self.right_sidebar.layers)))
			self.right_sidebar.set_selected_indices(all_indices)
			if self.canvas_area:
				self.canvas_area.update_transform_widget_for_layer()
			self.right_sidebar.tab_widget.setTabEnabled(2, True)
	
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
	
	def _zoom_out(self):
		"""Zoom out on canvas"""
		if hasattr(self.canvas_area, 'canvas_widget'):
			self.canvas_area.canvas_widget.zoom_out()
	
	def _zoom_reset(self):
		"""Reset canvas zoom to 100%"""
		if hasattr(self.canvas_area, 'canvas_widget'):
			self.canvas_area.canvas_widget.zoom_reset()
	
	def _set_grid_size(self, divisions):
		"""Set grid size (0 = off, 2/4/8/16 = grid divisions)"""
		if hasattr(self.canvas_area, 'canvas_widget'):
			if divisions == 0:
				self.canvas_area.canvas_widget.set_show_grid(False)
			else:
				self.canvas_area.canvas_widget.set_show_grid(True)
				self.canvas_area.canvas_widget.set_grid_divisions(divisions)
	
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
			QMessageBox.critical(self, "Export Error", f"Failed to export PNG:\n{str(e)}")
	
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
			print(f"Error loading config: {e}")
			self.recent_files = []
	
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
			print(f"Error saving config: {e}")
	
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
			# Load the file
			coa_data = load_coa_from_file(filepath)
			self._apply_coa_data(coa_data)
			
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
			QMessageBox.critical(self, "Load Error", f"Failed to load coat of arms:\n{str(e)}")
	
	def _clear_recent_files(self):
		"""Clear the recent files list"""
		self.recent_files = []
		self._update_recent_files_menu()
		self._save_config()
	
	def _autosave(self):
		"""Perform autosave to temporary file"""
		try:
			# Only autosave if there are unsaved changes
			if not self.is_saved:
				# Create config directory if it doesn't exist
				os.makedirs(self.config_dir, exist_ok=True)
				
				# Get current state
				canvas = self.canvas_area.canvas_widget
				base_colors = self.right_sidebar.get_base_colors()
				base_color_names = [
					getattr(canvas, 'base_color1_name', 'black'),
					getattr(canvas, 'base_color2_name', 'yellow'),
					getattr(canvas, 'base_color3_name', 'black')
				]
				
				# Build CoA data
				coa_data = build_coa_for_save(
					base_colors,
					canvas.base_texture,
					self.right_sidebar.layers,
					base_color_names
				)
				
				# Save to autosave file
				save_coa_to_file(coa_data, self.autosave_file)
				print("Autosaved")
		except Exception as e:
			print(f"Autosave failed: {e}")
	
	def _check_autosave_recovery(self):
		"""Check if autosave file exists and offer to recover"""
		try:
			if os.path.exists(self.autosave_file):
				reply = QMessageBox.question(
					self,
					"Recover Autosave",
					"An autosave file was found. Would you like to recover it?",
					QMessageBox.Yes | QMessageBox.No,
					QMessageBox.Yes
				)
				
				if reply == QMessageBox.Yes:
					# Load autosave
					coa_data = load_coa_from_file(self.autosave_file)
					self._apply_coa_data(coa_data)
					
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
			print(f"Error checking autosave: {e}")
			# Try to remove corrupted autosave file
			try:
				if os.path.exists(self.autosave_file):
					os.remove(self.autosave_file)
			except:
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
		"""Apply texture to selected layer or create new layer"""
		self.right_sidebar.set_emblem_color_count(color_count)
		selected_indices = self.right_sidebar.get_selected_indices()
		
		if selected_indices:
			self._update_layer_texture(selected_indices[0], dds_filename, color_count)
		else:
			self._create_layer_with_texture(dds_filename, color_count)
	
	def _update_layer_texture(self, idx, dds_filename, color_count):
		"""Update existing layer's texture while preserving other properties"""
		if 0 <= idx < len(self.right_sidebar.layers):
			old_layer = self.right_sidebar.layers[idx]
			
			# Preserve all existing properties, update only texture-related fields
			self.right_sidebar.layers[idx] = {
				**old_layer,
				'filename': dds_filename,
				'path': dds_filename,
				'colors': color_count
			}
			
			# Invalidate thumbnail cache for this layer since texture changed
			if hasattr(self.right_sidebar, 'layer_list_widget') and self.right_sidebar.layer_list_widget:
				self.right_sidebar.layer_list_widget.invalidate_thumbnail(idx)
			
			# Update UI and canvas
			self.right_sidebar._rebuild_layer_list()
			self.right_sidebar._update_layer_selection()
			self.canvas_area.canvas_widget.set_layers(self.right_sidebar.layers)
			self._save_state("Change layer texture")
	
	def _create_layer_with_texture(self, dds_filename, color_count):
		"""Create new layer with selected texture at top of stack"""
		new_layer = {
			'filename': dds_filename,
			'path': dds_filename,
			'colors': color_count,
			'depth': 0,
			'pos_x': 0.5,
			'pos_y': 0.5,
			'scale_x': DEFAULT_SCALE_X,
			'scale_y': DEFAULT_SCALE_Y,
			'flip_x': DEFAULT_FLIP_X,
			'flip_y': DEFAULT_FLIP_Y,
			'rotation': DEFAULT_ROTATION,
			'color1': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR1]['rgb'],
			'color2': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR2]['rgb'],
			'color3': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR3]['rgb'],
			'color1_name': DEFAULT_EMBLEM_COLOR1,
			'color2_name': DEFAULT_EMBLEM_COLOR2,
			'color3_name': DEFAULT_EMBLEM_COLOR3,
			'mask': None  # No mask = render everywhere (default)
		}
		
		# Append to end of array (which displays at top due to reversed UI)
		self.right_sidebar.layers.append(new_layer)
		new_index = len(self.right_sidebar.layers) - 1
		self.right_sidebar.selected_layer_indices = {new_index}
		self.right_sidebar.last_selected_index = new_index
		
		# Update UI
		self.right_sidebar._rebuild_layer_list()
		self.right_sidebar._update_layer_selection()
		
		# Update canvas
		self.canvas_area.canvas_widget.set_layers(self.right_sidebar.layers)
		
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
		"""Filter events to capture arrow keys before child widgets consume them"""
		if event.type() == event.KeyPress:
			# Intercept arrow keys when layers are selected
			if event.key() in [Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down]:
				selected_indices = self.right_sidebar.get_selected_indices()
				if selected_indices:
					# Handle arrow key movement
					from constants import ARROW_KEY_MOVE_NORMAL, ARROW_KEY_MOVE_FINE
					move_amount = ARROW_KEY_MOVE_FINE if event.modifiers() & Qt.ShiftModifier else ARROW_KEY_MOVE_NORMAL
					
					for idx in selected_indices:
						layer = self.right_sidebar.layers[idx]
						if event.key() == Qt.Key_Left:
							layer['pos_x'] = max(0.0, layer.get('pos_x', 0.5) - move_amount)
						elif event.key() == Qt.Key_Right:
							layer['pos_x'] = min(1.0, layer.get('pos_x', 0.5) + move_amount)
						elif event.key() == Qt.Key_Up:
							layer['pos_y'] = max(0.0, layer.get('pos_y', 0.5) - move_amount)
						elif event.key() == Qt.Key_Down:
							layer['pos_y'] = min(1.0, layer.get('pos_y', 0.5) + move_amount)
					
					# Update UI
					self.right_sidebar._load_layer_properties()
					self.canvas_area.canvas_widget.set_layers(self.right_sidebar.layers)
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
		# Delete key for delete layer
		elif event.key() == Qt.Key_Delete:
			if self.right_sidebar.get_selected_indices():
				self.right_sidebar._delete_layer()
				event.accept()
			else:
				super().keyPressEvent(event)
		# Ctrl+A for select all layers
		elif event.key() == Qt.Key_A and event.modifiers() & Qt.ControlModifier:
			if self.right_sidebar.layers:
				# Select all layer indices
				all_indices = set(range(len(self.right_sidebar.layers)))
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
			if 0 <= idx < len(self.right_sidebar.layers):
				layer = self.right_sidebar.layers[idx]
				layer['rotation'] = (layer['rotation'] + angle_delta) % 360
		
		# Update canvas
		self.canvas_area.canvas_widget.set_layers(self.right_sidebar.layers)
		
		# Update transform widget (which updates properties panel)
		self.canvas_area.update_transform_widget_for_layer()
		
		# Save to history
		self._save_state(f"Rotate {'+' if angle_delta > 0 else ''}{angle_delta}°")
	
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
			
			# Update layer properties and transform widget if layers are selected
			selected_indices = list(state.get('selected_layer_indices', set()))
			if selected_indices:
				self.right_sidebar._load_layer_properties()
				self.canvas_area.update_transform_widget_for_layer()
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
			
			# Clear all layers
			self.right_sidebar.layers = []
			self.right_sidebar.clear_selection()
			self.right_sidebar._rebuild_layer_list()
			
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
			self.canvas_area.canvas_widget.set_layers([])
			
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
			QMessageBox.critical(self, "Error", f"Error creating new CoA: {e}")
	
	def save_coa(self):
		"""Save current CoA - if no file path, prompts for location"""
		if self.current_file_path:
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
			QMessageBox.critical(self, "Save Error", f"Failed to save coat of arms:\n{str(e)}")
	
	def _save_to_file(self, filename):
		"""Internal method to save CoA data to a file"""
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
			
			# Save to file
			save_coa_to_file(coa_data, filename)
			
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
			QMessageBox.critical(self, "Save Error", f"Failed to save coat of arms:\n{str(e)}")
	
	def load_coa(self):
		"""Load a coat of arms from file"""
		self.file_actions.load_coa()
	
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
		except Exception as e:
			QMessageBox.warning(self, "Copy Error", f"Failed to copy coat of arms: {str(e)}")
	
	def paste_coa(self):
		"""Paste CoA from clipboard and apply to editor"""
		try:
			# Get clipboard text
			coa_text = QApplication.clipboard().text()
			if not coa_text.strip():
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
			QMessageBox.critical(self, "Paste Error", f"Failed to paste coat of arms:\n{str(e)}\n\nThe clipboard may not contain valid coat of arms data.")
	
	def copy_layer(self):
		"""Copy all selected layers to clipboard as CoA sub-blocks"""
		try:
			# Check if layers are selected
			selected_indices = self.right_sidebar.get_selected_indices()
			if not selected_indices:
				return
			
			# Serialize all selected layers using service
			layer_texts = []
			for layer_idx in selected_indices:
				if 0 <= layer_idx < len(self.right_sidebar.layers):
					layer = self.right_sidebar.layers[layer_idx]
					layer_text = serialize_layer_to_text(layer)
					layer_texts.append(layer_text)
			
			if layer_texts:
				full_text = '\n\n'.join(layer_texts)
				QApplication.clipboard().setText(full_text)
		except Exception as e:
			QMessageBox.warning(self, "Copy Error", f"Failed to copy layer: {str(e)}")
	
	def duplicate_selected_layer(self):
		"""Duplicate the currently selected layers"""
		try:
			# Check if layers are selected
			selected_indices = self.right_sidebar.get_selected_indices()
			if not selected_indices:
				return
			
			# Sort indices to maintain order
			sorted_indices = sorted(selected_indices)
			
			# Duplicate all selected layers
			duplicated_layers = []
			for layer_idx in sorted_indices:
				if layer_idx < len(self.right_sidebar.layers):
					layer = self.right_sidebar.layers[layer_idx]
					duplicated_layer = duplicate_layer(layer)
					duplicated_layers.append(duplicated_layer)
			
			if not duplicated_layers:
				return
			
			# Determine insertion position
			if len(selected_indices) > 1:
				# Multiple layers selected - place at the end (highest index = in front)
				insert_position = len(self.right_sidebar.layers)
			else:
				# Single layer selected - place directly above it (higher index = in front)
				insert_position = max(sorted_indices) + 1
			
			# Insert all duplicated layers at position
			for i, dup_layer in enumerate(duplicated_layers):
				self.right_sidebar.layers.insert(insert_position + i, dup_layer)
			
			# Select the newly duplicated layers
			new_indices = set(range(insert_position, insert_position + len(duplicated_layers)))
			self.right_sidebar.selected_layer_indices = new_indices
			self.right_sidebar.last_selected_index = insert_position
			
			# Clear layer thumbnail cache since indices have shifted
			if hasattr(self.right_sidebar, 'layer_list_widget') and self.right_sidebar.layer_list_widget:
				self.right_sidebar.layer_list_widget.clear_thumbnail_cache()
			
			# Rebuild the layer list UI
			self.right_sidebar._rebuild_layer_list()
			
			# Update canvas and transform widget
			self.canvas_area.canvas_widget.set_layers(self.right_sidebar.layers)
			if self.canvas_area:
				self.canvas_area.update_transform_widget_for_layer()
			
			# Force immediate canvas redraw and window preview update
			self.canvas_area.canvas_widget.repaint()
			self.repaint()  # Update main window and taskbar preview
			
			# Save to history
			layer_word = "layers" if len(duplicated_layers) > 1 else "layer"
			self._save_state(f"Duplicate {len(duplicated_layers)} {layer_word}")
		except Exception as e:
			QMessageBox.warning(self, "Duplicate Error", f"Failed to duplicate layer: {str(e)}")
	
	def duplicate_selected_layer_below(self):
		"""Duplicate the currently selected layer BELOW the original (for Ctrl+drag)"""
		try:
			# Check if a single layer is selected (multi-layer ctrl+drag not supported)
			selected_indices = self.right_sidebar.get_selected_indices()
			if not selected_indices or len(selected_indices) != 1:
				return
			
			layer_idx = selected_indices[0]
			if layer_idx >= len(self.right_sidebar.layers):
				return
			
			# Duplicate the layer
			layer = self.right_sidebar.layers[layer_idx]
			duplicated_layer = duplicate_layer(layer)
			
			# Insert BEFORE (below) the original layer - lower index = further back
			insert_position = layer_idx
			self.right_sidebar.layers.insert(insert_position, duplicated_layer)
			
			# Keep the ORIGINAL layer selected (which is now at layer_idx + 1)
			self.right_sidebar.selected_layer_indices = {layer_idx + 1}
			self.right_sidebar.last_selected_index = layer_idx + 1
			
			# Clear layer thumbnail cache since indices have shifted
			if hasattr(self.right_sidebar, 'layer_list_widget') and self.right_sidebar.layer_list_widget:
				self.right_sidebar.layer_list_widget.clear_thumbnail_cache()
			
			# Rebuild the layer list UI
			self.right_sidebar._rebuild_layer_list()
			
			# Update canvas layers (but don't update transform widget - that would kill the drag)
			self.canvas_area.canvas_widget.set_layers(self.right_sidebar.layers)
			
			# Force immediate canvas redraw
			self.canvas_area.canvas_widget.repaint()
			self.repaint()
			
			# Save to history
			self._save_state("Duplicate layer (Ctrl+drag)")
		except Exception as e:
			QMessageBox.warning(self, "Duplicate Error", f"Failed to duplicate layer: {str(e)}")
	
	def paste_layer(self):
		"""Paste layers from clipboard (as CoA sub-blocks) and add to layers"""
		try:
			# Get clipboard text
			layer_text = QApplication.clipboard().text()
			if not layer_text.strip():
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
			
			# Switch to Layers tab if currently on Base tab
			if self.right_sidebar.tab_widget.currentIndex() == 0:
				self.right_sidebar.tab_widget.setCurrentIndex(1)
			
			# Update UI
			self.right_sidebar._rebuild_layer_list()
			self.right_sidebar._update_layer_selection()
			self.right_sidebar._load_layer_properties()
			self.right_sidebar.tab_widget.setTabEnabled(2, True)
			
			# Update canvas and transform widget
			self.canvas_area.canvas_widget.set_layers(self.right_sidebar.layers)
			
			# Use timer to ensure transform widget updates after UI settles
			if self.canvas_area:
				QTimer.singleShot(0, self.canvas_area.update_transform_widget_for_layer)
			
			# Save to history
			layer_word = "layers" if len(layers_data) > 1 else "layer"
			self._save_state(f"Paste {len(layers_data)} {layer_word}")
		except Exception as e:
			QMessageBox.warning(self, "Paste Error", f"Failed to paste layer: {str(e)}")
	
	def paste_layer_smart(self):
		"""Smart paste - pastes at mouse position if over canvas, otherwise at offset position"""
		if hasattr(self, 'canvas_area'):
			mouse_pos = self.canvas_area.mapFromGlobal(self.cursor().pos())
			# Get canvas_widget position relative to canvas_area (accounting for container margins)
			from PyQt5.QtCore import QRect
			canvas_widget_pos = self.canvas_area.canvas_widget.mapTo(self.canvas_area, QPoint(0, 0))
			canvas_geometry = QRect(canvas_widget_pos, self.canvas_area.canvas_widget.size())
			
			if canvas_geometry.contains(mouse_pos):
				# Mouse is over canvas, paste at mouse position
				self.paste_layer_at_position(mouse_pos, canvas_geometry)
				return
		
		# Otherwise, paste at offset position
		self.paste_layer()
	
	def paste_layer_at_position(self, mouse_pos, canvas_geometry):
		"""Paste layers at mouse position on canvas with clamping to legal positions"""
		try:
			# Get clipboard text
			layer_text = QApplication.clipboard().text()
			if not layer_text.strip():
				return
			
			# Parse layers from clipboard using service (handles multiple)
			layers_data = parse_multiple_layers_from_text(layer_text)
			if not layers_data:
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
			
			# Get zoom level from canvas widget
			zoom_level = self.canvas_area.canvas_widget.zoom_level
			
			print(f"DEBUG PASTE: mouse_pos=({mouse_pos.x()}, {mouse_pos.y()}), local=({local_x}, {local_y})")
			print(f"DEBUG PASTE: canvas_geometry=({canvas_geometry.x()}, {canvas_geometry.y()}, {canvas_geometry.width()}x{canvas_geometry.height()})")
			print(f"DEBUG PASTE: canvas_size={canvas_size}, offset=({canvas_offset_x}, {canvas_offset_y})")
			print(f"DEBUG PASTE: canvas_x={canvas_x}, canvas_y={canvas_y}")
			print(f"DEBUG PASTE: zoom_level={zoom_level}")
			
			# Convert to normalized coords [0-1]
			# Canvas rendering uses: center = (pos - 0.5) * 1.1 * zoom_level
			# So reverse: pos = (center / (1.1 * zoom_level)) + 0.5
			norm_x = (canvas_x / (canvas_size / 2) / 1.1 / zoom_level) + 0.5
			norm_y = (canvas_y / (canvas_size / 2) / 1.1 / zoom_level) + 0.5
			
			print(f"DEBUG PASTE: norm_x={norm_x}, norm_y={norm_y}")
			
			# Clamp to legal positions [0-1]
			norm_x = max(0.0, min(1.0, norm_x))
			norm_y = max(0.0, min(1.0, norm_y))
			
			# Calculate centroid of pasted layers to preserve relative positions
			if len(layers_data) > 1:
				centroid_x = sum(layer.get('pos_x', 0.5) for layer in layers_data) / len(layers_data)
				centroid_y = sum(layer.get('pos_y', 0.5) for layer in layers_data) / len(layers_data)
				
				# Calculate offset from centroid to click position
				offset_x = norm_x - centroid_x
				offset_y = norm_y - centroid_y
				
				# Apply offset to all layers (preserves relative positions)
				for layer_data in layers_data:
					layer_data['pos_x'] = max(0.0, min(1.0, layer_data.get('pos_x', 0.5) + offset_x))
					layer_data['pos_y'] = max(0.0, min(1.0, layer_data.get('pos_y', 0.5) + offset_y))
			else:
				# Single layer - just set to click position
				layers_data[0]['pos_x'] = norm_x
				layers_data[0]['pos_y'] = norm_y
			
			# Add all layers at the top (end of list = frontmost)
			start_index = len(self.right_sidebar.layers)
			self.right_sidebar.layers.extend(layers_data)
			
			# Select all newly pasted layers
			new_indices = list(range(start_index, len(self.right_sidebar.layers)))
			self.right_sidebar.selected_layer_indices = set(new_indices)
			self.right_sidebar.last_selected_index = new_indices[-1] if new_indices else None
			
			# Switch to Layers tab if currently on Base tab
			if self.right_sidebar.tab_widget.currentIndex() == 0:
				self.right_sidebar.tab_widget.setCurrentIndex(1)
			
			# Update UI
			self.right_sidebar._rebuild_layer_list()
			self.right_sidebar._update_layer_selection()
			self.right_sidebar._load_layer_properties()
			
			# Enable Properties tab
			self.right_sidebar.tab_widget.setTabEnabled(2, True)
			
			# Update canvas and transform widget
			self.canvas_area.canvas_widget.set_layers(self.right_sidebar.layers)
			
			# Use timer to ensure transform widget updates after UI settles
			if self.canvas_area:
				QTimer.singleShot(0, self.canvas_area.update_transform_widget_for_layer)
			
			# Save to history
			layer_word = "layers" if len(layers_data) > 1 else "layer"
			self._save_state(f"Paste {len(layers_data)} {layer_word} at position")
		except Exception as e:
			QMessageBox.warning(self, "Paste Error", f"Failed to paste layers: {str(e)}")
	
	def _apply_coa_data(self, coa_data):
		"""Apply parsed CoA data to editor"""
		# Parse CoA using service
		parsed = parse_coa_for_editor(coa_data)
		base_data = parsed['base']
		layers = parsed['layers']
		
		# Apply base pattern and colors
		self.canvas_area.canvas_widget.set_base_texture(base_data['pattern'])
		self.canvas_area.canvas_widget.set_base_colors(base_data['colors'])
		self.right_sidebar.set_base_colors(base_data['colors'], base_data['color_names'])
		
		# Clear existing layers and add parsed layers
		self.right_sidebar.layers = list(layers)
		
		# Update UI - switch to Layers tab and rebuild
		self.right_sidebar.tab_widget.setCurrentIndex(1)
		self.right_sidebar._rebuild_layer_list()
		if len(self.right_sidebar.layers) > 0:
			self.right_sidebar._select_layer(0)
		
		# Update canvas
		self.canvas_area.canvas_widget.set_layers(self.right_sidebar.layers)

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
