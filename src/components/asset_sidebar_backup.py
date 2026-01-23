from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                              QScrollArea, QPushButton, QWidget, QGridLayout, QComboBox)
from PyQt5.QtCore import Qt, QTimer


class AssetSidebar(QFrame):
	"""Left sidebar for browsing and selecting assets"""
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.parent_window = parent
		self.size_buttons = {}
		self.current_icon_size = 80  # Default M size
		self.current_category = "All"
		
		# Define asset counts per category (placeholder data)
		self.category_assets = {
			"All": 40,
			"Patterns": 25,
			"Emblems": 30,
			"Borders": 15,
			"Backgrounds": 20
		}
		
		self.setMinimumWidth(200)
		self.setMaximumWidth(400)
		
		self._setup_ui()
	
	def _load_asset_data(self):
		"""Load asset definitions from JSON files"""
		asset_data = {
			"Emblems": [],
			"Patterns": []
		}
		
		# Load emblems
		emblems_json = "json_output/colored_emblems/50_coa_designer_emblems.json"
		if os.path.exists(emblems_json):
			with open(emblems_json, 'r', encoding='utf-8') as f:
				data = json.load(f)
				for filename, properties in data.items():
					if properties is None or filename == "﻿":
						continue
					# Convert .dds to .png
					png_filename = filename.replace('.dds', '.png')
					image_path = f"source_coa_files/colored_emblems/{png_filename}"
					if os.path.exists(image_path):
						asset_data["Emblems"].append({
							"filename": png_filename,
							"path": image_path,
							"category": properties.get("category", "unknown"),
							"colors": properties.get("colors", 1)
						})
		
		# Load patterns
		patterns_json = "json_output/patterns/50_coa_designer_patterns.json"
		if os.path.exists(patterns_json):
			with open(patterns_json, 'r', encoding='utf-8') as f:
				data = json.load(f)
				for filename, properties in data.items():
					if properties is None or filename == "﻿":
						continue
					# Skip if marked as not visible
					if properties.get("visible", True) == False:
						continue
					# Convert .dds to .png
					png_filename = filename.replace('.dds', '.png')
					image_path = f"source_coa_files/patterns/{png_filename}"
					if os.path.exists(image_path):
						asset_data["Patterns"].append({
							"filename": png_filename,
							"path": image_path,
							"colors": properties.get("colors", 1)
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
		self.category_combo.addItems(["All", "Emblems", "Patterns"])
		self.category_combo.currentTextChanged.connect(self.change_category)
		self.category_combo.setStyleSheet("""
			QComboBox {
				padding: 4px 8px;
				border-radius: 3px;
				border: none;
			}
			QComboBox::drop-down {
				border: none;
			}
			QComboBox::down-arrow {
				image: none;
				border-left: 3px solid transparent;
				border-right: 3px solid transparent;
				border-top: 5px solid;
				margin-right: 5px;
			}
		""")
		category_layout.addWidget(self.category_combo, 1)
		
		layout.addLayout(category_layout)
		
		# Size filter buttons (S, M, L, XL)
		size_layout = QHBoxLayout()
		size_layout.setSpacing(5)
		size_layout.setContentsMargins(10, 5, 10, 10)
		
		for size, icon_size in [("S", 60), ("M", 80), ("L", 120), ("XL", 180)]:
			size_btn = QPushButton(size)
			size_btn.setFixedSize(40, 30)
			size_btn.setCheckable(True)
			if size == "M":  # Default to Medium
				size_btn.setChecked(True)
			size_btn.setStyleSheet("""
				QPushButton {
					border-radius: 3px;
					font-weight: bold;
					padding: 0px;
				}
				QPushButton:hover {
					background-color: rgba(255, 255, 255, 30);
				}
				QPushButton:checked {
					border: 2px solid #5a8dbf;
				}
			""")
			size_btn.clicked.connect(lambda checked, s=icon_size, b=size: self.resize_assets(s, b))
			self.size_buttons[size] = size_btn
			size_layout.addWidget(size_btn)
		
		size_layout.addStretch()
		layout.addLayout(size_layout)
		
		# Scrollable area
		self.asset_scroll = QScrollArea()
		self.asset_scroll.setWidgetResizable(True)
		self.asset_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		
		# Content widget with grid layout for square buttons
		self.assets_content = QWidget()
		self.assets_content_layout = QVBoxLayout(self.assets_content)
		self.assets_content_layout.setAlignment(Qt.AlignTop)
		self.assets_content_layout.setSpacing(5)
		self.assets_content_layout.setContentsMargins(5, 5, 5, 5)
		
		# Create initial grid
		self.build_asset_grid()
		
		self.asset_scroll.setWidget(self.assets_content)
		layout.addWidget(self.asset_scroll)
	
	def calculate_columns(self):
		"""Calculate number of columns based on sidebar width and icon size"""
		# Get available width (subtract margins and spacing)
		available_width = self.asset_scroll.viewport().width() - 10  # 5px margin on each side
		spacing = 5
		
		# Calculate how many icons fit
		columns = max(1, (available_width + spacing) // (self.current_icon_size + spacing))
		return columns
	
	def build_asset_grid(self):
		"""Build or rebuild the asset grid with calculated number of columns"""
		# Calculate columns based on available width
		columns = self.calculate_columns()
		
		# Clear existing layout items
		while self.assets_content_layout.count():
			item = self.assets_content_layout.takeAt(0)
			if item.widget():
				item.widget().deleteLater()
			elif item.layout():
				self.clear_layout(item.layout())
		
		# Create new grid
		grid_layout = QGridLayout()
		grid_layout.setSpacing(5)
		
		# Add placeholder square items
		self.asset_buttons = []
		for i in range(self.category_assets[self.current_category]):
			item = QPushButton(f"{i+1}")
			item.setFixedSize(self.current_icon_size, self.current_icon_size)
			item.setCheckable(True)
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
					background-color: rgba(90, 141, 191, 20);
				}
			""")
			item.clicked.connect(lambda checked, btn=item: self._select_asset(btn))
			self.asset_buttons.append(item)
			row = i // columns
			col = i % columns
			grid_layout.addWidget(item, row, col)
		
		self.assets_content_layout.addLayout(grid_layout)
		self.assets_content_layout.addStretch()
	
	def clear_layout(self, layout):
		"""Recursively clear a layout"""
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
		# Clear existing asset buttons
		for btn in self.asset_buttons:
			btn.deleteLater()
		self.asset_buttons.clear()
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
		"""Handle asset selection - uncheck all others"""
		for btn in self.asset_buttons:
			if btn != selected_button:
				btn.setChecked(False)
