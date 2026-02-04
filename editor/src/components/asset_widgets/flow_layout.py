"""
FlowLayout - Auto-wrapping layout (standard Qt example pattern)
Based on Qt's official FlowLayout example
"""
from PyQt5.QtWidgets import QLayout, QSizePolicy
from PyQt5.QtCore import Qt, QPoint, QRect, QSize


class FlowLayout(QLayout):
	"""Layout that arranges widgets in rows, wrapping to new row when needed"""
	
	def __init__(self, parent=None, margin=0, spacing=-1):
		super().__init__(parent)
		
		if parent is not None:
			self.setContentsMargins(margin, margin, margin, margin)
		
		self.setSpacing(spacing)
		self.item_list = []
	
	def __del__(self):
		item = self.takeAt(0)
		while item:
			item = self.takeAt(0)
	
	def addItem(self, item):
		self.item_list.append(item)
	
	def count(self):
		return len(self.item_list)
	
	def itemAt(self, index):
		if 0 <= index < len(self.item_list):
			return self.item_list[index]
		return None
	
	def takeAt(self, index):
		if 0 <= index < len(self.item_list):
			return self.item_list.pop(index)
		return None
	
	def expandingDirections(self):
		return Qt.Orientations(Qt.Orientation(0))
	
	def hasHeightForWidth(self):
		return True
	
	def heightForWidth(self, width):
		height = self._do_layout(QRect(0, 0, width, 0), True)
		return height
	
	def setGeometry(self, rect):
		super().setGeometry(rect)
		self._do_layout(rect, False)
	
	def sizeHint(self):
		return self.minimumSize()
	
	def minimumSize(self):
		size = QSize()
		
		for item in self.item_list:
			size = size.expandedTo(item.minimumSize())
		
		size += QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().top())
		return size
	
	def _do_layout(self, rect, test_only):
		x = rect.x()
		y = rect.y()
		line_height = 0
		line_items = []
		
		# Max spacing threshold (stop spreading and add another item instead)
		max_spacing = 20
		
		for item in self.item_list:
			wid = item.widget()
			space_x = self.spacing() + wid.style().layoutSpacing(
				QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
			space_y = self.spacing() + wid.style().layoutSpacing(
				QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)
			
			next_x = x + item.sizeHint().width() + space_x
			if next_x - space_x > rect.right() and line_height > 0:
				# Justify current line before starting new one
				if not test_only and len(line_items) > 0:
					self._justify_line(line_items, rect, max_spacing)
				
				line_items = []
				x = rect.x()
				y = y + line_height + space_y
				next_x = x + item.sizeHint().width() + space_x
				line_height = 0
			
			line_items.append((item, x, y))
			x = next_x
			line_height = max(line_height, item.sizeHint().height())
		
		# Justify last line
		if not test_only and len(line_items) > 0:
			self._justify_line(line_items, rect, max_spacing)
		
		return y + line_height - rect.y()
	
	def _justify_line(self, line_items, rect, max_spacing):
		"""Distribute extra space between items on a line, up to max_spacing"""
		if len(line_items) == 0:
			return
		
		# Calculate total width of items
		total_item_width = sum(item.sizeHint().width() for item, _, _ in line_items)
		available_width = rect.width()
		extra_space = available_width - total_item_width
		
		if len(line_items) == 1:
			# Single item, center it
			item, _, y_pos = line_items[0]
			x_pos = rect.x() + extra_space // 2
			item.setGeometry(QRect(QPoint(x_pos, y_pos), item.sizeHint()))
		else:
			# Multiple items, distribute space between them
			num_gaps = len(line_items) - 1
			gap_size = min(max_spacing, extra_space // num_gaps) if num_gaps > 0 else 0
			
			# Center the line if gaps would exceed max_spacing
			total_gap_space = gap_size * num_gaps
			remaining_space = extra_space - total_gap_space
			start_x = rect.x() + remaining_space // 2
			
			x_pos = start_x
			for item, _, y_pos in line_items:
				item.setGeometry(QRect(QPoint(x_pos, y_pos), item.sizeHint()))
				x_pos += item.sizeHint().width() + gap_size
