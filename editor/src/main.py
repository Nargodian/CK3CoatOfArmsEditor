import sys
import os
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

# PyQt5 imports
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPalette, QColor

# Model imports
from models.coa import CoA

# Utility imports
from utils.history_manager import HistoryManager
from utils.logger import loggerRaise, set_main_window

from constants import MAX_HISTORY_ENTRIES

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
    
    # ========================================
    # COA Model Edit Lock
    # ========================================
    
    def acquire_edit_lock(self, requester):
        """Acquire exclusive edit lock for continuous numerical edits.
        
        Args:
            requester: Object requesting the lock (for debugging)
            
        Raises:
            RuntimeError: If lock is already held by another component
        """
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
