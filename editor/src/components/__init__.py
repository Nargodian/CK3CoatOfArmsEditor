"""UI components for Coat of Arms Editor

This package contains all UI components organized into subpackages:
- asset_widgets: Future home for asset browser components
- canvas_widgets: Future home for canvas and rendering components  
- property_sidebar_widgets: Future home for property editing widgets
- transform_widgets: Future home for transform control components

Direct imports for backwards compatibility:
"""

# Import existing top-level components for backwards compatibility
from .asset_sidebar import AssetSidebar
from .canvas_area import CanvasArea
from .canvas_widget_NEW import CoatOfArmsCanvas
from .property_sidebar import PropertySidebar
from .toolbar import create_toolbar
from .transform_widget import TransformWidget

__all__ = [
    'AssetSidebar',
    'CanvasArea',
    'CoatOfArmsCanvas',
    'PropertySidebar',
    'create_toolbar',
    'TransformWidget',
]
