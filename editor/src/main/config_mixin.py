"""Configuration management for CoatOfArmsEditor"""

import os
import json
from PyQt5.QtWidgets import QMessageBox
from utils.logger import loggerRaise


class ConfigMixin:
	"""Configuration file operations, recent files, and autosave"""
	
	def _load_config(self):
		"""Load recent files and settings from config file"""
		try:
			if os.path.exists(self.config_file):
				with open(self.config_file, 'r', encoding='utf-8') as f:
					config = json.load(f)
					self.recent_files = config.get('recent_files', [])
					# Filter out files that no longer exist
					self.recent_files = [f for f in self.recent_files if os.path.exists(f)]
		except Exception as e:
			loggerRaise(e, "Error loading config")
	
	def _save_config(self):
		"""Save recent files and settings to config file"""
		try:
			# Create config directory if it doesn't exist
			os.makedirs(self.config_dir, exist_ok=True)
			
			config = {
				'recent_files': self.recent_files[:self.max_recent_files]
			}
			
			with open(self.config_file, 'w', encoding='utf-8') as f:
				json.dump(config, f, indent=2)
		except Exception as e:
			loggerRaise(e, "Error saving config")
	
	def _add_to_recent_files(self, filepath):
		"""Add a file to the recent files list"""
		# Remove if already in list
		if filepath in self.recent_files:
			self.recent_files.remove(filepath)
		
		# Add to front of list
		self.recent_files.insert(0, filepath)
		
		# Trim to max size
		self.recent_files = self.recent_files[:self.max_recent_files]
		
		# Update menu
		if hasattr(self, 'recent_menu'):
			self._update_recent_files_menu()
		
		# Save config
		self._save_config()
	
	def _update_recent_files_menu(self):
		"""Update the Recent Files submenu"""
		self.recent_menu.clear()
		
		if not self.recent_files:
			no_recent = self.recent_menu.addAction("No recent files")
			no_recent.setEnabled(False)
		else:
			for filepath in self.recent_files:
				if os.path.exists(filepath):
					filename = os.path.basename(filepath)
					action = self.recent_menu.addAction(filename)
					action.setToolTip(filepath)
					# Use lambda with default argument to capture filepath
					action.triggered.connect(lambda checked, f=filepath: self._open_recent_file(f))
			
			self.recent_menu.addSeparator()
			clear_action = self.recent_menu.addAction("Clear Recent Files")
			clear_action.triggered.connect(self._clear_recent_files)
	
	def _clear_recent_files(self):
		"""Clear the recent files list"""
		self.recent_files = []
		self._update_recent_files_menu()
		self._save_config()
	
	def _open_recent_file(self, filepath):
		"""Open a file from the recent files list"""
		if not os.path.exists(filepath):
			QMessageBox.warning(self, "File Not Found", f"The file no longer exists:\n{filepath}")
			# Remove from recent files
			self.recent_files.remove(filepath)
			self._update_recent_files_menu()
			self._save_config()
			return
		
		# Prompt to save current changes
		if not self._prompt_save_if_needed():
			return
		
		try:
			# Read file
			with open(filepath, 'r', encoding='utf-8') as f:
				coa_text = f.read()
			
			# Clear and parse into existing CoA instance
			self.coa.clear()
			self.coa.parse(coa_text)
			
			# Clear selection from previous CoA BEFORE any UI updates that might query it
			self.right_sidebar.layer_list_widget.selected_layer_uuids.clear()
			self.right_sidebar.layer_list_widget.last_selected_uuid = None
			
			# Apply to UI - update from model
			# Set base texture and colors
			self.canvas_area.canvas_widget.set_base_texture(self.coa.pattern)
			self.canvas_area.canvas_widget.set_base_colors([self.coa.pattern_color1, self.coa.pattern_color2, self.coa.pattern_color3])
			self.right_sidebar.tab_widget.setCurrentIndex(1)
			self.right_sidebar._rebuild_layer_list()

			# Update canvas
			self.canvas_area.canvas_widget.update()
			
			# Set current file path and mark as saved
			self.current_file_path = filepath
			self.is_saved = True
			self._update_window_title()
			
			# Add to recent files (moves to top)
			self._add_to_recent_files(filepath)
			
			# Clear history and save initial state
			self.history_manager.clear()
			self._save_state("Load CoA")
		except Exception as e:
			loggerRaise(e, "Failed to load coat of arms")
		self._update_recent_files_menu()
		self._save_config()
	
	def _autosave(self):
		"""Perform autosave to temporary file"""
		try:
			# Only autosave if there are unsaved changes
			if not self.is_saved:
				# Create config directory if it doesn't exist
				os.makedirs(self.config_dir, exist_ok=True)
				
				# Save using model
				coa_string = self.coa.to_string()
				with open(self.autosave_file, 'w', encoding='utf-8') as f:
					f.write(coa_string)
				
				print("Autosaved")
		except Exception as e:
			loggerRaise(e, "Autosave failed")
	
	def _check_autosave_recovery(self):
		"""Check for autosave file and prompt for recovery"""
		try:
			if os.path.exists(self.autosave_file):
				reply = QMessageBox.question(
					self,
					"Recover Autosave",
					"An autosave file was found. Would you like to recover it?",
					QMessageBox.Yes | QMessageBox.No,
					QMessageBox.Yes
				)
				
				if reply == QMessageBox.Yes:
					# Read and parse into existing CoA instance
					with open(self.autosave_file, 'r', encoding='utf-8') as f:
						coa_text = f.read()
					self.coa.clear()
					self.coa.parse(coa_text)
					
					# Apply to UI - update from model
					self.canvas_area.canvas_widget.set_base_texture(self.coa.pattern)
					self.canvas_area.canvas_widget.set_base_colors([self.coa.pattern_color1, self.coa.pattern_color2, self.coa.pattern_color3])
					self.canvas_area.canvas_widget.base_color1_name = self.coa.pattern_color1_name
					self.canvas_area.canvas_widget.base_color2_name = self.coa.pattern_color2_name
					self.canvas_area.canvas_widget.base_color3_name = self.coa.pattern_color3_name
					
					base_color_names = [self.coa.pattern_color1_name, self.coa.pattern_color2_name, self.coa.pattern_color3_name]
					self.right_sidebar.set_base_colors([self.coa.pattern_color1, self.coa.pattern_color2, self.coa.pattern_color3], base_color_names)
					
					# Update UI
					self.right_sidebar.tab_widget.setCurrentIndex(1)
					
					# Mark as unsaved (since it's recovered from autosave)
					self.current_file_path = None
					self.is_saved = False
					self._update_window_title()
					
					# Clear history and save state
					self.history_manager.clear()
					self._save_state("Recover autosave")
					
					# Remove autosave file after recovery
					os.remove(self.autosave_file)
		except Exception as e:
			loggerRaise(e, "Error checking autosave")
	
	def _update_window_title(self):
		"""Update window title with current file name"""
		if self.current_file_path:
			filename = os.path.basename(self.current_file_path)
			modified = "" if self.is_saved else "*"
			self.setWindowTitle(f"{filename}{modified} - Coat Of Arms Designer")
		else:
			modified = "" if self.is_saved else "*"
			self.setWindowTitle(f"Untitled{modified} - Coat Of Arms Designer")
	
	def _prompt_save_if_needed(self):
		"""Prompt user to save if there are unsaved changes
		
		Returns:
			True if it's safe to proceed (saved or discarded)
			False if user cancelled
		"""
		if not self.is_saved:
			reply = QMessageBox.question(
				self,
				"Unsaved Changes",
				"Do you want to save your changes?",
				QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
				QMessageBox.Save
			)
			
			if reply == QMessageBox.Save:
				self.file_actions.save_coa()
				# Check if save was successful (user might have cancelled save dialog)
				return self.is_saved
			elif reply == QMessageBox.Cancel:
				return False
			# Discard falls through
		
		return True
