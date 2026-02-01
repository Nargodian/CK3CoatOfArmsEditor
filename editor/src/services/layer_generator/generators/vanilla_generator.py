"""Vanilla CK3 Layout Generator - Pre-defined official CK3 emblem layouts."""

import json
from pathlib import Path
import numpy as np
from PyQt5.QtWidgets import QLabel, QComboBox, QVBoxLayout

from services.layer_generator.base_generator import BaseGenerator


class VanillaGenerator(BaseGenerator):
    """Generator for CK3's official emblem layouts.
    
    Loads pre-calculated layouts from emblem_layouts.json and allows
    selection via dropdown. No user-configurable parameters - layouts
    are applied exactly as defined in the game files.
    """
    
    # Class-level storage for loaded layouts
    _loaded_layouts = None
    _layout_names = []
    
    def __init__(self):
        super().__init__()
        self.selected_layout = None
        self.layout_dropdown = None
        
        # Load layouts on first instantiation
        if VanillaGenerator._loaded_layouts is None:
            VanillaGenerator._load_layouts()
        
        # Default to first layout if available
        if VanillaGenerator._layout_names:
            self.selected_layout = VanillaGenerator._layout_names[0]
    
    @classmethod
    def _load_layouts(cls):
        """Load emblem layouts from JSON file."""
        layouts_path = Path("ck3_assets/emblem_layouts.json")
        
        if not layouts_path.exists():
            cls._loaded_layouts = {}
            cls._layout_names = []
            return
        
        try:
            with open(layouts_path, 'r', encoding='utf-8') as f:
                cls._loaded_layouts = json.load(f)
            
            # Preserve insertion order from JSON (Python 3.7+ dict order)
            cls._layout_names = list(cls._loaded_layouts.keys())
            
        except Exception as e:
            print(f"Error loading vanilla layouts: {e}")
            cls._loaded_layouts = {}
            cls._layout_names = []
    
    def get_title(self) -> str:
        """Return display title for popup."""
        return "Vanilla CK3 Layouts"
    
    def build_controls(self, parent_widget):
        """Build UI controls for layout selection."""
        layout = QVBoxLayout()
        
        # Info label
        info_label = QLabel("Select an official CK3 emblem layout:")
        layout.addWidget(info_label)
        
        # Layout dropdown
        self.layout_dropdown = QComboBox()
        
        # Populate with layout names (remove coa_designer_ prefix for display)
        for layout_name in VanillaGenerator._layout_names:
            display_name = layout_name.replace("coa_designer_", "").replace("_", " ").title()
            self.layout_dropdown.addItem(display_name, layout_name)  # userData = actual key
        
        # Set current selection
        if self.selected_layout:
            idx = VanillaGenerator._layout_names.index(self.selected_layout)
            self.layout_dropdown.setCurrentIndex(idx)
        
        # Connect selection change
        self.layout_dropdown.currentIndexChanged.connect(self._on_layout_changed)
        
        layout.addWidget(self.layout_dropdown)
        
        # Info label showing instance count
        self.instance_count_label = QLabel()
        self._update_instance_count()
        layout.addWidget(self.instance_count_label)
        
        layout.addStretch()
        
        return layout
    
    def _on_layout_changed(self, index):
        """Handle layout selection change."""
        if index >= 0:
            self.selected_layout = self.layout_dropdown.itemData(index)
            self._update_instance_count()
            
            # Notify popup to update preview
            if self.on_parameter_changed:
                self.on_parameter_changed()
    
    def _update_instance_count(self):
        """Update the instance count label."""
        if not self.selected_layout or not hasattr(self, 'instance_count_label'):
            return
        
        instances = VanillaGenerator._loaded_layouts.get(self.selected_layout, [])
        count = len(instances)
        self.instance_count_label.setText(f"Instances: {count}")
    
    def generate_positions(self, **params) -> np.ndarray:
        """Generate instance positions from selected vanilla layout.
        
        Returns:
            5xN numpy array: [[x, y, scale_x, scale_y, rotation], ...]
        """
        if not self.selected_layout:
            # Return default single center instance
            return np.array([[0.5, 0.5, 1.0, 1.0, 0.0]])
        
        # Get layout data
        layout_data = VanillaGenerator._loaded_layouts.get(self.selected_layout, [])
        
        if not layout_data:
            return np.array([[0.5, 0.5, 1.0, 1.0, 0.0]])
        
        # Convert to numpy array (data is already in correct format)
        return np.array(layout_data, dtype=float)
