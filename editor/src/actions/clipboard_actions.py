"""Clipboard operations - copy/paste CoA and layers"""
from PyQt5.QtWidgets import QMessageBox, QApplication
from PyQt5.QtGui import QCursor
from models.coa import Layer
from utils.logger import loggerRaise
from constants import PASTE_OFFSET_X, PASTE_OFFSET_Y


class ClipboardActions:
    """Handles clipboard operations for CoA and layers"""
    
    def __init__(self, main_window):
        """Initialize with reference to main window
        
        Args:
            main_window: The CoatOfArmsEditor main window instance
        """
        self.main_window = main_window
    
    def copy_coa(self):
        """Copy current CoA to clipboard"""
        #COA INTEGRATION ACTION: Step 7 - Use CoA model for copy operations
        try:
            # Use model's to_string() method
            clipboard_text = self.main_window.coa.to_string()
            
            # OLD CODE (will remove in Step 9):
            # from services.file_operations import coa_to_clipboard_text, build_coa_for_save
            # coa_data = build_coa_for_save(self.main_window.right_sidebar.layers)
            # clipboard_text = coa_to_clipboard_text(coa_data)
            
            # Copy to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(clipboard_text)
            
            self.main_window.status_left.setText("CoA copied to clipboard")
            
        except Exception as e:
            loggerRaise(e, f"Failed to copy CoA: {str(e)}")
    
    def paste_coa(self):
        """Paste CoA from clipboard"""
        #COA INTEGRATION ACTION: Step 7 - Use CoA model for paste operations
        try:
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            
            if not text:
                QMessageBox.information(
                    self.main_window,
                    "Paste CoA",
                    "Clipboard is empty"
                )
                return
            
            # Clear and parse into existing CoA instance
            self.main_window.coa.clear()
            self.main_window.coa.parse(text)
            
            # Apply to UI - update from model
            self.main_window.canvas_area.canvas_widget.set_base_texture(self.main_window.coa.pattern)
            self.main_window.canvas_area.canvas_widget.set_base_colors([self.main_window.coa.pattern_color1, self.main_window.coa.pattern_color2, self.main_window.coa.pattern_color3])
            
            self.main_window.right_sidebar._refresh_base_colors_from_model()
            
            # Update UI - layers are accessed through CoA model now
            self.main_window.right_sidebar.tab_widget.setCurrentIndex(1)
            self.main_window.right_sidebar._rebuild_layer_list()
            if self.main_window.coa.get_layer_count() > 0:
                self.main_window.canvas_area.canvas_widget.update()
            
            # OLD CODE (will remove in Step 10):
            # from utils.coa_parser import parse_coa_string
            # from services.coa_serializer import parse_coa_for_editor
            # coa_data = parse_coa_string(text)
            # self.main_window._apply_coa_data(coa_data)
            
            self.main_window.status_left.setText("CoA pasted from clipboard")
            
        except Exception as e:
            loggerRaise(e, f"Failed to paste CoA: {str(e)}")
    def copy_layer(self):
        """Copy selected layer(s) to clipboard"""
        selected_uuids = self.main_window.right_sidebar.get_selected_uuids()
        
        if not selected_uuids:
            QMessageBox.information(
                self.main_window,
                "Copy Layer",
                "No layer selected"
            )
            return
        
        # PHASE 6: Detect if copying whole container or individual layers
        # Check if all selected layers share the same container_uuid
        container_uuids = set()
        for uuid in selected_uuids:
            container_uuid = self.main_window.coa.get_layer_container(uuid)
            container_uuids.add(container_uuid)
        
        # Determine copy type:
        # - If all layers share same non-None container_uuid AND count matches container: preserve container_uuid
        # - Otherwise (individual layers, mixed containers, or root layers): strip container_uuid
        is_whole_container = False
        if len(container_uuids) == 1 and None not in container_uuids:
            container_uuid = next(iter(container_uuids))
            container_layers = self.main_window.coa.get_layers_by_container(container_uuid)
            if set(selected_uuids) == set(container_layers):
                is_whole_container = True
        
        # Serialize selected layers using CoA method
        if is_whole_container:
            # Container copy: preserve container_uuid
            clipboard_text = self.main_window.coa.serialize_layers_to_string(selected_uuids, strip_container_uuid=False)
        else:
            # Individual/mixed copy: strip container_uuid
            clipboard_text = self.main_window.coa.serialize_layers_to_string(selected_uuids, strip_container_uuid=True)
        
        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(clipboard_text)
        
        count = len(selected_uuids)
        copy_type = "container" if is_whole_container else "layer(s)"
        self.main_window.status_left.setText(f"{count} {copy_type} copied to clipboard")
    
    def _paste_layers_common(self, text, target_pos=None):
        """Common paste logic handling parsing, positioning, and container rules"""
        from models.coa import CoA
        from models.transform import Vec2
        
        # Parse as a CoA and extract layers
        # Use specific parser method that handles clipboard fragments and metadata correctly
        temp_coa = CoA()
        temp_uuids = temp_coa.parse_layers_string(text)
        
        if not temp_coa or temp_coa.get_layer_count() == 0:
            QMessageBox.information(
                self.main_window,
                "Paste Layer",
                "No valid layer data in clipboard"
            )
            return

        # Position Adjustment
        if target_pos:
            # Calculate centroid of temp layers
            if len(temp_uuids) > 1:
                centroid_x, centroid_y = temp_coa.get_layer_centroid(temp_uuids)
                offset_x = target_pos.x - centroid_x
                offset_y = target_pos.y - centroid_y
                temp_coa.adjust_layer_positions(temp_uuids, offset_x, offset_y)
            else:
                # Single layer/instance
                # If multiple instances, center AABB
                if temp_coa.get_layer_instance_count(temp_uuids[0]) > 1:
                    bounds = temp_coa.get_layer_bounds(temp_uuids[0])
                    offset_x = target_pos.x - bounds['center_x']
                    offset_y = target_pos.y - bounds['center_y']
                    temp_coa.translate_all_instances(temp_uuids[0], offset_x, offset_y)
                else:
                    # Single instance: set position directly
                    temp_coa.set_layer_position(temp_uuids[0], target_pos.x, target_pos.y)
        else:
            # Default offset
            temp_coa.adjust_layer_positions(temp_uuids, PASTE_OFFSET_X, PASTE_OFFSET_Y)
            
        # PHASE 6: Detect if pasted data has container_uuid (Rule 1 vs Rule 2)
        # Check if any layer in clipboard has container_uuid set
        has_container_uuid = False
        clipboard_container_uuids = set()
        for uuid in temp_uuids:
            container_uuid = temp_coa.get_layer_container(uuid)
            if container_uuid is not None:
                has_container_uuid = True
                clipboard_container_uuids.add(container_uuid)
        
        # Check current selection to determine paste target
        selected_uuids = self.main_window.right_sidebar.get_selected_uuids()
        selected_container_uuid = None
        if selected_uuids:
            # Check if selection is a container (all layers share same container_uuid)
            selection_containers = set()
            for uuid in selected_uuids:
                container_uuid = self.main_window.coa.get_layer_container(uuid)
                if container_uuid is not None:
                    selection_containers.add(container_uuid)
            
            # If all selected layers in same container, that's our target container
            if len(selection_containers) == 1:
                selected_container_uuid = next(iter(selection_containers))
        
        # Apply paste rules
        if not has_container_uuid:
            # RULE 1: Layers without container_uuid
            # If container selected: adopt that container_uuid and paste at top of container
            # If sub-layer selected: adopt that layer's container_uuid and paste at that position
            # If root layer selected: paste above it (no container)
            # If nothing selected: paste at end (no container)
            
            target_uuid = None
            target_container = None
            
            if selected_uuids and selected_container_uuid:
                # Container or sub-layer selected: adopt container, paste at top
                target_container = selected_container_uuid
                # Find first layer in container for target_uuid
                container_layers = self.main_window.coa.get_layers_by_container(selected_container_uuid)
                if container_layers:
                    target_uuid = container_layers[0]
            elif selected_uuids:
                # Root layer selected: paste above it
                target_uuid = selected_uuids[0]
            
            # Set container_uuid on all temp layers
            if target_container:
                for uuid in temp_uuids:
                    temp_coa.set_layer_container(uuid, target_container)
            
            # Serialize and parse
            layers_string = temp_coa.serialize_layers_to_string(temp_uuids, strip_container_uuid=False)
            new_uuids = self.main_window.coa.parse(layers_string, target_uuid=target_uuid)
            
        else:
            # RULE 2: Layers with container_uuid
            # Create new container(s) at root level
            # Regenerate container_uuid for each unique container in clipboard
            
            # Build mapping of old container_uuid -> new container_uuid
            container_uuid_map = {}
            for old_container_uuid in clipboard_container_uuids:
                # Regenerate container UUID (keeps name, new UUID portion)
                new_container_uuid = self.main_window.coa.regenerate_container_uuid(old_container_uuid)
                container_uuid_map[old_container_uuid] = new_container_uuid
            
            # Update temp layers with new container UUIDs
            for uuid in temp_uuids:
                old_container = temp_coa.get_layer_container(uuid)
                if old_container in container_uuid_map:
                    temp_coa.set_layer_container(uuid, container_uuid_map[old_container])
            
            # Determine paste position
            target_uuid = None
            if selected_uuids:
                if selected_container_uuid:
                    # Container selected: paste ABOVE container (not inside)
                    # Find first layer in selected container, use as target
                    container_layers = self.main_window.coa.get_layers_by_container(selected_container_uuid)
                    if container_layers:
                        target_uuid = container_layers[0]
                else:
                    # Root layer selected: paste above it
                    target_uuid = selected_uuids[0]
            
            # Serialize and parse (container_uuid preserved)
            layers_string = temp_coa.serialize_layers_to_string(temp_uuids, strip_container_uuid=False)
            new_uuids = self.main_window.coa.parse(layers_string, target_uuid=target_uuid)
        
        # PHASE 7: Validate container contiguity after paste
        splits = self.main_window.coa.validate_container_contiguity()
        if splits:
            # Log splits for debugging
            for split in splits:
                self.main_window._logger.info(f"Container split: {split['old_container']} -> {split['new_container']} ({split['layer_count']} layers)")
        
        # Set selection state BEFORE rebuilding UI (so rebuild can apply correct visual state)
        if new_uuids:
            # Check if all pasted layers share the same container_uuid
            pasted_containers = set()
            for uuid in new_uuids:
                container_uuid = self.main_window.coa.get_layer_container(uuid)
                if container_uuid is not None:
                    pasted_containers.add(container_uuid)
            
            # If all layers are in same container, select the container instead of individual layers
            if len(pasted_containers) == 1:
                container_uuid = next(iter(pasted_containers))
                self.main_window.right_sidebar.layer_list_widget.selected_layer_uuids = set(new_uuids)
                self.main_window.right_sidebar.layer_list_widget.selected_container_uuids = {container_uuid}
                self.main_window.right_sidebar.layer_list_widget.last_selected_uuid = new_uuids[0]
            else:
                # Mixed or root layers - select individual layers
                self.main_window.right_sidebar.layer_list_widget.selected_layer_uuids = set(new_uuids)
                self.main_window.right_sidebar.layer_list_widget.selected_container_uuids = set()
                self.main_window.right_sidebar.layer_list_widget.last_selected_uuid = new_uuids[0]
        
        # Update UI (rebuild will apply selection visuals to new buttons)
        self.main_window.right_sidebar._rebuild_layer_list()
        self.main_window.canvas_area.canvas_widget.update()
        
        # Trigger selection callback to load properties
        if new_uuids:
            self.main_window.right_sidebar.layer_list_widget.update_selection_visuals()
        
        # Save to history
        count = temp_coa.get_layer_count()
        paste_type = "container" if has_container_uuid else "layer(s)"
        self.main_window._save_state(f"Paste {count} {paste_type}")
        
        self.main_window.status_left.setText(f"{count} {paste_type} pasted")
    
    def paste_layer(self):
        """Paste layer(s) from clipboard with smart container handling"""
        try:
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if not text:
                return
            
            self._paste_layers_common(text)
        except Exception as e:
            loggerRaise(e, f"Failed to paste layer: {str(e)}")

    def paste_layer_smart(self):
        """Smart paste - pastes at mouse position if over canvas, otherwise at offset position"""
        try:
            mouse_pos = self.main_window.canvas_area.mapFromGlobal(self.main_window.cursor().pos())
            canvas_geometry = self.main_window.canvas_area.canvas_widget.geometry()
            
            # If mouse is over canvas, paste at position
            if canvas_geometry.contains(mouse_pos):
                self.paste_layer_at_position(mouse_pos, canvas_geometry)
            else:
                # Fall back to regular paste with offset
                self.paste_layer()
        except Exception as e:
            loggerRaise(e, f"Failed to smart paste: {str(e)}")

    def paste_layer_at_position(self, mouse_pos, canvas_geometry):
        """Paste layer at specific mouse position"""
        try:
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if not text:
                return

            # Note: We use global cursor pos to ensure consistency with legacy behavior and avoid coordinate mapping issues
            # But since we have mouse_pos in canvas_area space, we can use it.
            # Convert canvas_area pos to canvas_widget pos
            canvas_widget_pos = self.main_window.canvas_area.canvas_widget.mapFrom(self.main_window.canvas_area, mouse_pos)
            
            # Convert canvas pixels to CoA space
            from models.transform import Vec2
            coa_pos = self.main_window.canvas_area.canvas_widget.canvas_to_coa(
                Vec2(canvas_widget_pos.x(), canvas_widget_pos.y())
            )
            
            self._paste_layers_common(text, target_pos=coa_pos)
            
        except Exception as e:
            loggerRaise(e, f"Failed to paste at position: {str(e)}")
    
    def duplicate_selected_layer(self):
        """Duplicate selected layer(s) and place above"""
        selected_uuids = self.main_window.right_sidebar.get_selected_uuids()
        
        if not selected_uuids:
            QMessageBox.information(
                self.main_window,
                "Duplicate Layer",
                "No layer selected"
            )
            return
        
        # Duplicate using CoA model
        new_uuids = []
        for uuid in selected_uuids:
            new_uuid = self.main_window.coa.duplicate_layer(uuid)
            new_uuids.append(new_uuid)
        
        # Update UI
        self.main_window.right_sidebar._rebuild_layer_list()
        self.main_window.canvas_area.canvas_widget.update()
        
        # Select the new duplicated layers
        if new_uuids:
            self.main_window.right_sidebar.layer_list_widget.selected_layer_uuids = set(new_uuids)
            self.main_window.right_sidebar.layer_list_widget.last_selected_uuid = new_uuids[0]
            self.main_window.right_sidebar.layer_list_widget.update_selection_visuals()
        
        # Save to history
        count = len(selected_uuids)
        self.main_window._save_state(f"Duplicate {count} layer(s)")
    
    def duplicate_selected_layer_below(self, keep_selection=False):
        """Duplicate selected layer(s) and place below
        
        Args:
            keep_selection: If True, keep original selection (for ctrl+drag). If False, select duplicates.
        """
        selected_uuids = self.main_window.right_sidebar.get_selected_uuids()
        
        if not selected_uuids:
            return
        
        # Store original selection
        original_selection = set(selected_uuids)
        
        # Duplicate using pure UUID-based positioning
        new_uuids = []
        for uuid in selected_uuids:
            # Duplicate and place below original (pushes original forward/above)
            new_uuid = self.main_window.coa.duplicate_layer_below(uuid, uuid)
            new_uuids.append(new_uuid)
        
        # Update UI
        self.main_window.right_sidebar._rebuild_layer_list()
        self.main_window.canvas_area.canvas_widget.update()
        
        # Select the appropriate layers based on keep_selection flag
        if keep_selection:
            # Keep original selection (for ctrl+drag) - originals are still at same UUIDs
            self.main_window.right_sidebar.layer_list_widget.selected_layer_uuids = original_selection
            if selected_uuids:
                self.main_window.right_sidebar.layer_list_widget.last_selected_uuid = selected_uuids[0]
            # Update visual state WITHOUT triggering selection callback (which resets drag state)
            for uuid, container_widget in self.main_window.right_sidebar.layer_list_widget.layer_buttons:
                if hasattr(container_widget, 'layer_button'):
                    container_widget.layer_button.setChecked(uuid in original_selection)
                else:
                    container_widget.setChecked(uuid in original_selection)
        else:
            # Select the new duplicated layers (normal duplicate operation)
            if new_uuids:
                self.main_window.right_sidebar.layer_list_widget.selected_layer_uuids = set(new_uuids)
                self.main_window.right_sidebar.layer_list_widget.last_selected_uuid = new_uuids[0]
            self.main_window.right_sidebar.layer_list_widget.update_selection_visuals()
        
        # Save to history (but not during ctrl+drag - that's saved on mouse release)
        if not keep_selection:
            count = len(selected_uuids)
            self.main_window._save_state(f"Duplicate {count} layer(s) below")
    
    def duplicate_selected_layer(self):
        """Duplicate selected layer(s) and place above"""
        selected_uuids = self.main_window.right_sidebar.get_selected_uuids()
        
        if not selected_uuids:
            QMessageBox.information(
                self.main_window,
                "Duplicate Layer",
                "No layer selected"
            )
            return
        
        # Duplicate using CoA model
        new_uuids = []
        for uuid in selected_uuids:
            new_uuid = self.main_window.coa.duplicate_layer(uuid)
            new_uuids.append(new_uuid)
        
        # Update UI
        self.main_window.right_sidebar._rebuild_layer_list()
        self.main_window.canvas_area.canvas_widget.update()
        
        # Select the new duplicated layers
        if new_uuids:
            self.main_window.right_sidebar.layer_list_widget.selected_layer_uuids = set(new_uuids)
            self.main_window.right_sidebar.layer_list_widget.last_selected_uuid = new_uuids[0]
            self.main_window.right_sidebar.layer_list_widget.update_selection_visuals()
        
        # Save to history
        count = len(selected_uuids)
        self.main_window._save_state(f"Duplicate {count} layer(s)")

