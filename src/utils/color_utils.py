"""
CK3 Coat of Arms Editor - Color Utilities

This module provides color conversion and manipulation utilities.

Functions handle conversion between CK3 color names (e.g., "red", "blue")
and RGB tuples/strings, which is needed for CoA serialization and display.
"""

import re
import sys
from pathlib import Path

# Add src directory to path for imports
src_dir = Path(__file__).resolve().parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from constants import CK3_NAMED_COLORS

# Build COLOR_MAP from constants for backward compatibility
COLOR_MAP = {name: data['rgb'] for name, data in CK3_NAMED_COLORS.items()}


def color_name_to_rgb(color_name):
    """Convert CK3 color name to RGB [0-1]
    
    Uses accurate color values extracted from CK3's default_colors.txt
    and converted from HSV to RGB. See docs/specifications/color_conversions.txt
    for complete conversion reference.
    
    Args:
        color_name: Color name string or "rgb { R G B }" format
        
    Returns:
        List of RGB values in [0-1] range: [r, g, b]
    """
    # Check if it's an rgb { R G B } custom color
    if isinstance(color_name, str) and color_name.startswith('rgb'):
        # Parse "rgb { 74 201 202 }" format
        match = re.search(r'rgb\s*\{\s*(\d+)\s+(\d+)\s+(\d+)\s*\}', color_name)
        if match:
            r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
            return [r / 255.0, g / 255.0, b / 255.0]
    
    return COLOR_MAP.get(color_name, [1.0, 1.0, 1.0])


def rgb_to_color_name(rgb, color_name=None):
    """Convert RGB [0-1] to CK3 color format
    
    If color_name is provided (from swatch), use the name.
    Otherwise (from color picker), output rgb { R G B } format.
    
    Args:
        rgb: List of RGB values in [0-1] range: [r, g, b]
        color_name: Optional named color string from swatch selection
        
    Returns:
        Color name string or "rgb { R G B }" format string
    """
    if not rgb:
        return 'white'
    
    # If we have a named color (from swatch), use it
    if color_name:
        return color_name
    
    # Otherwise output custom RGB format (from color picker)
    r, g, b = rgb[0], rgb[1], rgb[2]
    r_int = int(round(r * 255))
    g_int = int(round(g * 255))
    b_int = int(round(b * 255))
    return f"rgb {{ {r_int} {g_int} {b_int} }}"


def parse_rgb_string(rgb_string):
    """Parse "rgb { R G B }" format to RGB [0-1]
    
    Args:
        rgb_string: String in "rgb { R G B }" format
        
    Returns:
        List of RGB values in [0-1] range: [r, g, b], or None if parse fails
    """
    if not isinstance(rgb_string, str):
        return None
        
    match = re.search(r'rgb\s*\{\s*(\d+)\s+(\d+)\s+(\d+)\s*\}', rgb_string)
    if match:
        r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return [r / 255.0, g / 255.0, b / 255.0]
    
    return None

