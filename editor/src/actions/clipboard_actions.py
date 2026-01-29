"""Clipboard operations - copy/paste CoA and layers"""
from PyQt5.QtWidgets import QMessageBox, QApplication
from models.layer import Layer


class ClipboardActions:
	"""Handles clipboard operations for CoA and layers"""
	
	def __init__(self, main_window):
		"""Initialize with reference to main window
		
		Args:
			main_window: The CoatOfArmsEditor main window instance
		"""
		self.main_window = main_window
	
	def copy_coa(self):
		"""Copy current CoA to clipboard"""
		#COA INTEGRATION ACTION: Step 7 - Use CoA model for copy operations
		try:
			# Use model's to_string() method
			clipboard_text = self.main_window.coa.to_string()
			
			# OLD CODE (will remove in Step 9):
			# from services.file_operations import coa_to_clipboard_text, build_coa_for_save
			# coa_data = build_coa_for_save(self.main_window.right_sidebar.layers)
			# clipboard_text = coa_to_clipboard_text(coa_data)
			
			# Copy to clipboard
			clipboard = QApplication.clipboard()
			clipboard.setText(clipboard_text)
			
			self.main_window.status_left.setText("CoA copied to clipboard")
			
		except Exception as e:
			QMessageBox.critical(
				self.main_window,
				"Error",
				f"Failed to copy CoA: {str(e)}"
			)
	
	def paste_coa(self):
		"""Paste CoA from clipboard"""
		#COA INTEGRATION ACTION: Step 7 - Use CoA model for paste operations
		try:
			clipboard = QApplication.clipboard()
			text = clipboard.text()
			
			if not text:
				QMessageBox.information(
					self.main_window,
					"Paste CoA",
					"Clipboard is empty"
				)
				return
			
			# Parse into model using from_string()
			from models.coa import CoA
			self.main_window.coa = CoA.from_string(text)
			
			# Apply to UI - update from model
			self.main_window.canvas_area.canvas_widget.set_base_texture(self.main_window.coa.pattern)
			self.main_window.canvas_area.canvas_widget.set_base_colors([self.main_window.coa.pattern_color1, self.main_window.coa.pattern_color2, self.main_window.coa.pattern_color3])
			self.main_window.canvas_area.canvas_widget.base_color1_name = self.main_window.coa.pattern_color1_name
			self.main_window.canvas_area.canvas_widget.base_color2_name = self.main_window.coa.pattern_color2_name
			self.main_window.canvas_area.canvas_widget.base_color3_name = self.main_window.coa.pattern_color3_name
			
			base_color_names = [self.main_window.coa.pattern_color1_name, self.main_window.coa.pattern_color2_name, self.main_window.coa.pattern_color3_name]
			self.main_window.right_sidebar.set_base_colors([self.main_window.coa.pattern_color1, self.main_window.coa.pattern_color2, self.main_window.coa.pattern_color3], base_color_names)
			
			# Convert Layer objects to dicts for old UI code (temporary until Step 10)
			self.main_window.right_sidebar.layers = []
			for i in range(self.main_window.coa.get_layer_count()):
				layer = self.main_window.coa.get_layer_by_index(i)
				layer_dict = {
					'uuid': layer.uuid,
					'filename': layer.filename,
					'pos_x': layer.pos_x,
					'pos_y': layer.pos_y,
					'scale_x': layer.scale_x,
					'scale_y': layer.scale_y,
					'rotation': layer.rotation,
					'depth': i,
					'color1': layer.color1,
					'color2': layer.color2,
					'color3': layer.color3,
					'color1_name': layer.color1_name,
					'color2_name': layer.color2_name,
					'color3_name': layer.color3_name,
					'mask': layer.mask,
					'flip_x': layer.flip_x,
					'flip_y': layer.flip_y,
					'instance_count': layer.instance_count,
				}
				self.main_window.right_sidebar.layers.append(layer_dict)
			
			# Update UI
			self.main_window.right_sidebar.tab_widget.setCurrentIndex(1)
			self.main_window.right_sidebar._rebuild_layer_list()
			if len(self.main_window.right_sidebar.layers) > 0:
				self.main_window.right_sidebar._select_layer(0)
			
			# Update canvas
			self.main_window.canvas_area.canvas_widget.set_layers(self.main_window.right_sidebar.layers)
			
			# OLD CODE (will remove in Step 10):
			# from utils.coa_parser import parse_coa_string
			# from services.coa_serializer import parse_coa_for_editor
			# coa_data = parse_coa_string(text)
			# self.main_window._apply_coa_data(coa_data)
			
			self.main_window.status_left.setText("CoA pasted from clipboard")
			
		except Exception as e:
			QMessageBox.critical(
				self.main_window,
				"Error",
				f"Failed to paste CoA: {str(e)}"
			)
	
	def copy_layer(self):
		"""Copy selected layer(s) to clipboard"""
		from services.layer_operations import serialize_layer_to_text
		
		selected_indices = self.main_window.right_sidebar.get_selected_indices()
		
		if not selected_indices:
			QMessageBox.information(
				self.main_window,
				"Copy Layer",
				"No layer selected"
			)
			return
		
		# Get selected layers
		layers = [self.main_window.right_sidebar.layers[i] for i in selected_indices]
		
		# Serialize to text
		clipboard_text = serialize_layer_to_text(layers)
		
		# Copy to clipboard
		clipboard = QApplication.clipboard()
		clipboard.setText(clipboard_text)
		
		count = len(selected_indices)
		self.main_window.status_left.setText(f"{count} layer(s) copied to clipboard")
	
	def paste_layer(self):
		"""Paste layer from clipboard at original position with offset"""
		from services.layer_operations import parse_multiple_layers_from_text
		
		try:
			clipboard = QApplication.clipboard()
			text = clipboard.text()
			
			if not text:
				QMessageBox.information(
					self.main_window,
					"Paste Layer",
					"Clipboard is empty"
				)
				return
			
			# Parse layers from clipboard
			new_layers = parse_multiple_layers_from_text(text, self.main_window._find_asset_path)
			
			if not new_layers:
				QMessageBox.information(
					self.main_window,
					"Paste Layer",
					"No valid layer data in clipboard"
				)
				return
			
			# Add small offset to distinguish from original
			offset = 0.02
			for layer in new_layers:
				layer['pos_x'] = layer.get('pos_x', 0.5) + offset
				layer['pos_y'] = layer.get('pos_y', 0.5) + offset
			
			# Insert layers at top
			for layer in reversed(new_layers):
				self.main_window.right_sidebar.layers.insert(0, layer)
			
			# Update UI
			self.main_window.right_sidebar.refresh_layer_list()
			self.main_window.canvas_area.canvas_widget.set_layers(self.main_window.right_sidebar.layers)
			
			# Select the newly pasted layers
			self.main_window.right_sidebar.select_layers(list(range(len(new_layers))))
			
			# Save to history
			count = len(new_layers)
			self.main_window._save_state(f"Paste {count} layer(s)")
			
			self.main_window.status_left.setText(f"{count} layer(s) pasted")
			
		except Exception as e:
			QMessageBox.critical(
				self.main_window,
				"Error",
				f"Failed to paste layer: {str(e)}"
			)
	
	def paste_layer_smart(self):
		"""Smart paste that checks if mouse is over canvas"""
		from PyQt5.QtCore import QPoint
		
		# Get mouse position in canvas_area coordinates
		mouse_pos = self.main_window.canvas_area.mapFromGlobal(
			self.main_window.canvas_area.cursor().pos()
		)
		
		# Get canvas widget geometry within canvas_area
		canvas_geometry = self.main_window.canvas_area.canvas_widget.geometry()
		
		# If mouse is over canvas, paste at position
		if canvas_geometry.contains(mouse_pos):
			self.paste_layer_at_position(mouse_pos, canvas_geometry)
		else:
			# Fall back to regular paste with offset
			self.paste_layer()
	
	def paste_layer_at_position(self, mouse_pos, canvas_geometry):
		"""Paste layer at specific mouse position
		
		Args:
			mouse_pos: QPoint in canvas_area coordinates
			canvas_geometry: QRect of canvas_widget within canvas_area
		"""
		from PyQt5.QtCore import QPoint
		from services.layer_operations import parse_multiple_layers_from_text
		
		try:
			clipboard = QApplication.clipboard()
			text = clipboard.text()
			
			if not text:
				return
			
			# Parse layers from clipboard
			new_layers = parse_multiple_layers_from_text(text, self.main_window._find_asset_path)
			
			if not new_layers:
				return
			
			# Convert canvas_area coordinates to canvas_widget coordinates
			# Account for the canvas_container margins (10px)
			canvas_offset = self.main_window.canvas_area.canvas_widget.mapTo(
				self.main_window.canvas_area, 
				QPoint(0, 0)
			)
			canvas_x = mouse_pos.x() - canvas_offset.x()
			canvas_y = mouse_pos.y() - canvas_offset.y()
			
			# Get canvas widget size
			canvas_size = min(
				self.main_window.canvas_area.canvas_widget.width(),
				self.main_window.canvas_area.canvas_widget.height()
			)
			
			# Convert to normalized coordinates (-0.5 to 0.5 range, then offset to 0-1)
			# Formula: ((pixel_coord - center) / (size/2)) / 1.1 + 0.5
			# The 1.1 factor accounts for the rendering bounds scaling
			center = canvas_size / 2
			norm_x = ((canvas_x - center) / (canvas_size / 2) / 1.1) + 0.5
			norm_y = ((canvas_y - center) / (canvas_size / 2) / 1.1) + 0.5
			
			# If multiple layers, calculate centroid
			if len(new_layers) > 1:
				centroid_x = sum(layer.get('pos_x', 0.5) for layer in new_layers) / len(new_layers)
				centroid_y = sum(layer.get('pos_y', 0.5) for layer in new_layers) / len(new_layers)
				
				# Calculate offset from centroid to mouse position
				offset_x = norm_x - centroid_x
				offset_y = norm_y - centroid_y
				
				# Apply offset to all layers
				for layer in new_layers:
					layer['pos_x'] = layer.get('pos_x', 0.5) + offset_x
					layer['pos_y'] = layer.get('pos_y', 0.5) + offset_y
			else:
				# Single layer - place directly at mouse position
				new_layers[0]['pos_x'] = norm_x
				new_layers[0]['pos_y'] = norm_y
			
			# Insert layers at top
			for layer in reversed(new_layers):
				self.main_window.right_sidebar.layers.insert(0, layer)
			
			# Update UI
			self.main_window.right_sidebar.refresh_layer_list()
			self.main_window.canvas_area.canvas_widget.set_layers(self.main_window.right_sidebar.layers)
			
			# Select the newly pasted layers
			self.main_window.right_sidebar.select_layers(list(range(len(new_layers))))
			
			# Save to history
			count = len(new_layers)
			self.main_window._save_state(f"Paste {count} layer(s) at position")
			
			self.main_window.status_left.setText(f"{count} layer(s) pasted at position")
			
		except Exception as e:
			QMessageBox.critical(
				self.main_window,
				"Error",
				f"Failed to paste layer: {str(e)}"
			)
	
	def duplicate_selected_layer(self):
		"""Duplicate selected layer(s) and place above"""
		selected_indices = self.main_window.right_sidebar.get_selected_indices()
		
		if not selected_indices:
			QMessageBox.information(
				self.main_window,
				"Duplicate Layer",
				"No layer selected"
			)
			return
		
		# Duplicate using CoA model
		for idx in selected_indices:
			layer = self.main_window.right_sidebar.layers[idx]
			self.main_window.coa.duplicate_layer(layer.uuid)
		
		# Update UI
		self.main_window.right_sidebar.refresh_layer_list()
		self.main_window.canvas_area.canvas_widget.set_layers(self.main_window.right_sidebar.layers)
		
		# Select the new duplicated layers
		self.main_window.right_sidebar.select_layers(new_indices)
		
		# Save to history
		count = len(selected_indices)
		self.main_window._save_state(f"Duplicate {count} layer(s)")
	
	def duplicate_selected_layer_below(self):
		"""Duplicate selected layer(s) and place below"""
		selected_indices = self.main_window.right_sidebar.get_selected_indices()
		
		if not selected_indices:
			return
		
		# Duplicate using CoA model and move below
		for idx in selected_indices:
			layer = self.main_window.right_sidebar.layers[idx]
			new_uuid = self.main_window.coa.duplicate_layer(layer.uuid)
			# Move new layer from after to before original
			self.main_window.coa.move_layer(new_uuid, idx)
		
		# Update UI
		self.main_window.right_sidebar.refresh_layer_list()
		self.main_window.canvas_area.canvas_widget.set_layers(self.main_window.right_sidebar.layers)
		
		# Select the new duplicated layers
		self.main_window.right_sidebar.select_layers(new_indices)
		
		# Save to history
		count = len(selected_indices)
		self.main_window._save_state(f"Duplicate {count} layer(s) below")
