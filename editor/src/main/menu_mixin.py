"""Menu bar creation and menu action handlers for CoatOfArmsEditor"""

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox, QActionGroup
from PyQt5.QtCore import Qt


class MenuMixin:
    """Menu bar and menu action handlers"""
    
    def _create_menu_bar(self):
        """Create the menu bar with File, Edit, Help menus"""
        menubar = self.menuBar()
        
        # Add zoom controls to the right of menu bar
        from components.gui_widgets import ZoomToolbar
        self.zoom_toolbar = ZoomToolbar(self)
        self.zoom_toolbar.zoom_changed.connect(self._on_zoom_changed)
        menubar.setCornerWidget(self.zoom_toolbar, Qt.TopRightCorner)
        
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
        
        # Force RGB colors option
        self.force_rgb_action = file_menu.addAction("Force RGB Colors")
        self.force_rgb_action.setCheckable(True)
        self.force_rgb_action.setChecked(False)
        self.force_rgb_action.toggled.connect(self._on_force_rgb_toggled)
        
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
        
        cut_layer_action = self.layers_menu.addAction("Cu&t Layer")
        cut_layer_action.setShortcut("Ctrl+X")
        cut_layer_action.triggered.connect(self.clipboard_actions.cut_layer)
        
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
        
        ngon_action = path_menu.addAction("&N-gon")
        ngon_action.triggered.connect(lambda: self._open_generator('ngon'))
        
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
        
        # Zoom actions
        zoom_in_action = view_menu.addAction("Zoom &In")
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self._zoom_in)
        
        zoom_out_action = view_menu.addAction("Zoom &Out")
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self._zoom_out)
        
        zoom_reset_action = view_menu.addAction("&Reset Zoom")
        zoom_reset_action.setShortcut("Ctrl+0")
        zoom_reset_action.triggered.connect(self._zoom_reset)
        
        view_menu.addSeparator()
        
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
        
        self.grid_32x32_action = grid_menu.addAction("&32x32")
        self.grid_32x32_action.setCheckable(True)
        self.grid_32x32_action.triggered.connect(lambda: self._set_grid_size(32))
        
        grid_menu.addSeparator()
        
        self.grid_off_action = grid_menu.addAction("&Off")
        self.grid_off_action.setCheckable(True)
        self.grid_off_action.triggered.connect(lambda: self._set_grid_size(0))
        
        grid_menu.addSeparator()
        
        self.grid_snap_action = grid_menu.addAction("&Snap")
        self.grid_snap_action.setCheckable(True)
        self.grid_snap_action.setChecked(False)
        self.grid_snap_action.triggered.connect(self._toggle_grid_snap)
        
        # Group grid size actions (mutually exclusive)
        self.grid_action_group = QActionGroup(self)
        self.grid_action_group.addAction(self.grid_2x2_action)
        self.grid_action_group.addAction(self.grid_4x4_action)
        self.grid_action_group.addAction(self.grid_8x8_action)
        self.grid_action_group.addAction(self.grid_16x16_action)
        self.grid_action_group.addAction(self.grid_32x32_action)
        self.grid_action_group.addAction(self.grid_off_action)
        self.grid_off_action.setChecked(True)  # Start with grid off
        
        # Help Menu
        help_menu = menubar.addMenu("&Help")
        
        shortcuts_action = help_menu.addAction("&Keyboard Shortcuts")
        shortcuts_action.setShortcut("F1")
        shortcuts_action.triggered.connect(self._show_shortcuts)
        
        content_action = help_menu.addAction("&Content Loaded")
        content_action.triggered.connect(self._show_content_loaded)
        
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
    
    def _show_shortcuts(self):
        """Show keyboard shortcuts help dialog"""
        from components.gui_widgets import ShortcutsDialog
        dialog = ShortcutsDialog(self)
        dialog.exec_()
    
    def _show_about(self):
        """Show about dialog"""
        from utils.path_resolver import get_base_dir
        version_file = get_base_dir() / "VERSION"
        try:
            version = version_file.read_text().strip()
        except FileNotFoundError:
            version = "unknown"
        QMessageBox.about(self, "About Coat of Arms Designer",
            "<h3>Coat of Arms Designer</h3>"
            "<p>A tool for creating and editing Crusader Kings 3 coats of arms.</p>"
            f"<p>Version {version}</p>"
            "<hr>"
            "<p><b>AI Disclosure:</b> This tool was developed with heavy AI assistance. "
            "I respect that people have valid concerns about AI, and I do not wish to claim ownership over the output. "
            "This tool is provided for its own sake as a useful utility, "
            "free for anyone to use or modify.</p>")
    
    def _show_content_loaded(self):
        """Show content manifest dialog listing converted asset sources."""
        import json
        from utils.path_resolver import get_assets_dir
        
        manifest_path = get_assets_dir() / 'content_manifest.json'
        
        if not manifest_path.exists():
            QMessageBox.information(self, "Content Loaded",
                "No conversion data found.\n\n"
                "Run the Asset Converter to generate assets.")
            return
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
        except Exception:
            QMessageBox.warning(self, "Content Loaded",
                "Could not read content manifest.\n\n"
                "Try re-running the Asset Converter.")
            return
        
        converted = manifest.get('converted', 'Unknown')
        sources = manifest.get('sources', [])
        
        rows = []
        for src in sources:
            name = src.get('name', 'Unknown')
            parts = []
            for key in ('emblems', 'patterns', 'frames', 'realm_frames', 'title_frames'):
                count = src.get(key, 0)
                if count > 0:
                    label = key.replace('_', ' ').title()
                    parts.append(f"{count} {label}")
            detail = ", ".join(parts) if parts else "No assets"
            rows.append(f"<tr><td style='padding-right:20px;'><b>{name}</b></td><td>{detail}</td></tr>")
        
        table = "<table>" + "".join(rows) + "</table>" if rows else "<p>No sources found.</p>"
        
        QMessageBox.information(self, "Content Loaded",
            f"<h3>Converted Content</h3>"
            f"<p>Last converted: {converted}</p>"
            f"{table}")
    
    def _zoom_in(self):
        """Zoom in on canvas"""
        if hasattr(self.canvas_area, 'canvas_widget'):
            self.canvas_area.canvas_widget.zoom_in()
            # Update zoom toolbar
            if hasattr(self, 'zoom_toolbar'):
                self.zoom_toolbar.set_zoom_percent(self.canvas_area.canvas_widget.get_zoom_percent())
            # Update transform widget position after zoom change
            if hasattr(self.canvas_area, 'update_transform_widget_for_layer'):
                self.canvas_area.update_transform_widget_for_layer()
    
    def _zoom_out(self):
        """Zoom out on canvas"""
        if hasattr(self.canvas_area, 'canvas_widget'):
            self.canvas_area.canvas_widget.zoom_out()
            # Update zoom toolbar
            if hasattr(self, 'zoom_toolbar'):
                self.zoom_toolbar.set_zoom_percent(self.canvas_area.canvas_widget.get_zoom_percent())
            # Update transform widget position after zoom change
            if hasattr(self.canvas_area, 'update_transform_widget_for_layer'):
                self.canvas_area.update_transform_widget_for_layer()
    
    def _zoom_reset(self):
        """Reset canvas zoom to 100%"""
        if hasattr(self.canvas_area, 'canvas_widget'):
            self.canvas_area.canvas_widget.zoom_reset()
            # Update zoom toolbar
            if hasattr(self, 'zoom_toolbar'):
                self.zoom_toolbar.set_zoom_percent(100)
            # Update transform widget position after zoom change
            if hasattr(self.canvas_area, 'update_transform_widget_for_layer'):
                self.canvas_area.update_transform_widget_for_layer()
    
    def _on_zoom_changed(self, zoom_percent):
        """Handle zoom level change from toolbar"""
        if hasattr(self.canvas_area, 'canvas_widget'):
            self.canvas_area.canvas_widget.set_zoom_level(zoom_percent)
            # Update transform widget position after zoom change
            if hasattr(self.canvas_area, 'update_transform_widget_for_layer'):
                self.canvas_area.update_transform_widget_for_layer()
    
    def _toggle_grid_snap(self, checked):
        """Toggle snap-to-grid for transform positioning."""
        if hasattr(self.canvas_area, 'canvas_widget'):
            self.canvas_area.canvas_widget.snap_to_grid = checked
    
    def _set_grid_size(self, divisions):
        """Set grid size (0 = off, 2/4/8/16/32 = grid divisions)"""
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
            from utils.logger import loggerRaise
            loggerRaise(e, "Failed to split layer")
    
    def _merge_selected_layers(self):
        """Merge selected layers as instances into one layer"""
        try:
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
            from utils.logger import loggerRaise
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
            from utils.logger import loggerRaise
            loggerRaise(e, "Failed to group/ungroup layers")
    
    def _on_force_rgb_toggled(self, checked):
        """Update CoA model when Force RGB Colors is toggled"""
        if self.coa:
            self.coa._force_rgb_colors = checked
