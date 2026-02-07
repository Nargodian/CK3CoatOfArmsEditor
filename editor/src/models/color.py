"""
CK3 Coat of Arms Editor - Color Domain Model

Canonical color representation for the entire application.
All color operations flow through this class.
"""

import re
from typing import List, Tuple, Optional
from constants import CK3_NAMED_COLORS, HIGH_CONTRAST_DARK, HIGH_CONTRAST_LIGHT, MIN_COLOR_DISTANCE


class Color:
    """Mutable color representation with uint8 RGB storage and optional name tag.
    
    This is the single source of truth for all color data in the application.
    Internal storage: _r, _g, _b (uint8 0-255), _name (string)
    
    Modifications ONLY through controlled setter methods to maintain name tag invariant:
    - set_float(), set_hex() - clear name to empty string
    - set_name() - preserve name tag
    
    Direct property assignment is discouraged - use setter methods.
    """
    
    def __init__(self, r: int, g: int, b: int, name: str = ""):
        """Direct construction from RGB uint8 values (0-255).
        
        Args:
            r: Red component (0-255)
            g: Green component (0-255)
            b: Blue component (0-255)
            name: Optional color name (for palette colors)
        """
        # Clamp to valid uint8 range
        self._r = max(0, min(255, int(r)))
        self._g = max(0, min(255, int(g)))
        self._b = max(0, min(255, int(b)))
        self._name = name
    
    @property
    def r(self) -> int:
        """Red component (0-255) - READ ONLY"""
        return self._r
    
    @property
    def g(self) -> int:
        """Green component (0-255) - READ ONLY"""
        return self._g
    
    @property
    def b(self) -> int:
        """Blue component (0-255) - READ ONLY"""
        return self._b
    
    @property
    def name(self) -> str:
        """Color name (empty string for custom colors) - READ ONLY"""
        return self._name
    
    # ========================================
    # Setter Methods (controlled mutation with name tag management)
    # ========================================
    
    def set_float(self, r: float, g: float, b: float) -> None:
        """Set color from normalized float RGB [0-1]. Clears name tag.
        
        Args:
            r: Red component (0-1)
            g: Green component (0-1)
            b: Blue component (0-1)
        """
        self._r = max(0, min(255, int(round(r * 255))))
        self._g = max(0, min(255, int(round(g * 255))))
        self._b = max(0, min(255, int(round(b * 255))))
        self._name = ""  # Custom color - clear name
    
    def set_hex(self, hex_string: str) -> bool:
        """Set color from hex string RRGGBB or #RRGGBB. Clears name tag.
        
        Args:
            hex_string: Hex color string with or without leading #
            
        Returns:
            True if parse succeeded, False otherwise
        """
        if not isinstance(hex_string, str):
            return False
        
        # Strip leading # if present
        hex_string = hex_string.lstrip('#')
        
        # Must be 6 hex digits
        if len(hex_string) != 6:
            return False
        
        try:
            self._r = int(hex_string[0:2], 16)
            self._g = int(hex_string[2:4], 16)
            self._b = int(hex_string[4:6], 16)
            self._name = ""  # Custom color - clear name
            return True
        except ValueError:
            return False
    
    def set_name(self, color_name: str) -> bool:
        """Set color from CK3 named color or rgb format. Preserves name if palette color.
        
        Args:
            color_name: CK3 color name or rgb format string
            
        Returns:
            True if color was set, False otherwise
        """
        # Check if it's a custom rgb color
        if isinstance(color_name, str) and color_name.strip().startswith('rgb'):
            match = re.search(r'rgb\s*\{\s*(\d+)\s+(\d+)\s+(\d+)\s*\}', color_name)
            if match:
                self._r = max(0, min(255, int(match.group(1))))
                self._g = max(0, min(255, int(match.group(2))))
                self._b = max(0, min(255, int(match.group(3))))
                self._name = ""  # Custom RGB - no name
                return True
            return False
        
        # Look up named color from palette
        if color_name in CK3_NAMED_COLORS:
            rgb_float = CK3_NAMED_COLORS[color_name]['rgb']
            self._r = int(rgb_float[0] * 255)
            self._g = int(rgb_float[1] * 255)
            self._b = int(rgb_float[2] * 255)
            self._name = color_name  # Preserve palette name
            return True
        
        return False
    
    def set_rgb255(self, r: int, g: int, b: int) -> None:
        """Set color from RGB uint8 values (0-255). Clears name tag.
        
        Args:
            r: Red component (0-255)
            g: Green component (0-255)
            b: Blue component (0-255)
        """
        self._r = max(0, min(255, int(r)))
        self._g = max(0, min(255, int(g)))
        self._b = max(0, min(255, int(b)))
        self._name = ""  # Custom color - clear name
    
    # ========================================
    # Output Methods
    # ========================================
    
    def to_float3(self) -> List[float]:
        """Convert to normalized float RGB [0-1] for OpenGL/rendering.
        
        Returns:
            List of [r, g, b] in 0-1 range
        """
        return [self._r / 255.0, self._g / 255.0, self._b / 255.0]
    
    def to_tuple_float3(self) -> Tuple[float, float, float]:
        """Convert to normalized float RGB tuple (0-1) for OpenGL/rendering.
        
        Returns:
            Tuple of (r, g, b) in 0-1 range
        """
        return (self._r / 255.0, self._g / 255.0, self._b / 255.0)
    
    def to_ck3_string(self, force_rgb: bool = False) -> str:
        """Convert to CK3 game format - name or rgb format.
        
        If this color has a name (palette color) and force_rgb is False,
        returns the name. Otherwise returns RGB format.
        
        Args:
            force_rgb: If True, always output RGB format even if named
            
        Returns:
            Color name string or rgb format string
        """
        if self._name and not force_rgb:
            return self._name
        return f"rgb {{ {self._r} {self._g} {self._b} }}"
    
    def to_hex(self) -> str:
        """Convert to hex color string: #RRGGBB.
        
        Returns:
            Hex color string with leading #
        """
        return f"#{self._r:02X}{self._g:02X}{self._b:02X}"
    def to_qcolor(self):
        """Convert to PyQt5 QColor object.
        
        Returns:
            QColor: Qt color object for UI rendering
        """
        from PyQt5.QtGui import QColor
        return QColor(self._r, self._g, self._b)
    def to_rgb255(self) -> List[int]:
        """Convert to RGB uint8 list [0-255].
        
        Returns:
            List of [r, g, b] in 0-255 range
        """
        return [self._r, self._g, self._b]
    
    # ========================================
    # Static Factory Methods
    # ========================================
    
    @staticmethod
    def from_name(color_name: str) -> 'Color':
        """Create Color from CK3 named color or RGB string.
        
        Handles both named colors (red, blue) and RGB strings.
        Falls back to white if color not found.
        Preserves name tag for palette colors.
        
        Args:
            color_name: CK3 color name or rgb format string
            
        Returns:
            Color object
        """
        # Check if it's a custom rgb color
        if isinstance(color_name, str) and color_name.strip().startswith('rgb'):
            match = re.search(r'rgb\s*\{\s*(\d+)\s+(\d+)\s+(\d+)\s*\}', color_name)
            if match:
                r = int(match.group(1))
                g = int(match.group(2))
                b = int(match.group(3))
                return Color(r, g, b, name="")  # Custom RGB - no name
        
        # Look up named color from palette
        if color_name in CK3_NAMED_COLORS:
            rgb_float = CK3_NAMED_COLORS[color_name]['rgb']
            r = int(rgb_float[0] * 255)
            g = int(rgb_float[1] * 255)
            b = int(rgb_float[2] * 255)
            return Color(r, g, b, name=color_name)  # Preserve palette name
        
        # Fallback to white
        return Color(255, 255, 255, name="white")
    
    @staticmethod
    def from_ck3_string(ck3_string: str) -> Optional['Color']:
        """Create Color from CK3 RGB string format.
        
        Args:
            ck3_string: String in rgb format
            
        Returns:
            Color object if parse succeeds, None otherwise
        """
        if not isinstance(ck3_string, str):
            return None
        
        match = re.search(r'rgb\s*\{\s*(\d+)\s+(\d+)\s+(\d+)\s*\}', ck3_string)
        if match:
            r = int(match.group(1))
            g = int(match.group(2))
            b = int(match.group(3))
            return Color(r, g, b, name="")
        
        return None
    
    @staticmethod
    def from_hex(hex_string: str) -> Optional['Color']:
        """Create Color from hex string: #RRGGBB or RRGGBB.
        
        Args:
            hex_string: Hex color string with or without leading #
            
        Returns:
            Color object if parse succeeds, None otherwise
        """
        if not isinstance(hex_string, str):
            return None
        
        # Strip leading # if present
        hex_string = hex_string.lstrip('#')
        
        # Must be 6 hex digits
        if len(hex_string) != 6:
            return None
        
        try:
            r = int(hex_string[0:2], 16)
            g = int(hex_string[2:4], 16)
            b = int(hex_string[4:6], 16)
            return Color(r, g, b, name="")
        except ValueError:
            return None
    
    @staticmethod
    def from_float3(rgb_float: List[float]) -> 'Color':
        """Create Color from normalized float RGB [0-1].
        
        Args:
            rgb_float: List of [r, g, b] in 0-1 range
            
        Returns:
            Color object
        """
        r = int(round(rgb_float[0] * 255))
        g = int(round(rgb_float[1] * 255))
        b = int(round(rgb_float[2] * 255))
        return Color(r, g, b, name="")
    
    @staticmethod
    def from_rgb255(r: int, g: int, b: int) -> 'Color':
        """Create Color from RGB uint8 values (0-255).
        
        This is just an alias for the constructor for consistency with other factory methods.
        No name tag (custom color).
        
        Args:
            r: Red component (0-255)
            g: Green component (0-255)
            b: Blue component (0-255)
            
        Returns:
            Color object
        """
        return Color(r, g, b, name="")
    
    # ========================================
    # Color Operations
    # ========================================
    
    def get_contrasting_background(self, background_color: 'Color') -> 'Color':
        """Get contrasting background color for this emblem color.
        
        Calculates color distance between emblem and background.
        If too similar (distance < threshold), returns high contrast fallback:
        - Dark emblems get white background
        - Light emblems get black background
        
        Args:
            background_color: Background Color to test against
            
        Returns:
            Color object - either background_color or high contrast fallback
        """
        # Convert to 0-1 range for distance calculation
        emblem_float = self.to_float3()
        bg_float = background_color.to_float3()
        
        # Calculate Euclidean distance in RGB space
        dist = sum((emblem_float[i] - bg_float[i]) ** 2 for i in range(3)) ** 0.5
        
        # If colors are too similar, use high contrast fallback
        if dist < MIN_COLOR_DISTANCE:
            # Calculate brightness of emblem (luminance)
            brightness = 0.299 * emblem_float[0] + 0.587 * emblem_float[1] + 0.114 * emblem_float[2]
            
            # Dark emblem - white background, light emblem - black background
            if brightness < 0.5:
                return Color.from_float3(HIGH_CONTRAST_LIGHT)
            else:
                return Color.from_float3(HIGH_CONTRAST_DARK)
        else:
            # Colors are different enough, use actual background color
            return background_color
    
    # ========================================
    # Equality and Hashing
    # ========================================
    
    def __eq__(self, other) -> bool:
        """Test equality based on RGB values."""
        if not isinstance(other, Color):
            return False
        return self._r == other._r and self._g == other._g and self._b == other._b and self._name == other._name
    
    def __hash__(self) -> int:
        """Hash based on RGB values for use in dicts/sets."""
        return hash((self._r, self._g, self._b))
    
    def __repr__(self) -> str:
        """Debug representation."""
        return f"Color({self._r}, {self._g}, {self._b})"
    
    def __str__(self) -> str:
        """String representation - uses hex format."""
        return self.to_hex()
