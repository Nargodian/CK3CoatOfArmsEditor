"""Base class for symmetry transform plugins.

Each transform type is a self-contained plugin that defines:
- UI controls for its parameters
- Transform calculation logic
- Canvas overlay visualization
"""

from abc import ABC, abstractmethod
from typing import List, Callable
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtGui import QPainter


class BaseSymmetryTransform(ABC):
    """Abstract base class for symmetry transforms.
    
    Subclasses must implement:
    - get_name(): Return internal identifier (e.g., "bisector")
    - get_display_name(): Return UI display name (e.g., "Bisector")
    - build_controls(): Create parameter UI widgets
    - calculate_transforms(): Generate mirror transforms from seed
    - draw_overlay(): Render visual indicators on canvas
    """
    
    # Class-level settings cache (persists across instances)
    _settings_cache = {}
    
    def __init__(self):
        """Initialize transform with default settings."""
        self.settings = {}  # Stores parameter values
        self._controls = {}  # Maps parameter names to widgets
        self._on_change_callback = None  # Callback when parameters change
        
        # Restore cached settings for this transform type if available
        cache_key = self.__class__.__name__
        if cache_key in BaseSymmetryTransform._settings_cache:
            self.settings.update(BaseSymmetryTransform._settings_cache[cache_key])
    
    @abstractmethod
    def get_name(self) -> str:
        """Return internal identifier for this transform type.
        
        Returns:
            Name string (e.g., "bisector", "rotational", "grid")
        """
        pass
    
    @abstractmethod
    def get_display_name(self) -> str:
        """Return display name for UI.
        
        Returns:
            Display string (e.g., "Bisector", "Rotational", "Grid")
        """
        pass
    
    @abstractmethod
    def build_controls(self, parent: QWidget) -> QVBoxLayout:
        """Build parameter control widgets.
        
        Args:
            parent: Parent widget for controls
            
        Returns:
            Layout containing all parameter controls
        """
        pass
    
    @abstractmethod
    def calculate_transforms(self, seed_transform):
        """Calculate mirror transforms from seed instance.
        
        Args:
            seed_transform: Transform object with pos, scale, rotation
            
        Returns:
            List of Transform objects for mirrors (NOT including seed)
        """
        pass
    
    @abstractmethod
    def draw_overlay(self, painter: QPainter, layer_uuid: str, coa):
        """Draw visual indicators on canvas.
        
        Args:
            painter: QPainter for drawing
            layer_uuid: UUID of layer to visualize
            coa: CoA model instance
        """
        pass
    
    def get_properties(self) -> List[float]:
        """Serialize settings to property list for storage.
        
        Returns:
            List of float values representing current settings
        """
        # Default implementation - subclasses should override
        return []
    
    def set_properties(self, properties: List[float]):
        """Deserialize property list into settings.
        
        Args:
            properties: List of float values from storage
        """
        # Default implementation - subclasses should override
        pass
    
    def _save_to_cache(self):
        """Save current settings to class-level cache."""
        cache_key = self.__class__.__name__
        BaseSymmetryTransform._settings_cache[cache_key] = self.settings.copy()
    
    def set_change_callback(self, callback: Callable):
        """Set callback to be called when parameters change.
        
        Args:
            callback: Function to call with no arguments when params change
        """
        self._on_change_callback = callback
    
    def _on_param_changed(self, param_name: str, value):
        """Handle parameter value change.
        
        Args:
            param_name: Name of parameter that changed
            value: New value
        """
        self.settings[param_name] = value
        self._save_to_cache()
        
        # Notify parent that parameters changed
        if self._on_change_callback:
            self._on_change_callback()
