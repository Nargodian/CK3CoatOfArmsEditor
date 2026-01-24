# PyQt5 imports
from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSizePolicy)
from PyQt5.QtCore import Qt

# Local component imports
from .canvas_widget import CoatOfArmsCanvas
from .transform_widget import TransformWidget


class CanvasArea(QFrame):
	"""Center canvas area for coat of arms preview"""
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setStyleSheet("QFrame { background-color: #0d0d0d; }")
		self.property_sidebar = None  # Will be set by main window
		self.main_window = None  # Will be set by main window
		
		# Cache for multi-layer transform (prevents cumulative transforms)
		self._drag_start_layers = None
		
		self._setup_ui()
	
	def mousePressEvent(self, event):
		"""Handle clicks on canvas background to deselect layers"""
		# If clicking outside the canvas widget itself, deselect layer
		if self.property_sidebar and self.property_sidebar.get_selected_indices():
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
		self.transform_widget.transformEnded.connect(self._on_transform_ended)
		self.transform_widget.nonUniformScaleUsed.connect(self._on_non_uniform_scale_used)
		self.transform_widget.layerDuplicated.connect(self._on_layer_duplicated)
		self.transform_widget.raise_()  # Ensure it's on top
		
		layout.addWidget(canvas_container, stretch=1)
		
		# Bottom bar
		bottom_bar = self._create_bottom_bar()
		layout.addWidget(bottom_bar)
	
	def _create_bottom_bar(self):
		"""Create the bottom bar with frame and splendor dropdowns"""
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
		self.frame_combo.setCurrentIndex(2)  # Default to House
		self.frame_combo.currentTextChanged.connect(self._on_frame_changed)
		bottom_layout.addWidget(self.frame_combo)
		
		bottom_layout.addSpacing(20)
		
		# Splendor dropdown
		splendor_label = QLabel("Splendor:")
		splendor_label.setStyleSheet("font-size: 11px; border: none;")
		bottom_layout.addWidget(splendor_label)
		
		self.splendor_combo = self._create_combo_box([
			"Base Origins / Obscure",
			"Insignificant / Noteworthy",
			"Reputable / Well-Known",
			"Significant / Famous",
			"Glorious / Fabled",
			"Legendary"
		])
		self.splendor_combo.setCurrentIndex(3)  # Default to Significant/Famous
		self.splendor_combo.currentIndexChanged.connect(self._on_splendor_changed)
		bottom_layout.addWidget(self.splendor_combo)
		
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
	
	def update_transform_widget_for_layer(self, layer_index=None):
		"""Update transform widget to match selected layer(s)
		
		For single selection: shows layer transform directly
		For multi-selection: calculates screen-space AABB (Axis-Aligned Bounding Box)
		  from all selected layer positions ± scales/2
		"""
		# Reset initial group state when selection changes (Task 3.6)
		self._initial_group_center = None
		self._initial_group_rotation = 0
		
		if not self.property_sidebar:
			self.transform_widget.set_visible(False)
			return
		
		# Get selected indices
		selected_indices = self.property_sidebar.get_selected_indices()
		
		# Use layer_index parameter if provided (backward compatibility)
		if layer_index is not None:
			if layer_index < 0 or layer_index >= len(self.property_sidebar.layers):
				self.transform_widget.set_visible(False)
				return
			selected_indices = [layer_index]
		
		if not selected_indices:
			self.transform_widget.set_visible(False)
			return
		
		# SINGLE SELECTION: Show layer transform directly
		if len(selected_indices) == 1:
			idx = selected_indices[0]
			if idx < 0 or idx >= len(self.property_sidebar.layers):
				self.transform_widget.set_visible(False)
				return
			
			layer = self.property_sidebar.layers[idx]
			pos_x = layer.get('pos_x', 0.5)
			pos_y = layer.get('pos_y', 0.5)
			scale_x = layer.get('scale_x', 0.5)
			scale_y = layer.get('scale_y', 0.5)
			rotation = layer.get('rotation', 0)
			
			self.transform_widget.set_transform(pos_x, pos_y, scale_x, scale_y, rotation)
			self.transform_widget.set_visible(True)
			return
		
		# MULTI-SELECTION: Calculate screen-space AABB
		# During rotation, use cached AABB to prevent widget from traveling
		if self.transform_widget.is_rotating and self.transform_widget.cached_aabb is not None:
			# Use cached values during rotation
			group_pos_x, group_pos_y, group_scale_x, group_scale_y = self.transform_widget.cached_aabb
		else:
			# Calculate AABB from current layer positions
			min_x = float('inf')
			max_x = float('-inf')
			min_y = float('inf')
			max_y = float('-inf')
			
			for idx in selected_indices:
				if idx < 0 or idx >= len(self.property_sidebar.layers):
					continue
				
				layer = self.property_sidebar.layers[idx]
				pos_x = layer.get('pos_x', 0.5)
				pos_y = layer.get('pos_y', 0.5)
				scale_x = layer.get('scale_x', 0.5)
				scale_y = layer.get('scale_y', 0.5)
				
				# Calculate layer AABB in normalized space (use abs for negative scales/flips)
				layer_min_x = pos_x - abs(scale_x) / 2
				layer_max_x = pos_x + abs(scale_x) / 2
				layer_min_y = pos_y - abs(scale_y) / 2
				layer_max_y = pos_y + abs(scale_y) / 2
				
				min_x = min(min_x, layer_min_x)
				max_x = max(max_x, layer_max_x)
				min_y = min(min_y, layer_min_y)
				max_y = max(max_y, layer_max_y)
			
			# Calculate group center and scale
			group_pos_x = (min_x + max_x) / 2
			group_pos_y = (min_y + max_y) / 2
			group_scale_x = max_x - min_x
			group_scale_y = max_y - min_y
			
			# Cache AABB when rotation starts
			if not self.transform_widget.is_rotating:
				self.transform_widget.cached_aabb = (group_pos_x, group_pos_y, group_scale_x, group_scale_y)
		
		# Store initial group state for rotation calculations (Task 3.6)
		if not hasattr(self, '_initial_group_center'):
			self._initial_group_center = (group_pos_x, group_pos_y)
			self._initial_group_rotation = 0
		
		# For multi-selection, start rotation at 0
		group_rotation = 0
		
		self.transform_widget.set_transform(group_pos_x, group_pos_y, group_scale_x, group_scale_y, group_rotation)
		self.transform_widget.set_visible(True)
	def _on_transform_changed(self, pos_x, pos_y, scale_x, scale_y, rotation):
		"""Handle transform changes from the widget		
		For single selection: updates layer directly
		For multi-selection: applies group transform to all selected layers
		"""
		selected_indices = self.property_sidebar.get_selected_indices() if self.property_sidebar else []
		if not selected_indices:
			return
		
		# SINGLE SELECTION: Direct update
		if len(selected_indices) == 1:
			idx = selected_indices[0]
			if idx < 0 or idx >= len(self.property_sidebar.layers):
				return
			
			layer = self.property_sidebar.layers[idx]
			layer['pos_x'] = pos_x
			layer['pos_y'] = pos_y
			layer['scale_x'] = scale_x
			layer['scale_y'] = scale_y
			layer['rotation'] = rotation
			
			self.canvas_widget.set_layers(self.property_sidebar.layers)
			self.property_sidebar._load_layer_properties()
			return
		
		# MULTI-SELECTION: Group transform
		# Cache original layer states at drag start to prevent cumulative transforms
		if self._drag_start_layers is None:
			self._drag_start_layers = []
			for idx in selected_indices:
				if idx < 0 or idx >= len(self.property_sidebar.layers):
					continue
				layer = self.property_sidebar.layers[idx]
				self._drag_start_layers.append({
					'index': idx,
					'pos_x': layer.get('pos_x', 0.5),
					'pos_y': layer.get('pos_y', 0.5),
					'scale_x': layer.get('scale_x', 0.5),
					'scale_y': layer.get('scale_y', 0.5)
				})
			
			# Calculate and cache the original group AABB (only once at drag start)
			original_min_x = float('inf')
			original_max_x = float('-inf')
			original_min_y = float('inf')
			original_max_y = float('-inf')
			
			for layer_state in self._drag_start_layers:
				pos_x_orig = layer_state['pos_x']
				pos_y_orig = layer_state['pos_y']
				scale_x_orig = layer_state['scale_x']
				scale_y_orig = layer_state['scale_y']
				
				# Use abs() to handle negative scales (flipped layers)
				layer_min_x = pos_x_orig - abs(scale_x_orig) / 2
				layer_max_x = pos_x_orig + abs(scale_x_orig) / 2
				layer_min_y = pos_y_orig - abs(scale_y_orig) / 2
				layer_max_y = pos_y_orig + abs(scale_y_orig) / 2
				
				original_min_x = min(original_min_x, layer_min_x)
				original_max_x = max(original_max_x, layer_max_x)
				original_min_y = min(original_min_y, layer_min_y)
				original_max_y = max(original_max_y, layer_max_y)
			
			# Cache the original AABB
			self._drag_start_aabb = {
				'center_x': (original_min_x + original_max_x) / 2,
				'center_y': (original_min_y + original_max_y) / 2,
				'scale_x': original_max_x - original_min_x,
				'scale_y': original_max_y - original_min_y
			}
		
		# Use cached original AABB
		original_center_x = self._drag_start_aabb['center_x']
		original_center_y = self._drag_start_aabb['center_y']
		original_scale_x = self._drag_start_aabb['scale_x']
		original_scale_y = self._drag_start_aabb['scale_y']
		
		# Calculate transform deltas
		position_delta_x = pos_x - original_center_x
		position_delta_y = pos_y - original_center_y
		
		# Calculate scale factors (avoid division by zero)
		scale_factor_x = scale_x / original_scale_x if original_scale_x > 0.001 else 1.0
		scale_factor_y = scale_y / original_scale_y if original_scale_y > 0.001 else 1.0
		
		# Calculate rotation delta (Task 3.6)
		rotation_delta = rotation - getattr(self, '_initial_group_rotation', 0)
		
		# Apply transforms to all selected layers using cached states
		import math
		for layer_state in self._drag_start_layers:
			idx = layer_state['index']
			if idx < 0 or idx >= len(self.property_sidebar.layers):
				continue
			
			# Get original positions from cache
			pos_x_orig = layer_state['pos_x']
			pos_y_orig = layer_state['pos_y']
			scale_x_orig = layer_state['scale_x']
			scale_y_orig = layer_state['scale_y']
			
			# Calculate offset from original group center
			offset_x = pos_x_orig - original_center_x
			offset_y = pos_y_orig - original_center_y
			
			# Check if we're rotating (ferris wheel behavior: only positions change)
			if self.transform_widget.is_rotating:
				# ROTATION ONLY: Apply rotation to offset, no scaling
				rotation_rad = math.radians(rotation_delta)
				cos_r = math.cos(rotation_rad)
				sin_r = math.sin(rotation_rad)
				new_offset_x = offset_x * cos_r - offset_y * sin_r
				new_offset_y = offset_x * sin_r + offset_y * cos_r
				
				# Apply position delta
				new_pos_x = original_center_x + new_offset_x + position_delta_x
				new_pos_y = original_center_y + new_offset_y + position_delta_y
				
				# Keep scales unchanged
				new_scale_x = scale_x_orig
				new_scale_y = scale_y_orig
			else:
				# SCALE/POSITION: Apply scale to offset and layer scales
				new_offset_x = offset_x * scale_factor_x
				new_offset_y = offset_y * scale_factor_y
				
				# Apply position delta
				new_pos_x = original_center_x + new_offset_x + position_delta_x
				new_pos_y = original_center_y + new_offset_y + position_delta_y
				
				# Apply scale to layer scale, preserving flip direction (sign)
				sign_x = 1 if scale_x_orig >= 0 else -1
				sign_y = 1 if scale_y_orig >= 0 else -1
				new_scale_x = sign_x * abs(scale_x_orig) * scale_factor_x
				new_scale_y = sign_y * abs(scale_y_orig) * scale_factor_y
			
			# Update actual layer
			layer = self.property_sidebar.layers[idx]
			layer['pos_x'] = new_pos_x
			layer['pos_y'] = new_pos_y
			layer['scale_x'] = new_scale_x
			layer['scale_y'] = new_scale_y
			# Task 3.6: Individual layer rotations are preserved (NOT modified)
		
		# Update canvas
		self.canvas_widget.set_layers(self.property_sidebar.layers)
		# Don't reload properties during drag - it's expensive and causes UI issues
		# Properties will be reloaded when drag ends
	
	def _on_transform_ended(self):
		"""Handle transform drag end - save to history"""
		# Clear drag cache for next operation
		self._drag_start_layers = None
		self._drag_start_aabb = None
		
		# Reload properties to update UI with final values
		if self.property_sidebar:
			self.property_sidebar._load_layer_properties()
		
		if self.main_window and hasattr(self.main_window, '_save_state'):
			self.main_window._save_state("Transform layer")
	
	def _on_non_uniform_scale_used(self):
		"""Handle non-uniform scaling from transform widget - disable unified scale"""
		if self.property_sidebar and hasattr(self.property_sidebar, 'unified_scale_check'):
			if self.property_sidebar.unified_scale_check.isChecked():
				self.property_sidebar.unified_scale_check.setChecked(False)
	
	def _on_layer_duplicated(self):
		"""Handle Ctrl+drag layer duplication"""
		if self.main_window and hasattr(self.main_window, 'duplicate_selected_layer'):
			self.main_window.duplicate_selected_layer()
	
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
	
	def _on_splendor_changed(self, index):
		"""Handle splendor level change"""
		self.canvas_widget.set_splendor(index)
