"""File operations for the main window - new, save, load, export"""
from PyQt5.QtWidgets import QFileDialog, QMessageBox

# Import DEBUG_MODE from main
import sys
import os
# Add parent directory to path to import from main
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    
try:
    from main import DEBUG_MODE
except ImportError:
    DEBUG_MODE = True  # Fallback if main not available

#COA INTEGRATION ACTION: Step 6 - File actions use CoA model (Step 2 already implemented in main.py)
# Main file operations (save/load) already migrated in Step 2
# These helper methods delegate to main window which uses CoA model


class FileActions:
    """Handles all file menu operations"""
    
    def __init__(self, main_window):
        """Initialize with reference to main window
        
        Args:
            main_window: The CoatOfArmsEditor main window instance
        """
        self.main_window = main_window
    
    def new_coa(self):
        """Create new CoA, prompt to save if needed"""
        if not self.main_window._prompt_save_if_needed():
            return
        
        # Reset current file and saved flag
        self.main_window.current_file_path = None
        self.main_window.is_saved = True
        self.main_window._update_window_title()
        
        # Clear existing CoA to defaults
        self.main_window.coa.clear()
        
        # Clear history before loading (to avoid storing default state)
        self.main_window.history_manager.clear()
        
        # Rebuild UI to reflect new empty CoA
        self.main_window.right_sidebar._rebuild_layer_list()
        self.main_window.canvas_area.canvas_widget.update()
        
        # Create initial history entry
        self.main_window._save_state("New CoA")
        
        # Reset saved flag (saving state sets it to False)
        self.main_window.is_saved = True
        
        # Update UI
        self.main_window._update_window_title()
        self.main_window._update_status_bar()
    
    def save_coa(self):
        """Save the current coat of arms"""
        if self.main_window.current_file_path:
            self._save_to_file(self.main_window.current_file_path)
        else:
            self.save_coa_as()
    
    def save_coa_as(self):
        """Save the current coat of arms to a new file"""
        from services.file_operations import save_coa_to_file
        
        filename, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "Save Coat of Arms",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        if filename:
            self._save_to_file(filename)
    
    def _save_to_file(self, filename):
        """Internal save method
        
        Args:
            filename: Path to save file to
        """
        from services.file_operations import save_coa_to_file
        
        try:
            # Save CoA model directly using its to_string serialization
            save_coa_to_file(self.main_window.coa, filename)
            
            # Update current file and mark as saved
            self.main_window.current_file_path = filename
            self.main_window.is_saved = True
            self.main_window._update_window_title()
            
            # Add to recent files
            self.main_window._add_to_recent_files(filename)
            
            # Update status
            import os
            self.main_window.status_left.setText(f"Saved to {os.path.basename(filename)}")
            
        except Exception as e:
            if DEBUG_MODE:
                raise e
            QMessageBox.critical(
                self.main_window,
                "Error",
                f"Failed to save file: {str(e)}"
            )
    
    def load_coa(self):
        """Load a coat of arms from file"""
        #COA INTEGRATION ACTION: Step 2 - Use CoA model for loading
        from models.coa import CoA
        
        if not self.main_window._prompt_save_if_needed():
            return
        
        filename, _ = QFileDialog.getOpenFileName(
            self.main_window,
            "Load Coat of Arms",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if filename:
            try:
                # Read file
                with open(filename, 'r', encoding='utf-8') as f:
                    coa_text = f.read()
                
                # Clear and parse into existing CoA instance
                self.main_window.coa.clear()
                self.main_window.coa.parse(coa_text)
                
                # Apply to UI - update from model
                self.main_window.canvas_area.canvas_widget.set_base_texture(self.main_window.coa.pattern)
                self.main_window.canvas_area.canvas_widget.set_base_colors([self.main_window.coa.pattern_color1, self.main_window.coa.pattern_color2, self.main_window.coa.pattern_color3])
                self.main_window.canvas_area.canvas_widget.base_color1_name = self.main_window.coa.pattern_color1_name
                self.main_window.canvas_area.canvas_widget.base_color2_name = self.main_window.coa.pattern_color2_name
                self.main_window.canvas_area.canvas_widget.base_color3_name = self.main_window.coa.pattern_color3_name
                
                # Convert colors to 0-1 range for property sidebar
                base_colors_normalized = [
                    [c / 255.0 for c in self.main_window.coa.pattern_color1],
                    [c / 255.0 for c in self.main_window.coa.pattern_color2],
                    [c / 255.0 for c in self.main_window.coa.pattern_color3]
                ]
                base_color_names = [self.main_window.coa.pattern_color1_name, self.main_window.coa.pattern_color2_name, self.main_window.coa.pattern_color3_name]
                self.main_window.right_sidebar.set_base_colors(base_colors_normalized, base_color_names)
                
                # Update UI - layers are accessed through CoA model now
                self.main_window.right_sidebar.tab_widget.setCurrentIndex(1)
                self.main_window.right_sidebar._rebuild_layer_list()
                # Clear any selection from previous CoA
                self.main_window.right_sidebar.layer_list_widget.selected_layer_uuids.clear()
                self.main_window.right_sidebar.layer_list_widget.last_selected_uuid = None
                self.main_window.right_sidebar.layer_list_widget.update_selection_visuals()
                self.main_window.right_sidebar._on_layer_selection_changed()
                
                # Update canvas with CoA model
                self.main_window.canvas_area.canvas_widget.update()
                
                # Update file tracking
                self.main_window.current_file_path = filename
                self.main_window.is_saved = True
                self.main_window._update_window_title()
                
                # Add to recent files
                self.main_window._add_to_recent_files(filename)
                
                # Clear history before loading
                self.main_window.history_manager.clear()
                
                # Create initial history entry
                self.main_window._save_state("Load CoA")
                
                # OLD CODE (will remove in Step 10):
                # coa_data = load_coa_from_file(filename)
                # layers = parse_coa_for_editor(coa_data)
                # self.main_window.right_sidebar.set_layers(layers)
                
            except Exception as e:
                if DEBUG_MODE:
                    raise e
                QMessageBox.critical(
                    self.main_window,
                    "Error",
                    f"Failed to load file: {str(e)}"
                )
    
    def export_png(self):
        """Export current CoA as PNG with transparency"""
        try:
            # Open save file dialog
            filename, _ = QFileDialog.getSaveFileName(
                self.main_window,
                "Export as PNG",
                "",
                "PNG Files (*.png);;All Files (*)"
            )
            
            if not filename:
                return
            
            # Ensure .png extension
            if not filename.lower().endswith('.png'):
                if DEBUG_MODE:
                    raise e
                filename += '.png'
            
            # Use the canvas widget's proper export function for transparency
            success = self.main_window.canvas_area.canvas_widget.export_to_png(filename)
            
            if not success:
                QMessageBox.warning(
                    self.main_window,
                    "Export Failed",
                    "Failed to export PNG. Check console for errors."
                )
                return
            
            # Update status
            import os
            self.main_window.status_left.setText(f"Exported to {os.path.basename(filename)}")
            
        except Exception as e:
            QMessageBox.critical(
                self.main_window,
                "Export Error",
                f"Failed to export PNG: {str(e)}"
            )
