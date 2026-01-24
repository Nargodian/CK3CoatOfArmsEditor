"""
CK3 Coat of Arms Editor - CoA Serialization Service

This module handles serialization and deserialization of complete CoA data structures.
Works with coa_parser.py for parsing and provides high-level operations for the UI.
"""

from utils.color_utils import color_name_to_rgb


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
    pattern = coa.get('pattern', 'pattern__solid.dds')
    
    # Apply base colors (CK3 defaults: black, yellow, black)
    color1_name = coa.get('color1', 'black')
    color2_name = coa.get('color2', 'yellow')
    color3_name = coa.get('color3', 'black')
    
    base_colors = [
        color_name_to_rgb(color1_name),
        color_name_to_rgb(color2_name),
        color_name_to_rgb(color3_name)
    ]
    base_color_names = [color1_name, color2_name, color3_name]
    
    return {
        'pattern': pattern,
        'color_names': base_color_names,
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
            
            # Get color names and RGB values
            color1_name = emblem.get('color1', 'yellow')
            color2_name = emblem.get('color2', 'red')
            color3_name = emblem.get('color3', 'red')
            
            layer_data = {
                'filename': filename,
                'path': filename,  # Use filename as path - texture system and preview lookup both use this
                'colors': 3,  # Assume 3 colors for all emblems
                'pos_x': instance.get('position', [0.5, 0.5])[0],
                'pos_y': instance.get('position', [0.5, 0.5])[1],
                'scale_x': instance.get('scale', [1.0, 1.0])[0],
                'scale_y': instance.get('scale', [1.0, 1.0])[1],
                'rotation': instance.get('rotation', 0),
                'color1': color_name_to_rgb(color1_name),
                'color2': color_name_to_rgb(color2_name),
                'color3': color_name_to_rgb(color3_name),
                'color1_name': color1_name,
                'color2_name': color2_name,
                'color3_name': color3_name,
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
