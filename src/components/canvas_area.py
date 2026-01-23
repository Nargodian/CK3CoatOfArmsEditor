from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSizePolicy)
from PyQt5.QtCore import Qt
from .canvas_widget import CoatOfArmsCanvas
from .transform_widget import TransformWidget


class CanvasArea(QFrame):
	"""Center canvas area for coat of arms preview"""
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setStyleSheet("QFrame { background-color: #0d0d0d; }")
		self.property_sidebar = None  # Will be set by main window
		self._setup_ui()
	
	def mousePressEvent(self, event):
		"""Handle clicks on canvas background to deselect layers"""
		# If clicking outside the canvas widget itself, deselect layer
		if self.property_sidebar and self.property_sidebar.selected_layer_index is not None:
			# Check if click is on the canvas widget
			canvas_geometry = self.canvas_widget.geometry()
			if not canvas_geometry.contains(event.pos()):
				# Clicked outside canvas - deselect
				self.property_sidebar._deselect_layer()
		super().mousePressEvent(event)
	
	def _setup_ui(self):
		"""Setup the canvas area UI"""
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(0)
		
		# Container to center the square canvas
		canvas_container = QFrame()
		canvas_container.setStyleSheet("QFrame { background-color: #0d0d0d; }")
		canvas_layout = QVBoxLayout(canvas_container)
		canvas_layout.setContentsMargins(10, 10, 10, 10)
		canvas_layout.setAlignment(Qt.AlignCenter)
		
		# OpenGL canvas widget (square aspect)
		self.canvas_widget = CoatOfArmsCanvas()
		self.canvas_widget.setMinimumSize(400, 400)
		self.canvas_widget.setMaximumSize(1000, 1000)
		
		canvas_layout.addWidget(self.canvas_widget)
		
		# Transform widget (absolute positioned overlay)
		# Make it a child of canvas_widget so it overlays on top
		self.transform_widget = TransformWidget(self.canvas_widget)
		self.transform_widget.set_visible(False)
		self.transform_widget.transformChanged.connect(self._on_transform_changed)
		self.transform_widget.raise_()  # Ensure it's on top
		
		layout.addWidget(canvas_container, stretch=1)
		
		# Bottom bar
		bottom_bar = self._create_bottom_bar()
		layout.addWidget(bottom_bar)
	
	def _create_bottom_bar(self):
		"""Create the bottom bar with frame and prestige dropdowns"""
		bottom_bar = QFrame()
		bottom_bar.setStyleSheet("QFrame { background-color: #353535; border-top: 1px solid; }")
		bottom_bar.setFixedHeight(50)
		
		bottom_layout = QHBoxLayout(bottom_bar)
		bottom_layout.setContentsMargins(10, 5, 10, 5)
		bottom_layout.setSpacing(15)
		
		# Frame dropdown
		frame_label = QLabel("Frame:")
		frame_label.setStyleSheet("font-size: 11px; border: none;")
		bottom_layout.addWidget(frame_label)
		
		frame_options = ["None", "Dynasty", "House", "House China", "House Japan"] + \
		                [f"House Frame {i:02d}" for i in range(2, 31)]
		self.frame_combo = self._create_combo_box(frame_options)
		self.frame_combo.setCurrentIndex(1)  # Default to Dynasty
		self.frame_combo.currentTextChanged.connect(self._on_frame_changed)
		bottom_layout.addWidget(self.frame_combo)
		
		bottom_layout.addSpacing(20)
		
		# Prestige dropdown
		prestige_label = QLabel("Prestige:")
		prestige_label.setStyleSheet("font-size: 11px; border: none;")
		bottom_layout.addWidget(prestige_label)
		
		self.prestige_combo = self._create_combo_box(["Level 0", "Level 1", "Level 2", "Level 3", "Level 4", "Level 5"])
		self.prestige_combo.currentIndexChanged.connect(self._on_prestige_changed)
		bottom_layout.addWidget(self.prestige_combo)
		
		bottom_layout.addStretch()
		
		return bottom_bar
	
	def _create_combo_box(self, items):
		"""Create a styled combo box"""
		combo = QComboBox()
		combo.addItems(items)
		combo.setStyleSheet("""
			QComboBox {
				padding: 5px 10px;
				border-radius: 3px;
				min-width: 150px;
				border: none;
			}
			QComboBox::drop-down {
				border: none;
			}
			QComboBox::down-arrow {
				image: none;
				border-left: 4px solid transparent;
				border-right: 4px solid transparent;
				border-top: 6px solid;
				margin-right: 5px;
			}
		""")
		return combo
	
	def set_property_sidebar(self, sidebar):
		"""Set reference to property sidebar for layer selection"""
		self.property_sidebar = sidebar
	
	def update_transform_widget_for_layer(self, layer_index):
		"""Update transform widget to match the selected layer"""
		if not self.property_sidebar or layer_index is None:
			self.transform_widget.set_visible(False)
			return
		
		if layer_index < 0 or layer_index >= len(self.property_sidebar.layers):
			self.transform_widget.set_visible(False)
			return
		
		layer = self.property_sidebar.layers[layer_index]
		
		# Get transform values from layer
		pos_x = layer.get('pos_x', 0.5)
		pos_y = layer.get('pos_y', 0.5)
		scale_x = layer.get('scale_x', 0.5)
		scale_y = layer.get('scale_y', 0.5)
		rotation = layer.get('rotation', 0)
		
		# Update transform widget
		self.transform_widget.set_transform(pos_x, pos_y, scale_x, scale_y, rotation)
		self.transform_widget.set_visible(True)
	
	def _on_transform_changed(self, pos_x, pos_y, scale_x, scale_y, rotation):
		"""Handle transform changes from the widget"""
		if not self.property_sidebar or self.property_sidebar.selected_layer_index is None:
			return
		
		idx = self.property_sidebar.selected_layer_index
		if idx < 0 or idx >= len(self.property_sidebar.layers):
			return
		
		# Update layer data
		layer = self.property_sidebar.layers[idx]
		layer['pos_x'] = pos_x
		layer['pos_y'] = pos_y
		layer['scale_x'] = scale_x
		layer['scale_y'] = scale_y
		layer['rotation'] = rotation
		
		# Update canvas
		self.canvas_widget.set_layers(self.property_sidebar.layers)
		
		# Update property sidebar UI
		self.property_sidebar._load_layer_properties()
	
	def _on_frame_changed(self, frame_text):
		"""Handle frame selection change"""
		# Convert display text to frame name
		frame_map = {
			"None": "None",
			"Dynasty": "dynasty",
			"House": "house",
			"House China": "house_china",
			"House Japan": "house_japan"
		}
		
		# Handle House Frame XX format
		if frame_text.startswith("House Frame"):
			frame_num = frame_text.split()[-1]
			frame_name = f"house_frame_{frame_num}"
		else:
			frame_name = frame_map.get(frame_text, "None")
		
		self.canvas_widget.set_frame(frame_name)
	
	def _on_prestige_changed(self, index):
		"""Handle prestige level change"""
		self.canvas_widget.set_prestige(index)
