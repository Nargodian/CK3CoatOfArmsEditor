"""UI setup for CoatOfArmsEditor"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QSplitter, QStatusBar, QLabel
from PyQt5.QtCore import Qt, QTimer

from components.asset_sidebar import AssetSidebar
from components.canvas_area import CanvasArea
from components.property_sidebar import PropertySidebar
from constants import DEFAULT_BASE_CATEGORY
from models.coa import CoA


class UISetupMixin:
    """UI initialization and component wiring"""
    
    def setup_ui(self):
        """Initialize and wire up all UI components"""
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
        # Pass CoA reference to canvas area and canvas widget
        self.canvas_area.coa = self.coa
        self.canvas_area.canvas_widget.coa = self.coa
        # Connect transform widget to main window for edit lock access
        self.canvas_area.transform_widget.main_window = self
        splitter.addWidget(self.canvas_area)
        
        # Right properties sidebar
        self.right_sidebar = PropertySidebar(self)
        self.right_sidebar.main_window = self
        # Pass CoA reference to property sidebar and layer list
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
        
        self.statusBar().setStyleSheet("QStatusBar { border-top: 1px solid rgba(255, 255, 255, 40); padding: 4px; }")
        
        # Update status bar with initial stats
        self._update_status_bar()
        
        # Note: Cannot set frame/base here - OpenGL not initialized yet
        # Will be set after show() triggers initializeGL()
