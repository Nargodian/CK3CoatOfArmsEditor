"""Transform widget handle system - ABC-based handle architecture.

Each handle type is a class that knows:
- How to draw itself
- How to test if a mouse position hits it
- What its abstract position is (normalized coordinates)
"""

from abc import ABC, abstractmethod
from PyQt5.QtCore import QPointF
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
		# Local position relative to AABB
		local_x = self.norm_x * half_w
		local_y = self.norm_y * half_h
		
		# Apply rotation
		rad = math.radians(rotation)
		cos_r = math.cos(rad)
		sin_r = math.sin(rad)
		
		rotated_x = local_x * cos_r - local_y * sin_r
		rotated_y = local_x * sin_r + local_y * cos_r
		
		# Translate to widget space
		return center_x + rotated_x, center_y + rotated_y
	
	def hit_test(self, mouse_x, mouse_y, center_x, center_y, half_w, half_h, rotation):
		px, py = self._get_pixel_pos(center_x, center_y, half_w, half_h, rotation)
		dx = mouse_x - px
		dy = mouse_y - py
		distance = math.sqrt(dx*dx + dy*dy)
		return distance <= (self.handle_size + self.hit_tolerance)
	
	def draw(self, painter, center_x, center_y, half_w, half_h, rotation):
		px, py = self._get_pixel_pos(center_x, center_y, half_w, half_h, rotation)
		
		painter.setPen(QPen(QColor(255, 255, 255), 2))
		painter.setBrush(QBrush(QColor(100, 100, 255)))
		painter.drawEllipse(QPointF(px, py), float(self.handle_size), float(self.handle_size))


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
		
		# Apply rotation
		rad = math.radians(rotation)
		cos_r = math.cos(rad)
		sin_r = math.sin(rad)
		
		rotated_x = local_x * cos_r - local_y * sin_r
		rotated_y = local_x * sin_r + local_y * cos_r
		
		return center_x + rotated_x, center_y + rotated_y
	
	def hit_test(self, mouse_x, mouse_y, center_x, center_y, half_w, half_h, rotation):
		px, py = self._get_pixel_pos(center_x, center_y, half_w, half_h, rotation)
		dx = mouse_x - px
		dy = mouse_y - py
		distance = math.sqrt(dx*dx + dy*dy)
		return distance <= (self.handle_size + self.hit_tolerance)
	
	def draw(self, painter, center_x, center_y, half_w, half_h, rotation):
		px, py = self._get_pixel_pos(center_x, center_y, half_w, half_h, rotation)
		
		painter.setPen(QPen(QColor(255, 255, 255), 2))
		painter.setBrush(QBrush(QColor(100, 255, 100)))
		painter.drawRect(int(px - self.handle_size/2), int(py - self.handle_size/2),
		                 self.handle_size, self.handle_size)


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
		# Start at top edge
		local_x = 0
		local_y = -half_h - self.offset
		
		# Apply rotation
		rad = math.radians(rotation)
		cos_r = math.cos(rad)
		sin_r = math.sin(rad)
		
		rotated_x = local_x * cos_r - local_y * sin_r
		rotated_y = local_x * sin_r + local_y * cos_r
		
		return center_x + rotated_x, center_y + rotated_y
	
	def hit_test(self, mouse_x, mouse_y, center_x, center_y, half_w, half_h, rotation):
		px, py = self._get_pixel_pos(center_x, center_y, half_w, half_h, rotation)
		dx = mouse_x - px
		dy = mouse_y - py
		distance = math.sqrt(dx*dx + dy*dy)
		return distance <= (self.handle_size + self.hit_tolerance)
	
	def draw(self, painter, center_x, center_y, half_w, half_h, rotation):
		px, py = self._get_pixel_pos(center_x, center_y, half_w, half_h, rotation)
		
		painter.setPen(QPen(QColor(255, 255, 255), 2))
		painter.setBrush(QBrush(QColor(255, 100, 100)))
		painter.drawEllipse(QPointF(px, py), float(self.handle_size), float(self.handle_size))


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
		"""Draw bounding box (not a handle circle)."""
		painter.save()
		
		# Transform to rotated space
		transform = QTransform()
		transform.translate(center_x, center_y)
		transform.rotate(rotation)
		painter.setTransform(transform)
		
		# Draw box
		painter.setPen(QPen(QColor(100, 150, 255), 2))
		painter.setBrush(QBrush())
		painter.drawRect(int(-half_w), int(-half_h), int(half_w * 2), int(half_h * 2))
		
		painter.restore()


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
		"""Rectangular hit area along arrow shaft."""
		# Transform mouse to local space
		dx = mouse_x - center_x
		dy = mouse_y - center_y
		
		rad = -math.radians(rotation)
		cos_r = math.cos(rad)
		sin_r = math.sin(rad)
		
		local_x = dx * cos_r - dy * sin_r
		local_y = dx * sin_r + dy * cos_r
		
		# Check hit area based on axis
		if self.axis == 'x':
			# Arrow extends right from center
			in_shaft = (self.start_offset <= local_x <= self.start_offset + self.length and
			            abs(local_y) <= self.hit_tolerance)
			return in_shaft
		else:  # y axis
			# Arrow extends down from center
			in_shaft = (self.start_offset <= local_y <= self.start_offset + self.length and
			            abs(local_x) <= self.hit_tolerance)
			return in_shaft
	
	def draw(self, painter, center_x, center_y, half_w, half_h, rotation):
		"""Draw axis arrow."""
		painter.save()
		
		transform = QTransform()
		transform.translate(center_x, center_y)
		transform.rotate(rotation)
		painter.setTransform(transform)
		
		color = QColor(255, 100, 100) if self.axis == 'x' else QColor(100, 255, 100)
		painter.setPen(QPen(color, 2))
		
		if self.axis == 'x':
			# X arrow (red, right)
			start_x = int(self.start_offset)
			end_x = int(self.start_offset + self.length)
			head = int(self.head_size)
			painter.drawLine(start_x, 0, end_x, 0)
			# Arrow head
			painter.drawLine(end_x, 0, end_x - head, -head)
			painter.drawLine(end_x, 0, end_x - head, head)
		else:
			# Y arrow (green, down)
			start_y = int(self.start_offset)
			end_y = int(self.start_offset + self.length)
			head = int(self.head_size)
			painter.drawLine(0, start_y, 0, end_y)
			# Arrow head
			painter.drawLine(0, end_y, -head, end_y - head)
			painter.drawLine(0, end_y, head, end_y - head)
		
		painter.restore()


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
