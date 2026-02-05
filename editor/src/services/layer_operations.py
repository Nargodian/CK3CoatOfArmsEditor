"""
CK3 Coat of Arms Editor - Layer Operations Service

This module handles layer creation, duplication, and manipulation operations.
These functions provide layer manipulation logic independent of the UI.
"""

import os
import json
from utils.color_utils import color_name_to_rgb, rgb_to_color_name
from utils.path_resolver import get_emblem_metadata_path
from utils.metadata_cache import get_texture_color_count
from constants import (
    DEFAULT_POSITION_X, DEFAULT_POSITION_Y,
    DEFAULT_SCALE_X, DEFAULT_SCALE_Y,
    DEFAULT_ROTATION,
    DEFAULT_EMBLEM_COLOR1, DEFAULT_EMBLEM_COLOR2, DEFAULT_EMBLEM_COLOR3,
    CK3_NAMED_COLORS
)

# Register this module as a caller for Layer tracking
from models.coa import LayerTracker
LayerTracker.register('serialize_layer_to_text')
LayerTracker.register('split_layer_instances')
LayerTracker.register('merge_layers_as_instances')


def create_default_layer(filename, colors=None, **overrides):
    """Create new layer with default values
    
    Args:
        filename: Texture filename for the layer
        colors: Number of colors (1, 2, or 3), auto-detected from metadata if None
        **overrides: Optional property overrides (pos_x, pos_y, scale_x, etc.)
        
    Returns:
        Layer object
    """
    from models.coa import Layer
    
    # Auto-detect color count from metadata if not provided
    if colors is None:
        colors = get_texture_color_count(filename)
    
    # Create default instance
    default_instance = {
        'pos_x': DEFAULT_POSITION_X,
        'pos_y': DEFAULT_POSITION_Y,
        'scale_x': DEFAULT_SCALE_X,
        'scale_y': DEFAULT_SCALE_Y,
        'rotation': DEFAULT_ROTATION,
        'depth': 0.0
    }
    
    layer_data = {
        'filename': filename,
        'path': filename,
        'colors': colors,
        'instances': [default_instance],  # List of instances
        'selected_instance': 0,  # Index of currently selected instance
        'flip_x': False,
        'flip_y': False,
        'color1': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR1]['rgb'],
        'color2': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR2]['rgb'],
        'color3': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR3]['rgb'],
        'color1_name': DEFAULT_EMBLEM_COLOR1,
        'color2_name': DEFAULT_EMBLEM_COLOR2,
        'color3_name': DEFAULT_EMBLEM_COLOR3,
        'mask': None  # None = render everywhere (default), or [int, int, int] for mask channels
    }
    
    # Apply any overrides
    layer_data.update(overrides)
    
    # Create and return Layer object
    return Layer(layer_data, caller='create_default_layer')


# _migrate_layer_to_instances removed - Layer objects handle instances internally


def duplicate_layer(layer, offset_x=0.0, offset_y=0.0):
    """Duplicate a layer with optional position offset
    
    Args:
        layer: Source Layer object
        offset_x: X position offset for duplicate
        offset_y: Y position offset for duplicate
        
    Returns:
        New Layer object (deep copy)
    """
    from models.coa import Layer
    
    # Ensure we have a Layer object
    if not isinstance(layer, Layer):
        layer = Layer(layer, caller='duplicate_layer')
    
    # Use Layer's duplicate method
    return layer.duplicate(offset_x=offset_x, offset_y=offset_y, caller='duplicate_layer')


def serialize_layer_to_text(layer):
    """Serialize layer(s) to colored_emblem block format
    
    Args:
        layer: Layer object, dict, or list of layers
        
    Returns:
        String in CoA colored_emblem format
    """
    from models.coa import Layer
    
    # Handle list of layers
    if isinstance(layer, list):
        if not layer:
            return ""
        # Serialize each layer and join with double newline
        serialized = [serialize_layer_to_text(l) for l in layer]
        return "\n\n".join(serialized)
    
    # Ensure we have a Layer object
    if not isinstance(layer, Layer):
        # Create Layer from dict if needed
        layer = Layer(layer, caller='serialize_layer_to_text')
    
    # Build instance list using Layer's instance access
    instances = []
    for i in range(layer.instance_count):
        inst = layer.get_instance(i, caller='serialize_layer_to_text')
        instance_data = {
            "position": [inst.pos.x, inst.pos.y],
            "scale": [inst.scale.x, inst.scale.y],
            "rotation": int(inst.rotation)
        }
        # Add depth if not default
        if inst.depth is not None and inst.depth != 0.0:
            instance_data['depth'] = inst.depth
        instances.append(instance_data)
    
    # If no instances, create default
    if not instances:
        instances = [{
            "position": [DEFAULT_POSITION_X, DEFAULT_POSITION_Y],
            "scale": [DEFAULT_SCALE_X, DEFAULT_SCALE_Y],
            "rotation": 0
        }]
    
    emblem_data = {
        "texture": layer.filename,
        "instance": instances
    }
    
    # Add mask if present (None means render everywhere, so omit it)
    if layer.mask is not None:
        emblem_data['mask'] = layer.mask
    
    # Add colors only if they differ from defaults
    color1_str = rgb_to_color_name(layer.color1, layer.color1_name)
    color2_str = rgb_to_color_name(layer.color2, layer.color2_name)
    color3_str = rgb_to_color_name(layer.color3, layer.color3_name)
    
    if color1_str != DEFAULT_EMBLEM_COLOR1:
        emblem_data['color1'] = color1_str
    if color2_str != DEFAULT_EMBLEM_COLOR2:
        emblem_data['color2'] = color2_str
    if color3_str != DEFAULT_EMBLEM_COLOR3:
        emblem_data['color3'] = color3_str
    
    # Wrap in colored_emblem block
    data = {"colored_emblem": emblem_data}
    
    # Serialize using CoA serializer
    return serialize_coa_to_string(data)


def _emblem_to_layer_data(emblem):
    """Convert emblem dict (from parser) to Layer object
    
    Args:
        emblem: Emblem dictionary from CoA parser
        
    Returns:
        Layer object, or None if invalid
    """
    from models.coa import Layer
    import uuid as uuid_module
    # Get emblem properties
    filename = emblem.get('texture', '')
    if not filename:
        return None
    
    # Get ALL instances (not just first one)
    instances_raw = emblem.get('instance', [])
    if not instances_raw:
        instances_raw = [{'position': [0.5, 0.5], 'scale': [1.0, 1.0], 'rotation': 0}]
    
    # Convert to instance format
    instances = []
    for inst_raw in instances_raw:
        instance = {
            'pos_x': inst_raw.get('position', [0.5, 0.5])[0],
            'pos_y': inst_raw.get('position', [0.5, 0.5])[1],
            'scale_x': inst_raw.get('scale', [1.0, 1.0])[0],
            'scale_y': inst_raw.get('scale', [1.0, 1.0])[1],
            'rotation': inst_raw.get('rotation', 0),
            'depth': inst_raw.get('depth', 0.0)
        }
        instances.append(instance)
    
    # Get colors
    color1_name = emblem.get('color1', DEFAULT_EMBLEM_COLOR1)
    color2_name = emblem.get('color2', DEFAULT_EMBLEM_COLOR2)
    color3_name = emblem.get('color3', DEFAULT_EMBLEM_COLOR3)
    
    # Look up actual color count from texture metadata
    color_count = _get_texture_color_count(filename)
    
    # Get mask field (if present)
    mask = emblem.get('mask')
    if mask is not None:
        # Convert to list of 3 integers, padding with 0 if needed
        if not isinstance(mask, list):
            mask = [mask]
        # Ensure exactly 3 values, pad with 0
        mask = list(mask) + [0, 0, 0]
        mask = mask[:3]
    
    # Build layer data
    layer_data = {
        'uuid': str(uuid_module.uuid4()),
        'filename': filename,
        'path': filename,
        'colors': color_count,
        'instances': instances,
        'selected_instance': 0,  # Default to first instance
        'flip_x': False,
        'flip_y': False,
        'color1': color_name_to_rgb(color1_name),
        'color2': color_name_to_rgb(color2_name),
        'color3': color_name_to_rgb(color3_name),
        'color1_name': color1_name,
        'color2_name': color2_name,
        'color3_name': color3_name,
        'mask': mask  # None or [int, int, int] for mask channels
    }
    
    return Layer(layer_data, caller='_emblem_to_layer_data')


def parse_layer_from_text(layer_text):
    """Parse a layer from colored_emblem block format
    
    Args:
        layer_text: Text containing colored_emblem block
        
    Returns:
        Layer object, or None if parse fails
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
        List of Layer objects
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


def split_layer_instances(layer):
    """Split a multi-instance layer into N single-instance layers
    
    Args:
        layer: Layer object
        
    Returns:
        List of new Layer objects, one per instance
    """
    from models.coa import Layer
    import uuid as uuid_module
    
    # Ensure we have a Layer object
    if not isinstance(layer, Layer):
        layer = Layer(layer, caller='split_layer_instances')
    
    if layer.instance_count <= 1:
        # Already single instance, return copy of original
        return [duplicate_layer(layer)]
    
    # Create one layer per instance
    new_layers = []
    for i in range(layer.instance_count):
        inst = layer.get_instance(i, caller='split_layer_instances')
        # Create new layer with same properties
        new_layer_data = {
            'uuid': str(uuid_module.uuid4()),
            'filename': layer.filename,
            'path': layer.path,
            'colors': layer.colors,
            'flip_x': layer.flip_x,
            'flip_y': layer.flip_y,
            'color1': layer.color1.copy() if layer.color1 else None,
            'color2': layer.color2.copy() if layer.color2 else None,
            'color3': layer.color3.copy() if layer.color3 else None,
            'color1_name': layer.color1_name,
            'color2_name': layer.color2_name,
            'color3_name': layer.color3_name,
            'mask': list(layer.mask) if layer.mask else None,
            'instances': [dict(inst)],  # Single instance copy
            'selected_instance': 0
        }
        new_layers.append(Layer(new_layer_data, caller='split_layer_instances'))
    
    return new_layers


def merge_layers_as_instances(layers, use_topmost_properties=False):
    """Merge multiple layers into one multi-instance layer
    
    Args:
        layers: List of Layer objects to merge
        use_topmost_properties: If True, use properties from topmost layer (index 0)
                                If False and layers incompatible, raise ValueError
        
    Returns:
        New merged Layer object
        
    Raises:
        ValueError: If layers incompatible and use_topmost_properties=False
    """
    if not layers:
        return None
    
    from models.coa import Layer
    import uuid as uuid_module
    
    # Ensure all are Layer objects
    layer_objs = []
    for layer in layers:
        if isinstance(layer, Layer):
            layer_objs.append(layer)
        else:
            layer_objs.append(Layer(layer, caller='merge_layers_as_instances'))
    
    if len(layer_objs) == 1:
        return duplicate_layer(layer_objs[0])
    
    # Use topmost layer (index 0) as base
    base = layer_objs[0]
    
    # Create merged layer with base properties
    merged_data = {
        'uuid': str(uuid_module.uuid4()),
        'filename': base.filename,
        'path': base.path,
        'colors': base.colors,
        'flip_x': base.flip_x,
        'flip_y': base.flip_y,
        'color1': base.color1.copy() if base.color1 else None,
        'color2': base.color2.copy() if base.color2 else None,
        'color3': base.color3.copy() if base.color3 else None,
        'color1_name': base.color1_name,
        'color2_name': base.color2_name,
        'color3_name': base.color3_name,
        'mask': list(base.mask) if base.mask else None,
        'instances': [],
        'selected_instance': 0
    }
    
    # Collect all instances from all layers
    for layer in layer_objs:
        for i in range(layer.instance_count):
            inst = layer.get_instance(i, caller='merge_layers_as_instances')
            merged_data['instances'].append(dict(inst))
    
    return Layer(merged_data, caller='merge_layers_as_instances')
