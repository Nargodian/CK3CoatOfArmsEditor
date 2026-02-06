"""Drag context dataclass for transform widget.

Unified drag state management to replace multiple boolean flags.
"""

from dataclasses import dataclass, field


@dataclass
class DragContext:
    """Unified drag state for transform widget interactions.
    
    Replaces fragile boolean flags with single extensible object.
    """
    operation: str  # 'translate', 'scale_corner', 'scale_edge', 'rotate', 'axis_x', 'axis_y'
    modifiers: set = field(default_factory=set)  # {'ctrl', 'alt', 'shift'}
    duplicate_created: bool = False
    is_multi_selection: bool = False
    cached_aabb: tuple = None  # (pos_x, pos_y, scale_x, scale_y) for rotation
    # Future-proof: add fields as needed without breaking existing code
    metadata: dict = field(default_factory=dict)
