"""Global logging and error handling utilities"""
import sys
import traceback
from PyQt5.QtWidgets import QMessageBox

# Detect debug mode - True if running from source, False if packaged
DEBUG_MODE = not getattr(sys, 'frozen', False)

_main_window = None

def set_main_window(window):
    """Set the main window reference for showing popups"""
    global _main_window
    _main_window = window

def loggerRaise(e: Exception, user_message: str = None, title: str = "Error"):
    """Handle exceptions with optional popup in release mode
    
    Args:
        e: The exception to handle
        user_message: User-friendly message to show in popup (optional)
        title: Title for the popup dialog
    
    In DEBUG_MODE:
        - Just raises the exception (shows full traceback)
    
    In RELEASE_MODE:
        - Shows popup with user message or exception string
        - Logs the full traceback
        - Then raises the exception
    """
    if DEBUG_MODE:
        # Dev mode: just raise to see full traceback
        raise e
    else:
        # Release mode: show popup, log, then raise
        
        # Log the full traceback
        tb = traceback.format_exc()
        print(f"ERROR: {tb}", file=sys.stderr)
        
        # Show user-friendly popup
        message = user_message if user_message else str(e)
        if _main_window:
            QMessageBox.critical(_main_window, title, message)
        else:
            # Fallback if no main window set
            print(f"ERROR POPUP (no window): {title} - {message}", file=sys.stderr)
        
        # Re-raise so application can handle it appropriately
        raise e
