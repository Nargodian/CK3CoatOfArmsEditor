"""
CK3 Coat of Arms Serializer - INTERNAL IMPLEMENTATION ONLY

⚠️ WARNING: DO NOT ACCESS THIS MODULE DIRECTLY ⚠️

This is an internal implementation detail of the CoA model.
External code should ONLY use CoA methods for serialization.

This module works with dictionaries and Layer objects as an intermediate
representation. Direct usage violates the CoA encapsulation model.

Use CoA methods instead:
- To serialize full CoA: coa.to_string()
- To serialize specific layers: coa.serialize_layers_to_string(uuids)
- To parse: CoA.from_string(text)

Direct access to this module is FORBIDDEN by the refactoring rules.
"""

import json
from models.color import Color
from utils.path_resolver import get_emblem_metadata_path
from utils.metadata_cache import get_texture_color_count


def extract_coa_structure(coa_data):
    """Extract base CoA structure from parsed data
    
    Args:
        coa_data: Parsed CoA data dictionary
        
    Returns:
        Tuple of (coa_dict, coa_id) where coa_dict is the CoA object
    """
    # Get the CoA object (first key)
    coa_id = list(coa_data.keys())[0]
    coa = coa_data[coa_id]
    return coa, coa_id


def extract_base_layer_data(coa):
    """Extract base layer pattern and colors from CoA
    
    Args:
        coa: CoA dictionary
        
    Returns:
        Dict with pattern, color names, and RGB colors
    """
    pattern = coa.get('pattern', 'pattern_solid.dds')  # CK3 default
    
    # Apply base colors (CK3 defaults: black, yellow, black) as Color objects
    color1_name = coa.get('color1', 'black')
    color2_name = coa.get('color2', 'yellow')
    color3_name = coa.get('color3', 'black')
    
    base_colors = [
        Color.from_name(color1_name),
        Color.from_name(color2_name),
        Color.from_name(color3_name)
    ]
    
    return {
        'pattern': pattern,
        'colors': base_colors
    }


def extract_emblem_layers(coa):
    """Extract and parse emblem layers from CoA with depth sorting
    
    Args:
        coa: CoA dictionary
        
    Returns:
        List of layer data dictionaries sorted by depth (back to front)
    """
    emblem_instances = []
    
    for emblem in coa.get('colored_emblem', []):
        filename = emblem.get('texture', '')
        
        # Get instances, or create default if none exist
        instances = emblem.get('instance', [])
        if not instances:
            # No instance block means default values
            instances = [{'position': [0.5, 0.5], 'scale': [1.0, 1.0], 'rotation': 0}]
        
        for instance in instances:
            # Get depth value (default to 0 if not specified)
            depth = instance.get('depth', 0)
            
            # Parse colors from CK3 format (handles both named colors and rgb blocks)
            color1_str = emblem.get('color1', 'yellow')
            color2_str = emblem.get('color2', 'red')
            color3_str = emblem.get('color3', 'red')
            
            # Convert to Color objects
            color1 = Color.from_ck3_string(color1_str)
            color2 = Color.from_ck3_string(color2_str)
            color3 = Color.from_ck3_string(color3_str)
            
            # Look up actual color count from texture metadata
            color_count = get_texture_color_count(filename)
            
            # Split scale into magnitude and flip state
            scale_x_raw = instance.get('scale', [1.0, 1.0])[0]
            scale_y_raw = instance.get('scale', [1.0, 1.0])[1]
            
            layer_data = {
                'filename': filename,
                'path': filename,  # Use filename as path - texture system and preview lookup both use this
                'colors': color_count,  # Look up actual color count from metadata
                'pos_x': instance.get('position', [0.5, 0.5])[0],
                'pos_y': instance.get('position', [0.5, 0.5])[1],
                'scale_x': abs(scale_x_raw),  # Always store as positive
                'scale_y': abs(scale_y_raw),  # Always store as positive
                'flip_x': scale_x_raw < 0,    # Track flip separately
                'flip_y': scale_y_raw < 0,    # Track flip separately
                'rotation': instance.get('rotation', 0),
                'color1': color1,
                'color2': color2,
                'color3': color3,
                'depth': depth
            }
            emblem_instances.append(layer_data)
    
    # Sort by depth (higher depth = further back = first in list for rendering)
    emblem_instances.sort(key=lambda x: x['depth'], reverse=True)
    
    # Remove depth from layer data (it's only used for sorting)
    for layer_data in emblem_instances:
        del layer_data['depth']
    
    return emblem_instances


def parse_coa_for_editor(coa_data):
    """Parse complete CoA data for editor application
    
    Convenience function that extracts all necessary data from parsed CoA.
    
    Args:
        coa_data: Parsed CoA data dictionary
        
    Returns:
        Dict with 'base' and 'layers' keys containing extracted data
    """
    coa, coa_id = extract_coa_structure(coa_data)
    base_data = extract_base_layer_data(coa)
    layers = extract_emblem_layers(coa)
    
    return {
        'base': base_data,
        'layers': layers,
        'coa_id': coa_id
    }
