# PyQt5 imports
from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSizePolicy, QMenu, QCheckBox)
from PyQt5.QtCore import Qt

# Local component imports
from .canvas_widget_NEW import CoatOfArmsCanvas
from .transform_widget import TransformWidget


class CanvasArea(QFrame):
	"""Center canvas area for coat of arms preview"""
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setStyleSheet("QFrame { background-color: #141414; }")
		self.setContextMenuPolicy(Qt.CustomContextMenu)
		self.customContextMenuRequested.connect(self._show_context_menu)
		self.setMinimumWidth(800)  # Ensure canvas area has enough space
		
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
		
		# Top preview control bar (UI chrome in main layout)
		self.preview_bar = self._create_preview_bar()
		self.preview_bar.raise_()  # Ensure preview bar is on top
		layout.addWidget(self.preview_bar)
		
		# Container - PURE CONCEPTUAL BARRIER (no styling, no properties)
		# Exists ONLY as mathematical/organizational boundary
		# Mathematical assumption: container dimensions == canvas_widget dimensions
		canvas_container = QFrame()
		canvas_container_layout = QVBoxLayout(canvas_container)
		canvas_container_layout.setContentsMargins(0, 0, 0, 0)
		canvas_container_layout.setSpacing(0)
		
		# OpenGL canvas widget (fills 100% of container - stretch=1, no margins)
		self.canvas_widget = CoatOfArmsCanvas(canvas_container)
		self.canvas_widget.canvas_area = self  # Give canvas access to canvas_area
		# Widget fills container - zoom handled by scaling rendering, not widget size
		canvas_container_layout.addWidget(self.canvas_widget, stretch=1)
		
		# Transform widget (parented to canvas_container, absolute positioned overlay)
		# NOT added to layout - manually positioned/sized to overlay container's area
		# Parent to canvas_container (not canvas_widget) to avoid edge clipping
		# Pass canvas_widget as reference for coordinate calculations
		self.transform_widget = TransformWidget(canvas_container, self.canvas_widget)
		self.transform_widget.set_visible(False)
		self.transform_widget.transformChanged.connect(self._on_transform_changed)
		self.transform_widget.transformEnded.connect(self._on_transform_ended)
		self.transform_widget.nonUniformScaleUsed.connect(self._on_non_uniform_scale_used)
		self.transform_widget.layerDuplicated.connect(self._on_layer_duplicated)
		
		layout.addWidget(canvas_container, stretch=1)
		
		# Bottom bar (UI chrome in main layout)
		bottom_bar = self._create_bottom_bar()
		layout.addWidget(bottom_bar)
	
	def _create_preview_bar(self):
		"""Create the top preview control bar with government type and rank selection"""
		preview_bar = QFrame()
		preview_bar.setStyleSheet("QFrame { background-color: #2d2d2d; border: none; }")
		preview_bar.setFixedHeight(40)
		
		layout = QHBoxLayout(preview_bar)
		layout.setContentsMargins(8, 4, 8, 4)
		layout.setSpacing(8)
		
		# Government type dropdown - auto-populated from mask files
		government_label = QLabel("Government:")
		government_label.setStyleSheet("font-size: 11px; border: none;")
		layout.addWidget(government_label)
		
		# Discover government types from realm_frames directory
		government_types = self._discover_government_types()
		
		self.government_combo = self._create_combo_box(government_types)
		self.government_combo.setMinimumWidth(180)
		self.government_combo.currentIndexChanged.connect(self._on_government_changed)
		layout.addWidget(self.government_combo)
		
		# Rank dropdown
		rank_label = QLabel("Rank:")
		rank_label.setStyleSheet("font-size: 11px; border: none;")
		layout.addWidget(rank_label)
		ranks = ["Baron", "Count", "Duke", "King", "Emperor", "Hegemon"]
		self.rank_combo = self._create_combo_box(ranks)
		self.rank_combo.setMinimumWidth(120)
		self.rank_combo.setCurrentIndex(2)  # Default to Duke
		self.rank_combo.currentIndexChanged.connect(self._on_rank_changed)
		layout.addWidget(self.rank_combo)
		
		# Size dropdown (pixel sizes)
		size_label = QLabel("Size:")
		size_label.setStyleSheet("font-size: 11px; border: none;")
		layout.addWidget(size_label)
		sizes = ["28px", "44px", "62px", "86px", "115px"]
		self.size_combo = self._create_combo_box(sizes)
		self.size_combo.setMinimumWidth(100)
		self.size_combo.setCurrentIndex(3)  # Default to 86px
		self.size_combo.currentIndexChanged.connect(self._on_size_changed)
		layout.addWidget(self.size_combo)
		
		layout.addStretch()
		
		# Preview toggle checkbox (right-aligned)
		self.preview_toggle = QCheckBox("Preview")
		self.preview_toggle.setChecked(False)
		self.preview_toggle.setStyleSheet("QCheckBox { color: #ffffff; }")
		self.preview_toggle.toggled.connect(self._on_preview_toggle)
		layout.addWidget(self.preview_toggle)
		
		return preview_bar
	
	def _discover_government_types(self):
		"""Discover government types from realm_frames mask files"""
		from pathlib import Path
		from utils.path_resolver import get_resource_path
		
		try:
			realm_frames_dir = get_resource_path('..', 'ck3_assets', 'realm_frames')
			if not Path(realm_frames_dir).exists():
				# Fallback to hardcoded list if directory doesn't exist
				return ["Feudal", "Clan"]
			
			# Find all mask files
			governments = []
			self.government_file_map = {}  # Map display name -> filename
			
			for mask_file in sorted(Path(realm_frames_dir).glob("*_mask.png")):
				gov_key = mask_file.stem.replace("_mask", "")
				
				# Convert filename to display name
				if gov_key == "_default":
					display_name = "Feudal"
				else:
					# Remove _government suffix and convert to title case
					display_name = gov_key.replace("_government", "").replace("_", " ").title()
				
				governments.append(display_name)
				self.government_file_map[display_name] = gov_key
			
			return governments if governments else ["Feudal", "Clan"]
			
		except Exception as e:
			print(f"Error discovering governments: {e}")
			return ["Feudal", "Clan"]
	
	def _on_preview_toggle(self, checked):
		"""Handle preview toggle"""
		if self.canvas_widget:
			self.canvas_widget.set_preview_enabled(checked)
	
	def _on_government_changed(self, index):
		"""Handle government type change"""
		if self.canvas_widget:
			# Get display name from dropdown
			display_name = self.government_combo.currentText()
			# Map to file key
			gov_key = self.government_file_map.get(display_name, "_default")
			self.canvas_widget.set_preview_government(gov_key)
	
	def _on_rank_changed(self, index):
		"""Handle rank change"""
		if self.canvas_widget:
			self.canvas_widget.set_preview_rank(self.rank_combo.currentText())
	
	def _on_size_changed(self, index):
		"""Handle size change"""
		if self.canvas_widget:
			# Map index to size
			size_map = {0: 28, 1: 44, 2: 62, 3: 86, 4: 115}
			size = size_map.get(index, 86)
			self.canvas_widget.set_preview_size(size)
	
	def _create_bottom_bar(self):
		"""Create the bottom bar with frame and splendor dropdowns"""
		bottom_bar = QFrame()
		bottom_bar.setStyleSheet("QFrame { background-color: #2d2d2d; border: none; }")
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
		self.frame_combo.setFixedWidth(120)  # Narrower width
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
		
		# Rotation mode dropdown
		rotation_label = QLabel("Rotation:")
		rotation_label.setStyleSheet("font-size: 11px; border: none;")
		bottom_layout.addWidget(rotation_label)
		
		self.rotation_mode_combo = self._create_combo_box([
			"Rotate Only",
			"Orbit Only",
			"Normal",
			"Rotate (Deep)",
			"Orbit (Deep)"
		])
		self.rotation_mode_combo.setFixedWidth(120)  # Narrower width
		self.rotation_mode_combo.setToolTip(
			"Rotation Mode:\n"
			"Rotate Only - Spin layers in place\n"
			"Orbit Only - Orbit layers around center\n"
			"Normal - Orbit + Rotate layers\n"
			"Rotate (Deep) - Spin all instances in place\n"
			"Orbit (Deep) - Orbit all instances around center"
		)
		self.rotation_mode_combo.setCurrentIndex(2)  # Default to Normal
		bottom_layout.addWidget(self.rotation_mode_combo)
		
		bottom_layout.addSpacing(20)
		
		# Add transform mode dropdown
		from PyQt5.QtWidgets import QPushButton, QComboBox
		self.transform_mode_combo = QComboBox()
		self.transform_mode_combo.addItems(["Normal", "Minimal", "Gimble"])
		self.transform_mode_combo.setCurrentIndex(0)  # Default to Normal
		self.transform_mode_combo.setToolTip("Transform Widget Mode (M)\nNormal: Scale + rotation handles\nMinimal: Corners only\nGimble: Position arrows + rotation ring")
		self.transform_mode_combo.setFixedHeight(20)
		self.transform_mode_combo.setStyleSheet("""
			QComboBox {
				font-size: 11px;
				padding: 2px 4px;
				border: 1px solid rgba(255, 255, 255, 40);
				background-color: rgba(40, 40, 40, 200);
				color: white;
			}
			QComboBox::drop-down {
				border: none;
			}
			QComboBox QAbstractItemView {
				background-color: rgba(40, 40, 40, 240);
				color: white;
				selection-background-color: rgba(100, 150, 255, 100);
			}
		""")
		self.transform_mode_combo.currentIndexChanged.connect(self._on_transform_mode_changed)
		bottom_layout.addWidget(self.transform_mode_combo)
		
		# Add layer picker tool button
		self.picker_btn = QPushButton("🎯")
		self.picker_btn.setCheckable(True)
		self.picker_btn.setToolTip("Layer Picker Tool\nClick to select layer under mouse cursor")
		self.picker_btn.setFixedSize(24, 20)
		self.picker_btn.setStyleSheet("""
			QPushButton { 
				font-size: 14px; 
				padding: 0px; 
				border: 1px solid rgba(255, 255, 255, 40); 
			}
			QPushButton:checked {
				background-color: rgba(100, 150, 255, 100);
				border: 1px solid rgba(100, 150, 255, 180);
			}
		""")
		self.picker_btn.toggled.connect(self._on_picker_button_toggled)
		bottom_layout.addWidget(self.picker_btn)
		
		# Add show selection toggle button
		self.show_selection_btn = QPushButton("👁")
		self.show_selection_btn.setCheckable(True)
		self.show_selection_btn.setChecked(False)
		self.show_selection_btn.setToolTip("Show Selection Tint\nHighlight selected layers in red")
		self.show_selection_btn.setFixedSize(24, 20)
		self.show_selection_btn.setStyleSheet("""
			QPushButton { 
				font-size: 14px; 
				padding: 0px; 
				border: 1px solid rgba(255, 255, 255, 40); 
			}
			QPushButton:checked {
				background-color: rgba(255, 100, 100, 100);
				border: 1px solid rgba(255, 100, 100, 180);
			}
		""")
		self.show_selection_btn.toggled.connect(self._on_show_selection_toggled)
		bottom_layout.addWidget(self.show_selection_btn)
		
		bottom_layout.addStretch()
		
		return bottom_bar
	
	def get_rotation_mode(self):
		"""Get current rotation mode from dropdown
		
		Returns:
			String mode name for CoA.rotate_selection()
		"""
		mode_map = {
			"Rotate Only": "rotate_only",
			"Orbit Only": "orbit_only",
			"Normal": "both",
			"Rotate (Deep)": "rotate_only_deep",
			"Orbit (Deep)": "orbit_only_deep"
		}
		if not hasattr(self, 'rotation_mode_combo'):
			return "both"
		current_text = self.rotation_mode_combo.currentText()
		return mode_map.get(current_text, "both")
	
	def _create_combo_box(self, items):
		"""Create a styled combo box with unicode down arrow"""
		combo = QComboBox()
		combo.addItems(items)
		combo.setStyleSheet("""
			QComboBox {
				padding: 5px 10px;
				padding-right: 25px;
				border-radius: 3px;
				border: none;
			}
			QComboBox::drop-down {
				border: none;
				width: 20px;
			}
			QComboBox::down-arrow {
				image: none;
			}
		""")
		
		# Create a label with unicode down arrow and position it
		from PyQt5.QtWidgets import QLabel
		from PyQt5.QtCore import Qt
		arrow_label = QLabel("▼", combo)
		arrow_label.setStyleSheet("color: #aaa; font-size: 10px; background: transparent;")
		arrow_label.setAttribute(Qt.WA_TransparentForMouseEvents)
		arrow_label.setAlignment(Qt.AlignCenter)
		
		# Position the arrow on the right side
		def update_arrow_position():
			arrow_label.setGeometry(combo.width() - 20, 0, 20, combo.height())
		
		# Override resizeEvent properly
		original_resize = combo.resizeEvent
		def resize_with_arrow(event):
			original_resize(event)
			update_arrow_position()
		combo.resizeEvent = resize_with_arrow
		update_arrow_position()
		
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
		self.transform_widget.active_handle = None
		self.transform_widget.drag_start_pos = None
		self.transform_widget.drag_start_transform = None
		self.transform_widget.drag_context = None
		
		# Reset initial group state when selection changes (Task 3.6)
		self._initial_group_center = None
		self._initial_group_rotation = 0
		
		# Don't show transform widget if picker tool is active
		if hasattr(self, 'picker_btn') and self.picker_btn.isChecked():
			self.transform_widget.set_visible(False)
			return
		
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
		
		# SINGLE SELECTION
		if len(selected_uuids) == 1:
			uuid = list(selected_uuids)[0]
			# Read from CoA model for transform widget positioning
			if not self.main_window or not self.main_window.coa:
				self.transform_widget.set_visible(False)
				return
			
			# Check if layer has multiple instances - treat as group transform
			instance_count = self.main_window.coa.get_layer_instance_count(uuid)
			
			if instance_count > 1:
				# Multi-instance layer: use AABB of all instances (group transform)
				try:
					bounds = self.main_window.coa.get_layer_bounds(uuid)
					group_pos_x = bounds['center_x']
					group_pos_y = bounds['center_y']
					group_scale_x = bounds['width']
					group_scale_y = bounds['height']
					group_rotation = 0
					
					# Convert CoA space to canvas pixels (Decision 3)
					center_x_topleft, center_y_topleft = self.canvas_widget.coa_to_canvas(group_pos_x, group_pos_y)
					half_w, half_h = self.canvas_widget.coa_scale_to_pixels(group_scale_x, group_scale_y)
										# Convert from top-left to center-origin coordinates
					center_x = center_x_topleft - self.transform_widget.width() / 2
					center_y = center_y_topleft - self.transform_widget.height() / 2
					
					# Pass is_multi_selection=True for group behavior
					self.transform_widget.set_transform(center_x, center_y, half_w, half_h, group_rotation, is_multi_selection=True)
					self.transform_widget.set_visible(True)
					return
				except ValueError:
					self.transform_widget.set_visible(False)
					return
			else:
				# Single instance: show layer transform directly
				pos_x = self.main_window.coa.get_layer_pos_x(uuid)
				pos_y = self.main_window.coa.get_layer_pos_y(uuid)
				scale_x = self.main_window.coa.get_layer_scale_x(uuid)
				scale_y = self.main_window.coa.get_layer_scale_y(uuid)
				rotation = self.main_window.coa.get_layer_rotation(uuid)
				
				if pos_x is None or pos_y is None:
					self.transform_widget.set_visible(False)
					return
				
				# Convert CoA space to canvas pixels (Decision 3)
				center_x_topleft, center_y_topleft = self.canvas_widget.coa_to_canvas(pos_x, pos_y)
				half_w, half_h = self.canvas_widget.coa_scale_to_pixels(scale_x, scale_y)
				
				# Convert from top-left to center-origin coordinates
			center_x = center_x_topleft - self.transform_widget.width() / 2
			center_y = center_y_topleft - self.transform_widget.height() / 2
		
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
		
		# Convert CoA space group AABB to frame-adjusted visual space
		frame_x, frame_y = self.canvas_widget.coa_to_frame(group_pos_x, group_pos_y)
		frame_scale, _ = self.canvas_widget.get_frame_transform()
		frame_scale_x = group_scale_x * frame_scale[0]
		frame_scale_y = group_scale_y * frame_scale[1]
	
		# Store initial group state for rotation calculations (Task 3.6)
		if not hasattr(self, '_initial_group_center'):
			self._initial_group_center = (group_pos_x, group_pos_y)
			self._initial_group_rotation = 0
		
		# For multi-selection, start rotation at 0
		group_rotation = 0
		
		# Convert to canvas pixels then to center-origin
		center_x_topleft, center_y_topleft = self.canvas_widget.frame_to_canvas(frame_x, frame_y)
		half_w, half_h = self.canvas_widget.coa_scale_to_pixels(group_scale_x, group_scale_y)
		
		# Convert from top-left to center-origin coordinates
		center_x = center_x_topleft - self.transform_widget.width() / 2
		center_y = center_y_topleft - self.transform_widget.height() / 2
		
		# Pass is_multi_selection=True to skip scale clamping (AABB can exceed 1.0)
		self.transform_widget.set_transform(center_x, center_y, half_w, half_h, group_rotation, is_multi_selection=True)
		self.transform_widget.set_visible(True)

	def _on_transform_changed(self, center_x, center_y, half_w, half_h, rotation):
		"""Handle transform changes from the widget (pixel space → CoA space).
		
		For rotation: routes through CoA.rotate_selection() using rotation mode dropdown
		For single selection with multiple instances: group transform around AABB center
		For single selection with one instance: direct transform
		For multi-selection: applies group transform to all selected layers
		
		Note: Widget sends canvas center-origin pixels, convert to top-left then to CoA space (Decision 3)
		"""
		selected_uuids = self.property_sidebar.get_selected_uuids() if self.property_sidebar else []
		if not selected_uuids:
			return
		
		# Convert from center-origin to top-left coordinates first
		center_x_topleft = center_x + self.transform_widget.width() / 2
		center_y_topleft = center_y + self.transform_widget.height() / 2
		
		# Convert canvas pixels back to CoA space (Decision 3)
		pos_x, pos_y = self.canvas_widget.canvas_to_coa(center_x_topleft, center_y_topleft)
		scale_x, scale_y = self.canvas_widget.pixels_to_coa_scale(half_w, half_h)
		
		# Check if we're rotating (using rotation handle)
		if hasattr(self.transform_widget, 'is_rotating') and self.transform_widget.is_rotating:
			# ROTATION: Apply from cached state for dynamic preview
			if not hasattr(self, '_rotation_start') or self._rotation_start is None:
				# First rotation frame - cache state
				self._rotation_start = rotation
				rotation_mode = self.get_rotation_mode()
				self.main_window.coa.begin_rotation_transform(list(selected_uuids), rotation_mode)
			
			# Calculate TOTAL delta from start
			total_delta = rotation - self._rotation_start
			
			# Apply rotation from cached state (prevents compounding)
			self.main_window.coa.apply_rotation_transform(list(selected_uuids), total_delta)
			
			# Update canvas for live preview
			self.canvas_widget.update()
			return
		
		# POSITION/SCALE TRANSFORMS (non-rotation)
		# SINGLE SELECTION
		if len(selected_uuids) == 1:
			uuid = list(selected_uuids)[0]
			instance_count = self.main_window.coa.get_layer_instance_count(uuid)
			
			# MULTI-INSTANCE: Use group transform relative to AABB center
			if instance_count > 1:
				# Cache initial AABB at drag start
				if not hasattr(self, '_single_layer_aabb') or self._single_layer_aabb is None:
					# Begin caching in CoA
					self.main_window.coa.begin_instance_group_transform(uuid)
					
					bounds = self.main_window.coa.get_layer_bounds(uuid)
					self._single_layer_aabb = {
						'center_x': bounds['center_x'],
						'center_y': bounds['center_y'],
						'width': bounds['width'],
						'height': bounds['height']
					}
					self._initial_instance_rotation = 0  # Widget starts at 0 for group
				
				# Calculate transform relative to CACHED original AABB (doesn't change)
				original_center_x = self._single_layer_aabb['center_x']
				original_center_y = self._single_layer_aabb['center_y']
				original_width = self._single_layer_aabb['width']
				original_height = self._single_layer_aabb['height']
				
				# Calculate scale factors
				scale_factor_x = scale_x / original_width if original_width > 0.001 else 1.0
				scale_factor_y = scale_y / original_height if original_height > 0.001 else 1.0
				
				# Calculate rotation delta
				rotation_delta = rotation - self._initial_instance_rotation
				
				# Apply group transform using CoA method (uses cached original positions)
				self.main_window.coa.transform_instances_as_group(
					uuid, pos_x, pos_y, scale_factor_x, scale_factor_y, rotation_delta
				)
			
			else:
				# SINGLE INSTANCE: Direct transform (no group behavior needed)
				self.main_window.coa.set_layer_position(uuid, pos_x, pos_y)
				self.main_window.coa.set_layer_scale(uuid, scale_x, scale_y)
				self.main_window.coa.set_layer_rotation(uuid, rotation)
			
			self.canvas_widget.update()
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
				# For multi-instance layers, use AABB bounds instead of first instance
				instance_count = self.main_window.coa.get_layer_instance_count(uuid)
				if instance_count > 1:
					# Multi-instance: use layer's AABB
					bounds = self.main_window.coa.get_layer_bounds(uuid)
					self._drag_start_layers.append({
						'uuid': uuid,
						'pos_x': bounds['center_x'],
						'pos_y': bounds['center_y'],
						'scale_x': bounds['width'],
						'scale_y': bounds['height'],
						'is_multi_instance': True
					})
				else:
					# Single instance: use cached transform
					cached = self.main_window.coa.get_cached_transform(uuid)
					if cached:
						self._drag_start_layers.append({
							'uuid': uuid,
							'pos_x': cached['pos_x'],
							'pos_y': cached['pos_y'],
							'scale_x': cached['scale_x'],
							'scale_y': cached['scale_y'],
							'is_multi_instance': False
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
			
			# Update layer: multi-instance layers need group transform
			if layer_state.get('is_multi_instance', False):
				# Multi-instance layer: transform all instances as a group
				# Calculate scale factors relative to original AABB
				scale_factor_x = new_scale_x / scale_x_orig if scale_x_orig > 0.001 else 1.0
				scale_factor_y = new_scale_y / scale_y_orig if scale_y_orig > 0.001 else 1.0
				
				# Use instance group transform (with cached positions)
				if not hasattr(self, f'_instance_transform_begun_{uuid}'):
					self.main_window.coa.begin_instance_group_transform(uuid)
					setattr(self, f'_instance_transform_begun_{uuid}', True)
				
				self.main_window.coa.transform_instances_as_group(
					uuid, new_pos_x, new_pos_y, scale_factor_x, scale_factor_y, 0.0
				)
			else:
				# Single instance layer: direct transform
				self.main_window.coa.set_layer_position(uuid, new_pos_x, new_pos_y)
				self.main_window.coa.set_layer_scale(uuid, new_scale_x, new_scale_y)
			# Task 3.6: Individual layer rotations are preserved (NOT modified)
		
		# Update canvas during drag for real-time feedback
		self.canvas_widget.update()
	
	def _on_transform_ended(self):
		"""Handle transform widget drag end"""
		# Clear rotation cache (rotation already applied during drag)
		if hasattr(self, '_rotation_start') and self._rotation_start is not None:
			self.main_window.coa.end_rotation_transform()
		
		# Clear CoA transform caches
		if self.main_window and self.main_window.coa:
			self.main_window.coa.end_transform_group()
			self.main_window.coa.end_instance_group_transform()
		
		# Clear instance transform flags
		attrs_to_remove = [attr for attr in dir(self) if attr.startswith('_instance_transform_begun_')]
		for attr in attrs_to_remove:
			delattr(self, attr)
		
		# Clear single layer state caches
		self._single_layer_initial_state = None
		self._single_layer_aabb = None
		self._initial_instance_rotation = 0
		self._rotation_start = None  # Clear rotation tracking
		
		# Update canvas
		self.canvas_widget.update()
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
		"""Handle Ctrl+drag layer duplication - duplicate goes BELOW original, keep original selected"""
		if self.main_window and hasattr(self.main_window, 'clipboard_actions'):
			self.main_window.clipboard_actions.duplicate_selected_layer_below(keep_selection=True)
	
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
	
	def _show_context_menu(self, pos):
		"""Show context menu with Edit menu actions"""
		if not self.main_window or not hasattr(self.main_window, 'edit_menu'):
			return
		
		# Create context menu and add Edit menu actions
		context_menu = QMenu(self)
		for action in self.main_window.edit_menu.actions():
			if action.isSeparator():
				context_menu.addSeparator()
			else:
				context_menu.addAction(action)
		
		context_menu.exec_(self.mapToGlobal(pos))
	
	def _on_splendor_changed(self, index):
		"""Handle splendor level change"""
		self.canvas_widget.set_splendor(index)
	
	def _on_picker_button_toggled(self, checked):
		"""Handle layer picker button toggle"""
		if checked:
			self.canvas_widget.set_tool_mode('layer_picker')
		else:
			# Deactivate picker and re-enable transform widget (keeps selection)
			self.canvas_widget.set_tool_mode(None)
			self.update_transform_widget_for_layer()
	
	def _on_show_selection_toggled(self, checked):
		"""Handle show selection button toggle"""
		# Trigger canvas update to show/hide selection tint
		self.canvas_widget.update()
	
	def _on_transform_mode_changed(self, index):
		"""Handle transform mode dropdown change"""
		mode = ["normal", "minimal", "gimble"][index]
		self.transform_widget.set_transform_mode(mode)
	
	# ========================================
	# Coordinate Conversion Methods
	# ========================================
	
	def canvas_area_to_canvas(self, x, y):
		"""Convert CanvasArea pixel coordinates to Canvas widget pixel coordinates.
		
		Args:
			x: X coordinate in CanvasArea space (Qt widget pixels)
			y: Y coordinate in CanvasArea space (Qt widget pixels)
			
		Returns:
			(canvas_x, canvas_y): Canvas widget pixel coordinates
		"""
		# Get canvas widget position within CanvasArea
		canvas_geometry = self.canvas_widget.geometry()
		canvas_x = x - canvas_geometry.x()
		canvas_y = y - canvas_geometry.y()
		return canvas_x, canvas_y
	
	def canvas_to_canvas_area(self, canvas_x, canvas_y):
		"""Convert Canvas widget pixel coordinates to CanvasArea pixel coordinates.
		
		Args:
			canvas_x: X coordinate in Canvas widget space
			canvas_y: Y coordinate in Canvas widget space
			
		Returns:
			(x, y): CanvasArea pixel coordinates
		"""
		# Get canvas widget position within CanvasArea
		canvas_geometry = self.canvas_widget.geometry()
		x = canvas_x + canvas_geometry.x()
		y = canvas_y + canvas_geometry.y()
		return x, y
	
	def canvas_area_to_canvas_widget(self, x, y):
		"""Convert CanvasArea top-left coords to canvas_widget CENTER-ORIGIN coords.
		
		Handles BOTH:
		1. Position translation (CanvasArea → canvas_widget local space)
		2. Origin shift (Qt top-left → graphics center-origin)
		
		Args:
			x: X coordinate in CanvasArea space (Qt widget, top-left origin)
			y: Y coordinate in CanvasArea space (Qt widget, top-left origin)
			
		Returns:
			(center_x, center_y): Canvas widget center-origin coordinates
		"""
		canvas_geom = self.canvas_widget.geometry()
		
		# Translate to canvas_widget local space
		local_x = x - canvas_geom.x()
		local_y = y - canvas_geom.y()
		
		# Shift origin from top-left to center
		center_x = local_x - canvas_geom.width() / 2
		center_y = local_y - canvas_geom.height() / 2
		
		return center_x, center_y
	
	def canvas_widget_to_canvas_area(self, center_x, center_y):
		"""Convert canvas_widget CENTER-ORIGIN coords to CanvasArea top-left coords.
		
		Handles BOTH:
		1. Origin shift (graphics center-origin → Qt top-left)
		2. Position translation (canvas_widget local space → CanvasArea)
		
		Args:
			center_x: X coordinate in canvas_widget center-origin space
			center_y: Y coordinate in canvas_widget center-origin space
			
		Returns:
			(x, y): CanvasArea top-left origin coordinates
		"""
		canvas_geom = self.canvas_widget.geometry()
		
		# Shift origin from center back to top-left
		local_x = center_x + canvas_geom.width() / 2
		local_y = center_y + canvas_geom.height() / 2
		
		# Translate to CanvasArea space
		return local_x + canvas_geom.x(), local_y + canvas_geom.y()
