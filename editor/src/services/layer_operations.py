"""
CK3 Coat of Arms Editor - Layer Operations Service

This module handles layer creation, duplication, and manipulation operations.
These functions provide layer manipulation logic independent of the UI.
"""

import os
import json
from utils.coa_parser import parse_coa_string, serialize_coa_to_string
from utils.color_utils import color_name_to_rgb, rgb_to_color_name
from utils.path_resolver import get_emblem_metadata_path
from constants import (
    DEFAULT_POSITION_X, DEFAULT_POSITION_Y,
    DEFAULT_SCALE_X, DEFAULT_SCALE_Y,
    DEFAULT_ROTATION,
    DEFAULT_EMBLEM_COLOR1, DEFAULT_EMBLEM_COLOR2, DEFAULT_EMBLEM_COLOR3,
    CK3_NAMED_COLORS
)

# Cache for texture metadata (color counts)
_TEXTURE_METADATA_CACHE = None

def _get_texture_color_count(filename):
    """Get the number of colors for a texture from JSON metadata
    
    Args:
        filename: Texture filename (e.g., 'ce_lion.dds')
        
    Returns:
        Number of colors (1, 2, or 3), defaults to 3 if not found
    """
    global _TEXTURE_METADATA_CACHE
    
    # Load cache on first use
    if _TEXTURE_METADATA_CACHE is None:
        _TEXTURE_METADATA_CACHE = {}
        json_path = get_emblem_metadata_path()
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for tex_filename, properties in data.items():
                        if properties and isinstance(properties, dict):
                            _TEXTURE_METADATA_CACHE[tex_filename] = properties.get('colors', 3)
            except Exception as e:
                print(f"Warning: Could not load texture metadata: {e}")
    
    # Look up color count
    return _TEXTURE_METADATA_CACHE.get(filename, 3)


def create_default_layer(filename, colors=3, **overrides):
    """Create new layer with default values
    
    Args:
        filename: Texture filename for the layer
        colors: Number of colors (1, 2, or 3)
        **overrides: Optional property overrides (pos_x, pos_y, scale_x, etc.)
        
    Returns:
        Dictionary with layer data
    """
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
    
    # Migrate old format if overrides contain pos_x, pos_y, etc.
    if 'pos_x' in overrides or 'pos_y' in overrides or 'scale_x' in overrides:
        _migrate_layer_to_instances(layer_data)
    
    return layer_data


def _migrate_layer_to_instances(layer_data):
    """Migrate old single-instance format to new instances list format
    
    Converts pos_x, pos_y, scale_x, scale_y, rotation, depth fields
    to instances list format. Modifies layer_data in place.
    
    Args:
        layer_data: Layer dictionary to migrate
    """
    # Check if already migrated
    if 'instances' in layer_data and isinstance(layer_data['instances'], list):
        # Already has instances, but may have old fields too - clean them up
        for key in ['pos_x', 'pos_y', 'scale_x', 'scale_y', 'rotation', 'depth']:
            layer_data.pop(key, None)
        return
    
    # Build instance from old format fields
    instance = {
        'pos_x': layer_data.pop('pos_x', DEFAULT_POSITION_X),
        'pos_y': layer_data.pop('pos_y', DEFAULT_POSITION_Y),
        'scale_x': layer_data.pop('scale_x', DEFAULT_SCALE_X),
        'scale_y': layer_data.pop('scale_y', DEFAULT_SCALE_Y),
        'rotation': layer_data.pop('rotation', DEFAULT_ROTATION),
        'depth': layer_data.pop('depth', 0.0)
    }
    
    # Set new format
    layer_data['instances'] = [instance]
    layer_data['selected_instance'] = 0


def duplicate_layer(layer, offset_x=0.0, offset_y=0.0):
    """Duplicate a layer with optional position offset
    
    Args:
        layer: Source layer dictionary
        offset_x: X position offset for duplicate
        offset_y: Y position offset for duplicate
        
    Returns:
        New layer dictionary (deep copy)
    """
    # Migrate old format if needed
    _migrate_layer_to_instances(layer)
    
    # Create a deep copy to avoid reference issues with lists
    duplicated = dict(layer)
    
    # Deep copy the mask list if present
    if 'mask' in duplicated and duplicated['mask'] is not None:
        duplicated['mask'] = list(duplicated['mask'])
    
    # Deep copy instances list
    if 'instances' in duplicated:
        duplicated['instances'] = [dict(inst) for inst in duplicated['instances']]
        
        # Apply offset if provided
        if offset_x != 0.0 or offset_y != 0.0:
            for inst in duplicated['instances']:
                if offset_x != 0.0:
                    inst['pos_x'] = min(1.0, max(0.0, inst.get('pos_x', 0.5) + offset_x))
                if offset_y != 0.0:
                    inst['pos_y'] = min(1.0, max(0.0, inst.get('pos_y', 0.5) + offset_y))
    
    return duplicated


def serialize_layer_to_text(layer):
    """Serialize a single layer to colored_emblem block format
    
    Args:
        layer: Layer dictionary
        
    Returns:
        String in CoA colored_emblem format
    """
    # Migrate old format if needed
    _migrate_layer_to_instances(layer)
    
    # Build instance list
    instances = []
    for inst in layer.get('instances', []):
        instance_data = {
            "position": [inst.get('pos_x', DEFAULT_POSITION_X), inst.get('pos_y', DEFAULT_POSITION_Y)],
            "scale": [inst.get('scale_x', DEFAULT_SCALE_X), inst.get('scale_y', DEFAULT_SCALE_Y)],
            "rotation": int(inst.get('rotation', DEFAULT_ROTATION))
        }
        # Add depth if not default
        depth = inst.get('depth', 0.0)
        if depth != 0.0:
            instance_data['depth'] = depth
        instances.append(instance_data)
    
    # If no instances, create default
    if not instances:
        instances = [{
            "position": [DEFAULT_POSITION_X, DEFAULT_POSITION_Y],
            "scale": [DEFAULT_SCALE_X, DEFAULT_SCALE_Y],
            "rotation": 0
        }]
    
    emblem_data = {
        "texture": layer.get('filename', ''),
        "instance": instances
    }
    
    # Add mask if present (None means render everywhere, so omit it)
    mask = layer.get('mask')
    if mask is not None:
        emblem_data['mask'] = mask
    
    # Add colors only if they differ from defaults
    color1_str = rgb_to_color_name(layer.get('color1', [1.0, 1.0, 1.0]), layer.get('color1_name'))
    color2_str = rgb_to_color_name(layer.get('color2', [1.0, 1.0, 1.0]), layer.get('color2_name'))
    color3_str = rgb_to_color_name(layer.get('color3', [1.0, 1.0, 1.0]), layer.get('color3_name'))
    
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


def split_layer_instances(layer):
    """Split a multi-instance layer into N single-instance layers
    
    Args:
        layer: Layer dictionary with instances array
        
    Returns:
        List of new layer dictionaries, one per instance
    """
    _migrate_layer_to_instances(layer)
    
    instances = layer.get('instances', [])
    if len(instances) <= 1:
        # Already single instance, return copy of original
        return [duplicate_layer(layer)]
    
    # Create one layer per instance
    new_layers = []
    for inst in instances:
        # Create new layer with same properties
        new_layer = {
            'filename': layer.get('filename'),
            'path': layer.get('path'),
            'colors': layer.get('colors', 3),
            'flip_x': layer.get('flip_x', False),
            'flip_y': layer.get('flip_y', False),
            'color1': layer.get('color1'),
            'color2': layer.get('color2'),
            'color3': layer.get('color3'),
            'color1_name': layer.get('color1_name'),
            'color2_name': layer.get('color2_name'),
            'color3_name': layer.get('color3_name'),
            'mask': list(layer['mask']) if layer.get('mask') else None,
            'instances': [dict(inst)],  # Single instance copy
            'selected_instance': 0
        }
        new_layers.append(new_layer)
    
    return new_layers


def check_layers_compatible_for_merge(layers):
    """Check if layers can be merged as instances
    
    Args:
        layers: List of layer dictionaries
        
    Returns:
        Tuple of (is_compatible, differences_dict)
        - is_compatible: True if all layers have same texture/colors/mask
        - differences_dict: Dict describing what differs (empty if compatible)
    """
    if not layers or len(layers) < 2:
        return True, {}
    
    # Get reference properties from first layer
    first = layers[0]
    ref_filename = first.get('filename')
    ref_colors = first.get('colors')
    ref_mask = first.get('mask')
    ref_flip_x = first.get('flip_x')
    ref_flip_y = first.get('flip_y')
    ref_color1 = first.get('color1')
    ref_color2 = first.get('color2')
    ref_color3 = first.get('color3')
    
    differences = {}
    
    # Check each layer against reference
    for idx, layer in enumerate(layers[1:], start=1):
        if layer.get('filename') != ref_filename:
            differences.setdefault('filename', []).append(idx)
        if layer.get('colors') != ref_colors:
            differences.setdefault('colors', []).append(idx)
        if layer.get('mask') != ref_mask:
            differences.setdefault('mask', []).append(idx)
        if layer.get('flip_x') != ref_flip_x:
            differences.setdefault('flip_x', []).append(idx)
        if layer.get('flip_y') != ref_flip_y:
            differences.setdefault('flip_y', []).append(idx)
        if layer.get('color1') != ref_color1:
            differences.setdefault('color1', []).append(idx)
        if layer.get('color2') != ref_color2:
            differences.setdefault('color2', []).append(idx)
        if layer.get('color3') != ref_color3:
            differences.setdefault('color3', []).append(idx)
    
    is_compatible = len(differences) == 0
    return is_compatible, differences


def merge_layers_as_instances(layers, use_topmost_properties=False):
    """Merge multiple layers into one multi-instance layer
    
    Args:
        layers: List of layer dictionaries to merge
        use_topmost_properties: If True, use properties from topmost layer (index 0)
                                If False and layers incompatible, raise ValueError
        
    Returns:
        New merged layer dictionary
        
    Raises:
        ValueError: If layers incompatible and use_topmost_properties=False
    """
    if not layers:
        return None
    
    if len(layers) == 1:
        return duplicate_layer(layers[0])
    
    # Check compatibility
    is_compatible, differences = check_layers_compatible_for_merge(layers)
    
    if not is_compatible and not use_topmost_properties:
        diff_props = ', '.join(differences.keys())
        raise ValueError(f"Layers have incompatible properties: {diff_props}")
    
    # Use topmost layer (index 0) as base
    base = layers[0]
    _migrate_layer_to_instances(base)
    
    # Create merged layer with base properties
    merged = {
        'filename': base.get('filename'),
        'path': base.get('path'),
        'colors': base.get('colors', 3),
        'flip_x': base.get('flip_x', False),
        'flip_y': base.get('flip_y', False),
        'color1': base.get('color1'),
        'color2': base.get('color2'),
        'color3': base.get('color3'),
        'color1_name': base.get('color1_name'),
        'color2_name': base.get('color2_name'),
        'color3_name': base.get('color3_name'),
        'mask': list(base['mask']) if base.get('mask') else None,
        'instances': [],
        'selected_instance': 0
    }
    
    # Collect all instances from all layers
    for layer in layers:
        _migrate_layer_to_instances(layer)
        for inst in layer.get('instances', []):
            merged['instances'].append(dict(inst))
    
    return merged
