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
		selected_indices = self.main_window.right_sidebar.get_selected_indices()
		if len(selected_indices) < 2:
			QMessageBox.information(
				self.main_window, 
				"Align Layers", 
				"Please select at least 2 layers to align."
			)
			return
		
		layers = [self.main_window.right_sidebar.layers[i] for i in selected_indices]
		
		if alignment in ['left', 'center', 'right']:
			# Horizontal alignment
			positions = [layer.get('pos_x', 0.5) for layer in layers]
			if alignment == 'left':
				target = min(positions)
			elif alignment == 'right':
				target = max(positions)
			else:  # center
				target = sum(positions) / len(positions)
			
			for idx in selected_indices:
				self.main_window.right_sidebar.layers[idx]['pos_x'] = target
		
		else:  # vertical alignment
			positions = [layer.get('pos_y', 0.5) for layer in layers]
			if alignment == 'top':
				target = min(positions)
			elif alignment == 'bottom':
				target = max(positions)
			else:  # middle
				target = sum(positions) / len(positions)
			
			for idx in selected_indices:
				self.main_window.right_sidebar.layers[idx]['pos_y'] = target
		
		# Update UI
		self.main_window.right_sidebar._load_layer_properties()
		self.main_window.canvas_area.canvas_widget.set_layers(self.main_window.right_sidebar.layers)
		self.main_window.canvas_area.update_transform_widget_for_layer()
		
		# Save to history
		self.main_window._save_state(f"Align layers {alignment}")
	
	def flip_x(self):
		"""Flip selected layers horizontally"""
		selected_indices = self.main_window.right_sidebar.get_selected_indices()
		if not selected_indices:
			return
		
		for idx in selected_indices:
			layer = self.main_window.right_sidebar.layers[idx]
			# Flip scale_x
			current_scale_x = layer.get('scale_x', 1.0)
			layer['scale_x'] = -current_scale_x
		
		# Update UI
		self.main_window.right_sidebar._load_layer_properties()
		self.main_window.canvas_area.canvas_widget.set_layers(self.main_window.right_sidebar.layers)
		self.main_window.canvas_area.update_transform_widget_for_layer()
		
		# Save to history
		self.main_window._save_state("Flip horizontal")
	
	def flip_y(self):
		"""Flip selected layers vertically"""
		selected_indices = self.main_window.right_sidebar.get_selected_indices()
		if not selected_indices:
			return
		
		for idx in selected_indices:
			layer = self.main_window.right_sidebar.layers[idx]
			# Flip scale_y
			current_scale_y = layer.get('scale_y', 1.0)
			layer['scale_y'] = -current_scale_y
		
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
		selected_indices = self.main_window.right_sidebar.get_selected_indices()
		if not selected_indices:
			return
		
		for idx in selected_indices:
			layer = self.main_window.right_sidebar.layers[idx]
			# Add rotation (normalized to 0-360)
			current_rotation = layer.get('rotation', 0.0)
			new_rotation = (current_rotation + degrees) % 360
			layer['rotation'] = new_rotation
		
		# Update UI
		self.main_window.right_sidebar._load_layer_properties()
		self.main_window.canvas_area.canvas_widget.set_layers(self.main_window.right_sidebar.layers)
		self.main_window.canvas_area.update_transform_widget_for_layer()
		
		# Save to history
		self.main_window._save_state(f"Rotate {degrees}°")
