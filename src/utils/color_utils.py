"""
CK3 Coat of Arms Editor - Color Utilities

This module provides color conversion and manipulation utilities.

Functions handle conversion between CK3 color names (e.g., "red", "blue")
and RGB tuples/strings, which is needed for CoA serialization and display.
"""

import re


# Official CK3 color definitions from game/common/named_colors/default_colors.txt
# Accurate RGB [0-1] values converted from HSV using color_conversions.txt
COLOR_MAP = {
    'black': [0.100, 0.090, 0.075],
    'blue': [0.080, 0.246, 0.400],
    'blue_dark': [0.030, 0.170, 0.300],
    'blue_light': [0.165, 0.365, 0.550],
    'brown': [0.450, 0.234, 0.117],
    'green': [0.120, 0.300, 0.138],
    'green_light': [0.200, 0.400, 0.220],
    'grey': [0.500, 0.500, 0.500],
    'orange': [0.600, 0.230, 0.000],
    'purple': [0.350, 0.105, 0.252],
    'red': [0.450, 0.133, 0.090],
    'red_dark': [0.300, 0.030, 0.030],
    'white': [0.800, 0.792, 0.784],
    'yellow': [0.750, 0.525, 0.188],
    'yellow_light': [1.000, 0.680, 0.200]
}


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

