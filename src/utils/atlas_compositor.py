"""
Atlas compositor for dynamic color application to emblems and patterns.

Composites pre-baked atlases with runtime colors for efficient preview generation.
"""

from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor
from PyQt5.QtCore import Qt, QRect
from pathlib import Path
from utils.path_resolver import get_emblem_atlas_dir, get_pattern_atlas_dir


def composite_emblem_atlas(atlas_path: str, colors: dict, background_color: tuple = None, size: int = 64) -> QPixmap:
    """
    Composite an emblem atlas (512x512, 4 quadrants) with colors.
    
    Layering order (back to front):
    1. Solid fill with backgroundColor1 (or background_color param)
    2. Bottom-left quad (b×2 channel) with color1
    3. Top-right quad (g×a channel) with color2
    4. Top-left quad (r×a channel) with color3
    
    Args:
        atlas_path: Path to the 512x512 emblem atlas PNG
        colors: Dict with 'color1', 'color2', 'color3' as (r, g, b) tuples (0-1 range)
        background_color: Optional background color as (r, g, b) tuple (0-1 range)
        size: Output pixmap size (square)
    
    Returns:
        QPixmap with composited emblem
    """
    # Load atlas
    atlas = QImage(atlas_path)
    if atlas.isNull():
        return QPixmap(size, size)
    
    # Extract quadrants (256x256 each)
    top_left = atlas.copy(QRect(0, 0, 256, 256))      # r×a
    top_right = atlas.copy(QRect(256, 0, 256, 256))   # g×a
    bottom_left = atlas.copy(QRect(0, 256, 256, 256)) # b×2
    bottom_right = atlas.copy(QRect(256, 256, 256, 256)) # 1-a (unused for now)
    
    # Create output pixmap
    result = QPixmap(size, size)
    result.fill(Qt.transparent)
    
    painter = QPainter(result)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    
    # Layer 1: Solid background
    bg_color = background_color or colors.get('background1', (0.75, 0.75, 0.75))
    bg_qcolor = QColor(int(bg_color[0] * 255), int(bg_color[1] * 255), int(bg_color[2] * 255))
    painter.fillRect(0, 0, size, size, bg_qcolor)
    
    # Layer 2: Bottom-left quad with color1
    if 'color1' in colors:
        color1 = colors['color1']
        c1_qcolor = QColor(int(color1[0] * 255), int(color1[1] * 255), int(color1[2] * 255))
        # Create colored layer with bottom-left alpha mask
        colored_layer = QImage(256, 256, QImage.Format_ARGB32)
        colored_layer.fill(c1_qcolor)
        # Apply alpha from bottom-left quad
        layer_painter = QPainter(colored_layer)
        layer_painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        layer_painter.drawImage(0, 0, bottom_left)
        layer_painter.end()
        # Draw to result
        painter.drawImage(QRect(0, 0, size, size), colored_layer)
    
    # Layer 3: Top-right quad with color2
    if 'color2' in colors:
        color2 = colors['color2']
        c2_qcolor = QColor(int(color2[0] * 255), int(color2[1] * 255), int(color2[2] * 255))
        colored_layer = QImage(256, 256, QImage.Format_ARGB32)
        colored_layer.fill(c2_qcolor)
        layer_painter = QPainter(colored_layer)
        layer_painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        layer_painter.drawImage(0, 0, top_right)
        layer_painter.end()
        painter.drawImage(QRect(0, 0, size, size), colored_layer)
    
    # Layer 4: Top-left quad with color3
    if 'color3' in colors:
        color3 = colors['color3']
        c3_qcolor = QColor(int(color3[0] * 255), int(color3[1] * 255), int(color3[2] * 255))
        colored_layer = QImage(256, 256, QImage.Format_ARGB32)
        colored_layer.fill(c3_qcolor)
        layer_painter = QPainter(colored_layer)
        layer_painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        layer_painter.drawImage(0, 0, top_left)
        layer_painter.end()
        painter.drawImage(QRect(0, 0, size, size), colored_layer)
    
    painter.end()
    return result


def composite_pattern_atlas(atlas_path: str, background_colors: dict, size: tuple = (64, 32)) -> QPixmap:
    """
    Composite a pattern atlas (512x256, 2 tiles) with background colors.
    
    Layering order (back to front):
    1. Solid fill with backgroundColor1
    2. Left tile (green channel) with backgroundColor2
    3. Right tile (blue channel) with backgroundColor3
    
    Args:
        atlas_path: Path to the 512x256 pattern atlas PNG
        background_colors: Dict with 'background1', 'background2', 'background3' as (r, g, b) tuples (0-1 range)
        size: Output pixmap size as (width, height)
    
    Returns:
        QPixmap with composited pattern
    """
    # Load atlas
    atlas = QImage(atlas_path)
    if atlas.isNull():
        return QPixmap(size[0], size[1])
    
    # Extract tiles (256x256 each)
    left_tile = atlas.copy(QRect(0, 0, 256, 256))    # green channel
    right_tile = atlas.copy(QRect(256, 0, 256, 256)) # blue channel
    
    # Create output pixmap
    result = QPixmap(size[0], size[1])
    result.fill(Qt.transparent)
    
    painter = QPainter(result)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    
    # Layer 1: Solid background with backgroundColor1
    bg1 = background_colors.get('background1', (0.75, 0.75, 0.75))
    bg1_qcolor = QColor(int(bg1[0] * 255), int(bg1[1] * 255), int(bg1[2] * 255))
    painter.fillRect(0, 0, size[0], size[1], bg1_qcolor)
    
    # Layer 2: Left tile with backgroundColor2
    if 'background2' in background_colors:
        bg2 = background_colors['background2']
        bg2_qcolor = QColor(int(bg2[0] * 255), int(bg2[1] * 255), int(bg2[2] * 255))
        colored_layer = QImage(256, 256, QImage.Format_ARGB32)
        colored_layer.fill(bg2_qcolor)
        layer_painter = QPainter(colored_layer)
        layer_painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        layer_painter.drawImage(0, 0, left_tile)
        layer_painter.end()
        painter.drawImage(QRect(0, 0, size[0], size[1]), colored_layer)
    
    # Layer 3: Right tile with backgroundColor3
    if 'background3' in background_colors:
        bg3 = background_colors['background3']
        bg3_qcolor = QColor(int(bg3[0] * 255), int(bg3[1] * 255), int(bg3[2] * 255))
        colored_layer = QImage(256, 256, QImage.Format_ARGB32)
        colored_layer.fill(bg3_qcolor)
        layer_painter = QPainter(colored_layer)
        layer_painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        layer_painter.drawImage(0, 0, right_tile)
        layer_painter.end()
        painter.drawImage(QRect(0, 0, size[0], size[1]), colored_layer)
    
    painter.end()
    return result


def get_atlas_path(asset_name: str, asset_type: str) -> Path:
    """
    Get the atlas path for an asset.
    
    Args:
        asset_name: Name of the asset (e.g., 'ce_boar_head.dds' or 'pattern_solid.dds')
        asset_type: Either 'emblem' or 'pattern'
    
    Returns:
        Path to the atlas file
    """
    if asset_type == 'emblem':
        # Convert ce_boar_head.dds -> ce_boar_head_atlas.png
        atlas_name = Path(asset_name).stem + '_atlas.png'
        return get_emblem_atlas_dir() / atlas_name
    elif asset_type == 'pattern':
        # Convert pattern_solid.dds -> pattern_solid_atlas.png
        atlas_name = Path(asset_name).stem + '_atlas.png'
        return get_pattern_atlas_dir() / atlas_name
    else:
        raise ValueError(f"Unknown asset type: {asset_type}")
