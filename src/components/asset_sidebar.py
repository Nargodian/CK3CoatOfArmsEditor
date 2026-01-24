# PyQt5 imports
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QScrollArea, QPushButton, QWidget, QGridLayout, QComboBox
)
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap

# Standard library imports
import json
import os

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
		
		# Load asset data from JSON files
		self.asset_data = self._load_asset_data()
		
		# Set default category to Nature (where ce_fleur.dds is located)
		self.current_category = "Nature"
		
		self.setMinimumWidth(200)
		self.setMaximumWidth(400)
		
		self._setup_ui()
	
	def _load_asset_data(self):
		"""Load asset definitions from JSON files"""
		asset_data = {}
		
		# Load emblems and organize by category
		emblems_json = "json_output/colored_emblems/50_coa_designer_emblems.json"
		if os.path.exists(emblems_json):
			with open(emblems_json, 'r', encoding='utf-8') as f:
				data = json.load(f)
				for filename, properties in data.items():
					if properties is None or filename == "\ufeff":
						continue
					# Convert .dds to .png
					png_filename = filename.replace('.dds', '.png')
					image_path = f"source_coa_files/coat_of_arms/colored_emblems/{png_filename}"
					if os.path.exists(image_path):
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
						"path": image_path,
						"category": category,
						"colors": colors
		if os.path.exists(textured_emblems_json):
			with open(textured_emblems_json, 'r', encoding='utf-8') as f:
				data = json.load(f)
				for filename, properties in data.items():
					if properties is None or filename == "\ufeff":
						continue
					# Convert .dds to .png
					png_filename = filename.replace('.dds', '.png')
					image_path = f"source_coa_files/coat_of_arms/textured_emblems/{png_filename}"
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
		patterns_json = "json_output/patterns/50_coa_designer_patterns.json"
		if os.path.exists(patterns_json):
			asset_data["__Base_Patterns__"] = []  # Special key for base patterns
			with open(patterns_json, 'r', encoding='utf-8') as f:
				data = json.load(f)
				for filename, properties in data.items():
					if properties is None or filename == "\ufeff":
						continue
					# Convert .dds to .png for display
					png_filename = filename.replace('.dds', '.png')
					image_path = f"source_coa_files/coat_of_arms/patterns/{png_filename}"
					if os.path.exists(image_path):
						# Add to preview map
						TEXTURE_PREVIEW_MAP[filename] = image_path
						
						asset_data["__Base_Patterns__"].append({
							"filename": filename,  # Store .dds name for texture lookup
							"display_name": png_filename,  # PNG name for display
							"path": image_path,
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
		self.category_combo.addItems(emblem_categories)
		if self.current_category and not self.current_category.startswith("__"):
			self.category_combo.setCurrentText(self.current_category)
		# Hide category dropdown initially (showing base patterns)
		self.category_combo.setVisible(False)
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
		
		# Grid for asset icons
		self.assets_grid = QGridLayout()
		self.assets_grid.setSpacing(8)
		scroll_layout.addLayout(self.assets_grid)
		scroll_layout.addStretch()
		
		self.build_asset_grid()
		
		scroll_area.setWidget(scroll_widget)
		layout.addWidget(scroll_area)
	
	def build_asset_grid(self):
		"""Build responsive grid of asset icons"""
		# Clear previous items
		self.clear_layout(self.assets_grid)
		# Clear button list
		self.asset_buttons.clear()
		
		# Get assets for current category
		assets = self._get_filtered_assets()
		
		# Calculate number of columns based on available width
		scroll_width = self.scroll_area.viewport().width()
		icon_padding = 8
		effective_width = self.current_icon_size + (icon_padding * 2)
		cols = max(1, scroll_width // effective_width)
		
		for i, asset in enumerate(assets):
			row = i // cols
			col = i % cols
			
			item = QPushButton()
			item.setFixedSize(self.current_icon_size, self.current_icon_size)
			
			# Load and set icon from file
			pixmap = QPixmap(asset["path"])
			if not pixmap.isNull():
				icon = QIcon(pixmap)
				item.setIcon(icon)
				item.setIconSize(QSize(self.current_icon_size - 10, self.current_icon_size - 10))
			
			item.setCheckable(True)
			item.setToolTip(asset.get("display_name", asset["filename"]))
			item.setProperty("asset_data", asset)  # Store asset data with button
			item.clicked.connect(lambda checked, b=item: self._select_asset(b))
			item.setStyleSheet("""
				QPushButton {
					border: 1px solid rgba(255, 255, 255, 40);
					border-radius: 4px;
				}
				QPushButton:hover {
					background-color: rgba(255, 255, 255, 30);
					border: 1px solid rgba(255, 255, 255, 80);
				}
				QPushButton:checked {
					border: 2px solid #5a8dbf;
				}
			""")
			
			self.assets_grid.addWidget(item, row, col)
			self.asset_buttons.append(item)
		
		# If we're in patterns mode and showing pattern__solid_designer.dds, select it by default
		if self.current_mode == "patterns":
			for btn in self.asset_buttons:
				asset_data = btn.property("asset_data")
				if asset_data and "pattern__solid_designer" in asset_data.get("filename", ""):
					btn.setChecked(True)
					break
	
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
		# Properly disconnect and delete existing buttons
		for btn in self.asset_buttons:
			try:
				btn.clicked.disconnect()
			except:
				pass
			btn.deleteLater()
		self.asset_buttons.clear()
		# Clear the grid layout
		self.clear_layout(self.assets_grid)
		# Rebuild the grid with new category
		self.build_asset_grid()
	
	def handle_resize(self):
		"""Handle resize event to recalculate grid columns"""
		# Use timer to avoid rapid rebuilding during resize
		if not hasattr(self, '_resize_timer'):
			self._resize_timer = QTimer()
			self._resize_timer.setSingleShot(True)
			self._resize_timer.timeout.connect(self.build_asset_grid)
		
		self._resize_timer.stop()
		self._resize_timer.start(100)  # 100ms debounce
	
	def _select_asset(self, selected_button):
		"""Handle asset selection - uncheck all others and emit signal"""
		for btn in self.asset_buttons:
			if btn != selected_button:
				btn.setChecked(False)
		
		# Emit signal with asset data
		asset_data = selected_button.property("asset_data")
		if asset_data:
			self.asset_selected.emit(asset_data)
	
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
			self.category_combo.clear()
			emblem_categories = sorted([k for k in self.asset_data.keys() if not k.startswith("__")])
			self.category_combo.addItems(emblem_categories)
			if emblem_categories:
				self.current_category = emblem_categories[0]
		
				self.category_combo.setCurrentText(self.current_category)
		
		# Rebuild grid with new mode
		for btn in self.asset_buttons:
			try:
				btn.clicked.disconnect()
			except:
				pass
			btn.deleteLater()
		self.asset_buttons.clear()
		self.clear_layout(self.assets_grid)
		self.build_asset_grid()
