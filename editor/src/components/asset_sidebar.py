# PyQt5 imports
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QScrollArea, QPushButton, QWidget, QComboBox, QMenu
)
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap

# Component imports
from .flow_layout import FlowLayout

# Standard library imports
import json
import os
from constants import (
    DEFAULT_BASE_CATEGORY, DEFAULT_EMBLEM_CATEGORY,
    DEFAULT_BASE_COLOR1, DEFAULT_BASE_COLOR2, DEFAULT_BASE_COLOR3,
    DEFAULT_EMBLEM_COLOR1, DEFAULT_EMBLEM_COLOR2, DEFAULT_EMBLEM_COLOR3,
    CK3_NAMED_COLORS
)
from utils.atlas_compositor import composite_emblem_atlas, composite_pattern_atlas, get_atlas_path
from utils.path_resolver import get_emblem_metadata_path, get_pattern_metadata_path, get_emblem_source_dir, get_pattern_source_dir

# Global dictionary mapping texture filenames to preview image paths
# Key: filename (e.g., "ce_kamon_sorrel.dds"), Value: preview path
TEXTURE_PREVIEW_MAP = {}


class AssetSidebar(QFrame):
	"""Left sidebar for browsing and selecting assets"""
	
	# Signal emitted when an asset is selected, passes the asset data
	asset_selected = pyqtSignal(dict)
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.parent_window = parent
		self.size_buttons = {}
		self.current_icon_size = 80  # Default M size
		self.current_category = None  # Will be set after loading data
		self.asset_buttons = []
		self.current_mode = "patterns"  # Start in patterns mode (Base tab)
		self.last_emblem_category = DEFAULT_EMBLEM_CATEGORY  # Remember last viewed emblem category
		self.right_sidebar = None  # Will be set by parent to access layer colors
		
		# Track stacked emblem widgets for fast color updates
		self.emblem_widgets = []
		
		# Load asset data from JSON files
		self.asset_data = self._load_asset_data()
		
		# Set default category to base patterns on startup
		self.current_category = DEFAULT_BASE_CATEGORY
		
		self.setMinimumWidth(200)
		self.setMaximumWidth(400)
		
		self._setup_ui()
	
	def _load_asset_data(self):
		"""Load asset definitions from JSON files"""
		asset_data = {}
		
		# Load emblems and organize by category
		emblems_json = get_emblem_metadata_path()
		textured_emblems_json = "json_output/coat_of_arms/colored_emblems/50_coa_designer_emblems.json"  # Legacy path, may not exist
		if emblems_json.exists():
			with open(emblems_json, 'r', encoding='utf-8') as f:
				data = json.load(f)
				# Validate data is a dictionary
				if not isinstance(data, dict):
					print(f"Warning: Invalid emblem metadata format in {emblems_json}")
					data = {}
				for filename, properties in data.items():
					if properties is None or filename == "\ufeff" or not isinstance(properties, dict):
						continue
					# Convert .dds to .png
					png_filename = filename.replace('.dds', '.png')
					image_path = get_emblem_source_dir() / png_filename
					if image_path.exists():
						# Add to preview map
						TEXTURE_PREVIEW_MAP[filename] = image_path
						
						category = properties.get("category", None)
						colors = properties.get("colors", 1)
						
						# Skip assets without a category or with 0 colors (blank/empty assets)
						if not category or colors == 0:
							continue
						
						category = category.title()
						if category not in asset_data:
							asset_data[category] = []
						asset_data[category].append({
							"filename": png_filename,  # PNG for display
							"dds_filename": filename,  # DDS for texture lookup
							"path": str(image_path),
							"category": category,
							"colors": colors
						})
		if os.path.exists(textured_emblems_json):
			with open(textured_emblems_json, 'r', encoding='utf-8') as f:
				data = json.load(f)
				# Validate data is a dictionary
				if not isinstance(data, dict):
					print(f"Warning: Invalid textured emblem metadata format")
					data = {}
				for filename, properties in data.items():
					if properties is None or filename == "\ufeff" or not isinstance(properties, dict):
						continue
					# Convert .dds to .png (textured emblems use legacy path, may not exist in new structure)
					png_filename = filename.replace('.dds', '.png')
					image_path = f"ck3_assets/coat_of_arms/textured_emblems/{png_filename}"
					if os.path.exists(image_path):
						# Add to preview map
						TEXTURE_PREVIEW_MAP[filename] = image_path
						
						category = properties.get("category", None)
						# Skip assets without a category
						if not category:
							continue
						category = "Textured " + category.title()
						if category not in asset_data:
							asset_data[category] = []
						asset_data[category].append({
							"filename": png_filename,  # PNG for display
							"dds_filename": filename,  # DDS for texture lookup
							"path": image_path,
							"category": category,
							"colors": properties.get("colors", 1)
						})
		
		# Load base patterns (background layer - separate from emblems)
		patterns_json = get_pattern_metadata_path()
		if patterns_json.exists():
			asset_data["__Base_Patterns__"] = []  # Special key for base patterns
			with open(patterns_json, 'r', encoding='utf-8') as f:
				data = json.load(f)
				# Validate data is a dictionary
				if not isinstance(data, dict):
					print(f"Warning: Invalid pattern metadata format in {patterns_json}")
					data = {}
				for filename, properties in data.items():
					if properties is None or filename == "\ufeff" or not isinstance(properties, dict):
						continue
					# Convert .dds to .png for display
					png_filename = filename.replace('.dds', '.png')
					image_path = get_pattern_source_dir() / png_filename
					if image_path.exists():
						# Add to preview map
						TEXTURE_PREVIEW_MAP[filename] = str(image_path)
						
						asset_data["__Base_Patterns__"].append({
							"filename": filename,  # Store .dds name for texture lookup
							"display_name": png_filename,  # PNG name for display
							"path": str(image_path),
							"colors": properties.get("colors", 1),
							"visible": properties.get("visible", True)
						})
		
		return asset_data
	
	def _setup_ui(self):
		"""Setup the asset sidebar UI"""
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		
		# Header
		header = QLabel("Assets")
		header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
		layout.addWidget(header)
		
		# Category dropdown
		category_layout = QHBoxLayout()
		category_layout.setSpacing(8)
		category_layout.setContentsMargins(10, 0, 10, 5)
		
		category_label = QLabel("Category:")
		category_label.setStyleSheet("font-size: 11px;")
		category_layout.addWidget(category_label)
		
		self.category_combo = QComboBox()
		# Build category list: only emblem categories (not base patterns)
		emblem_categories = sorted([k for k in self.asset_data.keys() if not k.startswith("__")])
		# Block signals during initialization to avoid triggering change_category
		self.category_combo.blockSignals(True)
		self.category_combo.addItems(emblem_categories)
		if self.current_category and not self.current_category.startswith("__"):
			self.category_combo.setCurrentText(self.current_category)
		# Hide category dropdown initially (showing base patterns)
		self.category_combo.setVisible(False)
		self.category_combo.blockSignals(False)
		self.category_combo.currentTextChanged.connect(self.change_category)
		self.category_combo.setStyleSheet("""
			QComboBox {
				padding: 4px 8px;
				border-radius: 3px;
				font-size: 11px;
			}
		""")
		category_layout.addWidget(self.category_combo, 1)
		
		layout.addLayout(category_layout)
		
		# Size filter buttons
		size_layout = QHBoxLayout()
		size_layout.setSpacing(4)
		size_layout.setContentsMargins(10, 5, 10, 5)
		
		sizes = [("S", 60), ("M", 80), ("L", 120), ("XL", 180)]
		for size_label, size_value in sizes:
			btn = QPushButton(size_label)
			btn.setCheckable(True)
			btn.setChecked(size_value == 80)  # M is default
			btn.clicked.connect(lambda checked, s=size_value, l=size_label: self.resize_assets(s, l))
			btn.setStyleSheet("""
				QPushButton {
					padding: 4px 8px;
					border-radius: 3px;
					font-size: 11px;
					min-width: 30px;
				}
				QPushButton:hover {
					background-color: rgba(255, 255, 255, 30);
				}
				QPushButton:checked {
					border: 2px solid #5a8dbf;
				}
			""")
			size_layout.addWidget(btn)
			self.size_buttons[size_label] = btn
		
		layout.addLayout(size_layout)
		
		# Scrollable asset grid
		scroll_area = QScrollArea()
		scroll_area.setWidgetResizable(True)
		scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.scroll_area = scroll_area
		
		scroll_widget = QWidget()
		scroll_layout = QVBoxLayout(scroll_widget)
		scroll_layout.setContentsMargins(10, 10, 10, 10)
		
		# Flow layout for asset icons (auto-wraps based on width)
		self.assets_flow = FlowLayout()
		self.assets_flow.setSpacing(8)
		scroll_layout.addLayout(self.assets_flow)
		scroll_layout.addStretch()
		
		self.build_asset_grid()
		
		scroll_area.setWidget(scroll_widget)
		layout.addWidget(scroll_area)
	
	def build_asset_grid(self):
		"""Build responsive grid of asset icons with dynamic color compositing"""
		# Clear previous items
		self.clear_layout(self.assets_flow)
		# Clear button list
		self.asset_buttons.clear()
		# Clear emblem widget references
		self.emblem_widgets.clear()
		
		# Get assets for current category
		assets = self._get_filtered_assets()
		
		# Get current layer colors for compositing
		colors = self._get_current_layer_colors()
		
		# No need to calculate columns - FlowLayout handles wrapping automatically
		for i, asset in enumerate(assets):
			item = QPushButton()
			item.setFixedSize(self.current_icon_size, self.current_icon_size)
			
			# For emblems: use stacked widget for performance, For patterns: use composited pixmap
			if self.current_mode == "emblems":
				# Use stacked widget approach for instant color updates
				from components.asset_widgets.stacked_emblem_widget import StackedEmblemWidget
				from utils.atlas_compositor import get_atlas_path
				from utils.color_utils import get_contrasting_background
				
				filename = asset.get('filename', '')
				atlas_path = get_atlas_path(filename, 'emblem')
				
				if atlas_path.exists():
					# Create stacked widget
					stacked_widget = StackedEmblemWidget(str(atlas_path), size=self.current_icon_size - 10)
					
					# Set background with smart contrast
					emblem_color1 = colors['color1']
					base_background_color1 = colors['background1']
					contrast_bg = get_contrasting_background(emblem_color1, base_background_color1)
					stacked_widget.set_background_color(contrast_bg)
					
					# Set colors
					stacked_widget.set_colors(colors['color1'], colors['color2'], colors['color3'])
					
					# Track widget for future color updates
					self.emblem_widgets.append(stacked_widget)
					
					# Add stacked widget to button's layout
					button_layout = QVBoxLayout(item)
					button_layout.setContentsMargins(5, 5, 5, 5)
					button_layout.addWidget(stacked_widget)
				else:
					# Fallback to static preview
					pixmap = QPixmap(asset["path"])
					if not pixmap.isNull():
						icon = QIcon(pixmap)
						item.setIcon(icon)
						item.setIconSize(QSize(self.current_icon_size - 10, self.current_icon_size - 10))
			else:
				# For patterns: use traditional composited pixmap (each has unique colors)
				pixmap = self._create_asset_preview(asset, colors)
				if not pixmap.isNull():
					icon = QIcon(pixmap)
					item.setIcon(icon)
					# Set icon size to fill the button
					item.setIconSize(QSize(self.current_icon_size - 10, self.current_icon_size - 10))
			
			item.setToolTip(asset.get("display_name", asset["filename"]))
			item.setProperty("asset_data", asset)  # Store asset data with button
			item.clicked.connect(lambda checked, b=item: self._select_asset(b))
			
			# Enable context menu
			item.setContextMenuPolicy(Qt.CustomContextMenu)
			item.customContextMenuRequested.connect(lambda pos, b=item: self._show_asset_context_menu(b, pos))
			
			item.setStyleSheet("""
				QPushButton {
					border: 1px solid rgba(255, 255, 255, 40);
					border-radius: 4px;
				}
				QPushButton:hover {
					background-color: rgba(255, 255, 255, 30);
					border: 1px solid rgba(255, 255, 255, 80);
				}
			""")
			
			self.assets_flow.addWidget(item)
	
	def _get_filtered_assets(self):
		"""Get assets filtered by current category and visibility"""
		assets = self.asset_data.get(self.current_category, [])
		# Filter out assets marked as not visible
		return [asset for asset in assets if asset.get('visible', True)]
	
	def clear_layout(self, layout):
		"""Recursively clear all widgets from a layout"""
		if layout is not None:
			while layout.count():
				item = layout.takeAt(0)
				widget = item.widget()
				if widget is not None:
					widget.deleteLater()
				else:
					self.clear_layout(item.layout())
	
	def resize_assets(self, icon_size, button_label):
		"""Resize asset icons when size button is clicked"""
		# Update all button states
		for size, btn in self.size_buttons.items():
			btn.setChecked(size == button_label)
		
		# Update current icon size
		self.current_icon_size = icon_size
		
		# Rebuild grid with new icon size
		self.build_asset_grid()
	
	def change_category(self, category):
		"""Update the asset grid when category changes"""
		self.current_category = category
		# Remember emblem category for persistence across tab changes
		if not category.startswith("__"):
			self.last_emblem_category = category
		# Properly disconnect and delete existing buttons
		for btn in self.asset_buttons:
			try:
				btn.clicked.disconnect()
			except:
				pass
			btn.deleteLater()
		self.asset_buttons.clear()
		# Clear the flow layout
		self.clear_layout(self.assets_flow)
		# Rebuild the asset grid
		"""Handle resize event to recalculate grid columns"""
		# Use timer to avoid rapid rebuilding during resize
		if not hasattr(self, '_resize_timer'):
			self._resize_timer = QTimer()
			self._resize_timer.setSingleShot(True)
			self._resize_timer.timeout.connect(self.build_asset_grid)
		
		self._resize_timer.stop()
		self._resize_timer.start(100)  # 100ms debounce
	
	def _select_asset(self, selected_button):
		"""Handle asset selection - emit signal with asset data"""
		asset_data = selected_button.property("asset_data")
		if asset_data:
			self.asset_selected.emit(asset_data)
	
	def _show_asset_context_menu(self, button, pos):
		"""Show context menu for asset button with Generate submenu (emblems only)."""
		asset_data = button.property("asset_data")
		if not asset_data:
			return
		
		# Only show Generate menu for emblems, not base patterns
		if self.current_mode != "emblems":
			return
		
		# Create context menu
		menu = QMenu(self)
		
		# Add "Generate" submenu with all generator types
		generate_menu = menu.addMenu("Generate")
		
		# Path category
		path_menu = generate_menu.addMenu("Path")
		path_menu.addAction("Circular").triggered.connect(
			lambda: self._open_generator_with_asset(asset_data, 'circular'))
		path_menu.addAction("Line").triggered.connect(
			lambda: self._open_generator_with_asset(asset_data, 'line'))
		path_menu.addAction("Spiral").triggered.connect(
			lambda: self._open_generator_with_asset(asset_data, 'spiral'))
		
		# Grid category
		grid_menu = generate_menu.addMenu("Grid")
		grid_menu.addAction("Grid").triggered.connect(
			lambda: self._open_generator_with_asset(asset_data, 'grid'))
		grid_menu.addAction("Diamond").triggered.connect(
			lambda: self._open_generator_with_asset(asset_data, 'diamond'))
		
		# Misc category
		misc_menu = generate_menu.addMenu("Misc")
		misc_menu.addAction("Fibonacci").triggered.connect(
			lambda: self._open_generator_with_asset(asset_data, 'fibonacci'))
		misc_menu.addAction("Radial").triggered.connect(
			lambda: self._open_generator_with_asset(asset_data, 'radial'))
		misc_menu.addAction("Star").triggered.connect(
			lambda: self._open_generator_with_asset(asset_data, 'star'))
		
		# Vanilla
		generate_menu.addAction("Vanilla").triggered.connect(
			lambda: self._open_generator_with_asset(asset_data, 'vanilla'))
		
		# Show menu at button position
		menu.exec_(button.mapToGlobal(pos))
	
	def _open_generator_with_asset(self, asset_data, generator_type):
		"""Open generator popup with pre-selected asset.
		
		Args:
			asset_data: Asset data dictionary
			generator_type: Type of generator to open
		"""
		if self.parent_window and hasattr(self.parent_window, '_open_generator_with_asset'):
			# Get the .dds filename for texture
			texture = asset_data.get('dds_filename', asset_data.get('filename', ''))
			self.parent_window._open_generator_with_asset(texture, generator_type)
	
	def switch_mode(self, mode):
		"""Switch between showing emblems or base patterns"""
		if mode == self.current_mode:
			return
		
		self.current_mode = mode
		
		if mode == "patterns":
			# Show base patterns - hide category dropdown
			self.category_combo.setVisible(False)
			self.current_category = "__Base_Patterns__"
		else:
			# Show emblem categories - show category dropdown
			self.category_combo.setVisible(True)
			self.category_combo.blockSignals(True)
			self.category_combo.clear()
			emblem_categories = sorted([k for k in self.asset_data.keys() if not k.startswith("__")])
			self.category_combo.addItems(emblem_categories)
			if emblem_categories:
				# Use last viewed emblem category if available, otherwise use default
				if self.last_emblem_category and self.last_emblem_category in emblem_categories:
					self.current_category = self.last_emblem_category
				elif DEFAULT_EMBLEM_CATEGORY in emblem_categories:
					self.current_category = DEFAULT_EMBLEM_CATEGORY
				else:
					self.current_category = emblem_categories[0]
		
				self.category_combo.setCurrentText(self.current_category)
			self.category_combo.blockSignals(False)
		
		# Rebuild grid with new mode
		for btn in self.asset_buttons:
			try:
				btn.clicked.disconnect()
			except:
				pass
			btn.deleteLater()
		self.asset_buttons.clear()
		self.clear_layout(self.assets_flow)
		self.build_asset_grid()
	
	def _get_current_layer_colors(self):
		"""Get colors from currently selected layer for preview compositing"""
		if not self.right_sidebar or not hasattr(self.right_sidebar, 'layers'):
			# Return default colors
			return {
				'color1': tuple(CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR1]['rgb']),
				'color2': tuple(CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR2]['rgb']),
				'color3': tuple(CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR3]['rgb']),
				'background1': tuple(CK3_NAMED_COLORS[DEFAULT_BASE_COLOR1]['rgb']),
				'background2': tuple(CK3_NAMED_COLORS[DEFAULT_BASE_COLOR2]['rgb']),
				'background3': tuple(CK3_NAMED_COLORS[DEFAULT_BASE_COLOR3]['rgb'])
			}
		
		# Get background colors from base color buttons (always from Base tab)
		base_colors = self.right_sidebar.get_base_colors()
		background1 = tuple(base_colors[0]) if len(base_colors) > 0 else tuple(CK3_NAMED_COLORS[DEFAULT_BASE_COLOR1]['rgb'])
		background2 = tuple(base_colors[1]) if len(base_colors) > 1 else tuple(CK3_NAMED_COLORS[DEFAULT_BASE_COLOR2]['rgb'])
		background3 = tuple(base_colors[2]) if len(base_colors) > 2 else tuple(CK3_NAMED_COLORS[DEFAULT_BASE_COLOR3]['rgb'])
		
		# Get selected layer UUIDs
		selected_uuids = self.right_sidebar.get_selected_uuids()
		if not selected_uuids:
			# Use first layer or defaults
			if self.right_sidebar.coa and self.right_sidebar.coa.get_layer_count() > 0:
				layer = self.right_sidebar.coa.get_layer_by_index(0)
				return {
					'color1': layer.color1 or tuple(CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR1]['rgb']),
					'color2': layer.color2 or tuple(CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR2]['rgb']),
					'color3': layer.color3 or tuple(CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR3]['rgb']),
					'background1': background1,
					'background2': background2,
					'background3': background3
				}
			else:
				return {
					'color1': tuple(CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR1]['rgb']),
					'color2': tuple(CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR2]['rgb']),
					'color3': tuple(CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR3]['rgb']),
					'background1': background1,
					'background2': background2,
					'background3': background3
				}
		else:
			uuid = list(selected_uuids)[0]
		
		# Extract colors from layer using CoA API (stored as 0-1 range floats)
		return {
			'color1': self.right_sidebar.coa.get_layer_color(uuid, 1) or tuple(CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR1]['rgb']),
			'color2': self.right_sidebar.coa.get_layer_color(uuid, 2) or tuple(CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR2]['rgb']),
			'color3': self.right_sidebar.coa.get_layer_color(uuid, 3) or tuple(CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR3]['rgb']),
			'background1': background1,
			'background2': background2,
			'background3': background3
		}
	
	def _create_asset_preview(self, asset, colors):
		"""Create a dynamically colored preview for an asset"""
		filename = asset.get('filename', '')
		
		# Try to get atlas path
		try:
			if self.current_mode == "emblems":
				from utils.color_utils import get_contrasting_background
				
				# For emblems, use smart contrast background
				emblem_color1 = colors['color1']
				base_background_color1 = colors['background1']
				
				# Create new colors dict with contrasting background
				emblem_colors = {
					'color1': emblem_color1,
					'color2': colors['color2'],
					'color3': colors['color3'],
					'background1': get_contrasting_background(emblem_color1, base_background_color1)
				}
				
				atlas_path = get_atlas_path(filename, 'emblem')
				if atlas_path.exists():
					return composite_emblem_atlas(str(atlas_path), emblem_colors, size=self.current_icon_size)
			elif self.current_mode == "patterns":
				atlas_path = get_atlas_path(filename, 'pattern')
				if atlas_path.exists():
					bg_colors = {
						'background1': colors['background1'],
						'background2': colors['background2'],
						'background3': colors['background3']
					}
					# Stretch pattern to fill full square icon (will distort 2:1 to 1:1)
					pattern_pixmap = composite_pattern_atlas(str(atlas_path), bg_colors, 
						size=(self.current_icon_size, self.current_icon_size))
					return pattern_pixmap
		except Exception as e:
			# Fall back to static preview
			print(f"Atlas compositor error for {filename}: {e}")
			import traceback
			traceback.print_exc()
			pass
		
		# Fallback: use static preview
		pixmap = QPixmap(asset["path"])
		if not pixmap.isNull():
			# For patterns (2:1 ratio), stretch to fill full square button height
			if self.current_mode == "patterns" and pixmap.width() > pixmap.height():
				# Stretch to square instead of maintaining aspect ratio
				pattern_scaled = pixmap.scaled(self.current_icon_size, self.current_icon_size,
					Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
				return pattern_scaled
			else:
				# For emblems or other assets, use normal scaling
				if pixmap.width() != self.current_icon_size:
					pixmap = pixmap.scaled(self.current_icon_size, self.current_icon_size, 
						Qt.KeepAspectRatio, Qt.SmoothTransformation)
		return pixmap
	
	def update_asset_colors(self):
		"""Update colors when layer colors change"""
		if self.current_mode == "emblems":
			# For emblems: update all stacked widgets directly (fast!)
			colors = self._get_current_layer_colors()
			
			from utils.color_utils import get_contrasting_background
			contrast_bg = get_contrasting_background(colors['color1'], colors['background1'])
			
			# Update all emblem widgets
			for widget in self.emblem_widgets:
				widget.set_background_color(contrast_bg)
				widget.set_colors(colors['color1'], colors['color2'], colors['color3'])
		else:
			# For patterns: rebuild grid (each pattern has unique colors)
			self.build_asset_grid()
