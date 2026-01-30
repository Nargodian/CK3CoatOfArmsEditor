"""Layer transformation operations - align, flip, rotate"""
from PyQt5.QtWidgets import QMessageBox


class LayerTransformActions:
	"""Handles layer transformation operations"""
	
	def __init__(self, main_window):
		"""Initialize with reference to main window
		
		Args:
			main_window: The CoatOfArmsEditor main window instance
		"""
		self.main_window = main_window
	
	def align_layers(self, alignment):
		"""Align selected layers
		
		Args:
			alignment: One of 'left', 'center', 'right', 'top', 'middle', 'bottom'
		"""
		#COA INTEGRATION ACTION: Step 6 - Use CoA model for alignment
		selected_uuids = self.main_window.right_sidebar.get_selected_uuids()
		if len(selected_uuids) < 2:
			QMessageBox.information(
				self.main_window, 
				"Align Layers", 
				"Please select at least 2 layers to align."
			)
			return
		
		# Use model method directly with UUIDs
		self.main_window.coa.align_layers(selected_uuids, alignment)
		
		# OLD CODE (will remove in Step 9):
		# layers = [self.main_window.right_sidebar.layers[i] for i in selected_indices]
		# if alignment in ['left', 'center', 'right']:
		# 	positions = [layer.get('pos_x', 0.5) for layer in layers]
		# 	if alignment == 'left':
		# 		target = min(positions)
		# 	elif alignment == 'right':
		# 		target = max(positions)
		# 	else:
		# 		target = sum(positions) / len(positions)
		# 	for idx in selected_indices:
		# 		self.main_window.right_sidebar.layers[idx]['pos_x'] = target
		# else:
		# 	positions = [layer.get('pos_y', 0.5) for layer in layers]
		# 	if alignment == 'top':
		# 		target = min(positions)
		# 	elif alignment == 'bottom':
		# 		target = max(positions)
		# 	else:
		# 		target = sum(positions) / len(positions)
		# 	for idx in selected_indices:
		# 		self.main_window.right_sidebar.layers[idx]['pos_y'] = target
		
		# Update UI
		self.main_window.right_sidebar._load_layer_properties()
		self.main_window.canvas_area.canvas_widget.set_layers(self.main_window.right_sidebar.layers)
		self.main_window.canvas_area.update_transform_widget_for_layer()
		
		# Save to history
		self.main_window._save_state(f"Align layers {alignment}")
	
	def flip_x(self):
		"""Flip selected layers horizontally"""
		#COA INTEGRATION ACTION: Step 6 - Use CoA model for flip operations
		selected_uuids = self.main_window.right_sidebar.get_selected_uuids()
		if not selected_uuids:
			return
		
		# Use model method for each layer
		for uuid in selected_uuids:
			self.main_window.coa.flip_layer(uuid, flip_x=True, flip_y=None)
		
		# OLD CODE (will remove in Step 9):
		# for idx in selected_indices:
		# 	layer = self.main_window.right_sidebar.layers[idx]
		# 	current_scale_x = layer.get('scale_x', 1.0)
		# 	layer['scale_x'] = -current_scale_x
		
		# Update UI
		self.main_window.right_sidebar._load_layer_properties()
		self.main_window.canvas_area.canvas_widget.set_layers(self.main_window.right_sidebar.layers)
		self.main_window.canvas_area.update_transform_widget_for_layer()
		
		# Save to history
		self.main_window._save_state("Flip horizontal")
	
	def flip_y(self):
		"""Flip selected layers vertically"""
		#COA INTEGRATION ACTION: Step 6 - Use CoA model for flip operations
		selected_uuids = self.main_window.right_sidebar.get_selected_uuids()
		if not selected_uuids:
			return
		
		# Use model method for each layer
		for uuid in selected_uuids:
			self.main_window.coa.flip_layer(uuid, flip_x=None, flip_y=True)
		
		# OLD CODE (will remove in Step 9):
		# for idx in selected_indices:
		# 	layer = self.main_window.right_sidebar.layers[idx]
		# 	current_scale_y = layer.get('scale_y', 1.0)
		# 	layer['scale_y'] = -current_scale_y
		
		# Update UI
		self.main_window.right_sidebar._load_layer_properties()
		self.main_window.canvas_area.canvas_widget.set_layers(self.main_window.right_sidebar.layers)
		self.main_window.canvas_area.update_transform_widget_for_layer()
		
		# Save to history
		self.main_window._save_state("Flip vertical")
	
	def rotate_layers(self, degrees):
		"""Rotate selected layers by specified degrees
		
		Args:
			degrees: Rotation amount in degrees (90, 180, or -90)
		"""
		#COA INTEGRATION ACTION: Step 6 - Use CoA model for rotation operations
		selected_uuids = self.main_window.right_sidebar.get_selected_uuids()
		if not selected_uuids:
			return
		
		# Use model method for each layer
		for uuid in selected_uuids:
			self.main_window.coa.rotate_layer(uuid, degrees)
		
		# OLD CODE (will remove in Step 9):
		# for idx in selected_indices:
		# 	layer = self.main_window.right_sidebar.layers[idx]
		# 	current_rotation = layer.get('rotation', 0.0)
		# 	new_rotation = (current_rotation + degrees) % 360
		# 	layer['rotation'] = new_rotation
		
		# Update UI
		self.main_window.right_sidebar._load_layer_properties()
		self.main_window.canvas_area.canvas_widget.set_layers(self.main_window.right_sidebar.layers)
		self.main_window.canvas_area.update_transform_widget_for_layer()
		
		# Save to history
		self.main_window._save_state(f"Rotate {degrees}°")
	
	def move_to(self, position):
		"""Move selected layers to fixed positions
		
		Args:
			position: One of 'left', 'center', 'right', 'top', 'middle', 'bottom'
		"""
		#COA INTEGRATION ACTION: Step 6 - Use CoA model for move_to operations
		selected_uuids = self.main_window.right_sidebar.get_selected_uuids()
		if not selected_uuids:
			return
		
		# Use model method
		self.main_window.coa.move_layers_to(selected_uuids, position)
		
		# OLD CODE (will remove in Step 9):
		# fixed_positions = {
		# 	'left': 0.25, 'center': 0.5, 'right': 0.75,
		# 	'top': 0.25, 'middle': 0.5, 'bottom': 0.75
		# }
		# target = fixed_positions.get(position, 0.5)
		# if position in ['left', 'center', 'right']:
		# 	for idx in selected_indices:
		# 		self.main_window.right_sidebar.layers[idx]['pos_x'] = target
		# else:
		# 	for idx in selected_indices:
		# 		self.main_window.right_sidebar.layers[idx]['pos_y'] = target
		
		# Update UI
		self.main_window.right_sidebar._load_layer_properties()
		self.main_window.canvas_area.canvas_widget.set_layers(self.main_window.right_sidebar.layers)
		self.main_window.canvas_area.update_transform_widget_for_layer()
		
		# Save to history
		self.main_window._save_state(f"Move to {position}")
