"""Transform widget handle system - ABC-based handle architecture.

Each handle type is a class that knows:
- How to draw itself
- How to test if a mouse position hits it
- What its abstract position is (normalized coordinates)
"""

from abc import ABC, abstractmethod
from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QTransform
import math


class Handle(ABC):
    """Abstract base class for transform handles."""
    
    @abstractmethod
    def hit_test(self, mouse_x, mouse_y, center_x, center_y, half_w, half_h, rotation) -> bool:
        """Test if mouse position hits this handle.
        
        Args:
            mouse_x, mouse_y: Mouse position in widget pixel coordinates
            center_x, center_y: AABB center in widget pixels
            half_w, half_h: AABB half-dimensions in pixels
            rotation: Rotation in degrees
            
        Returns:
            bool: True if mouse hits this handle
        """
        pass
    
    @abstractmethod
    def draw(self, painter, center_x, center_y, half_w, half_h, rotation):
        """Draw this handle.
        
        Args:
            painter: QPainter instance
            center_x, center_y: AABB center in widget pixels
            half_w, half_h: AABB half-dimensions in pixels
            rotation: Rotation in degrees
        """
        pass
    
    @abstractmethod
    def drag(self, mouse_x, mouse_y, start_mouse_x, start_mouse_y, 
             start_transform, modifiers):
        """Handle drag operation for this handle type.
        
        Args:
            mouse_x, mouse_y: Current mouse position in center-origin coordinates
            start_mouse_x, start_mouse_y: Drag start mouse position in center-origin coordinates
            start_transform: Transform object with initial state
            modifiers: Qt keyboard modifiers (for shift/alt behavior)
            
        Returns:
            Transform: Updated transform object
        """
        pass
    
    @abstractmethod
    def get_cursor(self):
        """Get the Qt cursor shape for this handle.
        
        Returns:
            Qt.CursorShape: Cursor to display when hovering over this handle
        """
        pass


class CornerHandle(Handle):
    """Corner handle for diagonal scaling."""
    
    def __init__(self, corner_type, handle_size=8, hit_tolerance=4):
        """
        Args:
            corner_type: 'tl', 'tr', 'bl', 'br'
            handle_size: Visual size of handle in pixels
            hit_tolerance: Extra pixels for hit detection
        """
        self.corner_type = corner_type
        self.handle_size = handle_size
        self.hit_tolerance = hit_tolerance
        
        # Abstract position (normalized to AABB)
        self.norm_x, self.norm_y = {
            'tl': (-1, -1),
            'tr': (1, -1),
            'bl': (-1, 1),
            'br': (1, 1),
        }[corner_type]
    
    def _get_pixel_pos(self, center_x, center_y, half_w, half_h, rotation):
        """Calculate actual pixel position from abstract position."""
        # Local position relative to AABB (no rotation - axis-aligned)
        local_x = self.norm_x * half_w
        local_y = self.norm_y * half_h
        
        # Translate to widget space (no rotation applied)
        return center_x + local_x, center_y + local_y
    
    def hit_test(self, mouse_x, mouse_y, center_x, center_y, half_w, half_h, rotation):
        px, py = self._get_pixel_pos(center_x, center_y, half_w, half_h, rotation)
        dx = mouse_x - px
        dy = mouse_y - py
        distance = math.sqrt(dx*dx + dy*dy)
        return distance <= (self.handle_size + self.hit_tolerance)
    
    def draw(self, painter, center_x, center_y, half_w, half_h, rotation):
        px, py = self._get_pixel_pos(center_x, center_y, half_w, half_h, rotation)
        
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.setBrush(QBrush(QColor(90, 141, 191)))
        painter.drawEllipse(QPointF(px, py), float(self.handle_size), float(self.handle_size))
    
    def drag(self, mouse_x, mouse_y, start_mouse_x, start_mouse_y, 
             start_transform, modifiers):
        """Uniform diagonal scaling - maintains aspect ratio."""
        from PyQt5.QtCore import Qt
        from models.transform import Transform, Vec2
        
        alt_pressed = modifiers and (modifiers & Qt.AltModifier)
        
        # Determine anchor point (opposite corner)
        if alt_pressed:
            # Alt: anchor opposite corner
            anchor_map = {
                'tl': (start_transform.pos.x + start_transform.scale.x, start_transform.pos.y + start_transform.scale.y),
                'tr': (start_transform.pos.x - start_transform.scale.x, start_transform.pos.y + start_transform.scale.y),
                'bl': (start_transform.pos.x + start_transform.scale.x, start_transform.pos.y - start_transform.scale.y),
                'br': (start_transform.pos.x - start_transform.scale.x, start_transform.pos.y - start_transform.scale.y)
            }
            anchor_x, anchor_y = anchor_map[self.corner_type]
            
            # Distance from anchor
            curr_dist = math.sqrt((mouse_x - anchor_x)**2 + (mouse_y - anchor_y)**2)
            start_dist = math.sqrt((start_mouse_x - anchor_x)**2 + (start_mouse_y - anchor_y)**2)
            
            if start_dist > 0:
                scale_factor = curr_dist / start_dist
                new_hw = start_transform.scale.x * scale_factor
                new_hh = start_transform.scale.y * scale_factor
                # Reposition center to keep anchor fixed
                new_cx = anchor_x + (start_transform.pos.x - anchor_x) * scale_factor
                new_cy = anchor_y + (start_transform.pos.y - anchor_y) * scale_factor
                return Transform(Vec2(new_cx, new_cy), Vec2(new_hw, new_hh), start_transform.rotation)
        else:
            # Normal: scale from center
            start_dist = math.sqrt((start_mouse_x - start_transform.pos.x)**2 + (start_mouse_y - start_transform.pos.y)**2)
            curr_dist = math.sqrt((mouse_x - start_transform.pos.x)**2 + (mouse_y - start_transform.pos.y)**2)
            
            if start_dist > 0:
                scale_factor = curr_dist / start_dist
                new_hw = start_transform.scale.x * scale_factor
                new_hh = start_transform.scale.y * scale_factor
                return Transform(start_transform.pos, Vec2(new_hw, new_hh), start_transform.rotation)
        
        # Fallback: no change
        return start_transform
    
    def get_cursor(self):
        """Diagonal resize cursor for corner handles."""
        return Qt.SizeFDiagCursor


class EdgeHandle(Handle):
    """Edge handle for single-axis scaling."""
    
    def __init__(self, edge_type, handle_size=8, hit_tolerance=4):
        """
        Args:
            edge_type: 't', 'r', 'b', 'l'
            handle_size: Visual size of handle in pixels
            hit_tolerance: Extra pixels for hit detection
        """
        self.edge_type = edge_type
        self.handle_size = handle_size
        self.hit_tolerance = hit_tolerance
        
        # Abstract position (normalized to AABB)
        self.norm_x, self.norm_y = {
            't': (0, -1),
            'r': (1, 0),
            'b': (0, 1),
            'l': (-1, 0),
        }[edge_type]
    
    def _get_pixel_pos(self, center_x, center_y, half_w, half_h, rotation):
        """Calculate actual pixel position from abstract position."""
        local_x = self.norm_x * half_w
        local_y = self.norm_y * half_h
        
        # No rotation applied - keep edges axis-aligned
        return center_x + local_x, center_y + local_y
    
    def hit_test(self, mouse_x, mouse_y, center_x, center_y, half_w, half_h, rotation):
        px, py = self._get_pixel_pos(center_x, center_y, half_w, half_h, rotation)
        dx = mouse_x - px
        dy = mouse_y - py
        distance = math.sqrt(dx*dx + dy*dy)
        return distance <= (self.handle_size + self.hit_tolerance)
    
    def draw(self, painter, center_x, center_y, half_w, half_h, rotation):
        px, py = self._get_pixel_pos(center_x, center_y, half_w, half_h, rotation)
        
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.setBrush(QBrush(QColor(90, 141, 191)))
        painter.drawRect(int(px - self.handle_size/2), int(py - self.handle_size/2),
                         self.handle_size, self.handle_size)
    
    def drag(self, mouse_x, mouse_y, start_mouse_x, start_mouse_y, 
             start_transform, modifiers):
        """Single-axis scaling - only changes width OR height.
        
        Args:
            start_transform: Transform object with initial state
            
        Returns:
            Transform object with updated state
        """
        from PyQt5.QtCore import Qt
        from models.transform import Transform, Vec2
        
        alt_pressed = modifiers and (modifiers & Qt.AltModifier)
        
        # Determine which axis this edge controls
        if self.edge_type in ['l', 'r']:
            # Left/Right edges scale width
            if alt_pressed:
                # Alt: Anchor opposite edge (left anchors right, right anchors left)
                anchor_x = start_transform.pos.x + start_transform.scale.x if self.edge_type == 'l' else start_transform.pos.x - start_transform.scale.x
                # Center is midpoint between anchor and mouse
                new_cx = (anchor_x + mouse_x) / 2.0
                # Half-width is distance from center to mouse
                new_hw = abs(mouse_x - new_cx)
                return Transform(Vec2(new_cx, start_transform.pos.y), Vec2(new_hw, start_transform.scale.y), start_transform.rotation)
            else:
                # Normal: Scale from center symmetrically
                start_dist = abs(start_mouse_x - start_transform.pos.x)
                curr_dist = abs(mouse_x - start_transform.pos.x)
                if start_dist > 0:
                    new_hw = start_transform.scale.x * (curr_dist / start_dist)
                    return Transform(start_transform.pos, Vec2(new_hw, start_transform.scale.y), start_transform.rotation)
        else:
            # Top/Bottom edges scale height
            if alt_pressed:
                # Alt: Anchor opposite edge (top anchors bottom, bottom anchors top)
                anchor_y = start_transform.pos.y + start_transform.scale.y if self.edge_type == 't' else start_transform.pos.y - start_transform.scale.y
                # Center is midpoint between anchor and mouse
                new_cy = (anchor_y + mouse_y) / 2.0
                # Half-height is distance from center to mouse
                new_hh = abs(mouse_y - new_cy)
                return Transform(Vec2(start_transform.pos.x, new_cy), Vec2(start_transform.scale.x, new_hh), start_transform.rotation)
            else:
                # Normal: Scale from center symmetrically
                start_dist = abs(start_mouse_y - start_transform.pos.y)
                curr_dist = abs(mouse_y - start_transform.pos.y)
                if start_dist > 0:
                    new_hh = start_transform.scale.y * (curr_dist / start_dist)
                    return Transform(start_transform.pos, Vec2(start_transform.scale.x, new_hh), start_transform.rotation)
        
        # Fallback
        return start_transform
    
    def get_cursor(self):
        """Horizontal or vertical resize cursor based on edge orientation."""
        if self.edge_type in ['l', 'r']:
            return Qt.SizeHorCursor
        else:
            return Qt.SizeVerCursor


class RotationHandle(Handle):
    """Rotation handle (circle/dot above bbox)."""
    
    def __init__(self, offset=30, handle_size=8, hit_tolerance=4):
        """
        Args:
            offset: Distance above top edge in pixels
            handle_size: Visual size of handle in pixels
            hit_tolerance: Extra pixels for hit detection
        """
        self.offset = offset
        self.handle_size = handle_size
        self.hit_tolerance = hit_tolerance
    
    def _get_pixel_pos(self, center_x, center_y, half_w, half_h, rotation):
        """Calculate rotation handle position."""
        # Start at top edge (axis-aligned, no rotation)
        local_x = 0
        local_y = -half_h - self.offset
        
        # No rotation applied - keep handle at top of axis-aligned bbox
        return center_x + local_x, center_y + local_y
    
    def hit_test(self, mouse_x, mouse_y, center_x, center_y, half_w, half_h, rotation):
        px, py = self._get_pixel_pos(center_x, center_y, half_w, half_h, rotation)
        dx = mouse_x - px
        dy = mouse_y - py
        distance = math.sqrt(dx*dx + dy*dy)
        return distance <= (self.handle_size + self.hit_tolerance)
    
    def draw(self, painter, center_x, center_y, half_w, half_h, rotation):
        px, py = self._get_pixel_pos(center_x, center_y, half_w, half_h, rotation)
        
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.setBrush(QBrush(QColor(90, 141, 191)))
        painter.drawEllipse(QPointF(px, py), float(self.handle_size), float(self.handle_size))
    
    def drag(self, mouse_x, mouse_y, start_mouse_x, start_mouse_y, 
             start_transform, modifiers):
        """Rotate around center by calculating angle delta."""
        from PyQt5.QtCore import Qt
        from models.transform import Transform
        
        shift_pressed = modifiers and (modifiers & Qt.ShiftModifier)
        
        # Calculate angles from center
        start_angle = math.degrees(math.atan2(start_mouse_y - start_transform.pos.y, start_mouse_x - start_transform.pos.x))
        current_angle = math.degrees(math.atan2(mouse_y - start_transform.pos.y, mouse_x - start_transform.pos.x))
        
        angle_delta = current_angle - start_angle
        new_rot = start_transform.rotation + angle_delta
        
        # Shift: snap to 45-degree increments
        if shift_pressed:
            new_rot = round(new_rot / 45.0) * 45.0
        
        return Transform(start_transform.pos, start_transform.scale, new_rot)
    
    def get_cursor(self):
        """Cross cursor for rotation."""
        return Qt.CrossCursor


class CenterHandle(Handle):
    """Center handle - full AABB hit area for translation."""
    
    def hit_test(self, mouse_x, mouse_y, center_x, center_y, half_w, half_h, rotation):
        """Test if mouse is inside rotated AABB."""
        # Transform mouse to local (unrotated) space
        dx = mouse_x - center_x
        dy = mouse_y - center_y
        
        rad = -math.radians(rotation)  # Inverse rotation
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)
        
        local_x = dx * cos_r - dy * sin_r
        local_y = dx * sin_r + dy * cos_r
        
        # Check if in AABB
        return abs(local_x) <= half_w and abs(local_y) <= half_h
    
    def draw(self, painter, center_x, center_y, half_w, half_h, rotation):
        """Draw axis-aligned bounding box with center X mark."""
        # Draw box without rotation - axis-aligned AABB
        painter.setPen(QPen(QColor(90, 141, 191, 200), 2))
        painter.setBrush(QBrush())
        painter.drawRect(int(center_x - half_w), int(center_y - half_h), 
                         int(half_w * 2), int(half_h * 2))
        
        # Draw center X mark
        x_size = 5  # Size of the X mark
        painter.setPen(QPen(QColor(90, 141, 191, 150), 2))
        painter.drawLine(int(center_x - x_size), int(center_y - x_size),
                         int(center_x + x_size), int(center_y + x_size))
        painter.drawLine(int(center_x - x_size), int(center_y + x_size),
                         int(center_x + x_size), int(center_y - x_size))
    
    def drag(self, mouse_x, mouse_y, start_mouse_x, start_mouse_y, 
             start_transform, modifiers):
        """Translate the entire transform by mouse delta."""
        from models.transform import Transform, Vec2
        
        dx = mouse_x - start_mouse_x
        dy = mouse_y - start_mouse_y
        return Transform(Vec2(start_transform.pos.x + dx, start_transform.pos.y + dy), start_transform.scale, start_transform.rotation)
    
    def get_cursor(self):
        """Move cursor for center/translation."""
        return Qt.SizeAllCursor


class ArrowHandle(Handle):
    """Axis arrow for gimble mode (X or Y axis)."""
    
    def __init__(self, axis, start_offset=15, length=50, head_size=8, hit_tolerance=8):
        """
        Args:
            axis: 'x' or 'y'
            start_offset: Distance from center to arrow start
            length: Arrow shaft length
            head_size: Arrow head triangle size
            hit_tolerance: Hit area width/height
        """
        self.axis = axis
        self.start_offset = start_offset
        self.length = length
        self.head_size = head_size
        self.hit_tolerance = hit_tolerance
    
    def hit_test(self, mouse_x, mouse_y, center_x, center_y, half_w, half_h, rotation):
        """Rectangular hit area along arrow shaft (axis-aligned, no rotation)."""
        # Check hit area in screen space (arrows are axis-aligned)
        if self.axis == 'x':
            # Arrow extends right from center
            start_x = center_x + self.start_offset
            end_x = center_x + self.start_offset + self.length
            in_shaft = (start_x <= mouse_x <= end_x and
                        abs(mouse_y - center_y) <= self.hit_tolerance)
            return in_shaft
        else:  # y axis
            # Arrow extends down from center
            start_y = center_y + self.start_offset
            end_y = center_y + self.start_offset + self.length
            in_shaft = (start_y <= mouse_y <= end_y and
                        abs(mouse_x - center_x) <= self.hit_tolerance)
            return in_shaft
    
    def draw(self, painter, center_x, center_y, half_w, half_h, rotation):
        """Draw axis-aligned arrow with solid triangle tip."""
        from PyQt5.QtGui import QPolygonF
        
        color = QColor(255, 80, 80) if self.axis == 'x' else QColor(80, 255, 80)
        painter.setPen(QPen(color, 3))
        painter.setBrush(QBrush(color))  # Solid fill for arrow head
        
        if self.axis == 'x':
            # X arrow (red, pointing right) - axis-aligned
            start_x = int(center_x + self.start_offset)
            end_x = int(center_x + self.start_offset + self.length)
            y = int(center_y)
            head = int(self.head_size)
            
            # Draw shaft
            painter.drawLine(start_x, y, end_x, y)
            
            # Draw solid triangle arrow head
            arrow_tip = QPolygonF([
                QPointF(end_x, y),                    # Tip
                QPointF(end_x - head, y - head),      # Top
                QPointF(end_x - head, y + head)       # Bottom
            ])
            painter.drawPolygon(arrow_tip)
        else:
            # Y arrow (green, pointing down) - axis-aligned
            start_y = int(center_y + self.start_offset)
            end_y = int(center_y + self.start_offset + self.length)
            x = int(center_x)
            head = int(self.head_size)
            
            # Draw shaft
            painter.drawLine(x, start_y, x, end_y)
            
            # Draw solid triangle arrow head
            arrow_tip = QPolygonF([
                QPointF(x, end_y),                    # Tip
                QPointF(x - head, end_y - head),      # Left
                QPointF(x + head, end_y - head)       # Right
            ])
            painter.drawPolygon(arrow_tip)
    
    def drag(self, mouse_x, mouse_y, start_mouse_x, start_mouse_y, 
             start_transform, modifiers):
        """Axis-constrained translation - X arrow locks Y, Y arrow locks X."""
        from models.transform import Transform, Vec2
        
        dx = mouse_x - start_mouse_x
        dy = mouse_y - start_mouse_y
        
        if self.axis == 'x':
            # X arrow: only move horizontally
            return Transform(Vec2(start_transform.pos.x + dx, start_transform.pos.y), start_transform.scale, start_transform.rotation)
        else:
            # Y arrow: only move vertically
            return Transform(Vec2(start_transform.pos.x, start_transform.pos.y + dy), start_transform.scale, start_transform.rotation)
    
    def get_cursor(self):
        """Horizontal or vertical cursor based on arrow axis."""
        if self.axis == 'x':
            return Qt.SizeHorCursor
        else:
            return Qt.SizeVerCursor


class RingHandle(Handle):
    """Rotation ring for gimble mode."""
    
    def __init__(self, radius=80, hit_tolerance=8):
        """
        Args:
            radius: Ring radius in pixels
            hit_tolerance: Hit area thickness (ring ± tolerance)
        """
        self.radius = radius
        self.hit_tolerance = hit_tolerance
    
    def hit_test(self, mouse_x, mouse_y, center_x, center_y, half_w, half_h, rotation):
        """Annular hit area (ring with tolerance)."""
        dx = mouse_x - center_x
        dy = mouse_y - center_y
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Check if in ring tolerance
        return abs(distance - self.radius) <= self.hit_tolerance
    
    def draw(self, painter, center_x, center_y, half_w, half_h, rotation):
        """Draw rotation ring circle."""
        painter.setPen(QPen(QColor(255, 200, 100), 2))
        painter.setBrush(QBrush())
        painter.drawEllipse(QPointF(center_x, center_y), float(self.radius), float(self.radius))
    
    def drag(self, mouse_x, mouse_y, start_mouse_x, start_mouse_y, 
             start_transform, modifiers):
        """Rotate around center - same behavior as RotationHandle."""
        from PyQt5.QtCore import Qt
        from models.transform import Transform
        
        shift_pressed = modifiers and (modifiers & Qt.ShiftModifier)
        
        # Calculate angles from center
        start_angle = math.degrees(math.atan2(start_mouse_y - start_transform.pos.y, start_mouse_x - start_transform.pos.x))
        current_angle = math.degrees(math.atan2(mouse_y - start_transform.pos.y, mouse_x - start_transform.pos.x))
        
        angle_delta = current_angle - start_angle
        new_rot = start_transform.rotation + angle_delta
        
        # Shift: snap to 45-degree increments
        if shift_pressed:
            new_rot = round(new_rot / 45.0) * 45.0
        
        return Transform(start_transform.pos, start_transform.scale, new_rot)
    
    def get_cursor(self):
        """Cross cursor for rotation ring."""
        return Qt.CrossCursor


class GimbleCenterHandle(Handle):
    """Center dot for gimble mode."""
    
    def __init__(self, dot_radius=6, hit_tolerance=4):
        """
        Args:
            dot_radius: Visual radius of center dot
            hit_tolerance: Extra pixels for hit detection
        """
        self.dot_radius = dot_radius
        self.hit_tolerance = hit_tolerance
    
    def hit_test(self, mouse_x, mouse_y, center_x, center_y, half_w, half_h, rotation):
        """Circular hit area at center."""
        dx = mouse_x - center_x
        dy = mouse_y - center_y
        distance = math.sqrt(dx*dx + dy*dy)
        return distance <= (self.dot_radius + self.hit_tolerance)
    
    def draw(self, painter, center_x, center_y, half_w, half_h, rotation):
        """Draw center dot."""
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setBrush(QBrush(QColor(150, 150, 255)))
        painter.drawEllipse(QPointF(center_x, center_y), float(self.dot_radius), float(self.dot_radius))
    
    def drag(self, mouse_x, mouse_y, start_mouse_x, start_mouse_y, 
             start_cx, start_cy, start_hw, start_hh, start_rot, modifiers):
        """Translate entire transform - same behavior as CenterHandle."""
        dx = mouse_x - start_mouse_x
        dy = mouse_y - start_mouse_y
        return (start_cx + dx, start_cy + dy, start_hw, start_hh, start_rot)
    
    def get_cursor(self):
        """Move cursor for gimble center."""
        return Qt.SizeAllCursor
