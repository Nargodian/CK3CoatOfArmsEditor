"""
CK3 Coat of Arms Editor - File Operations Service

This module handles file I/O operations for CoA data.
Separates file operations from UI logic.
"""

from models.coa import CoA


def save_coa_to_file(coa, filename):
    """Save CoA data to text file
    
    Args:
        coa: CoA model instance
        filename: Path to save file
        
    Raises:
        Exception: If file write fails
    """
    # Serialize CoA model to string using its built-in method
    coa_string = coa.to_string()
    
    # Write to file
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(coa_string)
    
    print(f"CoA saved to {filename}")


def load_coa_from_file(filename):
    """Load and parse CoA from text file
    
    Args:
        filename: Path to CoA file
        
    Returns:
        CoA model instance
        
    Raises:
        Exception: If file read or parse fails
    """
    # Read file
    with open(filename, 'r', encoding='utf-8') as f:
        coa_text = f.read()
    
    # Parse into CoA model
    coa = CoA.from_string(coa_text)
    if not coa:
        raise ValueError("Failed to parse coat of arms data - not a valid CK3 format")
    
    print(f"CoA loaded from {filename}")
    return coa



def coa_to_clipboard_text(coa):
    """Convert CoA to clipboard text format
    
    Args:
        coa: CoA model instance
        
    Returns:
        Serialized CoA string
    """
    return coa.to_string()


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
