"""Instance class for layer instances - encapsulates transform data for a single instance"""

from typing import Dict, Any
from constants import DEFAULT_POSITION_X, DEFAULT_POSITION_Y, DEFAULT_SCALE_X, DEFAULT_SCALE_Y, DEFAULT_ROTATION


class Instance:
    """Represents a single instance of a layer emblem
    
    Each layer can have multiple instances (copies) of the same emblem,
    each with its own transform (position, scale, rotation).
    
    Properties:
        pos_x: X position (0.0-1.0)
        pos_y: Y position (0.0-1.0)
        scale_x: X scale factor
        scale_y: Y scale factor
        rotation: Rotation angle in degrees
        depth: Z-depth for rendering order
    """
    
    def __init__(self, data: Dict[str, Any] = None):
        """Create instance from data dictionary
        
        Args:
            data: Dictionary with instance data, or None for defaults
        """
        if data is None:
            data = {}
        
        self._pos_x = data.get('pos_x', DEFAULT_POSITION_X)
        self._pos_y = data.get('pos_y', DEFAULT_POSITION_Y)
        self._scale_x = data.get('scale_x', DEFAULT_SCALE_X)
        self._scale_y = data.get('scale_y', DEFAULT_SCALE_Y)
        self._rotation = data.get('rotation', DEFAULT_ROTATION)
        self._depth = data.get('depth', 0.0)
    
    # ========================================
    # Properties
    # ========================================
    
    @property
    def pos_x(self) -> float:
        """X position (0.0-1.0)"""
        return self._pos_x
    
    @pos_x.setter
    def pos_x(self, value: float):
        """Set X position with clamping"""
        self._pos_x = max(0.0, min(1.0, float(value)))
    
    @property
    def pos_y(self) -> float:
        """Y position (0.0-1.0)"""
        return self._pos_y
    
    @pos_y.setter
    def pos_y(self, value: float):
        """Set Y position with clamping"""
        self._pos_y = max(0.0, min(1.0, float(value)))
    
    @property
    def scale_x(self) -> float:
        """X scale factor"""
        return self._scale_x
    
    @scale_x.setter
    def scale_x(self, value: float):
        """Set X scale factor"""
        self._scale_x = float(value)
    
    @property
    def scale_y(self) -> float:
        """Y scale factor"""
        return self._scale_y
    
    @scale_y.setter
    def scale_y(self, value: float):
        """Set Y scale factor"""
        self._scale_y = float(value)
    
    @property
    def rotation(self) -> float:
        """Rotation angle in degrees"""
        return self._rotation
    
    @rotation.setter
    def rotation(self, value: float):
        """Set rotation angle"""
        self._rotation = float(value)
    
    @property
    def depth(self) -> float:
        """Z-depth for rendering order"""
        return self._depth
    
    @depth.setter
    def depth(self, value: float):
        """Set depth"""
        self._depth = float(value)
    
    # ========================================
    # Serialization
    # ========================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert instance to dictionary for serialization
        
        Returns:
            Dictionary with instance data
        """
        return {
            'pos_x': self._pos_x,
            'pos_y': self._pos_y,
            'scale_x': self._scale_x,
            'scale_y': self._scale_y,
            'rotation': self._rotation,
            'depth': self._depth
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Instance':
        """Create instance from dictionary
        
        Args:
            data: Dictionary with instance data
            
        Returns:
            New Instance object
        """
        return Instance(data)
    
    # ========================================
    # Utility Methods
    # ========================================
    
    def copy(self) -> 'Instance':
        """Create a deep copy of this instance
        
        Returns:
            New Instance with same values
        """
        return Instance(self.to_dict())
    
    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"Instance(pos=({self._pos_x:.3f}, {self._pos_y:.3f}), scale=({self._scale_x:.3f}, {self._scale_y:.3f}), rot={self._rotation:.1f}°)"
