"""Symmetry transform plugin system.

Each transform is a self-contained plugin that defines its UI,
calculation logic, and overlay visualization.
"""

from .base_transform import BaseSymmetryTransform
from .bisector_transform import BisectorTransform
from .rotational_transform import RotationalTransform
from .grid_transform import GridTransform

# Registry of available transforms
AVAILABLE_TRANSFORMS = {
    'bisector': BisectorTransform,
    'rotational': RotationalTransform,
    'grid': GridTransform,
}

def get_transform(transform_type: str) -> BaseSymmetryTransform:
    """Get transform instance by type.
    
    Args:
        transform_type: Transform type identifier
        
    Returns:
        Transform instance or None if not found
    """
    transform_class = AVAILABLE_TRANSFORMS.get(transform_type)
    if transform_class:
        return transform_class()
    return None

def get_available_transforms():
    """Get list of available transform types.
    
    Returns:
        List of (name, display_name) tuples
    """
    transforms = []
    for name, cls in AVAILABLE_TRANSFORMS.items():
        instance = cls()
        transforms.append((name, instance.get_display_name()))
    return transforms
