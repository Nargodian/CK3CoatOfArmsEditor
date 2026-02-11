"""Asset selection and texture application for CoatOfArmsEditor"""

from utils.logger import loggerRaise


class AssetMixin:
    """Asset selection handlers and base/emblem texture application"""
    
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
            # Update the model so it exports correctly
            self.coa.pattern = filename
            self.canvas_area.canvas_widget.set_base_texture(filename)
            self._save_state("Change base texture")
    
    def _apply_emblem_texture(self, dds_filename, color_count):
        """Apply texture to selected layer(s) or create new layer"""
        self.right_sidebar.set_emblem_color_count(color_count)
        selected_uuids = self.right_sidebar.get_selected_uuids()
        
        if selected_uuids:
            # Update all selected layers (single undo entry for the group)
            for uuid in selected_uuids:
                self._update_layer_texture(uuid, dds_filename, color_count, save_state=False)
            self._save_state("Change layer texture")
        else:
            self._create_layer_with_texture(dds_filename, color_count)
    
    def _update_layer_texture(self, uuid, dds_filename, color_count, save_state=True):
        """Update existing layer's texture while preserving other properties
        
        Args:
            uuid: Layer UUID
            dds_filename: New texture filename
            color_count: Number of colors for the texture
            save_state: If True, save undo state after update. Set to False when
                       batching multiple updates (caller saves state once after loop).
        """
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
            # Reload properties to refresh color swatches based on new texture
            self.right_sidebar._load_layer_properties()
            self.canvas_area.canvas_widget.update()
            if save_state:
                self._save_state("Change layer texture")
    
    def _create_layer_with_texture(self, dds_filename, color_count):
        """Create new layer with selected texture, using asset sidebar colors."""
        # Check for selection to add above
        selected_uuids = self.right_sidebar.get_selected_uuids()
        target_uuid = selected_uuids[0] if selected_uuids else None
        
        # Get colors from asset sidebar pickers
        c1, c2, c3 = self.left_sidebar.get_asset_colors()
        
        # Use CoA model to add layer
        if target_uuid:
            # Add below selected layer (in front of it)
            layer_uuid = self.coa.add_layer(
                emblem_path=dds_filename,
                pos_x=0.5,
                pos_y=0.5,
                colors=color_count,
                target_uuid=target_uuid,
                color1=c1,
                color2=c2,
                color3=c3
            )
        else:
            # No selection, add at front
            layer_uuid = self.coa.add_layer(
                emblem_path=dds_filename,
                pos_x=0.5,
                pos_y=0.5,
                colors=color_count,
                color1=c1,
                color2=c2,
                color3=c3
            )
        
        # Update UI - rebuild layer list first
        self.right_sidebar._rebuild_layer_list()
        
        # Then auto-select the newly added layer using UUID from CoA
        new_uuid = self.coa.get_last_added_uuid()
        if new_uuid:
            self.right_sidebar.layer_list_widget.selected_layer_uuids = {new_uuid}
            self.right_sidebar.layer_list_widget.last_selected_uuid = new_uuid
            self.right_sidebar.layer_list_widget.update_selection_visuals()
        
        # Update canvas
        self.canvas_area.canvas_widget.on_coa_structure_changed()  # Invalidate picker RTT
        self.canvas_area.canvas_widget.update()
        
        # Trigger selection change callback to update properties and transform widget
        self.right_sidebar._on_layer_selection_changed()
        
        self._save_state("Create layer")
    
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
