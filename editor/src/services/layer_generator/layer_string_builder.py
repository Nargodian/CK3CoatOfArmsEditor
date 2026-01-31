"""Helper functions for building CK3 layer format strings."""

def build_layer_string(instances: 'np.ndarray', emblem_texture: str) -> str:
	"""Build CK3 format string for a layer with instances.
	
	Args:
		instances: Nx5 or Nx6 numpy array [[x, y, scale_x, scale_y, rotation, (label_code)], ...]
		          or single instance [x, y, scale_x, scale_y, rotation, (label_code)]
		          6th column (label_code) is optional and ignored if present
		emblem_texture: Emblem texture filename (.dds)
		
	Returns:
		CK3 format layer string
	"""
	import numpy as np
	
	# Ensure instances is 2D array
	if instances.ndim == 1:
		instances = instances.reshape(1, -1)
	
	lines = []
	lines.append("layers_export = {")
	lines.append("\tcolored_emblem = {")
	lines.append(f'\t\ttexture = "{emblem_texture}"')
	lines.append('\t\tcolor1 = "white"')
	
	# Serialize each instance (use only first 5 columns)
	for instance_data in instances:
		x, y, scale_x, scale_y, rotation = instance_data[:5]  # Ignore 6th column if present
		lines.append('\t\t\tinstance = {')
		lines.append(f'\t\t\t\tposition = {{ {x} {y} }}')
		lines.append(f'\t\t\t\tscale = {{ {scale_x} {scale_y} }}')
		if rotation != 0:
			lines.append(f'\t\t\t\trotation = {rotation}')
		lines.append('\t\t\t}')
	
	lines.append("\t}")
	lines.append("}")
	
	return '\n'.join(lines)
