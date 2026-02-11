"""History management and undo/redo for CoatOfArmsEditor"""

from PyQt5.QtCore import QTimer
from utils.logger import loggerRaise


class HistoryMixin:
    """Undo/redo system, state management, and status bar updates"""
    
    def _capture_current_state(self):
        """Capture the current state for history"""
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
            # Restore CoA from snapshot
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
            
            # Update property sidebar from model
            self.right_sidebar._refresh_base_colors_from_model()
            
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
        
        # Cancel any pending debounced save — a direct save supersedes it
        self.property_change_timer.stop()
        self._pending_property_change = None
        
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
