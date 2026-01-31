"""Clipboard operations - copy/paste CoA and layers"""
from PyQt5.QtWidgets import QMessageBox, QApplication
from models.coa import Layer
from utils.logger import loggerRaise


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
			loggerRaise(e, f"Failed to copy CoA: {str(e)}")
	
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
			
			# Clear and parse into existing CoA instance
			self.main_window.coa.clear()
			self.main_window.coa.parse(text)
			
			# Apply to UI - update from model
			self.main_window.canvas_area.canvas_widget.set_base_texture(self.main_window.coa.pattern)
			self.main_window.canvas_area.canvas_widget.set_base_colors([self.main_window.coa.pattern_color1, self.main_window.coa.pattern_color2, self.main_window.coa.pattern_color3])
			self.main_window.canvas_area.canvas_widget.base_color1_name = self.main_window.coa.pattern_color1_name
			self.main_window.canvas_area.canvas_widget.base_color2_name = self.main_window.coa.pattern_color2_name
			self.main_window.canvas_area.canvas_widget.base_color3_name = self.main_window.coa.pattern_color3_name
			
			base_color_names = [self.main_window.coa.pattern_color1_name, self.main_window.coa.pattern_color2_name, self.main_window.coa.pattern_color3_name]
			self.main_window.right_sidebar.set_base_colors([self.main_window.coa.pattern_color1, self.main_window.coa.pattern_color2, self.main_window.coa.pattern_color3], base_color_names)
			
			# Update UI - layers are accessed through CoA model now
			self.main_window.right_sidebar.tab_widget.setCurrentIndex(1)
			self.main_window.right_sidebar._rebuild_layer_list()
			if self.main_window.coa.get_layer_count() > 0:
							self.main_window.canvas_area.canvas_widget.update()
			
			# OLD CODE (will remove in Step 10):
			# from utils.coa_parser import parse_coa_string
			# from services.coa_serializer import parse_coa_for_editor
			# coa_data = parse_coa_string(text)
			# self.main_window._apply_coa_data(coa_data)
			
			self.main_window.status_left.setText("CoA pasted from clipboard")
			
		except Exception as e:
			loggerRaise(e, f"Failed to paste CoA: {str(e)}")
	def copy_layer(self):
		"""Copy selected layer(s) to clipboard"""
		selected_uuids = self.main_window.right_sidebar.get_selected_uuids()
		
		if not selected_uuids:
			QMessageBox.information(
				self.main_window,
				"Copy Layer",
				"No layer selected"
			)
			return
		
		# Serialize selected layers using CoA method
		clipboard_text = self.main_window.coa.serialize_layers_to_string(selected_uuids)
		
		# Copy to clipboard
		clipboard = QApplication.clipboard()
		clipboard.setText(clipboard_text)
		
		count = len(selected_uuids)
		self.main_window.status_left.setText(f"{count} layer(s) copied to clipboard")
	
	def paste_layer(self):
		"""Paste layer from clipboard at original position with offset"""
		from models.coa import CoA
		
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
			
			# Parse as a CoA and extract layers
			# Try full CoA first, then colored_emblem blocks only
			try:
				temp_coa = CoA.from_string(text)
			except:
				temp_coa = CoA.from_layers_string(text)
			
			if not temp_coa or temp_coa.get_layer_count() == 0:
				QMessageBox.information(
					self.main_window,
					"Paste Layer",
					"No valid layer data in clipboard"
				)
				return
			
			# Check for selection to paste above
			selected_uuids = self.main_window.right_sidebar.get_selected_uuids()
			target_uuid = selected_uuids[0] if selected_uuids else None
			
			# Copy layers from temp CoA to main CoA with offset
			if target_uuid:
				# Paste below selected layer (in front of it)
				new_uuids = self.main_window.coa.copy_layers_from_coa(temp_coa, apply_offset=True, target_uuid=target_uuid)
			else:
				# No selection, paste at front
				new_uuids = self.main_window.coa.copy_layers_from_coa(temp_coa, at_front=True, apply_offset=True)
			
			# Track all pasted UUIDs in CoA model for potential future use
			self.main_window.coa.set_last_added_uuids(new_uuids)
			
			# Update UI
			self.main_window.right_sidebar._rebuild_layer_list()
			self.main_window.canvas_area.canvas_widget.update()
			
			# Select the newly pasted layers
			if new_uuids:
				self.main_window.right_sidebar.layer_list_widget.selected_layer_uuids = set(new_uuids)
				self.main_window.right_sidebar.layer_list_widget.last_selected_uuid = new_uuids[0]
				self.main_window.right_sidebar.layer_list_widget.update_selection_visuals()
			
			# Save to history
			count = temp_coa.get_layer_count()
			self.main_window._save_state(f"Paste {count} layer(s)")
			
			self.main_window.status_left.setText(f"{count} layer(s) pasted")
			
		except Exception as e:
			loggerRaise(e, f"Failed to paste layer: {str(e)}")
	
	def paste_layer_smart(self):
		"""Smart paste - pastes at mouse position if over canvas, otherwise at offset position"""
		mouse_pos = self.main_window.canvas_area.mapFromGlobal(self.main_window.cursor().pos())
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
		from models.coa import CoA
		
		try:
			clipboard = QApplication.clipboard()
			text = clipboard.text()
			
			if not text:
				return
			
			# Parse as a CoA and extract layers
			# Try full CoA first, then colored_emblem blocks only
			try:
				temp_coa = CoA.from_string(text)
			except:
				temp_coa = CoA.from_layers_string(text)
			
			if not temp_coa or temp_coa.get_layer_count() == 0:
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
			
			# Get all UUIDs from temp CoA
			temp_uuids = [temp_coa.get_layer_uuid_by_index(i) for i in range(temp_coa.get_layer_count())]
			
			# Calculate centroid of temp layers
			if len(temp_uuids) > 1:
				# Multiple layers: position centroid at cursor
				centroid_x, centroid_y = temp_coa.get_layer_centroid(temp_uuids)
				
				# Calculate offset from centroid to mouse position
				offset_x = norm_x - centroid_x
				offset_y = norm_y - centroid_y
				
				# Apply offset to temp CoA layers
				temp_coa.adjust_layer_positions(temp_uuids, offset_x, offset_y)
			elif temp_coa.get_layer_instance_count(temp_uuids[0]) > 1:
				# Single multi-instance layer: position AABB center at cursor
				bounds = temp_coa.get_layer_bounds(temp_uuids[0])
				offset_x = norm_x - bounds['center_x']
				offset_y = norm_y - bounds['center_y']
				temp_coa.translate_all_instances(temp_uuids[0], offset_x, offset_y)
			else:
				# Single instance layer: position at cursor directly
				temp_coa.set_layer_position(temp_uuids[0], norm_x, norm_y)
			
			# Copy adjusted layers to main CoA
			new_uuids = self.main_window.coa.copy_layers_from_coa(temp_coa, at_front=True, apply_offset=False)
			
			# Update UI
			self.main_window.right_sidebar._rebuild_layer_list()
			self.main_window.canvas_area.canvas_widget.update()
			
			# Select the newly pasted layers
			if new_uuids:
				self.main_window.right_sidebar.layer_list_widget.selected_layer_uuids = set(new_uuids)
				self.main_window.right_sidebar.layer_list_widget.last_selected_uuid = new_uuids[0]
				self.main_window.right_sidebar.layer_list_widget.update_selection_visuals()
				# Trigger selection change callback to update property sidebar and transform widget
				self.main_window.right_sidebar._on_layer_selection_changed()
			
			# Save to history
			count = len(new_uuids)
			description = f"Paste {count} layer{'s' if count > 1 else ''} at position"
			self.main_window._save_state(description)
			
		except Exception as e:
			loggerRaise(e, f"Failed to paste layer: {str(e)}")
	
	def duplicate_selected_layer(self):
		"""Duplicate selected layer(s) and place above"""
		selected_uuids = self.main_window.right_sidebar.get_selected_uuids()
		
		if not selected_uuids:
			QMessageBox.information(
				self.main_window,
				"Duplicate Layer",
				"No layer selected"
			)
			return
		
		# Duplicate using CoA model
		new_uuids = []
		for uuid in selected_uuids:
			new_uuid = self.main_window.coa.duplicate_layer(uuid)
			new_uuids.append(new_uuid)
		
		# Update UI
		self.main_window.right_sidebar._rebuild_layer_list()
		self.main_window.canvas_area.canvas_widget.update()
		
		# Select the new duplicated layers
		if new_uuids:
			self.main_window.right_sidebar.layer_list_widget.selected_layer_uuids = set(new_uuids)
			self.main_window.right_sidebar.layer_list_widget.last_selected_uuid = new_uuids[0]
			self.main_window.right_sidebar.layer_list_widget.update_selection_visuals()
		
		# Save to history
		count = len(selected_uuids)
		self.main_window._save_state(f"Duplicate {count} layer(s)")
	
	def duplicate_selected_layer_below(self, keep_selection=False):
		"""Duplicate selected layer(s) and place below
		
		Args:
			keep_selection: If True, keep original selection (for ctrl+drag). If False, select duplicates.
		"""
		selected_uuids = self.main_window.right_sidebar.get_selected_uuids()
		
		if not selected_uuids:
			return
		
		# Store original selection
		original_selection = set(selected_uuids)
		
		# Duplicate using pure UUID-based positioning
		new_uuids = []
		for uuid in selected_uuids:
			# Duplicate and place below original (pushes original forward/above)
			new_uuid = self.main_window.coa.duplicate_layer_below(uuid, uuid)
			new_uuids.append(new_uuid)
		
		# Update UI
		self.main_window.right_sidebar._rebuild_layer_list()
		self.main_window.canvas_area.canvas_widget.update()
		
		# Select the appropriate layers based on keep_selection flag
		if keep_selection:
			# Keep original selection (for ctrl+drag) - originals are still at same UUIDs
			self.main_window.right_sidebar.layer_list_widget.selected_layer_uuids = original_selection
			if selected_uuids:
				self.main_window.right_sidebar.layer_list_widget.last_selected_uuid = selected_uuids[0]
			# Update visual state WITHOUT triggering selection callback (which resets drag state)
			for uuid, btn in self.main_window.right_sidebar.layer_list_widget.layer_buttons:
				btn.setChecked(uuid in original_selection)
		else:
			# Select the new duplicated layers (normal duplicate operation)
			if new_uuids:
				self.main_window.right_sidebar.layer_list_widget.selected_layer_uuids = set(new_uuids)
				self.main_window.right_sidebar.layer_list_widget.last_selected_uuid = new_uuids[0]
			self.main_window.right_sidebar.layer_list_widget.update_selection_visuals()
		
		# Save to history (but not during ctrl+drag - that's saved on mouse release)
		if not keep_selection:
			count = len(selected_uuids)
			self.main_window._save_state(f"Duplicate {count} layer(s) below")
	
	def duplicate_selected_layer(self):
		"""Duplicate selected layer(s) and place above"""
		selected_uuids = self.main_window.right_sidebar.get_selected_uuids()
		
		if not selected_uuids:
			QMessageBox.information(
				self.main_window,
				"Duplicate Layer",
				"No layer selected"
			)
			return
		
		# Duplicate using CoA model
		new_uuids = []
		for uuid in selected_uuids:
			new_uuid = self.main_window.coa.duplicate_layer(uuid)
			new_uuids.append(new_uuid)
		
		# Update UI
		self.main_window.right_sidebar._rebuild_layer_list()
		self.main_window.canvas_area.canvas_widget.update()
		
		# Select the new duplicated layers
		if new_uuids:
			self.main_window.right_sidebar.layer_list_widget.selected_layer_uuids = set(new_uuids)
			self.main_window.right_sidebar.layer_list_widget.last_selected_uuid = new_uuids[0]
			self.main_window.right_sidebar.layer_list_widget.update_selection_visuals()
		
		# Save to history
		count = len(selected_uuids)
		self.main_window._save_state(f"Duplicate {count} layer(s)")

