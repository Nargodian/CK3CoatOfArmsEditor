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

		# Update UI
		self.main_window.right_sidebar._load_layer_properties()
		self.main_window.canvas_area.canvas_widget.update()
		self.main_window.canvas_area.update_transform_widget_for_layer()
		
		# Save to history
		self.main_window._save_state(f"Align layers {alignment}")
	
	def flip_x(self, orbit: bool = False):
		"""Flip selected layers horizontally
		
		Args:
			orbit: If True, also mirror position across vertical center axis (x → 1.0 - x)
		"""
		try:
			#COA INTEGRATION ACTION: Step 6 - Use CoA model for flip operations
			selected_uuids = self.main_window.right_sidebar.get_selected_uuids()
			if not selected_uuids:
				return
			
			# For flips, mirror positions for groups unless explicitly in rotate_only mode
			if not orbit and len(selected_uuids) > 1 and hasattr(self.main_window, 'canvas_area'):
				rotation_mode = self.main_window.canvas_area.get_rotation_mode()
				# Mirror positions unless mode is rotate_only (which means no position changes)
				orbit = 'rotate_only' not in rotation_mode.lower()
			
			# Use CoA model method that handles both single and group flips
			self.main_window.coa.flip_selection(selected_uuids, flip_x=True, flip_y=False, orbit=orbit)
			
			# Update UI
			self.main_window.right_sidebar._load_layer_properties()
			self.main_window.canvas_area.canvas_widget.update()
			self.main_window.canvas_area.update_transform_widget_for_layer()
			
			# Save to history
			self.main_window._save_state("Flip horizontal")
		except Exception as e:
			from utils.logger import loggerRaise
			loggerRaise(e, f"Error flipping horizontally: {e}")
	
	def flip_y(self, orbit: bool = False):
		"""Flip selected layers vertically
		
		Args:
			orbit: If True, also mirror position across horizontal center axis (y → 1.0 - y)
		"""
		try:
			#COA INTEGRATION ACTION: Step 6 - Use CoA model for flip operations
			selected_uuids = self.main_window.right_sidebar.get_selected_uuids()
			if not selected_uuids:
				return
			
			# For flips, mirror positions for groups unless explicitly in rotate_only mode
			if not orbit and len(selected_uuids) > 1 and hasattr(self.main_window, 'canvas_area'):
				rotation_mode = self.main_window.canvas_area.get_rotation_mode()
				# Mirror positions unless mode is rotate_only (which means no position changes)
				orbit = 'rotate_only' not in rotation_mode.lower()
			
			# Use CoA model method that handles both single and group flips
			self.main_window.coa.flip_selection(selected_uuids, flip_x=False, flip_y=True, orbit=orbit)
			
			# Update UI
			self.main_window.right_sidebar._load_layer_properties()
			self.main_window.canvas_area.canvas_widget.update()
			self.main_window.canvas_area.update_transform_widget_for_layer()
			
			# Save to history
			self.main_window._save_state("Flip vertical")
		except Exception as e:
			from utils.logger import loggerRaise
			loggerRaise(e, f"Error flipping vertically: {e}")
	
	def rotate_layers(self, degrees):
		"""Rotate selected layers by specified degrees
		
		Args:
			degrees: Rotation amount in degrees (90, 180, or -90)
		"""
		#COA INTEGRATION ACTION: Step 6 - Use CoA model for rotation operations
		selected_uuids = self.main_window.right_sidebar.get_selected_uuids()
		if not selected_uuids:
			return
		
		# Get rotation mode from canvas area
		rotation_mode = 'auto'  # Default
		if hasattr(self.main_window, 'canvas_area'):
			rotation_mode = self.main_window.canvas_area.get_rotation_mode()
		
		# Use group rotation method that handles both single and multiple layers
		self.main_window.coa.rotate_selection(selected_uuids, degrees, rotation_mode)
		
		# Update UI
		self.main_window.right_sidebar._load_layer_properties()
		self.main_window.canvas_area.canvas_widget.update()
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
		
		# Update UI
		self.main_window.right_sidebar._load_layer_properties()
		self.main_window.canvas_area.canvas_widget.update()
		self.main_window.canvas_area.update_transform_widget_for_layer()
		
		# Save to history
		self.main_window._save_state(f"Move to {position}")
