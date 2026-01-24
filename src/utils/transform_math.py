"""
CK3 Coat of Arms Editor - Transform Math Utilities

This module provides mathematical functions for coordinate transformations
and geometry calculations used in layer manipulation.

These pure math functions handle coordinate system conversions and geometric
calculations without any UI dependencies.
"""

import math


def screen_to_normalized(x, y, width, height, canvas_scale=1.1):
    """Convert screen pixel coordinates to normalized [0-1] coordinate space
    
    The canvas uses a coordinate system where:
    - center is at (0.5, 0.5) in normalized space
    - coordinates are scaled by canvas_scale (default 1.1)
    - viewport size determines the pixel-to-normalized conversion
    
    Args:
        x: Screen X coordinate in pixels
        y: Screen Y coordinate in pixels  
        width: Viewport width in pixels
        height: Viewport height in pixels
        canvas_scale: Canvas scaling factor (default 1.1)
        
    Returns:
        Tuple of (nx, ny) normalized coordinates in [0-1] range
    """
    size = min(width, height)
    # OpenGL normalized space: 1 unit = size/2 pixels
    pixel_scale = canvas_scale * (size / 2)
    
    # Convert pixel offset from center to normalized offset
    center_x = width / 2
    center_y = height / 2
    offset_x = (x - center_x) / pixel_scale
    offset_y = (y - center_y) / pixel_scale
    
    # Convert to [0-1] space (add 0.5 to center at 0.5)
    nx = 0.5 + offset_x
    ny = 0.5 + offset_y
    
    return nx, ny


def normalized_to_screen(nx, ny, width, height, canvas_scale=1.1):
    """Convert normalized [0-1] coordinates to screen pixel coordinates
    
    Inverse of screen_to_normalized. Converts from the normalized coordinate
    system back to screen pixel coordinates.
    
    Args:
        nx: Normalized X coordinate in [0-1] range
        ny: Normalized Y coordinate in [0-1] range
        width: Viewport width in pixels
        height: Viewport height in pixels
        canvas_scale: Canvas scaling factor (default 1.1)
        
    Returns:
        Tuple of (x, y) screen coordinates in pixels
    """
    size = min(width, height)
    pixel_scale = canvas_scale * (size / 2)
    
    # Convert from [0-1] to centered offset
    offset_x = (nx - 0.5)
    offset_y = (ny - 0.5)
    
    # Scale to pixels and add center offset
    center_x = width / 2
    center_y = height / 2
    x = center_x + (offset_x * pixel_scale)
    y = center_y + (offset_y * pixel_scale)
    
    return x, y


def calculate_transform_center(pos_x, pos_y, width, height, canvas_scale=1.1):
    """Calculate the screen-space center point for a transform
    
    Helper function to get the center point in screen pixels for
    a transform at normalized position (pos_x, pos_y).
    
    Args:
        pos_x: Normalized X position in [0-1] range
        pos_y: Normalized Y position in [0-1] range
        width: Viewport width in pixels
        height: Viewport height in pixels
        canvas_scale: Canvas scaling factor (default 1.1)
        
    Returns:
        Tuple of (center_x, center_y) in screen pixels
    """
    size = min(width, height)
    offset_x = (width - size) / 2
    offset_y = (height - size) / 2
    
    canvas_x = (pos_x - 0.5) * canvas_scale * (size / 2)
    canvas_y = (pos_y - 0.5) * canvas_scale * (size / 2)
    
    center_x = offset_x + size / 2 + canvas_x
    center_y = offset_y + size / 2 + canvas_y
    
    return center_x, center_y


def calculate_bounds(pos_x, pos_y, scale_x, scale_y, rotation, base_width, base_height):
    """Calculate axis-aligned bounding box for a transformed rectangle
    
    Computes the AABB of a rectangle after applying scale and rotation transforms.
    Returns the bounds in normalized coordinate space.
    
    Args:
        pos_x: Normalized center X position in [0-1] range
        pos_y: Normalized center Y position in [0-1] range
        scale_x: X scale factor
        scale_y: Y scale factor
        rotation: Rotation in degrees
        base_width: Base width of the rectangle before transform
        base_height: Base height of the rectangle before transform
        
    Returns:
        Tuple of (min_x, min_y, max_x, max_y) in normalized [0-1] space
    """
    # Calculate half-extents after scaling
    half_w = (base_width * abs(scale_x)) / 2
    half_h = (base_height * abs(scale_y)) / 2
    
    # Get the four corners of the rectangle before rotation
    corners = [
        (-half_w, -half_h),
        (half_w, -half_h),
        (-half_w, half_h),
        (half_w, half_h)
    ]
    
    # Rotate corners
    rad = math.radians(rotation)
    cos_r = math.cos(rad)
    sin_r = math.sin(rad)
    
    rotated_corners = []
    for cx, cy in corners:
        rx = cx * cos_r - cy * sin_r
        ry = cx * sin_r + cy * cos_r
        rotated_corners.append((rx, ry))
    
    # Find min/max to get AABB
    xs = [c[0] for c in rotated_corners]
    ys = [c[1] for c in rotated_corners]
    
    min_x = pos_x + min(xs)
    max_x = pos_x + max(xs)
    min_y = pos_y + min(ys)
    max_y = pos_y + max(ys)
    
    return min_x, min_y, max_x, max_y


def constrain_aspect_ratio(scale_x, scale_y, maintain_sign=True):
    """Constrain scale values to maintain aspect ratio (uniform scaling)
    
    Takes potentially non-uniform scale values and returns uniform scale
    based on the larger absolute scale value.
    
    Args:
        scale_x: X scale factor
        scale_y: Y scale factor
        maintain_sign: If True, preserve the sign of each component
        
    Returns:
        Tuple of (constrained_scale_x, constrained_scale_y)
    """
    # Use the larger absolute scale
    abs_scale = max(abs(scale_x), abs(scale_y))
    
    if maintain_sign:
        # Preserve sign for each axis (allows negative scaling/flipping)
        sign_x = 1 if scale_x >= 0 else -1
        sign_y = 1 if scale_y >= 0 else -1
        return abs_scale * sign_x, abs_scale * sign_y
    else:
        # Both axes get the same scale
        return abs_scale, abs_scale


def pixel_delta_to_normalized(dx, dy, width, height, canvas_scale=1.1):
    """Convert a pixel delta to normalized coordinate delta
    
    Helper for converting mouse drag distances from pixels to normalized space.
    
    Args:
        dx: X delta in pixels
        dy: Y delta in pixels
        width: Viewport width in pixels
        height: Viewport height in pixels
        canvas_scale: Canvas scaling factor (default 1.1)
        
    Returns:
        Tuple of (delta_nx, delta_ny) in normalized space
    """
    size = min(width, height)
    pixel_scale = canvas_scale * (size / 2)
    
    delta_nx = dx / pixel_scale
    delta_ny = dy / pixel_scale
    
    return delta_nx, delta_ny


def angle_between_points(x1, y1, x2, y2):
    """Calculate angle in degrees from point 1 to point 2
    
    Args:
        x1, y1: First point coordinates
        x2, y2: Second point coordinates
        
    Returns:
        Angle in degrees
    """
    return math.degrees(math.atan2(y2 - y1, x2 - x1))

