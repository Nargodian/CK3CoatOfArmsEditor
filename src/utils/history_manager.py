"""
Undo/Redo History Manager for Coat of Arms Editor

Manages state history with undo/redo functionality.
Tracks all changes to layers, properties, and CoA-level operations.
"""

import copy


class HistoryManager:
	"""Manages undo/redo history with state snapshots"""
	
	def __init__(self, max_history=50):
		"""
		Initialize the history manager
		
		Args:
			max_history: Maximum number of states to keep in history
		"""
		self.max_history = max_history
		self.history = []  # List of state snapshots
		self.current_index = -1  # Current position in history (-1 means no states)
		self._listeners = []  # Callbacks to notify on state changes
	
	def save_state(self, state_data, description=""):
		"""
		Save a new state to history
		
		Args:
			state_data: Dictionary containing the full state to save
			description: Optional description of the change
		"""
		# If we're not at the end of history, remove everything after current position
		if self.current_index < len(self.history) - 1:
			self.history = self.history[:self.current_index + 1]
		
		# Create a deep copy of the state
		snapshot = {
			'data': copy.deepcopy(state_data),
			'description': description
		}
		
		# Add to history
		self.history.append(snapshot)
		self.current_index += 1
		
		# Trim history if it exceeds max_history
		if len(self.history) > self.max_history:
			self.history.pop(0)
			self.current_index -= 1
		
		# Notify listeners
		self._notify_listeners()
		
		print(f"[History] State saved: {description} (index: {self.current_index}, total: {len(self.history)})")
	
	def undo(self):
		"""
		Move back one state in history
		
		Returns:
			Dictionary containing the previous state, or None if at beginning
		"""
		if not self.can_undo():
			print("[History] Cannot undo - at beginning of history")
			return None
		
		# Move back one position
		self.current_index -= 1
		state = self.history[self.current_index]['data']
		description = self.history[self.current_index]['description']
		
		# Notify listeners
		self._notify_listeners()
		
		print(f"[History] Undo to: {description} (index: {self.current_index})")
		return copy.deepcopy(state)
	
	def redo(self):
		"""
		Move forward one state in history
		
		Returns:
			Dictionary containing the next state, or None if at end
		"""
		if not self.can_redo():
			print("[History] Cannot redo - at end of history")
			return None
		
		# Move forward one position
		self.current_index += 1
		state = self.history[self.current_index]['data']
		description = self.history[self.current_index]['description']
		
		# Notify listeners
		self._notify_listeners()
		
		print(f"[History] Redo to: {description} (index: {self.current_index})")
		return copy.deepcopy(state)
	
	def can_undo(self):
		"""Check if undo is available"""
		return self.current_index > 0
	
	def can_redo(self):
		"""Check if redo is available"""
		return self.current_index < len(self.history) - 1
	
	def clear(self):
		"""Clear all history"""
		self.history = []
		self.current_index = -1
		self._notify_listeners()
		print("[History] History cleared")
	
	def add_listener(self, callback):
		"""
		Add a listener to be notified when history state changes
		
		Args:
			callback: Function to call when history changes (receives can_undo, can_redo)
		"""
		self._listeners.append(callback)
	
	def remove_listener(self, callback):
		"""Remove a listener"""
		if callback in self._listeners:
			self._listeners.remove(callback)
	
	def _notify_listeners(self):
		"""Notify all listeners of history state change"""
		for callback in self._listeners:
			try:
				callback(self.can_undo(), self.can_redo())
			except Exception as e:
				print(f"[History] Error notifying listener: {e}")
	
	def get_current_description(self):
		"""Get the description of the current state"""
		if 0 <= self.current_index < len(self.history):
			return self.history[self.current_index]['description']
		return ""
	
	def get_undo_description(self):
		"""Get the description of the state that would be restored by undo"""
		if self.can_undo():
			return self.history[self.current_index - 1]['description']
		return ""
	
	def get_redo_description(self):
		"""Get the description of the state that would be restored by redo"""
		if self.can_redo():
			return self.history[self.current_index + 1]['description']
		return ""
