"""Clipboard operations - copy/paste CoA and layers"""
from PyQt5.QtWidgets import QMessageBox, QApplication
from models.coa import Layer
from utils.logger import loggerRaise
from constants import PASTE_OFFSET_X, PASTE_OFFSET_Y


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
		
		# PHASE 6: Detect if copying whole container or individual layers
		# Check if all selected layers share the same container_uuid
		container_uuids = set()
		for uuid in selected_uuids:
			container_uuid = self.main_window.coa.get_layer_container(uuid)
			container_uuids.add(container_uuid)
		
		# Determine copy type:
		# - If all layers share same non-None container_uuid AND count matches container: preserve container_uuid
		# - Otherwise (individual layers, mixed containers, or root layers): strip container_uuid
		is_whole_container = False
		if len(container_uuids) == 1 and None not in container_uuids:
			container_uuid = next(iter(container_uuids))
			container_layers = self.main_window.coa.get_layers_by_container(container_uuid)
			if set(selected_uuids) == set(container_layers):
				is_whole_container = True
		
		# Serialize selected layers using CoA method
		if is_whole_container:
			# Container copy: preserve container_uuid
			clipboard_text = self.main_window.coa.serialize_layers_to_string(selected_uuids, strip_container_uuid=False)
		else:
			# Individual/mixed copy: strip container_uuid
			clipboard_text = self.main_window.coa.serialize_layers_to_string(selected_uuids, strip_container_uuid=True)
		
		# Copy to clipboard
		clipboard = QApplication.clipboard()
		clipboard.setText(clipboard_text)
		
		count = len(selected_uuids)
		copy_type = "container" if is_whole_container else "layer(s)"
		self.main_window.status_left.setText(f"{count} {copy_type} copied to clipboard")
	
	def paste_layer(self):
		"""Paste layer from clipboard using two-rule system
		
		Rule 1 (no container_uuid): Adopt destination container or go to root
		Rule 2 (has container_uuid): Create new container at root level
		"""
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
			
			# Apply paste offset to temp CoA layers
			temp_uuids = [temp_coa.get_layer_uuid_by_index(i) for i in range(temp_coa.get_layer_count())]
			temp_coa.adjust_layer_positions(temp_uuids, PASTE_OFFSET_X, PASTE_OFFSET_Y)
			
			# PHASE 6: Detect if pasted data has container_uuid (Rule 1 vs Rule 2)
			# Check if any layer in clipboard has container_uuid set
			has_container_uuid = False
			clipboard_container_uuids = set()
			for uuid in temp_uuids:
				container_uuid = temp_coa.get_layer_container(uuid)
				if container_uuid is not None:
					has_container_uuid = True
					clipboard_container_uuids.add(container_uuid)
			
			# Check current selection to determine paste target
			selected_uuids = self.main_window.right_sidebar.get_selected_uuids()
			selected_container_uuid = None
			if selected_uuids:
				# Check if selection is a container (all layers share same container_uuid)
				selection_containers = set()
				for uuid in selected_uuids:
					container_uuid = self.main_window.coa.get_layer_container(uuid)
					if container_uuid is not None:
						selection_containers.add(container_uuid)
				
				# If all selected layers in same container, that's our target container
				if len(selection_containers) == 1:
					selected_container_uuid = next(iter(selection_containers))
			
			# Apply paste rules
			if not has_container_uuid:
				# RULE 1: Layers without container_uuid
				# If container selected: adopt that container_uuid and paste at top of container
				# If sub-layer selected: adopt that layer's container_uuid and paste at that position
				# If root layer selected: paste above it (no container)
				# If nothing selected: paste at end (no container)
				
				target_uuid = None
				target_container = None
				
				if selected_uuids and selected_container_uuid:
					# Container or sub-layer selected: adopt container, paste at top
					target_container = selected_container_uuid
					# Find first layer in container for target_uuid
					container_layers = self.main_window.coa.get_layers_by_container(selected_container_uuid)
					if container_layers:
						target_uuid = container_layers[0]
				elif selected_uuids:
					# Root layer selected: paste above it
					target_uuid = selected_uuids[0]
				
				# Set container_uuid on all temp layers
				if target_container:
					for uuid in temp_uuids:
						temp_coa.set_layer_container(uuid, target_container)
				
				# Serialize and parse
				layers_string = temp_coa.serialize_layers_to_string(temp_uuids, strip_container_uuid=False)
				new_uuids = self.main_window.coa.parse(layers_string, target_uuid=target_uuid)
				
			else:
				# RULE 2: Layers with container_uuid
				# Create new container(s) at root level
				# Regenerate container_uuid for each unique container in clipboard
				
				# Build mapping of old container_uuid -> new container_uuid
				container_uuid_map = {}
				for old_container_uuid in clipboard_container_uuids:
					# Regenerate container UUID (keeps name, new UUID portion)
					new_container_uuid = self.main_window.coa.regenerate_container_uuid(old_container_uuid)
					container_uuid_map[old_container_uuid] = new_container_uuid
				
				# Update temp layers with new container UUIDs
				for uuid in temp_uuids:
					old_container = temp_coa.get_layer_container(uuid)
					if old_container in container_uuid_map:
						temp_coa.set_layer_container(uuid, container_uuid_map[old_container])
				
				# Determine paste position
				target_uuid = None
				if selected_uuids:
					if selected_container_uuid:
						# Container selected: paste ABOVE container (not inside)
						# Find first layer in selected container, use as target
						container_layers = self.main_window.coa.get_layers_by_container(selected_container_uuid)
						if container_layers:
							target_uuid = container_layers[0]
					else:
						# Root layer selected: paste above it
						target_uuid = selected_uuids[0]
				
				# Serialize and parse (container_uuid preserved)
				layers_string = temp_coa.serialize_layers_to_string(temp_uuids, strip_container_uuid=False)
				new_uuids = self.main_window.coa.parse(layers_string, target_uuid=target_uuid)
			
			# PHASE 7: Validate container contiguity after paste
			splits = self.main_window.coa.validate_container_contiguity()
			if splits:
				# Log splits for debugging
				for split in splits:
					self.main_window._logger.info(f"Container split: {split['old_container']} -> {split['new_container']} ({split['layer_count']} layers)")
			
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
			paste_type = "container" if has_container_uuid else "layer(s)"
			self.main_window._save_state(f"Paste {count} {paste_type}")
			
			self.main_window.status_left.setText(f"{count} {paste_type} pasted")
			
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
			canvas_width = self.main_window.canvas_area.canvas_widget.width()
			canvas_height = self.main_window.canvas_area.canvas_widget.height()
			canvas_size = (canvas_width, canvas_height)
			
			# Get canvas offset within parent for qt_pixels_to_layer_pos
			# Add centering padding like _get_canvas_rect does
			size = min(canvas_width, canvas_height)
			canvas_offset_x = canvas_geometry.x() + (canvas_width - size) / 2
			canvas_offset_y = canvas_geometry.y() + (canvas_height - size) / 2
			# Get zoom level and pan offsets
			zoom_level = getattr(self.main_window.canvas_area.canvas_widget, 'zoom_level', 1.0)
			pan_x = getattr(self.main_window.canvas_area.canvas_widget, 'pan_x', 0.0)
			pan_y = getattr(self.main_window.canvas_area.canvas_widget, 'pan_y', 0.0)
			
			# Convert Qt pixels to frame space using shared coordinate functions
			from utils.coordinate_transforms import qt_pixels_to_layer_pos
			frame_x, frame_y = qt_pixels_to_layer_pos(
				mouse_pos.x(), mouse_pos.y(),
				canvas_size, canvas_offset_x, canvas_offset_y, zoom_level, pan_x, pan_y
			)
			
			# Convert frame space to CoA space
			norm_x, norm_y = self.main_window.canvas_area.canvas_widget.frame_to_coa_space(frame_x, frame_y)
			
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
			
			# Serialize adjusted layers back to string
			layers_string = temp_coa.serialize_layers_to_string(temp_uuids)
			
			# Parse directly into main CoA (no target_uuid = insert at front)
			new_uuids = self.main_window.coa.parse(layers_string, target_uuid=None)
			
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
			for uuid, container_widget in self.main_window.right_sidebar.layer_list_widget.layer_buttons:
				if hasattr(container_widget, 'layer_button'):
					container_widget.layer_button.setChecked(uuid in original_selection)
				else:
					container_widget.setChecked(uuid in original_selection)
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

