"""Transform widget modes - defines which handles are active for each mode."""

from .handles import (
	CornerHandle, EdgeHandle, RotationHandle, CenterHandle,
	ArrowHandle, RingHandle, GimbleCenterHandle
)
from constants import (
	TRANSFORM_HANDLE_SIZE, TRANSFORM_ROTATION_HANDLE_OFFSET,
	TRANSFORM_HIT_TOLERANCE, TRANSFORM_GIMBLE_ARROW_START_OFFSET,
	TRANSFORM_GIMBLE_ARROW_LENGTH, TRANSFORM_GIMBLE_ARROW_HEAD_SIZE,
	TRANSFORM_GIMBLE_RING_RADIUS, TRANSFORM_GIMBLE_RING_HIT_TOLERANCE,
	TRANSFORM_GIMBLE_CENTER_DOT_RADIUS
)


class TransformMode:
	"""Base class for transform modes."""
	
	def __init__(self):
		self.handles = {}  # handle_type -> handle_object
	
	def get_handles(self):
		"""Return all handles for this mode."""
		return self.handles
	
	def get_handle_at_pos(self, mouse_x, mouse_y, center_x, center_y, half_w, half_h, rotation):
		"""Find which handle (if any) is at mouse position.
		
		Returns:
			Handle object or None
		"""
		# Check handles in priority order
		for handle_type, handle in self.handles.items():
			if handle.hit_test(mouse_x, mouse_y, center_x, center_y, half_w, half_h, rotation):
				return handle
		return None


class BboxMode(TransformMode):
	"""Normal mode - full bounding box with all handles."""
	
	def __init__(self):
		super().__init__()
		
		# Create all handles
		self.handles = {
			# Corners (diagonal scaling)
			'tl': CornerHandle('tl', TRANSFORM_HANDLE_SIZE, TRANSFORM_HIT_TOLERANCE),
			'tr': CornerHandle('tr', TRANSFORM_HANDLE_SIZE, TRANSFORM_HIT_TOLERANCE),
			'bl': CornerHandle('bl', TRANSFORM_HANDLE_SIZE, TRANSFORM_HIT_TOLERANCE),
			'br': CornerHandle('br', TRANSFORM_HANDLE_SIZE, TRANSFORM_HIT_TOLERANCE),
			
			# Edges (single-axis scaling)
			't': EdgeHandle('t', TRANSFORM_HANDLE_SIZE, TRANSFORM_HIT_TOLERANCE),
			'r': EdgeHandle('r', TRANSFORM_HANDLE_SIZE, TRANSFORM_HIT_TOLERANCE),
			'b': EdgeHandle('b', TRANSFORM_HANDLE_SIZE, TRANSFORM_HIT_TOLERANCE),
			'l': EdgeHandle('l', TRANSFORM_HANDLE_SIZE, TRANSFORM_HIT_TOLERANCE),
			
			# Rotation handle
			'rotate': RotationHandle(TRANSFORM_ROTATION_HANDLE_OFFSET, 
			                         TRANSFORM_HANDLE_SIZE, 
			                         TRANSFORM_HIT_TOLERANCE),
			
			# Center (full AABB for translation)
			'center': CenterHandle(),
		}
	
	def get_handle_at_pos(self, mouse_x, mouse_y, center_x, center_y, half_w, half_h, rotation):
		"""Check handles in priority order (corners/edges before center)."""
		# Check order: rotation -> corners -> edges -> center
		check_order = [
			'rotate',
			'tl', 'tr', 'bl', 'br',
			't', 'r', 'b', 'l',
			'center'
		]
		
		for handle_type in check_order:
			if self.handles[handle_type].hit_test(mouse_x, mouse_y, center_x, center_y, half_w, half_h, rotation):
				return self.handles[handle_type]
		return None
		
		return None


class MinimalBboxMode(TransformMode):
	"""Minimal mode - bounding box with center drag only."""
	
	def __init__(self):
		super().__init__()
		
		# Only center handle (bounding box + translation)
		self.handles = {
			'center': CenterHandle(),
		}


class GimbleMode(TransformMode):
	"""Gimble mode - axis arrows + rotation ring + center dot."""
	
	def __init__(self):
		super().__init__()
		
		# Create gimble handles
		self.handles = {
			# Axis arrows
			'axis_x': ArrowHandle('x', 
			                      TRANSFORM_GIMBLE_ARROW_START_OFFSET,
			                      TRANSFORM_GIMBLE_ARROW_LENGTH,
			                      TRANSFORM_GIMBLE_ARROW_HEAD_SIZE,
			                      TRANSFORM_HIT_TOLERANCE),
			'axis_y': ArrowHandle('y',
			                      TRANSFORM_GIMBLE_ARROW_START_OFFSET,
			                      TRANSFORM_GIMBLE_ARROW_LENGTH,
			                      TRANSFORM_GIMBLE_ARROW_HEAD_SIZE,
			                      TRANSFORM_HIT_TOLERANCE),
			
			# Rotation ring
			'ring': RingHandle(TRANSFORM_GIMBLE_RING_RADIUS,
			                   TRANSFORM_GIMBLE_RING_HIT_TOLERANCE),
			
			# Center dot
			'center': GimbleCenterHandle(TRANSFORM_GIMBLE_CENTER_DOT_RADIUS,
			                             TRANSFORM_HIT_TOLERANCE),
		}
	
	def get_handle_at_pos(self, mouse_x, mouse_y, center_x, center_y, half_w, half_h, rotation):
		"""Check handles in priority order."""
		# Check order: ring -> arrows -> center
		check_order = ['ring', 'axis_x', 'axis_y', 'center']
		
		for handle_type in check_order:
			if self.handles[handle_type].hit_test(mouse_x, mouse_y, center_x, center_y, half_w, half_h, rotation):
				return self.handles[handle_type]
		
		return None


# Mode registry
MODES = {
	'bbox': BboxMode,
	'minimal_bbox': MinimalBboxMode,
	'gimble': GimbleMode,
}


def create_mode(mode_name):
	"""Factory function to create mode instances.
	
	Args:
		mode_name: 'bbox', 'minimal_bbox', or 'gimble'
		
	Returns:
		TransformMode instance
	"""
	mode_class = MODES.get(mode_name, BboxMode)
	return mode_class()
