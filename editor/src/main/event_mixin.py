"""Window event handlers for CoatOfArmsEditor"""

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer
from PyQt5 import QtWidgets


class EventMixin:
	"""Window event handlers (resize, show, eventFilter, keyPress)"""
	
	def resizeEvent(self, event):
		"""Handle window resize"""
		super().resizeEvent(event)
		# FlowLayout handles resize automatically, no manual recalculation needed
	
	def showEvent(self, event):
		"""Handle window show - save initial state after UI is set up"""
		super().showEvent(event)
		# Save initial state on first show (after OpenGL is initialized)
		if not hasattr(self, '_initial_state_saved'):
			self._initial_state_saved = True
			# Use a timer to ensure everything is fully initialized
			QTimer.singleShot(100, lambda: self._save_state("Initial state"))
	
	def eventFilter(self, obj, event):
		"""Filter events to capture arrow keys and context menus before child widgets consume them"""
		# Handle context menu events globally
		if event.type() == event.ContextMenu:
			# Get the widget under the cursor
			global_pos = event.globalPos()
			widget_under_cursor = QApplication.widgetAt(global_pos)
			
			# Traverse up to find the relevant widget
			while widget_under_cursor:
				# Check if we're over the canvas area or canvas widget
				if widget_under_cursor == self.canvas_area or widget_under_cursor == self.canvas_area.canvas_widget:
					menu = QtWidgets.QMenu(self)
					for action in self.edit_menu.actions():
						if action.isSeparator():
							menu.addSeparator()
						else:
							menu.addAction(action)
					menu.exec_(global_pos)
					return True
				
				# Check if we're over the layer list
				elif widget_under_cursor == self.right_sidebar.layer_list_widget or widget_under_cursor.parent() == self.right_sidebar.layer_list_widget:
					menu = QtWidgets.QMenu(self)
					for action in self.layers_menu.actions():
						if action.isSeparator():
							menu.addSeparator()
						else:
							menu.addAction(action)
					menu.exec_(global_pos)
					return True
				
				widget_under_cursor = widget_under_cursor.parent()
			
		if event.type() == event.KeyPress:
			# Intercept arrow keys when layers are selected
			if event.key() in [Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down]:
				selected_uuids = self.right_sidebar.get_selected_uuids()
				if selected_uuids:
					# Handle arrow key movement
					from constants import ARROW_KEY_MOVE_NORMAL, ARROW_KEY_MOVE_FINE
					move_amount = ARROW_KEY_MOVE_FINE if event.modifiers() & Qt.ShiftModifier else ARROW_KEY_MOVE_NORMAL
					
					for uuid in selected_uuids:
						current_x, current_y = self.coa.get_layer_position(uuid)
						
						if event.key() == Qt.Key_Left:
							new_x = current_x - move_amount
							self.coa.set_layer_position(uuid, new_x, current_y)
						elif event.key() == Qt.Key_Right:
							new_x = current_x + move_amount
							self.coa.set_layer_position(uuid, new_x, current_y)
						elif event.key() == Qt.Key_Up:
							new_y = current_y - move_amount
							self.coa.set_layer_position(uuid, current_x, new_y)
						elif event.key() == Qt.Key_Down:
							new_y = current_y + move_amount
							self.coa.set_layer_position(uuid, current_x, new_y)
					
					# Update UI
					self.right_sidebar._load_layer_properties()
					self.canvas_area.canvas_widget.update()
					self.canvas_area.update_transform_widget_for_layer()
					
					# Save to history
					self.save_property_change_debounced("Move layer with arrow keys")
					
					# Consume the event so child widgets don't process it
					return True
		
		# Let all other events pass through
		return False
	
	def keyPressEvent(self, event):
		"""Handle keyboard shortcuts"""
		# Ctrl+S for save
		if event.key() == Qt.Key_S and event.modifiers() == Qt.ControlModifier:
			self.save_coa()
			event.accept()
		# Ctrl+D for duplicate layer
		elif event.key() == Qt.Key_D and event.modifiers() == Qt.ControlModifier:
			if self.right_sidebar.get_selected_indices():
				self.clipboard_actions.duplicate_selected_layer()
				event.accept()
			else:
				super().keyPressEvent(event)
		# Ctrl+Z for undo
		elif event.key() == Qt.Key_Z and event.modifiers() == Qt.ControlModifier:
			self.undo()
			event.accept()
		# Ctrl+Y for redo
		elif event.key() == Qt.Key_Y and event.modifiers() == Qt.ControlModifier:
			self.redo()
			event.accept()
		# Ctrl+C for copy layer
		elif event.key() == Qt.Key_C and event.modifiers() == Qt.ControlModifier:
			if self.right_sidebar.get_selected_indices():
				self.clipboard_actions.copy_layer()
				event.accept()
			else:
				super().keyPressEvent(event)
		# Ctrl+V for paste layer - will be handled by canvas_area if over canvas
		elif event.key() == Qt.Key_V and event.modifiers() == Qt.ControlModifier:
			# Check if mouse is over canvas
			if hasattr(self, 'canvas_area'):
				mouse_pos = self.canvas_area.mapFromGlobal(self.cursor().pos())
				canvas_geometry = self.canvas_area.canvas_widget.geometry()
				if canvas_geometry.contains(mouse_pos):
					# Mouse is over canvas, paste at mouse position
					self.clipboard_actions.paste_layer_at_position(mouse_pos, canvas_geometry)
					event.accept()
					return
			# Otherwise, paste at center
			self.clipboard_actions.paste_layer()
			event.accept()
		# Delete key for delete layer
		elif event.key() == Qt.Key_Delete:
			if self.right_sidebar.get_selected_indices():
				self.right_sidebar._delete_layer()
				event.accept()
			else:
				super().keyPressEvent(event)
		# Ctrl+A for select all layers
		elif event.key() == Qt.Key_A and event.modifiers() & Qt.ControlModifier:
			layer_count = self.coa.get_layer_count()
			if layer_count > 0:
				# Select all layer indices
				all_indices = set(range(layer_count))
				self.right_sidebar.set_selected_indices(all_indices)
				# Update transform widget for multi-selection
				if self.canvas_area:
					self.canvas_area.update_transform_widget_for_layer()
				# Enable properties tab
				self.right_sidebar.tab_widget.setTabEnabled(2, True)
				event.accept()
			else:
				super().keyPressEvent(event)
		# M key for toggle minimal transform widget
		elif event.key() == Qt.Key_M and not event.modifiers():
			# Cycle through transform modes: Normal -> Minimal -> Gimble -> Normal
			current_index = self.canvas_area.transform_mode_combo.currentIndex()
			next_index = (current_index + 1) % 3
			self.canvas_area.transform_mode_combo.setCurrentIndex(next_index)
			event.accept()
		# P key for toggle picker tool
		elif event.key() == Qt.Key_P and not event.modifiers():
			self.canvas_area.bottom_bar.picker_btn.toggle()
			event.accept()
		# R key for rotate -45 degrees
		elif event.key() == Qt.Key_R and not event.modifiers():
			if self.right_sidebar.get_selected_indices():
				self._rotate_selected_layers(-45)
				event.accept()
			else:
				super().keyPressEvent(event)
		# Shift+R for rotate +45 degrees
		elif event.key() == Qt.Key_R and event.modifiers() == Qt.ShiftModifier:
			if self.right_sidebar.get_selected_indices():
				self._rotate_selected_layers(45)
				event.accept()
			else:
				super().keyPressEvent(event)
		else:
			super().keyPressEvent(event)
	
	def _rotate_selected_layers(self, angle_delta):
		"""Rotate selected layers by the specified angle."""
		selected_indices = self.right_sidebar.get_selected_indices()
		if not selected_indices:
			return
		
		# Rotate each selected layer
		for idx in selected_indices:
			if 0 <= idx < self.coa.get_layer_count():
				layer = self.coa.get_layer_by_index(idx)
				layer.rotation = (layer.rotation + angle_delta) % 360
		
		# Update canvas
		self.canvas_area.canvas_widget.update()
		
		# Update transform widget (which updates properties panel)
		self.canvas_area.update_transform_widget_for_layer()
		
		# Save to history
		self._save_state(f"Rotate {'+' if angle_delta > 0 else ''}{angle_delta}°")
	
	def closeEvent(self, event):
		"""Handle window close event - prompt to save if needed"""
		if self._prompt_save_if_needed():
			# Save config before closing
			self._save_config()
			event.accept()
		else:
			event.ignore()
