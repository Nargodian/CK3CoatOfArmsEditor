"""Transform data structures for coordinate and state representation."""
from dataclasses import dataclass


@dataclass
class Transform:
	"""Transform state: position, scale, and rotation.
	
	Used across coordinate spaces:
	- Widget space: center_x/y in pixels (center-origin), half_w/h in pixels
	- CoA space: pos_x/y in 0-1 normalized, scale_x/y in 0-1 normalized
	"""
	pos_x: float
	pos_y: float
	scale_x: float
	scale_y: float
	rotation: float = 0.0
