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
from models.color import Color

# Utility imports
from utils.history_manager import HistoryManager
from utils.logger import loggerRaise, set_main_window

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
    DEFAULT_PATTERN_TEXTURE, DEFAULT_BASE_CATEGORY,
    CK3_NAMED_COLORS, DEFAULT_SCALE_X, DEFAULT_SCALE_Y,
    DEFAULT_FLIP_X, DEFAULT_FLIP_Y, DEFAULT_ROTATION, MAX_HISTORY_ENTRIES
)

# Action imports
from actions.file_actions import FileActions
from actions.clipboard_actions import ClipboardActions
from actions.layer_transform_actions import LayerTransformActions

# Mixin imports
from main.menu_mixin import MenuMixin
from main.event_mixin import EventMixin
from main.config_mixin import ConfigMixin
from main.history_mixin import HistoryMixin
from main.asset_mixin import AssetMixin
from main.generator_mixin import GeneratorMixin
from main.ui_setup_mixin import UISetupMixin

# Layer generator imports
from services.layer_generator import GeneratorPopup
from services.layer_generator.generators import (
    CircularGenerator, LineGenerator, SpiralGenerator, ShapeGenerator,
    GridGenerator, DiamondGenerator, FibonacciGenerator,
    RadialGenerator, StarGenerator, VanillaGenerator, NgonGenerator
)


class CoatOfArmsEditor(MenuMixin, EventMixin, ConfigMixin, HistoryMixin, AssetMixin, GeneratorMixin, UISetupMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Coat Of Arms Designer")
        self.resize(1280, 720)
        self.setMinimumSize(1280, 720)
        
        # Initialize CoA model instance (single source of truth for all CoA data)
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
        
        # COA Model Edit Lock - prevents feedback loops
        self._edit_lock_holder = None  # Tracks which component owns the lock
        
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
    
    def acquire_edit_lock(self, requester):
        """Acquire exclusive edit lock for continuous numerical edits.
        
        Args:
            requester: Object requesting the lock (for debugging)
            
        Raises:
            RuntimeError: If lock is already held by another component
        """
        from utils.logger import loggerRaise
        if self._edit_lock_holder is not None:
            e = RuntimeError(f"Edit lock already held by {self._edit_lock_holder}")
            loggerRaise(e, f"Cannot acquire lock - already held by {self._edit_lock_holder}")
        self._edit_lock_holder = requester
    
    def release_edit_lock(self, requester):
        """Release edit lock - only lock holder can release.
        
        Args:
            requester: Object releasing the lock
            
        Raises:
            RuntimeError: If requester doesn't own the lock
        """
        from utils.logger import loggerRaise
        if self._edit_lock_holder != requester:
            e = RuntimeError(f"Lock held by {self._edit_lock_holder}, not {requester}")
            loggerRaise(e, f"Cannot release lock - not owned by requester")
        self._edit_lock_holder = None
    
    def is_edit_locked(self):
        """Check if edit lock is currently held.
        
        Returns:
            bool: True if lock is held by any component
        """
        return self._edit_lock_holder is not None
    
    # ============= UI Setup =============
    
    def setup_ui(self):
        # Create menu bar (includes zoom controls)
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
        self.left_sidebar.main_window = self  # Reference for CoA model access
        splitter.addWidget(self.left_sidebar)
        
        # Center canvas area
        self.canvas_area = CanvasArea(self)
        #COA INTEGRATION ACTION: Step 4-5 - Pass CoA reference to canvas area and canvas widget
        self.canvas_area.coa = self.coa
        self.canvas_area.canvas_widget.coa = self.coa
        # Connect transform widget to main window for edit lock access (Decision 4)
        self.canvas_area.transform_widget.main_window = self
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
        
        # Initialize base colors in canvas from CoA model
        base_colors = [
            self.coa.pattern_color1,
            self.coa.pattern_color2,
            self.coa.pattern_color3
        ]
        self.canvas_area.canvas_widget.set_base_colors(base_colors)
        
        # Property sidebar will refresh from CoA model after initialization timer
        
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
    
    # ========================================
    # COA Model Edit Lock
    # ========================================
    
    def acquire_edit_lock(self, requester):
        """Called by any component starting continuous edit.
        
        Args:
            requester: The component requesting the lock (for tracking)
            
        Raises:
            RuntimeError: If lock is already held by another component
        """
        if self._edit_lock_holder is not None:
            e = RuntimeError(f"Lock already held by {self._edit_lock_holder}")
            loggerRaise(e, f"Cannot acquire lock - already held by {self._edit_lock_holder}")
        self._edit_lock_holder = requester
    
    def release_edit_lock(self, requester):
        """Only lock holder can release.
        
        Args:
            requester: The component releasing the lock
            
        Raises:
            RuntimeError: If requester doesn't own the lock
        """
        if self._edit_lock_holder != requester:
            e = RuntimeError(f"Lock held by {self._edit_lock_holder}, not {requester}")
            loggerRaise(e, f"Cannot release lock - not owned by requester")
        self._edit_lock_holder = None
    
    def is_edit_locked(self):
        """All components check before writing to model.
        
        Returns:
            bool: True if edit lock is currently held
        """
        return self._edit_lock_holder is not None
    
    # ========================================
    # Core Application Methods
    # ========================================
    
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
    
    def new_coa(self):
        """Clear everything and start with default empty CoA"""
        try:
            # Prompt to save if there are unsaved changes
            if not self._prompt_save_if_needed():
                return
            
            # Clear selection (layers will be empty via CoA model)
            self.right_sidebar.clear_selection()
            
            # Reset base to default pattern and colors
            default_pattern = DEFAULT_PATTERN_TEXTURE
            default_color1 = Color.from_name(DEFAULT_BASE_COLOR1)
            default_color2 = Color.from_name(DEFAULT_BASE_COLOR2)
            default_color3 = Color.from_name(DEFAULT_BASE_COLOR3)
            default_colors = [
                default_color1,
                default_color2,
                default_color3
            ]
            
            self.canvas_area.canvas_widget.set_base_texture(default_pattern)
            self.canvas_area.canvas_widget.set_base_colors(default_colors)
            
            # Create new empty CoA and set its pattern/colors
            self.coa = CoA()
            self.coa.pattern = default_pattern
            self.coa.pattern_color1 = default_color1
            self.coa.pattern_color2 = default_color2
            self.coa.pattern_color3 = default_color3
            CoA.set_active(self.coa)  # Update active instance
            self.canvas_area.canvas_widget.update()
            
            # Property sidebar refreshes from CoA model
            self.right_sidebar._refresh_base_colors_from_model()
            
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
