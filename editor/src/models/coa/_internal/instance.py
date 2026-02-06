"""Instance class for layer instances - encapsulates transform data for a single instance"""

from typing import Dict, Any
from constants import DEFAULT_POSITION_X, DEFAULT_POSITION_Y, DEFAULT_SCALE_X, DEFAULT_SCALE_Y, DEFAULT_ROTATION
from models.transform import Vec2


class Instance:
    """Represents a single instance of a layer emblem
    
    Each layer can have multiple instances (copies) of the same emblem,
    each with its own transform (position, scale, rotation).
    
    Properties:
        pos: Position as Vec2 (0.0-1.0)
        scale: Scale as Vec2
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
        
        self._pos = Vec2(
            data.get('pos_x', DEFAULT_POSITION_X),
            data.get('pos_y', DEFAULT_POSITION_Y)
        )
        self._scale = Vec2(
            data.get('scale_x', DEFAULT_SCALE_X),
            data.get('scale_y', DEFAULT_SCALE_Y)
        )
        self._rotation = float(data.get('rotation', DEFAULT_ROTATION))
        self._depth = float(data.get('depth', 0.0))
        self._flip_x = bool(data.get('flip_x', False))
        self._flip_y = bool(data.get('flip_y', False))
    
    # ========================================
    # Primary Properties (Vec2)
    # ========================================
    
    @property
    def pos(self) -> Vec2:
        """Position as Vec2 (0.0-1.0)"""
        return self._pos
    
    @pos.setter
    def pos(self, value: Vec2):
        """Set position with clamping"""
        self._pos = Vec2(
            max(0.0, min(1.0, float(value.x))),
            max(0.0, min(1.0, float(value.y)))
        )
    
    @property
    def scale(self) -> Vec2:
        """Scale as Vec2"""
        return self._scale
    
    @scale.setter
    def scale(self, value: Vec2):
        """Set scale with clamping to [0.01, 1.0]"""
        self._scale = Vec2(
            max(0.01, min(1.0, float(value.x))),
            max(0.01, min(1.0, float(value.y)))
        )
    
    # ========================================
    # Legacy Properties (backward compatibility)
    # ========================================
    
    @property
    def pos_x(self) -> float:
        """X position (0.0-1.0) - legacy access"""
        return self._pos.x
    
    @pos_x.setter
    def pos_x(self, value: float):
        """Set X position with clamping - legacy access"""
        self._pos = Vec2(max(0.0, min(1.0, float(value))), self._pos.y)
    
    @property
    def pos_y(self) -> float:
        """Y position (0.0-1.0) - legacy access"""
        return self._pos.y
    
    @pos_y.setter
    def pos_y(self, value: float):
        """Set Y position with clamping - legacy access"""
        self._pos = Vec2(self._pos.x, max(0.0, min(1.0, float(value))))
    
    @property
    def scale_x(self) -> float:
        """X scale factor - legacy access"""
        return self._scale.x
    
    @scale_x.setter
    def scale_x(self, value: float):
        """Set X scale factor - legacy access"""
        self._scale = Vec2(float(value), self._scale.y)
    
    @property
    def scale_y(self) -> float:
        """Y scale factor - legacy access"""
        return self._scale.y
    
    @scale_y.setter
    def scale_y(self, value: float):
        """Set Y scale factor - legacy access"""
        self._scale = Vec2(self._scale.x, float(value))
    
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
    
    @property
    def flip_x(self) -> bool:
        """Horizontal flip state"""
        return self._flip_x
    
    @flip_x.setter
    def flip_x(self, value: bool):
        """Set horizontal flip"""
        self._flip_x = bool(value)
    
    @property
    def flip_y(self) -> bool:
        """Vertical flip state"""
        return self._flip_y
    
    @flip_y.setter
    def flip_y(self, value: bool):
        """Set vertical flip"""
        self._flip_y = bool(value)
    
    # ========================================
    # Serialization
    # ========================================
    
    def serialize(self) -> str:
        """Serialize instance to Clausewitz format
        
        Returns:
            Clausewitz-formatted instance block
        """
        # Apply flip to scale (negative scale in CK3 format = flip)
        scale_x = -self._scale.x if self._flip_x else self._scale.x
        scale_y = -self._scale.y if self._flip_y else self._scale.y
        
        lines = []
        lines.append('\t\t\tinstance = {')
        lines.append(f'\t\t\t\tposition = {{ {self._pos.x} {self._pos.y} }}')
        lines.append(f'\t\t\t\tscale = {{ {scale_x} {scale_y} }}')
        
        if self._rotation != 0:
            lines.append(f'\t\t\t\trotation = {self._rotation}')
        
        if self._depth != 0:
            lines.append(f'\t\t\t\tdepth = {self._depth}')
        
        lines.append('\t\t\t}')
        return '\n'.join(lines)
    
    @classmethod
    def parse(cls, data: Dict[str, Any]) -> 'Instance':
        """Parse instance from Clausewitz parser output
        
        Args:
            data: Dict from parser with 'position', 'scale', 'rotation', 'depth'
            
        Returns:
            New Instance object
        """
        # Parse position
        position = data.get('position', [0.5, 0.5])
        pos_x = position[0] if isinstance(position, list) else 0.5
        pos_y = position[1] if isinstance(position, list) and len(position) > 1 else 0.5
        
        # Parse scale (may be negative for flip)
        scale = data.get('scale', [1.0, 1.0])
        scale_x_raw = scale[0] if isinstance(scale, list) else 1.0
        scale_y_raw = scale[1] if isinstance(scale, list) and len(scale) > 1 else 1.0
        
        # Extract flip from scale sign
        flip_x = scale_x_raw < 0
        flip_y = scale_y_raw < 0
        
        return Instance({
            'pos_x': pos_x,
            'pos_y': pos_y,
            'scale_x': abs(scale_x_raw),  # Store as positive
            'scale_y': abs(scale_y_raw),
            'rotation': data.get('rotation', 0),
            'depth': data.get('depth', 0.0),
            'flip_x': flip_x,
            'flip_y': flip_y
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert instance to dictionary for serialization
        
        Returns:
            Dictionary with instance data
        """
        return {
            'pos_x': self._pos.x,
            'pos_y': self._pos.y,
            'scale_x': self._scale.x,
            'scale_y': self._scale.y,
            'rotation': self._rotation,
            'depth': self._depth,
            'flip_x': self._flip_x,
            'flip_y': self._flip_y
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
