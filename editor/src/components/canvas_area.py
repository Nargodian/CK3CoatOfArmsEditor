# PyQt5 imports
from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSizePolicy, QMenu, QCheckBox)
from PyQt5.QtCore import Qt

# Local component imports
from models.transform import Transform, Vec2
from .canvas_widget import CoatOfArmsCanvas
from .transform_widget import TransformWidget
from .canvas_area_helpers.canvas_area_transform_mixin import CanvasAreaTransformMixin
from .canvas_area_helpers.preview_bar import PreviewBar
from .canvas_area_helpers.bottom_bar import BottomBar
from services.government_discovery import GovernmentDiscovery


class CanvasArea(CanvasAreaTransformMixin, QFrame):
    """Center canvas area for coat of arms preview"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QFrame { background-color: #141414; }")
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setMinimumWidth(800)  # Ensure canvas area has enough space
        
        #COA INTEGRATION ACTION: Step 4 - Add CoA model reference (set by MainWindow)
        self.coa = None  # Reference to CoA model (will be set externally)
        self.property_sidebar = None  # Will be set by main window
        self.main_window = None  # Will be set by main window
    
        # Cache for multi-layer transform (prevents cumulative transforms)
        self._drag_start_layers = None
        # Track instance group transforms (replaces dynamic _instance_transform_begun_{uuid} attributes)
        self._instance_transforms = set()  # Set of UUIDs with active instance transforms
        
        self._setup_ui()
    
    def mousePressEvent(self, event):
        """Handle clicks on canvas background to deselect layers"""
        # If clicking outside the canvas widget itself, deselect layer
        if self.property_sidebar and self.property_sidebar.get_selected_uuids():
            # Check if click is on the canvas widget
            canvas_geometry = self.canvas_widget.geometry()
            if not canvas_geometry.contains(event.pos()):
                # Clicked outside canvas - deselect
                self.property_sidebar._deselect_layer()
        super().mousePressEvent(event)
    
    def _setup_ui(self):
        """Setup the canvas area UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Top preview control bar (UI chrome in main layout)
        self.preview_bar = PreviewBar(self)
        self.preview_bar.raise_()  # Ensure preview bar is on top
        layout.addWidget(self.preview_bar)
        
        # Container - PURE CONCEPTUAL BARRIER (no styling, no properties)
        # Exists ONLY as mathematical/organizational boundary
        # Mathematical assumption: container dimensions == canvas_widget dimensions
        canvas_container = QFrame()
        canvas_container_layout = QVBoxLayout(canvas_container)
        canvas_container_layout.setContentsMargins(0, 0, 0, 0)
        canvas_container_layout.setSpacing(0)
        
        # OpenGL canvas widget (fills 100% of container - stretch=1, no margins)
        self.canvas_widget = CoatOfArmsCanvas(canvas_container)
        self.canvas_widget.canvas_area = self  # Give canvas access to canvas_area
        # Widget fills container - zoom handled by scaling rendering, not widget size
        canvas_container_layout.addWidget(self.canvas_widget, stretch=1)
        
        # Transform widget (parented to canvas_container, absolute positioned overlay)
        # NOT added to layout - manually positioned/sized to overlay container's area
        # Parent to canvas_container (not canvas_widget) to avoid edge clipping
        # Pass canvas_widget as reference for coordinate calculations
        self.transform_widget = TransformWidget(canvas_container, self.canvas_widget)
        self.transform_widget.set_visible(False)
        self.transform_widget.transformChanged.connect(self._on_transform_changed)
        self.transform_widget.transformEnded.connect(self._on_transform_ended)
        self.transform_widget.nonUniformScaleUsed.connect(self._on_non_uniform_scale_used)
        self.transform_widget.layerDuplicated.connect(self._on_layer_duplicated)
        
        layout.addWidget(canvas_container, stretch=1)
        
        # Bottom bar (UI chrome in main layout)
        self.bottom_bar = BottomBar(self)
        layout.addWidget(self.bottom_bar)
    
    def get_rotation_mode(self):
        """Get current rotation mode from dropdown - delegates to bottom_bar"""
        return self.bottom_bar.get_rotation_mode()
    
    def set_property_sidebar(self, sidebar):
        """Set reference to property sidebar for layer selection"""
        self.property_sidebar = sidebar
    
    def update_transform_widget_for_layer(self, layer_index=None):
        """Update transform widget to match selected layer(s)"""
        self._reset_transform_state()
        
        if not self._should_show_transform_widget():
            self.transform_widget.set_visible(False)
            return
        
        selected_uuids = self.property_sidebar.get_selected_uuids()
        
        if len(selected_uuids) == 1:
            self._update_single_selection(list(selected_uuids)[0])
        else:
            self._update_multi_selection(selected_uuids)
    
    def _reset_transform_state(self):
        """Reset all transform-related state when selection changes"""
        self._drag_start_layers = None
        self._drag_start_aabb = None
        self.transform_widget.active_handle = None
        self.transform_widget.drag_start_pos = None
        self.transform_widget.drag_start_transform = None
        self.transform_widget.drag_context = None
        self._initial_group_center = None
        self._initial_group_rotation = 0
    
    def _should_show_transform_widget(self):
        """Check if transform widget should be shown"""
        if hasattr(self, 'bottom_bar') and self.bottom_bar.picker_btn.isChecked():
            return False
        if not self.property_sidebar:
            return False
        if not self.main_window or not self.main_window.coa:
            return False
        return True
    
    def _update_single_selection(self, uuid):
        """Update transform widget for single layer selection"""
        instance_count = self.main_window.coa.get_layer_instance_count(uuid)
        
        if instance_count > 1:
            self._update_multi_instance_selection(uuid)
        else:
            self._update_single_instance_selection(uuid)
    
    def _update_single_instance_selection(self, uuid):
        """Update transform widget for single-instance layer"""
        pos = self.main_window.coa.get_layer_pos(uuid)
        scale = self.main_window.coa.get_layer_scale(uuid)
        rotation = self.main_window.coa.get_layer_rotation(uuid)
        
        if pos is None:
            self.transform_widget.set_visible(False)
            return
        
        coa_transform = Transform(pos, scale, rotation)
        widget_transform = self.canvas_widget.coa_to_transform_widget(coa_transform)
        self.transform_widget.set_transform(
            widget_transform.pos.x, widget_transform.pos.y, 
            widget_transform.scale.x, widget_transform.scale.y, 
            widget_transform.rotation, is_multi_selection=False
        )
        self.transform_widget.set_visible(True)
    
    def _update_multi_instance_selection(self, uuid):
        """Update transform widget for multi-instance layer (AABB)"""
        try:
            bounds = self.main_window.coa.get_layer_bounds(uuid)
            coa_transform = Transform(
                Vec2(bounds['center_x'], bounds['center_y']), 
                Vec2(bounds['width'], bounds['height']), 0
            )
            widget_transform = self.canvas_widget.coa_to_transform_widget(coa_transform, is_aabb_dimension=True)
            self.transform_widget.set_transform(
                widget_transform.pos.x, widget_transform.pos.y, 
                widget_transform.scale.x, widget_transform.scale.y, 
                widget_transform.rotation, is_multi_selection=True
            )
            self.transform_widget.set_visible(True)
        except ValueError:
            self.transform_widget.set_visible(False)
    
    def _update_multi_selection(self, selected_uuids):
        """Update transform widget for multiple layer selection"""
        # Use cached AABB if actively transforming
        if hasattr(self, '_drag_start_aabb') and self._drag_start_aabb is not None:
            group_pos_x = self._drag_start_aabb['center_x']
            group_pos_y = self._drag_start_aabb['center_y']
            group_scale_x = self._drag_start_aabb['scale_x']
            group_scale_y = self._drag_start_aabb['scale_y']
        else:
            try:
                bounds = self.main_window.coa.get_layers_bounds(selected_uuids)
                group_pos_x = bounds['center_x']
                group_pos_y = bounds['center_y']
                group_scale_x = bounds['width']
                group_scale_y = bounds['height']
            except ValueError:
                self.transform_widget.set_visible(False)
                return
        
        # Store initial state for rotation
        if not hasattr(self, '_initial_group_center'):
            self._initial_group_center = (group_pos_x, group_pos_y)
            self._initial_group_rotation = 0
        
        coa_transform = Transform(Vec2(group_pos_x, group_pos_y), Vec2(group_scale_x, group_scale_y), 0)
        widget_transform = self.canvas_widget.coa_to_transform_widget(coa_transform, is_aabb_dimension=True)
        self.transform_widget.set_transform(
            widget_transform.pos.x, widget_transform.pos.y, 
            widget_transform.scale.x, widget_transform.scale.y, 
            widget_transform.rotation, is_multi_selection=True
        )
        self.transform_widget.set_visible(True)
    
    
    def _on_transform_changed(self, widget_transform):
        """Handle transform changes from the widget (pixel space → CoA space).
        
        Args:
            widget_transform: Transform object with pixel coordinates (widget space)
        """
        selected_uuids = self.property_sidebar.get_selected_uuids() if self.property_sidebar else []
        if not selected_uuids:
            return
        
        # Convert widget coordinates to CoA space
        coa_transform = self._convert_widget_to_coa_coords(widget_transform)
        
        # Handle rotation (rotation handle dragged)
        if hasattr(self.transform_widget, 'is_rotating') and self.transform_widget.is_rotating:
            self._handle_rotation_transform(selected_uuids, coa_transform.rotation)
            return
        
        # Handle single selection
        if len(selected_uuids) == 1:
            uuid = list(selected_uuids)[0]
            instance_count = self.main_window.coa.get_layer_instance_count(uuid)
            
            if instance_count > 1:
                # Multi-instance layer: group transform
                self._handle_multi_instance_transform(uuid, coa_transform)
            else:
                # Single-instance layer: direct transform
                self._handle_single_instance_transform(uuid, coa_transform)
            return
        
        # Handle multi-selection
        self._handle_multi_selection_transform(coa_transform, selected_uuids)
    
    def _on_transform_ended(self):
        """Handle transform widget drag end"""
        # Clear rotation cache (rotation already applied during drag)
        if hasattr(self, '_rotation_start') and self._rotation_start is not None:
            self.main_window.coa.end_rotation_transform()
        
        # Clear CoA transform caches
        if self.main_window and self.main_window.coa:
            self.main_window.coa.end_transform_group()
            self.main_window.coa.end_instance_group_transform()
        
        # Clear instance transform tracking
        self._instance_transforms.clear()
        
        # Clear single layer state caches
        self._single_layer_initial_state = None
        self._single_layer_aabb = None
        self._initial_instance_rotation = 0
        self._rotation_start = None  # Clear rotation tracking
        
        # Update canvas
        self.canvas_widget.update()
        self._drag_start_layers = None
        self._drag_start_aabb = None
        
        # Reload properties to update UI with final values
        if self.property_sidebar:
            self.property_sidebar._load_layer_properties()
        
        # Update transform widget to reset rotation to 0 for multi-selection
        self.update_transform_widget_for_layer()
        
        if self.main_window and hasattr(self.main_window, '_save_state'):
            self.main_window._save_state("Transform layer")
    
    def _on_non_uniform_scale_used(self):
        """Handle non-uniform scaling from transform widget - disable unified scale"""
        if self.property_sidebar and hasattr(self.property_sidebar, 'unified_scale_check'):
            if self.property_sidebar.unified_scale_check.isChecked():
                self.property_sidebar.unified_scale_check.setChecked(False)
    
    def _on_layer_duplicated(self):
        """Handle Ctrl+drag layer duplication - duplicate goes BELOW original, keep original selected"""
        if self.main_window and hasattr(self.main_window, 'clipboard_actions'):
            self.main_window.clipboard_actions.duplicate_selected_layer_below(keep_selection=True)
    
    def _show_context_menu(self, pos):
        """Show context menu with Edit menu actions"""
        if not self.main_window or not hasattr(self.main_window, 'edit_menu'):
            return
        
        # Create context menu and add Edit menu actions
        context_menu = QMenu(self)
        for action in self.main_window.edit_menu.actions():
            if action.isSeparator():
                context_menu.addSeparator()
            else:
                context_menu.addAction(action)
        
        context_menu.exec_(self.mapToGlobal(pos))
