"""Transform data structures for coordinate and state representation."""
from dataclasses import dataclass


@dataclass
class Vec2:
    """2D vector for coordinate pairs.
    
    Used for any x/y coordinate pair across different spaces:
    - Canvas pixels (top-left or center-origin)
    - Normalized coordinates (0-1 or ±1)
    - CoA space positions
    """
    x: float
    y: float
    
    def __iter__(self):
        """Allow tuple unpacking: x, y = vec2"""
        return iter((self.x, self.y))


@dataclass
class Transform:
    """Transform state: position, scale, rotation, and flip.
    
    Used across coordinate spaces:
    - Widget space: pos in pixels (center-origin), scale in pixels (half-dimensions)
    - CoA space: pos in 0-1 normalized, scale in 0-1 normalized
    """
    pos: Vec2
    scale: Vec2
    rotation: float = 0.0
    flip_x: bool = False
    flip_y: bool = False
