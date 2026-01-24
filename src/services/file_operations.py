"""
CK3 Coat of Arms Editor - File Operations Service

This module handles file I/O operations for CoA data.
Separates file operations from UI logic.
"""

from utils.coa_parser import parse_coa_string, serialize_coa_to_string
from utils.color_utils import rgb_to_color_name


def save_coa_to_file(coa_data, filename):
    """Save CoA data to text file
    
    Args:
        coa_data: Dictionary containing CoA structure
        filename: Path to save file
        
    Raises:
        Exception: If file write fails
    """
    # Serialize to string
    coa_string = serialize_coa_to_string(coa_data)
    
    # Write to file
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(coa_string)
    
    print(f"CoA saved to {filename}")


def load_coa_from_file(filename):
    """Load and parse CoA from text file
    
    Args:
        filename: Path to CoA file
        
    Returns:
        Parsed CoA data dictionary
        
    Raises:
        Exception: If file read or parse fails
    """
    # Read file
    with open(filename, 'r', encoding='utf-8') as f:
        coa_text = f.read()
    
    # Parse CoA data
    coa_data = parse_coa_string(coa_text)
    if not coa_data:
        raise ValueError("Failed to parse coat of arms data - not a valid CK3 format")
    
    print(f"CoA loaded from {filename}")
    return coa_data


def build_coa_for_save(base_colors, base_texture, layers, base_color_names):
    """Build CoA data structure for saving to file
    
    Args:
        base_colors: List of RGB colors [r, g, b] for base layer
        base_texture: Base pattern texture filename
        layers: List of layer dictionaries
        base_color_names: List of color names for base colors
        
    Returns:
        Dictionary with coa_export structure
    """
    coa_data = {
        "coa_export": {
            "custom": True,
            "pattern": base_texture or "pattern__solid.dds",
            "color1": rgb_to_color_name(base_colors[0], base_color_names[0]),
            "color2": rgb_to_color_name(base_colors[1], base_color_names[1]),
            "color3": rgb_to_color_name(base_colors[2], base_color_names[2])
        }
    }
    
    # Add layers grouped by texture
    if layers:
        coa_data["coa_export"]["colored_emblem"] = []
        texture_groups = {}
        
        for layer in layers:
            texture = layer.get('filename', layer.get('path', ''))
            if texture not in texture_groups:
                texture_groups[texture] = []
            texture_groups[texture].append(layer)
        
        for texture, grouped_layers in texture_groups.items():
            emblem = {
                "texture": texture,
                "color1": rgb_to_color_name(grouped_layers[0].get('color1'), grouped_layers[0].get('color1_name')),
                "instance": []
            }
            
            for layer in grouped_layers:
                instance = {
                    "position": [layer.get('pos_x', 0.5), layer.get('pos_y', 0.5)],
                    "scale": [layer.get('scale_x', 1.0), layer.get('scale_y', 1.0)],
                    "rotation": layer.get('rotation', 0)
                }
                emblem["instance"].append(instance)
            
            coa_data["coa_export"]["colored_emblem"].append(emblem)
    
    return coa_data


def build_coa_for_clipboard(base_colors, base_texture, layers, base_color_names):
    """Build CoA data structure for clipboard (with depth values)
    
    Args:
        base_colors: List of RGB colors [r, g, b] for base layer
        base_texture: Base pattern texture filename
        layers: List of layer dictionaries
        base_color_names: List of color names for base colors
        
    Returns:
        Dictionary with coa_clipboard structure
    """
    coa_data = {
        "coa_clipboard": {
            "custom": True,
            "pattern": base_texture or "pattern__solid_designer.dds",
            "colored_emblem": []
        }
    }
    
    # Add base colors only if they differ from defaults (black, yellow, black)
    color1_str = rgb_to_color_name(base_colors[0], base_color_names[0])
    color2_str = rgb_to_color_name(base_colors[1], base_color_names[1])
    color3_str = rgb_to_color_name(base_colors[2], base_color_names[2])
    
    if color1_str != 'black':
        coa_data["coa_clipboard"]["color1"] = color1_str
    if color2_str != 'yellow':
        coa_data["coa_clipboard"]["color2"] = color2_str
    if color3_str != 'black':
        coa_data["coa_clipboard"]["color3"] = color3_str
    
    # Add emblem layers with depth values
    for layer_idx, layer in enumerate(layers):
        instance = {
            "position": [layer.get('pos_x', 0.5), layer.get('pos_y', 0.5)],
            "scale": [layer.get('scale_x', 1.0), layer.get('scale_y', 1.0)],
            "rotation": int(layer.get('rotation', 0))
        }
        # Add depth for all layers except the first (layer 0 = frontmost, no depth)
        if layer_idx > 0:
            instance['depth'] = float(layer_idx) + 0.01
        
        emblem = {
            "texture": layer.get('filename', ''),
            "instance": [instance]
        }
        
        # Add emblem colors only if they differ from defaults (yellow, red, red)
        color1_str = rgb_to_color_name(layer.get('color1', [1.0, 1.0, 1.0]), layer.get('color1_name'))
        color2_str = rgb_to_color_name(layer.get('color2', [1.0, 1.0, 1.0]), layer.get('color2_name'))
        color3_str = rgb_to_color_name(layer.get('color3', [1.0, 1.0, 1.0]), layer.get('color3_name'))
        
        if color1_str != 'yellow':
            emblem['color1'] = color1_str
        if color2_str != 'red':
            emblem['color2'] = color2_str
        if color3_str != 'red':
            emblem['color3'] = color3_str
        
        coa_data["coa_clipboard"]["colored_emblem"].append(emblem)
    
    return coa_data


def coa_to_clipboard_text(base_colors, base_texture, layers, base_color_names):
    """Convert CoA to clipboard text format
    
    Args:
        base_colors: List of RGB colors [r, g, b] for base layer
        base_texture: Base pattern texture filename
        layers: List of layer dictionaries
        base_color_names: List of color names for base colors
        
    Returns:
        Serialized CoA string
    """
    coa_data = build_coa_for_clipboard(base_colors, base_texture, layers, base_color_names)
    return serialize_coa_to_string(coa_data)


def is_layer_subblock(text):
    """Detect if clipboard text is a layer sub-block vs full CoA
    
    A layer sub-block starts with 'colored_emblem = {' and doesn't have
    pattern or top-level CoA structure.
    
    Args:
        text: Text to analyze
        
    Returns:
        True if text appears to be a layer sub-block
    """
    text = text.strip()
    # Check if it starts with colored_emblem
    if text.startswith('colored_emblem'):
        return True
    # Check if it doesn't contain pattern (which is always in full CoA)
    if 'pattern' not in text:
        # Might be a layer if it has texture and instance
        if 'texture' in text and 'instance' in text:
            return True
    return False
