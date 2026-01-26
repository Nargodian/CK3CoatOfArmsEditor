"""File operations for the main window - new, save, load, export"""
from PyQt5.QtWidgets import QFileDialog, QMessageBox


class FileActions:
	"""Handles all file menu operations"""
	
	def __init__(self, main_window):
		"""Initialize with reference to main window
		
		Args:
			main_window: The CoatOfArmsEditor main window instance
		"""
		self.main_window = main_window
	
	def new_coa(self):
		"""Create new CoA, prompt to save if needed"""
		if not self.main_window._prompt_save_if_needed():
			return
		
		# Reset current file and modified flag
		self.main_window.current_file = None
		self.main_window.is_modified = False
		self.main_window._update_window_title()
		
		# Get starting layers from _default_layers
		default_layers = self.main_window._default_layers
		
		# Clear history before loading (to avoid storing default state)
		self.main_window.history_manager.clear()
		
		# Set layers in both property sidebar and canvas
		self.main_window.right_sidebar.set_layers(default_layers)
		self.main_window.canvas_area.canvas_widget.set_layers(default_layers)
		
		# Create initial history entry
		self.main_window._save_state("New CoA")
		
		# Reset modified flag (saving state sets it to True)
		self.main_window.is_modified = False
		
		# Update UI
		self.main_window._update_window_title()
		self.main_window._update_status_bar()
	
	def save_coa(self):
		"""Save the current coat of arms"""
		if self.main_window.current_file:
			self._save_to_file(self.main_window.current_file)
		else:
			self.save_coa_as()
	
	def save_coa_as(self):
		"""Save the current coat of arms to a new file"""
		from services.file_operations import save_coa_to_file
		
		filename, _ = QFileDialog.getSaveFileName(
			self.main_window,
			"Save Coat of Arms",
			"",
			"Text Files (*.txt);;All Files (*)"
		)
		if filename:
			self._save_to_file(filename)
	
	def _save_to_file(self, filename):
		"""Internal save method
		
		Args:
			filename: Path to save file to
		"""
		from services.file_operations import save_coa_to_file, build_coa_for_save
		
		try:
			# Build CoA data structure from current layers
			coa_data = build_coa_for_save(self.main_window.right_sidebar.layers)
			
			# Save to file
			save_coa_to_file(coa_data, filename)
			
			# Update current file and title
			self.main_window.current_file = filename
			self.main_window.is_modified = False
			self.main_window._update_window_title()
			
			# Add to recent files
			self.main_window._add_to_recent_files(filename)
			
			# Update status
			import os
			self.main_window.status_left.setText(f"Saved to {os.path.basename(filename)}")
			
		except Exception as e:
			QMessageBox.critical(
				self.main_window,
				"Error",
				f"Failed to save file: {str(e)}"
			)
	
	def load_coa(self):
		"""Load a coat of arms from file"""
		from services.file_operations import load_coa_from_file
		from services.coa_serializer import parse_coa_for_editor
		
		if not self.main_window._prompt_save_if_needed():
			return
		
		filename, _ = QFileDialog.getOpenFileName(
			self.main_window,
			"Load Coat of Arms",
			"",
			"Text Files (*.txt);;All Files (*)"
		)
		
		if filename:
			try:
				# Load and parse the file
				coa_data = load_coa_from_file(filename)
				layers = parse_coa_for_editor(coa_data, self.main_window._find_asset_path)
				
				# Clear history before loading
				self.main_window.history_manager.clear()
				
				# Set layers
				self.main_window.right_sidebar.set_layers(layers)
				self.main_window.canvas_area.canvas_widget.set_layers(layers)
				
				# Update file tracking
				self.main_window.current_file = filename
				self.main_window.is_modified = False
				self.main_window._update_window_title()
				
				# Add to recent files
				self.main_window._add_to_recent_files(filename)
				
				# Create initial history entry
				self.main_window._save_state("Load CoA")
				self.main_window.is_modified = False
				
			except Exception as e:
				QMessageBox.critical(
					self.main_window,
					"Error",
					f"Failed to load file: {str(e)}"
				)
	
	def export_png(self):
		"""Export current CoA as PNG with transparency"""
		try:
			# Open save file dialog
			filename, _ = QFileDialog.getSaveFileName(
				self.main_window,
				"Export as PNG",
				"",
				"PNG Files (*.png);;All Files (*)"
			)
			
			if not filename:
				return
			
			# Ensure .png extension
			if not filename.lower().endswith('.png'):
				filename += '.png'
			
			# Get the canvas widget's pixmap/image
			pixmap = self.main_window.canvas_area.canvas_widget.grab()
			
			# Save to file
			pixmap.save(filename, 'PNG')
			
			# Update status
			import os
			self.main_window.status_left.setText(f"Exported to {os.path.basename(filename)}")
			
		except Exception as e:
			QMessageBox.critical(
				self.main_window,
				"Export Error",
				f"Failed to export PNG: {str(e)}"
			)
