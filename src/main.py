import re
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QSplitter, QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor

from components.toolbar import create_toolbar
from components.asset_sidebar import AssetSidebar
from components.canvas_area import CanvasArea
from components.property_sidebar import PropertySidebar
from utils.coa_parser import parse_coa_string, serialize_coa_to_string


class CoatOfArmsEditor(QMainWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("Coat Of Arms Designer")
		self.resize(1280, 720)
		self.setMinimumSize(1280, 720)
		
		self.setup_ui()
	
	def setup_ui(self):
		# Create top toolbar
		create_toolbar(self)
		
		# Create central widget with splitter
		central_widget = QWidget()
		self.setCentralWidget(central_widget)
		
		main_layout = QHBoxLayout(central_widget)
		main_layout.setContentsMargins(0, 0, 0, 0)
		main_layout.setSpacing(0)
		
		# Create splitter for resizable panels
		splitter = QSplitter(Qt.Horizontal)
		
		# Left sidebar - scrollable assets
		self.left_sidebar = AssetSidebar(self)
		splitter.addWidget(self.left_sidebar)
		
		# Center canvas area
		self.canvas_area = CanvasArea(self)
		splitter.addWidget(self.canvas_area)
		
		# Right properties sidebar
		self.right_sidebar = PropertySidebar(self)
		splitter.addWidget(self.right_sidebar)
		
		# Connect canvas to property sidebar for layer updates
		self.right_sidebar.canvas_widget = self.canvas_area.canvas_widget
		
		# Initialize base colors in canvas from property sidebar
		base_colors = self.right_sidebar.get_base_colors()
		self.canvas_area.canvas_widget.set_base_colors(base_colors)
		
		# Connect property tab changes to asset sidebar mode
		self.right_sidebar.tab_widget.currentChanged.connect(self._on_property_tab_changed)
		
		# Connect asset selection to update color swatches
		self.left_sidebar.asset_selected.connect(self._on_asset_selected)
		
		# Set initial sizes (left: 250px, center: flex, right: 300px)
		splitter.setSizes([250, 730, 300])
		splitter.setCollapsible(0, False)
		splitter.setCollapsible(1, False)
		splitter.setCollapsible(2, False)
		
		main_layout.addWidget(splitter)
		
		# Note: Cannot set frame/base here - OpenGL not initialized yet
		# Will be set after show() triggers initializeGL()
	
	def _on_property_tab_changed(self, index):
		"""Handle property tab changes to switch asset sidebar mode"""
		# Index 0 = Base tab (show patterns), other tabs (show emblems)
		if index == 0:
			self.left_sidebar.switch_mode("patterns")
		else:
			self.left_sidebar.switch_mode("emblems")
	
	def _on_asset_selected(self, asset_data):
		"""Handle asset selection - update color swatches based on asset color count"""
		color_count = asset_data.get("colors", 1)
		filename = asset_data.get("filename")
		
		# Update color swatches based on which tab is active
		current_tab = self.right_sidebar.tab_widget.currentIndex()
		if current_tab == 0:  # Base tab
			self.right_sidebar.set_base_color_count(color_count)
			# Base is not a layer, update canvas base texture
			if filename:
				self.canvas_area.canvas_widget.set_base_texture(filename)
		else:  # Layers or Properties tab
			self.right_sidebar.set_emblem_color_count(color_count)
			
			# If a layer is selected, update it with the new asset
			if self.right_sidebar.selected_layer_index is not None:
				idx = self.right_sidebar.selected_layer_index
				if 0 <= idx < len(self.right_sidebar.layers):
					# Preserve existing properties when updating asset
					old_layer = self.right_sidebar.layers[idx]
					self.right_sidebar.layers[idx] = {
						'filename': asset_data.get('filename', ''),
						'path': asset_data.get('path', ''),
						'colors': color_count,
						'depth': old_layer.get('depth', idx),  # Preserve depth
						'pos_x': old_layer.get('pos_x', 0.5),
						'pos_y': old_layer.get('pos_y', 0.5),
					'scale_x': old_layer.get('scale_x', 1.0),
					'scale_y': old_layer.get('scale_y', 1.0),
					'rotation': old_layer.get('rotation', 0),
					'color1': old_layer.get('color1', [1.0, 0.854, 0.0]),
					'color2': old_layer.get('color2', [0.502, 0.0, 0.0]),
					'color3': old_layer.get('color3', [0.502, 0.0, 0.0]),
						'color1_name': old_layer.get('color1_name'),
						'color2_name': old_layer.get('color2_name'),
						'color3_name': old_layer.get('color3_name')
					}
					self.right_sidebar._rebuild_layer_list()
					self.right_sidebar._update_layer_selection()
					# Update canvas with new layers
					self.canvas_area.canvas_widget.set_layers(self.right_sidebar.layers)
	
	def resizeEvent(self, event):
		"""Handle window resize to recalculate grid columns in asset sidebar"""
		super().resizeEvent(event)
		if hasattr(self, 'left_sidebar'):
			self.left_sidebar.handle_resize()
	
	def copy_coa(self):
		"""Copy current CoA to clipboard as text"""
		try:
			# Get current state
			canvas = self.canvas_area.canvas_widget
			base_colors = self.right_sidebar.get_base_colors()
			
			# Build CoA data structure
			coa_data = {
				"coa_clipboard": {
					"custom": True,
					"pattern": canvas.base_texture or "pattern__solid_designer.dds",
					"colored_emblem": []
				}
			}
			
			# Add base colors only if they differ from defaults (black, yellow, black)
			color1_str = self._rgb_to_color_name(base_colors[0], getattr(canvas, 'base_color1_name', None))
			color2_str = self._rgb_to_color_name(base_colors[1], getattr(canvas, 'base_color2_name', None))
			color3_str = self._rgb_to_color_name(base_colors[2], getattr(canvas, 'base_color3_name', None))
			
			if color1_str != 'black':
				coa_data["coa_clipboard"]["color1"] = color1_str
			if color2_str != 'yellow':
				coa_data["coa_clipboard"]["color2"] = color2_str
			if color3_str != 'black':
				coa_data["coa_clipboard"]["color3"] = color3_str
			
			# Add emblem layers with depth values
			for layer_idx, layer in enumerate(self.right_sidebar.layers):
				instance = {
					"position": [layer.get('pos_x', 0.5), layer.get('pos_y', 0.5)],
					"scale": [layer.get('scale_x', 1.0), layer.get('scale_y', 1.0)],
					"rotation": int(layer.get('rotation', 0))
				}
				# Add depth for all layers except the first (layer 0 = frontmost, no depth)
				if layer_idx > 0:
					instance['depth'] = float(layer_idx) + 0.01
				
				emblem = {
					"texture": layer.get('filename', ''),
					"instance": [instance]
				}
				
				# Add emblem colors only if they differ from defaults (yellow, red, red)
				color1_str = self._rgb_to_color_name(layer.get('color1', [1.0, 1.0, 1.0]), layer.get('color1_name'))
				color2_str = self._rgb_to_color_name(layer.get('color2', [1.0, 1.0, 1.0]), layer.get('color2_name'))
				color3_str = self._rgb_to_color_name(layer.get('color3', [1.0, 1.0, 1.0]), layer.get('color3_name'))
				
				if color1_str != 'yellow':
					emblem['color1'] = color1_str
				if color2_str != 'red':
					emblem['color2'] = color2_str
				if color3_str != 'red':
					emblem['color3'] = color3_str
				
				coa_data["coa_clipboard"]["colored_emblem"].append(emblem)
			
			# Serialize and copy to clipboard
			coa_text = serialize_coa_to_string(coa_data)
			QApplication.clipboard().setText(coa_text)
			print("CoA copied to clipboard")
			
		except Exception as e:
			print(f"Error copying CoA: {e}")
			import traceback
			traceback.print_exc()
	
	def paste_coa(self):
		"""Paste CoA from clipboard and apply to editor"""
		try:
			# Get clipboard text
			coa_text = QApplication.clipboard().text()
			if not coa_text.strip():
				print("Clipboard is empty")
				return
			
			# Parse CoA data
			coa_data = parse_coa_string(coa_text)
			if not coa_data:
				print("Failed to parse clipboard data")
				return
			
			# Get the CoA object (first key)
			coa_id = list(coa_data.keys())[0]
			coa = coa_data[coa_id]
			
			# Apply base pattern
			if 'pattern' in coa:
				self.canvas_area.canvas_widget.set_base_texture(coa['pattern'])
			
			# Apply base colors (CK3 defaults: black, yellow, black)
			color1_name = coa.get('color1', 'black')
			color2_name = coa.get('color2', 'yellow')
			color3_name = coa.get('color3', 'black')
			
			base_colors = [
				self._color_name_to_rgb(color1_name),
				self._color_name_to_rgb(color2_name),
				self._color_name_to_rgb(color3_name)
			]
			base_color_names = [color1_name, color2_name, color3_name]
			
			self.canvas_area.canvas_widget.set_base_colors(base_colors)
			self.right_sidebar.set_base_colors(base_colors, base_color_names)
			
			# Clear existing layers
			self.right_sidebar.layers = []
			
			# Collect all emblem instances with their depth values
			emblem_instances = []
			for emblem in coa.get('colored_emblem', []):
				filename = emblem.get('texture', '')
				
				# Get instances, or create default if none exist
				instances = emblem.get('instance', [])
				if not instances:
					# No instance block means default values
					instances = [{'position': [0.5, 0.5], 'scale': [1.0, 1.0], 'rotation': 0}]
				
				for instance in instances:
					# Get depth value (default to 0 if not specified)
					depth = instance.get('depth', 0)
					
					layer_data = {
						'filename': filename,
						'path': filename,  # Use filename as path - texture system and preview lookup both use this
						'colors': 3,  # Assume 3 colors for all emblems
						'pos_x': instance.get('position', [0.5, 0.5])[0],
						'pos_y': instance.get('position', [0.5, 0.5])[1],
						'scale_x': instance.get('scale', [1.0, 1.0])[0],
						'scale_y': instance.get('scale', [1.0, 1.0])[1],
						'rotation': instance.get('rotation', 0),
						'color1': self._color_name_to_rgb(emblem.get('color1', 'yellow')),
						'color2': self._color_name_to_rgb(emblem.get('color2', 'red')),
						'color3': self._color_name_to_rgb(emblem.get('color3', 'red')),
						'depth': depth
					}
					emblem_instances.append(layer_data)
			
			# Sort by depth (higher depth = further back = first in list for rendering)
			emblem_instances.sort(key=lambda x: x['depth'], reverse=True)
			
			# Add sorted layers to sidebar
			for layer_data in emblem_instances:
				# Remove depth from layer data (it's only used for sorting)
				del layer_data['depth']
				self.right_sidebar.layers.append(layer_data)
				print(f"Added layer: {layer_data['filename']} (depth order)")
			
			# Update UI - switch to Layers tab and rebuild
			self.right_sidebar.tab_widget.setCurrentIndex(1)  # Switch to Layers tab
			self.right_sidebar._rebuild_layer_list()
			if len(self.right_sidebar.layers) > 0:
				self.right_sidebar._select_layer(0)
			
			# Update canvas
			self.canvas_area.canvas_widget.set_layers(self.right_sidebar.layers)
			print(f"CoA pasted from clipboard - {len(self.right_sidebar.layers)} layers created")
			
		except Exception as e:
			print(f"Error pasting CoA: {e}")
			import traceback
			traceback.print_exc()

	def _rgb_to_color_name(self, rgb, color_name=None):
		"""Convert RGB [0-1] to CK3 color format
		
		If color_name is provided (from swatch), use the name.
		Otherwise (from color picker), output rgb { R G B } format.
		"""
		if not rgb:
			return 'white'
		
		# If we have a named color (from swatch), use it
		if color_name:
			return color_name
		
		# Otherwise output custom RGB format (from color picker)
		r, g, b = rgb[0], rgb[1], rgb[2]
		r_int = int(round(r * 255))
		g_int = int(round(g * 255))
		b_int = int(round(b * 255))
		return f"rgb {{ {r_int} {g_int} {b_int} }}"
	
	def _find_asset_path(self, filename):
		"""Find the display path for an asset by filename"""
		if not filename:
			return ''
		# Try to find in the asset sidebar's loaded data
		if hasattr(self.left_sidebar, 'emblem_data'):
			for asset in self.left_sidebar.emblem_data:
				if asset.get('filename') == filename:
					return asset.get('path', '')
		return ''
	
	def _color_name_to_rgb(self, color_name):
		"""Convert CK3 color name to RGB [0-1]
		
		TODO: Extract actual RGB values from:
		<CK3_DIR>/game/common/named_colors/00_named_colors.txt
		
		These are approximate values based on common usage in CoA samples.
		For accurate colors, parse the game's named_colors file which defines
		colors in rgb { R G B } format (0-255 range).
		"""
		# Check if it's an rgb { R G B } custom color
		if isinstance(color_name, str) and color_name.startswith('rgb'):
			# Parse "rgb { 74 201 202 }" format
			match = re.search(r'rgb\s*\{\s*(\d+)\s+(\d+)\s+(\d+)\s*\}', color_name)
			if match:
				r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
				return [r / 255.0, g / 255.0, b / 255.0]
		
		# Official CK3 color definitions from game/common/named_colors/00_named_colors.txt
		# Extracted from default_colors.txt as RGB [0-1]
		color_map = {
			'black': [0.098, 0.090, 0.075],
			'blue': [0.08, 0.246, 0.4],
			'blue_dark': [0.055, 0.157, 0.255],
			'blue_light': [0.286, 0.788, 0.792],
			'brown': [0.341, 0.282, 0.235],
			'green': [0.275, 0.608, 0.29],
			'green_light': [0.557, 0.804, 0.427],
			'grey': [0.314, 0.314, 0.314],
			'orange': [0.8, 0.341, 0.02],
			'purple': [0.416, 0.196, 0.663],
			'red': [0.45, 0.133, 0.09],
			'red_dark': [0.235, 0.059, 0.039],
			'white': [0.98, 0.98, 0.98],
			'yellow': [0.75, 0.525, 0.188],
			'yellow_light': [0.969, 0.969, 0.6]
		}
		return color_map.get(color_name, [1.0, 1.0, 1.0])


def main():
	print("Starting Coat of Arms Designer...")
	app = QtWidgets.QApplication([])
	
	# Use Fusion style with dark palette
	app.setStyle("Fusion")
	
	dark_palette = QPalette()
	dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
	dark_palette.setColor(QPalette.WindowText, Qt.white)
	dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
	dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
	dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
	dark_palette.setColor(QPalette.ToolTipText, Qt.white)
	dark_palette.setColor(QPalette.Text, Qt.white)
	dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
	dark_palette.setColor(QPalette.ButtonText, Qt.white)
	dark_palette.setColor(QPalette.BrightText, Qt.red)
	dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
	dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
	dark_palette.setColor(QPalette.HighlightedText, Qt.black)
	
	app.setPalette(dark_palette)
	
	window = CoatOfArmsEditor()
	window.show()
	app.exec_()


if __name__ == "__main__":
	main()
