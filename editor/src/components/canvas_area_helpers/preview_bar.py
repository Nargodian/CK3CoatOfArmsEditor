"""Preview bar component for canvas area - controls government, rank, size, and preview toggle"""
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QCheckBox
from services.government_discovery import GovernmentDiscovery
from components.ui_helpers import create_styled_combo_box


class PreviewBar(QFrame):
    """Top preview control bar with government type, rank, and size selection"""
    
    def __init__(self, canvas_area):
        """Initialize preview bar
        
        Args:
            canvas_area: Parent CanvasArea instance
        """
        super().__init__()
        self.canvas_area = canvas_area
        
        self.setStyleSheet("QFrame { background-color: #2d2d2d; border: none; }")
        self.setFixedHeight(40)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the preview bar UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Government type dropdown - auto-populated from mask files
        government_label = QLabel("Government:")
        government_label.setStyleSheet("font-size: 11px; border: none;")
        layout.addWidget(government_label)
        
        # Discover government types using service
        government_types, self.government_file_map = GovernmentDiscovery.get_government_types()
        
        self.government_combo = create_styled_combo_box(government_types)
        self.government_combo.setMinimumWidth(180)
        self.government_combo.currentIndexChanged.connect(self._on_government_changed)
        layout.addWidget(self.government_combo)
        
        # Rank dropdown
        rank_label = QLabel("Rank:")
        rank_label.setStyleSheet("font-size: 11px; border: none;")
        layout.addWidget(rank_label)
        ranks = ["Baron", "Count", "Duke", "King", "Emperor", "Hegemon"]
        self.rank_combo = create_styled_combo_box(ranks)
        self.rank_combo.setMinimumWidth(120)
        self.rank_combo.setCurrentIndex(2)  # Default to Duke
        self.rank_combo.currentIndexChanged.connect(self._on_rank_changed)
        layout.addWidget(self.rank_combo)
        
        # Size dropdown (pixel sizes)
        size_label = QLabel("Size:")
        size_label.setStyleSheet("font-size: 11px; border: none;")
        layout.addWidget(size_label)
        sizes = ["28px", "44px", "62px", "86px", "115px"]
        self.size_combo = create_styled_combo_box(sizes)
        self.size_combo.setMinimumWidth(100)
        self.size_combo.setCurrentIndex(3)  # Default to 86px
        self.size_combo.currentIndexChanged.connect(self._on_size_changed)
        layout.addWidget(self.size_combo)
        
        layout.addStretch()
        
        # Preview toggle checkbox (right-aligned)
        self.preview_toggle = QCheckBox("Preview")
        self.preview_toggle.setChecked(False)
        self.preview_toggle.setStyleSheet("QCheckBox { color: #ffffff; }")
        self.preview_toggle.toggled.connect(self._on_preview_toggle)
        layout.addWidget(self.preview_toggle)
    
    def _on_preview_toggle(self, checked):
        """Handle preview toggle"""
        if self.canvas_area.canvas_widget:
            self.canvas_area.canvas_widget.set_preview_enabled(checked)
    
    def _on_government_changed(self, index):
        """Handle government type change"""
        if self.canvas_area.canvas_widget:
            # Get display name from dropdown
            display_name = self.government_combo.currentText()
            # Map to file key
            gov_key = self.government_file_map.get(display_name, "_default")
            self.canvas_area.canvas_widget.set_preview_government(gov_key)
    
    def _on_rank_changed(self, index):
        """Handle rank change"""
        if self.canvas_area.canvas_widget:
            self.canvas_area.canvas_widget.set_preview_rank(self.rank_combo.currentText())
    
    def _on_size_changed(self, index):
        """Handle size change"""
        if self.canvas_area.canvas_widget:
            # Map index to size
            size_map = {0: 28, 1: 44, 2: 62, 3: 86, 4: 115}
            size = size_map.get(index, 86)
            self.canvas_area.canvas_widget.set_preview_size(size)
