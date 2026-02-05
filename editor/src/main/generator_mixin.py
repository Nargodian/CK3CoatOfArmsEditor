"""Layer generation and text rendering for CoatOfArmsEditor"""

from PyQt5.QtWidgets import QMessageBox
from services.layer_generator.generators import ShapeGenerator
from services.layer_generator import GeneratorPopup
from utils.logger import loggerRaise


class GeneratorMixin:
	"""Layer generation methods and generator popup management"""
	
	def _preload_shapes(self):
		"""Preload all SVG shapes at startup."""
		# Get path to SVG directory
		from utils.path_resolver import get_resource_path
		svg_dir = get_resource_path('assets/svg')
		
		# Preload shapes into ShapeGenerator
		ShapeGenerator.preload_shapes(str(svg_dir))
	
	def _populate_shape_menu(self):
		"""Populate the Shape submenu with loaded SVG shapes."""
		shape_names = ShapeGenerator.get_shape_names()
		
		if not shape_names:
			# No shapes available
			no_shapes_action = self.shape_menu.addAction("(No shapes available)")
			no_shapes_action.setEnabled(False)
			return
		
		# Add menu item for each shape
		for shape_name in shape_names:
			action = self.shape_menu.addAction(shape_name)
			action.triggered.connect(lambda checked, name=shape_name: self._open_generator('shape', name))
	
	def _open_generator(self, generator_type: str, shape_name: str = None):
		"""Open the generator popup with specified generator type.
		
		Args:
			generator_type: Type of generator ('circular', 'line', 'spiral', 'ngon', 'shape', 
			                'grid', 'diamond', 'fibonacci', 'radial', 'star')
			shape_name: For 'shape' type, the name of the shape to use
		"""
		from services.layer_generator.generators import (
			CircularGenerator, LineGenerator, SpiralGenerator, ShapeGenerator,
			GridGenerator, DiamondGenerator, FibonacciGenerator,
			RadialGenerator, StarGenerator, VanillaGenerator, NgonGenerator
		)
		
		# Create generator instance based on type
		generator = None
		
		if generator_type == 'circular':
			generator = CircularGenerator()
		elif generator_type == 'line':
			generator = LineGenerator()
		elif generator_type == 'spiral':
			generator = SpiralGenerator()
		elif generator_type == 'ngon':
			generator = NgonGenerator()
		elif generator_type == 'shape':
			generator = ShapeGenerator(initial_shape=shape_name)
		elif generator_type == 'grid':
			generator = GridGenerator()
		elif generator_type == 'diamond':
			generator = DiamondGenerator()
		elif generator_type == 'fibonacci':
			generator = FibonacciGenerator()
		elif generator_type == 'radial':
			generator = RadialGenerator()
		elif generator_type == 'star':
			generator = StarGenerator()
		elif generator_type == 'vanilla':
			generator = VanillaGenerator()
		else:
			print(f"Unknown generator type: {generator_type}")
			return
		
		# Create popup if it doesn't exist
		if not self.generator_popup:
			self.generator_popup = GeneratorPopup(self)
		
		# Load generator into popup
		self.generator_popup.load_generator(generator)
		
		# Show popup
		result = self.generator_popup.exec_()
		
		# If user clicked Generate, create the layer
		if result == self.generator_popup.Accepted:
			# Check if text mode is active
			if self.generator_popup.is_text_mode():
				# Text mode: will create multiple layers (one per character)
				text_data = self.generator_popup.get_text_and_positions()
				if text_data:
					text, positions = text_data
					# Show warning dialog
					reply = QMessageBox.question(
						self,
						'Text Mode Warning',
						'Text mode will create multiple layers (one per character), not a single multi-instance layer.\n\nContinue?',
						QMessageBox.Yes | QMessageBox.No,
						QMessageBox.No
					)
					if reply == QMessageBox.Yes:
						self._create_text_layers(text, positions)
			else:
				# Count mode: create single multi-instance layer
				generated_instances = self.generator_popup.get_generated_instances()
				if generated_instances is not None and len(generated_instances) > 0:
					self._create_generated_layer(generated_instances)
	
	def _open_generator_with_asset(self, asset_texture: str, generator_type: str = 'circular'):
		"""Open generator popup with pre-selected asset.
		
		Args:
			asset_texture: Texture filename (.dds) of the asset to use
			generator_type: Type of generator to open ('circular', 'line', 'spiral', 'grid', 'diamond', 'fibonacci', 'radial', 'star', 'vanilla')
		"""
		from services.layer_generator.generators import (
			CircularGenerator, LineGenerator, SpiralGenerator,
			GridGenerator, DiamondGenerator, FibonacciGenerator,
			RadialGenerator, StarGenerator, VanillaGenerator
		)
		
		# Import and create appropriate generator based on type
		generator = None
		
		if generator_type == 'circular':
			generator = CircularGenerator()
		elif generator_type == 'line':
			generator = LineGenerator()
		elif generator_type == 'spiral':
			generator = SpiralGenerator()
		elif generator_type == 'grid':
			generator = GridGenerator()
		elif generator_type == 'diamond':
			generator = DiamondGenerator()
		elif generator_type == 'fibonacci':
			generator = FibonacciGenerator()
		elif generator_type == 'radial':
			generator = RadialGenerator()
		elif generator_type == 'star':
			generator = StarGenerator()
		elif generator_type == 'vanilla':
			generator = VanillaGenerator()
		
		if not generator:
			return
		
		# Create popup if it doesn't exist
		if not self.generator_popup:
			self.generator_popup = GeneratorPopup(self)
		
		# Load generator into popup
		self.generator_popup.load_generator(generator)
		
		# Show popup
		result = self.generator_popup.exec_()
		
		# If user clicked Generate, create the layer with selected asset
		if result == self.generator_popup.Accepted:
			# Check if text mode is active
			if self.generator_popup.is_text_mode():
				# Text mode: will create multiple layers (one per character) in a container
				text_data = self.generator_popup.get_text_and_positions()
				if text_data:
					text, positions = text_data
					self._create_text_layers(text, positions, emblem_texture=asset_texture)
			else:
				# Count mode: create single multi-instance layer
				generated_instances = self.generator_popup.get_generated_instances()
				if generated_instances is not None and len(generated_instances) > 0:
					self._create_generated_layer(generated_instances, emblem_texture=asset_texture)
	
	def _create_generated_layer(self, instances, emblem_texture: str = None):
		"""Create a layer from generated instance transforms.
		
		Args:
			instances: 5xN numpy array [[x, y, scale_x, scale_y, rotation], ...]
			emblem_texture: Optional custom emblem texture (.dds filename)
		"""
		try:
			import numpy as np
			from services.layer_generator.layer_string_builder import build_layer_string
			
			default_emblem = emblem_texture if emblem_texture else "ce_fleur.dds"
			
			# Apply frame scale compensation to prevent growth on drag
			# Get current frame scale
			frame_scale, _ = self.canvas_area.canvas_widget.get_frame_transform()
			frame_scale_x, frame_scale_y = frame_scale
			
			# Compensate instance scales by dividing by frame scale
			compensated_instances = instances.copy()
			compensated_instances[:, 2] /= frame_scale_x  # scale_x
			compensated_instances[:, 3] /= frame_scale_y  # scale_y
			
			# Build layer string
			layer_string = build_layer_string(compensated_instances, default_emblem)
			
			# Check for selection to insert above
			selected_uuids = self.right_sidebar.get_selected_uuids()
			target_uuid = selected_uuids[0] if selected_uuids else None
			
			# Parse directly into main CoA (parser handles insertion)
			new_uuids = self.coa.parse(layer_string, target_uuid=target_uuid)
			
			# Switch to Layers tab
			self.right_sidebar.tab_widget.setCurrentIndex(1)
			
			# Update UI
			self.right_sidebar._rebuild_layer_list()
			self.canvas_area.canvas_widget.on_coa_structure_changed()  # Invalidate picker RTT
			self.canvas_area.canvas_widget.update()
			
			# Select the newly created layer
			if new_uuids:
				self.right_sidebar.layer_list_widget.selected_layer_uuids = set(new_uuids)
				self.right_sidebar.layer_list_widget.last_selected_uuid = new_uuids[0]
				self.right_sidebar.layer_list_widget.update_selection_visuals()
			
			# Save to history
			count = len(instances)
			self._save_state(f"Generate layer ({count} instances)")
			
			self.status_left.setText(f"Generated layer with {count} instances")
			
		except Exception as e:
			loggerRaise(e, f"Failed to create generated layer: {str(e)}")
	
	def _create_text_layers(self, text: str, positions, emblem_texture: str = None):
		"""Create multiple layers for text mode (one layer per character).
		
		Args:
			text: Text string to render
			positions: 6xN numpy array [[x, y, scale_x, scale_y, rotation, label_code], ...]
			emblem_texture: Optional custom emblem texture (ignored for text - uses letter emblems)
		"""
		try:
			from services.layer_generator.text_emblem_mapper import get_emblem_for_char, label_code_to_char
			from services.layer_generator.layer_string_builder import build_layer_string
			
			# Reconstruct filtered text from label codes (6th column)
			# This ensures we match exactly what the generator used
			if positions.shape[1] < 6:
				print("Error: positions array missing label codes (6th column)")
				return
			
			label_codes = positions[:, 5].astype(int)
			filtered_text = ''.join(label_code_to_char(code) for code in label_codes)
			
			if len(filtered_text) == 0:
				print("No valid characters in text")
				return
			
			# Generate container UUID for all text layers
			container_name = f"text ({filtered_text})"
			container_uuid = self.coa.generate_container_uuid(container_name)
			
			# Check for selection to insert above
			selected_uuids = self.right_sidebar.get_selected_uuids()
			target_uuid = selected_uuids[0] if selected_uuids else None
			
			created_uuids = []
			
			# Create layers in reverse order so layer list reads correctly top-to-bottom
			for i in range(len(filtered_text) - 1, -1, -1):
				char = filtered_text[i]
				if char == ' ':
					continue  # Skip spaces - no layer created
				
				# Get emblem for this character
				emblem = get_emblem_for_char(char)
				if not emblem:
					continue  # Skip invalid characters
				
				# Build layer string (single instance, use first 5 columns)
				layer_string = build_layer_string(positions[i], emblem, container_uuid=container_uuid)
				
				# Parse directly into main CoA (parser handles insertion)
				new_uuids = self.coa.parse(layer_string, target_uuid=target_uuid)
				
				# Stack subsequent layers on top
				if new_uuids:
					target_uuid = new_uuids[0]
					created_uuids.extend(new_uuids)
			
			# Switch to Layers tab
			self.right_sidebar.tab_widget.setCurrentIndex(1)
			
			# Update UI
			self.right_sidebar._rebuild_layer_list()
			self.canvas_area.canvas_widget.on_coa_structure_changed()  # Invalidate picker RTT
			self.canvas_area.canvas_widget.update()
			
			# Select the newly created container and collapse it
			if created_uuids:
				self.right_sidebar.layer_list_widget.selected_layer_uuids = set(created_uuids)
				self.right_sidebar.layer_list_widget.selected_container_uuids = {container_uuid}
				self.right_sidebar.layer_list_widget.collapsed_containers.add(container_uuid)  # Start collapsed
				self.right_sidebar.layer_list_widget.last_selected_uuid = created_uuids[-1]
				self.right_sidebar.layer_list_widget.update_selection_visuals()
			
			# Save to history
			char_count = len(created_uuids)
			self._save_state(f"Generate text layers ({char_count} characters)")
			
			self.status_left.setText(f"Generated {char_count} text layers in container")
			
		except Exception as e:
			loggerRaise(e, f"Failed to create text layers: {str(e)}")
