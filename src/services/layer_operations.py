"""
CK3 Coat of Arms Editor - Layer Operations Service

This module handles layer creation, duplication, and manipulation operations.
These functions provide layer manipulation logic independent of the UI.
"""

from utils.coa_parser import parse_coa_string, serialize_coa_to_string
from utils.color_utils import color_name_to_rgb, rgb_to_color_name
from constants import (
    DEFAULT_POSITION_X, DEFAULT_POSITION_Y,
    DEFAULT_SCALE_X, DEFAULT_SCALE_Y,
    DEFAULT_ROTATION,
    DEFAULT_EMBLEM_COLOR1, DEFAULT_EMBLEM_COLOR2, DEFAULT_EMBLEM_COLOR3,
    CK3_NAMED_COLORS
)


def create_default_layer(filename, colors=3, **overrides):
    """Create new layer with default values
    
    Args:
        filename: Texture filename for the layer
        colors: Number of colors (1, 2, or 3)
        **overrides: Optional property overrides (pos_x, pos_y, scale_x, etc.)
        
    Returns:
        Dictionary with layer data
    """
    layer_data = {
        'filename': filename,
        'path': filename,
        'colors': colors,
        'pos_x': DEFAULT_POSITION_X,
        'pos_y': DEFAULT_POSITION_Y,
        'scale_x': DEFAULT_SCALE_X,
        'scale_y': DEFAULT_SCALE_Y,
        'rotation': DEFAULT_ROTATION,
        'flip_x': False,
        'flip_y': False,
        'color1': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR1]['rgb'],
        'color2': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR2]['rgb'],
        'color3': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR3]['rgb'],
        'color1_name': DEFAULT_EMBLEM_COLOR1,
        'color2_name': DEFAULT_EMBLEM_COLOR2,
        'color3_name': DEFAULT_EMBLEM_COLOR3
    }
    
    # Apply any overrides
    layer_data.update(overrides)
    
    return layer_data


def duplicate_layer(layer, offset_x=0.0, offset_y=0.0):
    """Duplicate a layer with optional position offset
    
    Args:
        layer: Source layer dictionary
        offset_x: X position offset for duplicate
        offset_y: Y position offset for duplicate
        
    Returns:
        New layer dictionary (deep copy)
    """
    # Create a deep copy
    duplicated = dict(layer)
    
    # Apply offset if provided
    if offset_x != 0.0:
        duplicated['pos_x'] = min(1.0, max(0.0, layer.get('pos_x', 0.5) + offset_x))
    if offset_y != 0.0:
        duplicated['pos_y'] = min(1.0, max(0.0, layer.get('pos_y', 0.5) + offset_y))
    
    return duplicated


def serialize_layer_to_text(layer):
    """Serialize a single layer to colored_emblem block format
    
    Args:
        layer: Layer dictionary
        
    Returns:
        String in CoA colored_emblem format
    """
    instance_data = {
        "position": [layer.get('pos_x', DEFAULT_POSITION_X), layer.get('pos_y', DEFAULT_POSITION_Y)],
        "scale": [layer.get('scale_x', DEFAULT_SCALE_X), layer.get('scale_y', DEFAULT_SCALE_Y)],
        "rotation": int(layer.get('rotation', DEFAULT_ROTATION))
    }
    
    emblem_data = {
        "texture": layer.get('filename', ''),
        "instance": [instance_data]
    }
    
    # Add colors only if they differ from defaults (yellow, red, red)
    color1_str = rgb_to_color_name(layer.get('color1', [1.0, 1.0, 1.0]), layer.get('color1_name'))
    color2_str = rgb_to_color_name(layer.get('color2', [1.0, 1.0, 1.0]), layer.get('color2_name'))
    color3_str = rgb_to_color_name(layer.get('color3', [1.0, 1.0, 1.0]), layer.get('color3_name'))
    
    if color1_str != 'yellow':
        emblem_data['color1'] = color1_str
    if color2_str != 'red':
        emblem_data['color2'] = color2_str
    if color3_str != 'red':
        emblem_data['color3'] = color3_str
    
    # Wrap in colored_emblem block
    data = {"colored_emblem": emblem_data}
    
    # Serialize using CoA serializer
    return serialize_coa_to_string(data)


def _emblem_to_layer_data(emblem):
    """Convert emblem dict (from parser) to layer data dict (for editor)
    
    Args:
        emblem: Emblem dictionary from CoA parser
        
    Returns:
        Layer data dict compatible with editor's layer format, or None if invalid
    """
    # Get emblem properties
    filename = emblem.get('texture', '')
    if not filename:
        return None
    
    # Get instance data (use first instance if multiple)
    instances = emblem.get('instance', [])
    if not instances:
        instances = [{'position': [0.5, 0.5], 'scale': [1.0, 1.0], 'rotation': 0}]
    instance = instances[0]
    
    # Get colors
    color1_name = emblem.get('color1', 'yellow')
    color2_name = emblem.get('color2', 'red')
    color3_name = emblem.get('color3', 'red')
    
    # Build layer data
    layer_data = {
        'filename': filename,
        'path': filename,
        'colors': 3,  # Assume 3 colors
        'pos_x': instance.get('position', [0.5, 0.5])[0],
        'pos_y': instance.get('position', [0.5, 0.5])[1],
        'scale_x': instance.get('scale', [1.0, 1.0])[0],
        'scale_y': instance.get('scale', [1.0, 1.0])[1],
        'rotation': instance.get('rotation', 0),
        'flip_x': False,
        'flip_y': False,
        'color1': color_name_to_rgb(color1_name),
        'color2': color_name_to_rgb(color2_name),
        'color3': color_name_to_rgb(color3_name),
        'color1_name': color1_name,
        'color2_name': color2_name,
        'color3_name': color3_name
    }
    
    return layer_data


def parse_layer_from_text(layer_text):
    """Parse a layer from colored_emblem block format
    
    Args:
        layer_text: Text containing colored_emblem block
        
    Returns:
        Layer data dict compatible with editor's layer format, or None if parse fails
    """
    try:
        # Parse the text
        data = parse_coa_string(layer_text)
        if not data:
            return None
        
        # Extract colored_emblem block (it's returned as a list)
        emblem_list = data.get('colored_emblem')
        if not emblem_list:
            return None
        
        # Get first emblem if it's a list
        if isinstance(emblem_list, list):
            if len(emblem_list) == 0:
                return None
            emblem = emblem_list[0]
        else:
            emblem = emblem_list
        
        # Convert emblem to layer data
        return _emblem_to_layer_data(emblem)
        
    except Exception as e:
        print(f"Error parsing layer: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_multiple_layers_from_text(text):
    """Parse multiple layers from clipboard text
    
    Handles text containing multiple colored_emblem blocks.
    Uses the proper CK3 parser which handles anonymous blocks correctly.
    
    Args:
        text: Text containing one or more colored_emblem blocks
        
    Returns:
        List of layer data dictionaries
    """
    try:
        # Parse using proper CK3 parser
        data = parse_coa_string(text)
        if not data:
            return []
        
        # Extract colored_emblem list (parser returns it as a list)
        emblem_list = data.get('colored_emblem')
        if not emblem_list:
            return []
        
        # Ensure it's a list
        if not isinstance(emblem_list, list):
            emblem_list = [emblem_list]
        
        # Convert each emblem to layer data
        layers_data = []
        for emblem in emblem_list:
            layer_data = _emblem_to_layer_data(emblem)
            if layer_data:
                layers_data.append(layer_data)
        
        return layers_data
        
    except Exception as e:
        print(f"Error parsing multiple layers: {e}")
        import traceback
        traceback.print_exc()
        return []
