"""Popup dialog for layer generation with preview and parameter controls."""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QWidget, QLabel, QFrame)
from PyQt5.QtCore import Qt, QSize, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPolygonF
import numpy as np
from typing import Optional, List, Tuple

from .base_generator import BaseGenerator


class PreviewWidget(QWidget):
    """Preview widget showing instance positions with simplified rendering."""
    
    PREVIEW_SIZE = 300  # Fixed 300x300 pixels
    INSTANCE_SIZE = 20  # Size of instance representation in pixels
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.PREVIEW_SIZE, self.PREVIEW_SIZE)
        self.instances = []  # List of (x, y, scale_x, scale_y, rotation) tuples
        
        # Style
        self.setStyleSheet("background-color: #000000; border: 3px solid #ffffff;")
    
    def set_instances(self, instances: np.ndarray):
        """Update instance transforms and redraw.
        
        Args:
            instances: 5xN numpy array [[x, y, scale_x, scale_y, rotation], ...]
                      where x, y are in 0-1 CoA coordinate space
        """
        self.instances = instances if len(instances) > 0 else []
        self.update()
    
    def paintEvent(self, event):
        """Draw instances as white squares with red triangle corners."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Fill background (black)
        painter.fillRect(self.rect(), QColor(0, 0, 0))
        
        # Draw each instance
        for instance in self.instances:
            x_coa, y_coa, scale_x, scale_y, rotation = instance
            
            # Convert CoA coordinates (0-1) to preview pixels (0-300)
            x_px = x_coa * self.PREVIEW_SIZE
            y_px = y_coa * self.PREVIEW_SIZE
            
            # Calculate instance size with scale (scale is percentage of preview area)
            width = scale_x * self.PREVIEW_SIZE
            height = scale_y * self.PREVIEW_SIZE
            
            # Save painter state
            painter.save()
            
            # Transform: translate to position, then rotate
            painter.translate(float(x_px), float(y_px))
            painter.rotate(float(rotation))
            
            # Draw white square centered at origin
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawRect(int(-width/2), int(-height/2), int(width), int(height))
            
            # Draw red triangle corner (top corner - north quadrant)
            # Triangle fills the top quadrant when square is divided by diagonals
            triangle = QPolygonF([
                QPointF(float(-width/2), float(-height/2)),  # Top-left
                QPointF(float(width/2), float(-height/2)),   # Top-right
                QPointF(0, 0)                                 # Center
            ])
            painter.setBrush(QBrush(QColor(255, 0, 0)))
            painter.setPen(Qt.NoPen)
            painter.drawPolygon(triangle)
            
            # Restore painter state
            painter.restore()


class GeneratorPopup(QDialog):
    """Popup dialog for layer generation with live preview.
    
    Displays generator-specific controls on the right and a live preview
    on the left showing the arrangement of instances.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_generator = None
        self.generated_instances = None  # Result from last generation
        
        self.setWindowTitle("Generate Layer")
        self.setModal(True)
        self.setMinimumSize(650, 400)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Create the dialog layout."""
        main_layout = QHBoxLayout(self)
        
        # LEFT: Preview widget
        preview_container = QVBoxLayout()
        preview_label = QLabel("Preview")
        preview_label.setAlignment(Qt.AlignCenter)
        preview_container.addWidget(preview_label)
        
        self.preview_widget = PreviewWidget()
        preview_container.addWidget(self.preview_widget)
        preview_container.addStretch()
        
        main_layout.addLayout(preview_container)
        
        # RIGHT: Controls panel
        right_panel = QVBoxLayout()
        
        # Title label
        self.title_label = QLabel("Generator")
        self.title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        right_panel.addWidget(self.title_label)
        
        # Controls container widget (will be populated by generator)
        self.controls_widget = QWidget()
        self.controls_layout = QVBoxLayout(self.controls_widget)
        right_panel.addWidget(self.controls_widget)
        
        right_panel.addStretch()
        
        # Buttons at bottom
        button_layout = QHBoxLayout()
        
        self.generate_button = QPushButton("Generate")
        self.generate_button.clicked.connect(self._on_generate)
        button_layout.addWidget(self.generate_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_button)
        
        right_panel.addLayout(button_layout)
        
        main_layout.addLayout(right_panel)
        
        # Set proportions
        main_layout.setStretch(0, 0)  # Preview fixed
        main_layout.setStretch(1, 1)  # Controls stretch
    
    def load_generator(self, generator: BaseGenerator):
        """Load a generator into the popup.
        
        Args:
            generator: Generator object to display
        """
        # Save settings from previous generator if any
        if self.current_generator:
            self._save_current_settings()
        
        # Clear old controls
        self._clear_controls()
        
        self.current_generator = generator
        self.setWindowTitle(f"Generate Layer - {generator.get_title()}")
        self.title_label.setText(generator.get_title())
        
        # Connect generator's parameter change callback to preview update
        generator.on_parameter_changed = self._update_preview
        
        # Build generator controls
        controls_layout = generator.build_controls(self)
        
        # Add all items from the generator's layout to our controls_layout
        while controls_layout.count():
            item = controls_layout.takeAt(0)
            if item.widget():
                self.controls_layout.addWidget(item.widget())
            elif item.layout():
                self.controls_layout.addLayout(item.layout())
        
        # Initial preview update
        self._update_preview()
    
    def _clear_controls(self):
        """Remove all widgets from controls container."""
        while self.controls_layout.count():
            child = self.controls_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())
                child.layout().deleteLater()  # Delete the layout itself too
    
    def _clear_layout(self, layout):
        """Recursively clear a layout."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())
                child.layout().deleteLater()  # Delete nested layouts too
    
    def _update_preview(self):
        """Update preview with current generator parameters."""
        if not self.current_generator:
            return
        
        try:
            # Get current parameters from generator
            params = self._collect_parameters()
            
            # Generate positions
            instances = self.current_generator.generate_positions(**params)
            
            # Update preview
            self.preview_widget.set_instances(instances)
            
        except Exception as e:
            print(f"Preview update failed: {e}")
            # Clear preview on error
            self.preview_widget.set_instances(np.array([]))
    
    def _collect_parameters(self) -> dict:
        """Collect current parameter values from generator controls.
        
        Returns:
            Dictionary of parameter names to values
        """
        # This is a placeholder - actual implementation will depend on
        # how generators expose their parameters
        # For now, return empty dict
        return {}
    
    def _save_current_settings(self):
        """Save current generator settings before switching/closing."""
        if self.current_generator:
            # Settings are stored in the generator object itself
            # They persist in memory during the session
            pass
    
    def _on_generate(self):
        """Handle Generate button click."""
        if not self.current_generator:
            return
        
        try:
            # Collect parameters
            params = self._collect_parameters()
            
            # Generate instances
            self.generated_instances = self.current_generator.generate_positions(**params)
            
            # Close dialog with accept status
            self.accept()
            
        except Exception as e:
            print(f"Generation failed: {e}")
            # TODO: Show error message to user
    
    def _on_cancel(self):
        """Handle Cancel button click."""
        self._save_current_settings()
        self._clear_controls()
        self.current_generator = None
        self.reject()
    
    def closeEvent(self, event):
        """Handle window close (X button)."""
        self._save_current_settings()
        self._clear_controls()
        self.current_generator = None
        super().closeEvent(event)
    
    def get_generated_instances(self) -> Optional[np.ndarray]:
        """Get the generated instance transforms.
        
        Returns:
            5xN numpy array of instance transforms, or None if cancelled
        """
        return self.generated_instances
