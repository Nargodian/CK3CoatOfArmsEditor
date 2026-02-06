"""Zoom toolbar widget with zoom controls."""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QToolButton, QMenu, QLabel
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QIcon
import os


class ZoomToolbar(QWidget):
    """Toolbar with zoom in/out buttons and zoom level dropdown"""
    
    zoom_changed = pyqtSignal(int)  # Emits zoom percentage (25-500)
    
    # Standard zoom presets
    ZOOM_PRESETS = [25, 50, 100, 150, 200, 300, 400, 500]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Zoom out button
        self.zoom_out_btn = QToolButton()
        self.zoom_out_btn.setText("−")
        self.zoom_out_btn.setToolTip("Zoom Out (Ctrl+-)")
        self.zoom_out_btn.clicked.connect(self._on_zoom_out)
        layout.addWidget(self.zoom_out_btn)
        
        # Zoom level display (shows actual zoom)
        self.zoom_display = QLabel("100%")
        self.zoom_display.setMinimumWidth(60)
        self.zoom_display.setAlignment(Qt.AlignCenter)
        self.zoom_display.setStyleSheet("QLabel { padding: 2px 4px; background-color: #2d2d2d; border: 1px solid #555; border-radius: 2px; }")
        layout.addWidget(self.zoom_display)
        
        # Zoom preset button with dropdown menu
        self.preset_btn = QToolButton()
        self.preset_btn.setText("🔍")  # Magnifying glass icon
        self.preset_btn.setToolTip("Jump to preset zoom level")
        self.preset_btn.setPopupMode(QToolButton.InstantPopup)
        
        # Create preset menu
        preset_menu = QMenu(self)
        for preset in self.ZOOM_PRESETS:
            action = preset_menu.addAction(f"{preset}%")
            action.setData(preset)
            action.triggered.connect(lambda checked, p=preset: self._on_preset_selected(p))
        
        self.preset_btn.setMenu(preset_menu)
        layout.addWidget(self.preset_btn)
        
        # Zoom in button
        self.zoom_in_btn = QToolButton()
        self.zoom_in_btn.setText("+")
        self.zoom_in_btn.setToolTip("Zoom In (Ctrl++)")
        self.zoom_in_btn.clicked.connect(self._on_zoom_in)
        layout.addWidget(self.zoom_in_btn)
        
        self.setLayout(layout)
    
    def _on_zoom_in(self):
        """Handle zoom in button click"""
        current_zoom = self.get_zoom_percent()
        # Find next preset
        for preset in self.ZOOM_PRESETS:
            if preset > current_zoom:
                self.set_zoom_percent(preset)
                return
        # Already at max, just use 125% of current
        new_zoom = min(500, int(current_zoom * 1.25))
        self.set_zoom_percent(new_zoom)
    
    def _on_zoom_out(self):
        """Handle zoom out button click"""
        current_zoom = self.get_zoom_percent()
        # Find previous preset
        for preset in reversed(self.ZOOM_PRESETS):
            if preset < current_zoom:
                self.set_zoom_percent(preset)
                return
        # Already at min, just use 80% of current
        new_zoom = max(25, int(current_zoom / 1.25))
        self.set_zoom_percent(new_zoom)
    
    def _on_preset_selected(self, preset_value):
        """Handle preset selection from dropdown menu"""
        self.zoom_changed.emit(preset_value)
    
    def set_zoom_percent(self, percent, emit_signal=True):
        """Set zoom level (updates display only, not combo selection)"""
        # Update the zoom display to show actual zoom
        self.zoom_display.setText(f"{percent}%")
        
        # Emit signal only if requested
        if emit_signal:
            self.zoom_changed.emit(percent)
    
    def get_zoom_percent(self):
        """Get current zoom percentage from display"""
        text = self.zoom_display.text().strip().rstrip('%')
        try:
            return int(text)
        except ValueError:
            return 100
