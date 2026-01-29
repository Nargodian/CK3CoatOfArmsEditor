"""
CK3 Coat of Arms Editor - File Operations Service

This module handles file I/O operations for CoA data.
Separates file operations from UI logic.
"""

from utils.coa_parser import parse_coa_string, serialize_coa_to_string
from utils.color_utils import rgb_to_color_name
from constants import DEFAULT_BASE_COLOR1, DEFAULT_BASE_COLOR2, DEFAULT_BASE_COLOR3


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
    
    # Add layers as separate colored_emblem blocks (CK3 format)
    if layers:
        coa_data["coa_export"]["colored_emblem"] = []
        
        for depth_index, layer in enumerate(layers):
            # Migrate old format if needed
            if 'pos_x' in layer and 'instances' not in layer:
                from services.layer_operations import _migrate_layer_to_instances
                _migrate_layer_to_instances(layer)
            
            texture = layer.get('filename', layer.get('path', ''))
            
            # Build instances list
            instances = []
            for inst in layer.get('instances', []):
                # Combine flip and scale for export
                scale_x = inst.get('scale_x', 1.0)
                scale_y = inst.get('scale_y', 1.0)
                if layer.get('flip_x', False):
                    scale_x = -scale_x
                if layer.get('flip_y', False):
                    scale_y = -scale_y
                
                instance = {
                    "position": [inst.get('pos_x', 0.5), inst.get('pos_y', 0.5)],
                    "scale": [scale_x, scale_y],
                    "rotation": int(inst.get('rotation', 0))
                }
                
                # Add depth: higher depth = further back
                # First layer (frontmost) = no depth, subsequent layers get increasing depth
                if depth_index < len(layers) - 1:
                    # Calculate depth from back: last layer gets highest depth
                    depth_from_back = len(layers) - 1 - depth_index
                    instance["depth"] = float(depth_from_back) + 0.01
                
                instances.append(instance)
            
            # If no instances, create default
            if not instances:
                instances = [{"position": [0.5, 0.5], "scale": [1.0, 1.0], "rotation": 0}]
            
            emblem = {
                "texture": texture,
                "color1": rgb_to_color_name(layer.get('color1'), layer.get('color1_name')),
                "instance": instances
            }
            
            # Add mask if present (None means render everywhere, so omit it)
            mask = layer.get('mask')
            if mask is not None:
                emblem['mask'] = mask
            
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
    
    # Add base colors only if they differ from defaults
    color1_str = rgb_to_color_name(base_colors[0], base_color_names[0])
    color2_str = rgb_to_color_name(base_colors[1], base_color_names[1])
    color3_str = rgb_to_color_name(base_colors[2], base_color_names[2])
    
    if color1_str != DEFAULT_BASE_COLOR1:
        coa_data["coa_clipboard"]["color1"] = color1_str
    if color2_str != DEFAULT_BASE_COLOR2:
        coa_data["coa_clipboard"]["color2"] = color2_str
    if color3_str != DEFAULT_BASE_COLOR3:
        coa_data["coa_clipboard"]["color3"] = color3_str
    
    # Add emblem layers with depth values
    for layer_idx, layer in enumerate(layers):
        # Migrate old format if needed
        if 'pos_x' in layer and 'instances' not in layer:
            from services.layer_operations import _migrate_layer_to_instances
            _migrate_layer_to_instances(layer)
        
        # Build instances list
        instances = []
        for inst in layer.get('instances', []):
            # Combine flip and scale for export
            scale_x = inst.get('scale_x', 1.0)
            scale_y = inst.get('scale_y', 1.0)
            if layer.get('flip_x', False):
                scale_x = -scale_x
            if layer.get('flip_y', False):
                scale_y = -scale_y
            
            instance = {
                "position": [inst.get('pos_x', 0.5), inst.get('pos_y', 0.5)],
                "scale": [scale_x, scale_y],
                "rotation": int(inst.get('rotation', 0))
            }
            # Add depth: higher depth = further back
            # First layer (frontmost) = no depth, subsequent layers get increasing depth
            if layer_idx < len(layers) - 1:
                # Calculate depth from back: last layer gets highest depth
                depth_from_back = len(layers) - 1 - layer_idx
                instance['depth'] = float(depth_from_back) + 0.01
            
            instances.append(instance)
        
        # If no instances, create default
        if not instances:
            instances = [{"position": [0.5, 0.5], "scale": [1.0, 1.0], "rotation": 0}]
        
        emblem = {
            "texture": layer.get('filename', ''),
            "color1": rgb_to_color_name(layer.get('color1'), layer.get('color1_name')),
            "instance": instances
        }
        
        # Add mask if present (None means render everywhere, so omit it)
        mask = layer.get('mask')
        if mask is not None:
            emblem['mask'] = mask
        
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
