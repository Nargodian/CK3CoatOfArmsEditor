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
		#COA INTEGRATION ACTION: Step 4 - Add CoA model reference (set by MainWindow)
		self.coa = None  # Reference to CoA model (will be set externally)
		self.property_sidebar = None  # Will be set by main window
		self.main_window = None  # Will be set by main window
	
		# Cache for multi-layer transform (prevents cumulative transforms)
		self._drag_start_layers = None
		
		self._setup_ui()
	
	def mousePressEvent(self, event):
		"""Handle clicks on canvas background to deselect layers"""
		# If clicking outside the canvas widget itself, deselect layer
		if self.property_sidebar and self.property_sidebar.get_selected_uuids():
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
		# Parent to canvas_container (not canvas_widget) to avoid edge clipping
		# Pass canvas_widget as reference for coordinate calculations
		self.transform_widget = TransformWidget(canvas_container, self.canvas_widget)
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
		
		bottom_layout.addSpacing(20)
		
		# Add minimal transform widget toggle button
		from PyQt5.QtWidgets import QPushButton
		self.minimal_transform_btn = QPushButton("▭")
		self.minimal_transform_btn.setCheckable(True)
		self.minimal_transform_btn.setToolTip("Toggle minimal transform widget (M)\nShows faint box only, drag and wheel functions work")
		self.minimal_transform_btn.setFixedSize(24, 20)
		self.minimal_transform_btn.setStyleSheet("QPushButton { font-size: 14px; padding: 0px; }")
		self.minimal_transform_btn.toggled.connect(self.transform_widget.set_minimal_mode)
		bottom_layout.addWidget(self.minimal_transform_btn)
		
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
		# Reset drag state when selection changes to prevent applying transforms to wrong layers
		self._drag_start_layers = None
		self._drag_start_aabb = None
		
		# Abort any active drag operation on the widget (prevents old drags from continuing)
		self.transform_widget.active_handle = self.transform_widget.HANDLE_NONE
		self.transform_widget.drag_start_pos = None
		self.transform_widget.drag_start_transform = None
		
		# Reset initial group state when selection changes (Task 3.6)
		self._initial_group_center = None
		self._initial_group_rotation = 0
		
		if not self.property_sidebar:
			self.transform_widget.set_visible(False)
			return
		
		# Get selected UUIDs
		selected_uuids = self.property_sidebar.get_selected_uuids()
		
		# Use layer_index parameter if provided (backward compatibility)
		if layer_index is not None:
			if layer_index < 0 or layer_index >= self.property_sidebar.get_layer_count():
				self.transform_widget.set_visible(False)
				return
		
		# SINGLE SELECTION: Show layer transform directly
		if len(selected_uuids) == 1:
			uuid = list(selected_uuids)[0]
			# Read from CoA model for transform widget positioning
			if not self.main_window or not self.main_window.coa:
				self.transform_widget.set_visible(False)
				return
			
			layer = self.main_window.coa.get_layer_by_uuid(uuid)
			if not layer:
				self.transform_widget.set_visible(False)
				return
			
			pos_x = layer.pos_x
			pos_y = layer.pos_y
			scale_x = layer.scale_x
			scale_y = layer.scale_y
			rotation = layer.rotation
			
			self.transform_widget.set_transform(pos_x, pos_y, scale_x, scale_y, rotation)
			self.transform_widget.set_visible(True)
			return
		
		# MULTI-SELECTION: Calculate screen-space AABB using CoA
		# If we have a drag_start_aabb (during active transform), use that to prevent scale compounding
		if hasattr(self, '_drag_start_aabb') and self._drag_start_aabb is not None:
			# Use cached original AABB from transform cache
			group_pos_x = self._drag_start_aabb['center_x']
			group_pos_y = self._drag_start_aabb['center_y']
			group_scale_x = self._drag_start_aabb['scale_x']
			group_scale_y = self._drag_start_aabb['scale_y']
		else:
			# Get UUIDs for selected layers directly
			selected_uuids = self.property_sidebar.get_selected_uuids()
			
			if not selected_uuids:
				self.transform_widget.set_visible(False)
				return
			
			# Use CoA's AABB calculation (only when not actively transforming)
			try:
				bounds = self.main_window.coa.get_layers_bounds(selected_uuids)
				group_pos_x = bounds['center_x']
				group_pos_y = bounds['center_y']
				group_scale_x = bounds['width']
				group_scale_y = bounds['height']
			except ValueError:
				self.transform_widget.set_visible(False)
				return
	
		# Store initial group state for rotation calculations (Task 3.6)
		if not hasattr(self, '_initial_group_center'):
			self._initial_group_center = (group_pos_x, group_pos_y)
			self._initial_group_rotation = 0
		
		# For multi-selection, start rotation at 0
		group_rotation = 0
		
		# Pass is_multi_selection=True to skip scale clamping (AABB can exceed 1.0)
		self.transform_widget.set_transform(group_pos_x, group_pos_y, group_scale_x, group_scale_y, group_rotation, is_multi_selection=True)
		self.transform_widget.set_visible(True)
	def _on_transform_changed(self, pos_x, pos_y, scale_x, scale_y, rotation):
		"""Handle transform changes from the widget		
		For single selection: updates layer directly
		For multi-selection: applies group transform to all selected layers
		"""
		selected_uuids = self.property_sidebar.get_selected_uuids() if self.property_sidebar else []
		if not selected_uuids:
			return
		
		# SINGLE SELECTION: Direct update
		if len(selected_uuids) == 1:
			uuid = list(selected_uuids)[0]
			layer = self.main_window.coa.get_layer_by_uuid(uuid)
			if not layer:
				return
			
			# Clamp position to valid range [0, 1]
			layer.pos_x = max(0.0, min(1.0, pos_x))
			layer.pos_y = max(0.0, min(1.0, pos_y))
			layer.scale_x = scale_x
			layer.scale_y = scale_y
			layer.rotation = rotation
			
			self.canvas_widget.set_coa(self.main_window.coa)
			# Don't reload properties during drag - causes feedback loop that resets flip state
			# Properties will be reloaded when drag ends in _on_transform_ended()
			return
		
		# MULTI-SELECTION: Group transform
		# Cache original layer states at drag start using CoA's transform cache
		if self._drag_start_layers is None:
			# Get selected UUIDs (already a list)
			selected_uuids = list(selected_uuids)
			
			# Begin transform group in CoA (caches original states)
			self.main_window.coa.begin_transform_group(selected_uuids)
			
			self._drag_start_layers = []
			self._aabb_synced = False  # Track if we've synced AABB this drag
			for uuid in selected_uuids:
				cached = self.main_window.coa.get_cached_transform(uuid)
				if cached:
					self._drag_start_layers.append({
						'uuid': uuid,
						'pos_x': cached['pos_x'],
						'pos_y': cached['pos_y'],
						'scale_x': cached['scale_x'],
						'scale_y': cached['scale_y']
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
				
				# Scales are always positive now (flip is separate)
				layer_min_x = pos_x_orig - scale_x_orig / 2
				layer_max_x = pos_x_orig + scale_x_orig / 2
				layer_min_y = pos_y_orig - scale_y_orig / 2
				layer_max_y = pos_y_orig + scale_y_orig / 2
				
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
		
		# Calculate rotation delta (Task 3.6)
		rotation_delta = rotation - getattr(self, '_initial_group_rotation', 0)
		
		# Apply transforms to all selected layers using cached states
		import math
		for layer_state in self._drag_start_layers:
			uuid = layer_state['uuid']
			
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
				# SCALE/POSITION: Calculate scale factors and apply to offset and layer scales
				# Calculate scale factors (avoid division by zero)
				scale_factor_x = scale_x / original_scale_x if original_scale_x > 0.001 else 1.0
				scale_factor_y = scale_y / original_scale_y if original_scale_y > 0.001 else 1.0
				
				new_offset_x = offset_x * scale_factor_x
				new_offset_y = offset_y * scale_factor_y
				
				# Apply position delta
				new_pos_x = original_center_x + new_offset_x + position_delta_x
				new_pos_y = original_center_y + new_offset_y + position_delta_y
				
				# Apply scale to layer scale (scales are always positive now, flip is separate)
				new_scale_x = scale_x_orig * scale_factor_x
				new_scale_y = scale_y_orig * scale_factor_y
			
			# Clamp positions to valid range [0, 1]
			new_pos_x = max(0.0, min(1.0, new_pos_x))
			new_pos_y = max(0.0, min(1.0, new_pos_y))
			
			# Clamp individual emblem scales to [0.01, 1.0]
			# BUT: Don't clamp during rotation - rotation should not affect scale at all
			if not self.transform_widget.is_rotating:
				new_scale_x = max(0.01, min(1.0, new_scale_x))
				new_scale_y = max(0.01, min(1.0, new_scale_y))
			
			# Update actual layer (flip_x and flip_y are preserved automatically)
			layer = self.main_window.coa.get_layer_by_uuid(uuid)
			if not layer:
				continue
			layer.pos_x = new_pos_x
			layer.pos_y = new_pos_y
			layer.scale_x = new_scale_x
			layer.scale_y = new_scale_y
			# Task 3.6: Individual layer rotations are preserved (NOT modified)
		
		# Update canvas during drag for real-time feedback
		self.canvas_widget.set_coa(self.main_window.coa)
	
	def _on_transform_ended(self):
		"""Handle transform widget drag end"""
		# Clear CoA transform cache
		if self.main_window and self.main_window.coa:
			self.main_window.coa.end_transform_group()
		
		# Update canvas
		self.canvas_widget.set_coa(self.main_window.coa)
		self._drag_start_layers = None
		self._drag_start_aabb = None
		
		# Reload properties to update UI with final values
		if self.property_sidebar:
			self.property_sidebar._load_layer_properties()
		
		# Update transform widget to reset rotation to 0 for multi-selection
		self.update_transform_widget_for_layer()
		
		if self.main_window and hasattr(self.main_window, '_save_state'):
			self.main_window._save_state("Transform layer")
	
	def _on_non_uniform_scale_used(self):
		"""Handle non-uniform scaling from transform widget - disable unified scale"""
		if self.property_sidebar and hasattr(self.property_sidebar, 'unified_scale_check'):
			if self.property_sidebar.unified_scale_check.isChecked():
				self.property_sidebar.unified_scale_check.setChecked(False)
	
	def _on_layer_duplicated(self):
		"""Handle Ctrl+drag layer duplication - duplicate goes BELOW original"""
		if self.main_window and hasattr(self.main_window, 'duplicate_selected_layer_below'):
			self.main_window.duplicate_selected_layer_below()
	
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
