"""
CK3 Coat of Arms Editor - Transform Widget Components

This package contains the refactored transform widget architecture:
- handles.py: ABC-based handle classes (CornerHandle, EdgeHandle, etc.)
- modes.py: Mode classes defining handle sets (BboxMode, GimbleMode, etc.)
- drag_context.py: Unified drag state management
"""

from .handles import (
    Handle, CornerHandle, EdgeHandle, RotationHandle,
    CenterHandle, ArrowHandle, RingHandle, GimbleCenterHandle
)
from .modes import TransformMode, BboxMode, MinimalBboxMode, GimbleMode, create_mode
from .drag_context import DragContext

__all__ = [
    'Handle', 'CornerHandle', 'EdgeHandle', 'RotationHandle',
    'CenterHandle', 'ArrowHandle', 'RingHandle', 'GimbleCenterHandle',
    'TransformMode', 'BboxMode', 'MinimalBboxMode', 'GimbleMode', 'create_mode',
    'DragContext',
]
