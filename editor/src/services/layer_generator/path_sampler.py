"""SVG path sampling service for shape-based instance generation.

Loads SVG files, discretizes paths into polylines, and provides efficient
point sampling along paths for positioning instances.
"""

import numpy as np
import xml.etree.ElementTree as ET
from typing import List, Tuple

try:
    from svgpathtools import parse_path, Path, Line, CubicBezier, QuadraticBezier, Arc
    SVG_TOOLS_AVAILABLE = True
except ImportError:
    SVG_TOOLS_AVAILABLE = False


class PathSampler:
    """Samples points along an SVG path with tangent angles.
    
    Converts SVG path data to discretized polylines and provides efficient
    sampling of evenly-spaced points along the path using length-based queries.
    """
    
    # Resolution for discretizing curves (points per unit length)
    CURVE_RESOLUTION = 50
    
    def __init__(self, svg_filepath: str):
        """Load and discretize SVG path.
        
        Args:
            svg_filepath: Path to SVG file
            
        Raises:
            FileNotFoundError: If SVG file doesn't exist
            ValueError: If SVG parsing fails or no paths found
            ImportError: If svgpathtools is not installed
        """
        if not SVG_TOOLS_AVAILABLE:
            raise ImportError("svgpathtools library is required. Install with: pip install svgpathtools")
        
        self.points = []  # List of (x, y) tuples
        self.cumulative_lengths = []  # Cumulative distance at each point
        self.total_length = 0.0
        
        self._load_svg(svg_filepath)
        self._calculate_lengths()
    
    def _load_svg(self, filepath: str):
        """Parse SVG file and extract top-level path data."""
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            # Handle SVG namespace
            ns = {'svg': 'http://www.w3.org/2000/svg'}
            paths = root.findall('./svg:path', ns)
            if not paths:
                # Try without namespace
                paths = root.findall('./path')
            
            if not paths:
                raise ValueError(f"No <path> elements found in {filepath}")
            
            # Process only top-level paths (concatenate if multiple)
            for path_elem in paths:
                d = path_elem.get('d')
                if d:
                    self._parse_path_data(d)
                    
        except ET.ParseError as e:
            raise ValueError(f"Failed to parse SVG file {filepath}: {e}")
    
    def _parse_path_data(self, path_data: str):
        """Parse SVG path 'd' attribute using svgpathtools and discretize."""
        # Use svgpathtools to parse the path
        path = parse_path(path_data)
        
        # Discretize each segment of the path
        for segment in path:
            if isinstance(segment, Line):
                # Lines are already straight - just add endpoints
                self.points.append((segment.start.real, segment.start.imag))
                self.points.append((segment.end.real, segment.end.imag))
            else:
                # Curves (CubicBezier, QuadraticBezier, Arc) - discretize
                segment_length = segment.length()
                num_points = max(2, int(segment_length * self.CURVE_RESOLUTION))
                
                for i in range(num_points):
                    t = i / (num_points - 1)
                    point = segment.point(t)
                    self.points.append((point.real, point.imag))
        
        # Remove duplicate consecutive points
        if len(self.points) > 1:
            cleaned = [self.points[0]]
            for i in range(1, len(self.points)):
                if self.points[i] != self.points[i-1]:
                    cleaned.append(self.points[i])
            self.points = cleaned
    
    def _calculate_lengths(self):
        """Pre-calculate cumulative lengths for fast lookup."""
        if len(self.points) < 2:
            raise ValueError("Path must have at least 2 points")
        
        self.cumulative_lengths = [0.0]
        total = 0.0
        
        points_array = np.array(self.points)
        for i in range(1, len(points_array)):
            segment_length = np.linalg.norm(points_array[i] - points_array[i-1])
            total += segment_length
            self.cumulative_lengths.append(total)
        
        self.total_length = total
    
    def sample_points(self, count: int, start_percent: float = 0.0, 
                     end_percent: float = 100.0) -> List[Tuple[float, float, float]]:
        """Sample evenly-spaced points along path with tangent angles.
        
        Args:
            count: Number of points to sample
            start_percent: Starting position on path (0-100)
            end_percent: Ending position on path (0-100)
            
        Returns:
            List of (x, y, angle_degrees) tuples where angle is tangent direction
        """
        if count < 1:
            return []
        
        # Convert percentages to absolute lengths
        start_length = (start_percent / 100.0) * self.total_length
        end_length = (end_percent / 100.0) * self.total_length
        
        if start_length > end_length:
            start_length, end_length = end_length, start_length
        
        segment_length = end_length - start_length
        
        result = []
        for i in range(count):
            if count == 1:
                t = 0.5  # Center point for single instance
            else:
                t = i / (count - 1)
            
            target_length = start_length + t * segment_length
            pos, angle = self._interpolate_at_length(target_length)
            result.append((pos[0], pos[1], angle))
        
        return result
    
    def _interpolate_at_length(self, target_length: float) -> Tuple[np.ndarray, float]:
        """Find position and tangent angle at specific path length.
        
        Returns:
            (position, angle_degrees) tuple
        """
        # Clamp to valid range
        target_length = np.clip(target_length, 0, self.total_length)
        
        # Binary search for segment containing target length
        idx = np.searchsorted(self.cumulative_lengths, target_length)
        
        if idx == 0:
            idx = 1
        elif idx >= len(self.points):
            idx = len(self.points) - 1
        
        # Interpolate within segment
        p0 = np.array(self.points[idx - 1])
        p1 = np.array(self.points[idx])
        
        seg_start_length = self.cumulative_lengths[idx - 1]
        seg_end_length = self.cumulative_lengths[idx]
        seg_length = seg_end_length - seg_start_length
        
        if seg_length < 1e-10:  # Avoid division by zero
            position = p0
            tangent = np.array([0.0, 1.0])  # Default to vertical
        else:
            t = (target_length - seg_start_length) / seg_length
            position = p0 + t * (p1 - p0)
            tangent = (p1 - p0) / np.linalg.norm(p1 - p0)
        
        # Calculate angle from tangent vector
        # Use atan2 to get angle in radians, convert to degrees
        # Adjust for CK3 coordinate system (0° = vertical, clockwise)
        angle_rad = np.arctan2(tangent[0], tangent[1])
        angle_deg = np.degrees(angle_rad)
        
        return position, angle_deg
