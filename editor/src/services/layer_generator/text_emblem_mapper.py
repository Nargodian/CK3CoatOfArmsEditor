"""Text emblem mapping for multi-instance layer generation.

Maps characters to available ce_letter_*.dds emblems.
"""

# Character to emblem filename mapping
# Based on available ce_letter_*.png files in ck3_assets/coa_emblems/source/
CHAR_TO_EMBLEM = {
    # Lowercase letters (a-z)
    'a': 'ce_letter_a.dds', 'b': 'ce_letter_b.dds', 'c': 'ce_letter_c.dds',
    'd': 'ce_letter_d.dds', 'e': 'ce_letter_e.dds', 'f': 'ce_letter_f.dds',
    'g': 'ce_letter_g.dds', 'h': 'ce_letter_h.dds', 'i': 'ce_letter_i.dds',
    'j': 'ce_letter_j.dds', 'k': 'ce_letter_k.dds', 'l': 'ce_letter_l.dds',
    'm': 'ce_letter_m.dds', 'n': 'ce_letter_n.dds', 'o': 'ce_letter_o.dds',
    'p': 'ce_letter_p.dds', 'q': 'ce_letter_q.dds', 'r': 'ce_letter_r.dds',
    's': 'ce_letter_s.dds', 't': 'ce_letter_t.dds', 'u': 'ce_letter_u.dds',
    'v': 'ce_letter_v.dds', 'w': 'ce_letter_w.dds', 'x': 'ce_letter_x.dds',
    'y': 'ce_letter_y.dds', 'z': 'ce_letter_z.dds',
    
    # Uppercase (map to lowercase emblems)
    'A': 'ce_letter_a.dds', 'B': 'ce_letter_b.dds', 'C': 'ce_letter_c.dds',
    'D': 'ce_letter_d.dds', 'E': 'ce_letter_e.dds', 'F': 'ce_letter_f.dds',
    'G': 'ce_letter_g.dds', 'H': 'ce_letter_h.dds', 'I': 'ce_letter_i.dds',
    'J': 'ce_letter_j.dds', 'K': 'ce_letter_k.dds', 'L': 'ce_letter_l.dds',
    'M': 'ce_letter_m.dds', 'N': 'ce_letter_n.dds', 'O': 'ce_letter_o.dds',
    'P': 'ce_letter_p.dds', 'Q': 'ce_letter_q.dds', 'R': 'ce_letter_r.dds',
    'S': 'ce_letter_s.dds', 'T': 'ce_letter_t.dds', 'U': 'ce_letter_u.dds',
    'V': 'ce_letter_v.dds', 'W': 'ce_letter_w.dds', 'X': 'ce_letter_x.dds',
    'Y': 'ce_letter_y.dds', 'Z': 'ce_letter_z.dds',
    
    # Greek letters
    'α': 'ce_letter_alpha.dds', 'ω': 'ce_letter_omega.dds', 'β': 'ce_letter_beta.dds',
}

# Valid characters whitelist (for textbox validation)
VALID_CHARS = set(CHAR_TO_EMBLEM.keys())
# Add space as valid (skipped during generation)
VALID_CHARS.add(' ')

# Maximum text length
MAX_TEXT_LENGTH = 100


def is_valid_char(char: str) -> bool:
    """Check if a character is valid for text mode.
    
    Args:
        char: Single character to validate
        
    Returns:
        True if character is valid (has emblem or is space)
    """
    return char in VALID_CHARS


def filter_text(text: str) -> str:
    """Filter text to only include valid characters.
    
    Invalid characters are silently removed.
    
    Args:
        text: Input text string
        
    Returns:
        Filtered text with only valid characters
    """
    return ''.join(c for c in text if is_valid_char(c))[:MAX_TEXT_LENGTH]


def get_emblem_for_char(char: str) -> str:
    """Get emblem filename for a character.
    
    Args:
        char: Character to look up
        
    Returns:
        Emblem filename (ce_letter_*.dds) or empty string if no emblem exists
    """
    return CHAR_TO_EMBLEM.get(char, '')


def text_to_emblems(text: str) -> list:
    """Convert text string to list of emblem filenames.
    
    Spaces are skipped (no entry in returned list).
    Invalid characters are skipped.
    
    Args:
        text: Input text string
        
    Returns:
        List of emblem filenames for each character (spaces/invalid chars omitted)
    """
    emblems = []
    for char in filter_text(text):
        if char == ' ':
            continue  # Skip spaces
        emblem = get_emblem_for_char(char)
        if emblem:
            emblems.append(emblem)
    return emblems


def char_to_label_code(char: str) -> int:
    """Convert character to label code for preview rendering.
    
    Label codes:
    - -1 = space (bounding box only)
    - 0 = invalid/no label
    - 1-26 = letters a-z
    - 27 = alpha (α)
    - 28 = omega (ω)
    - 29 = beta (β)
    
    Args:
        char: Single character
        
    Returns:
        Integer label code
    """
    if char == ' ':
        return -1
    
    # Lowercase a-z
    if 'a' <= char <= 'z':
        return ord(char) - ord('a') + 1
    
    # Uppercase A-Z (treat as lowercase)
    if 'A' <= char <= 'Z':
        return ord(char) - ord('A') + 1
    
    # Greek letters
    if char == 'α':
        return 27
    if char == 'ω':
        return 28
    if char == 'β':
        return 29
    
    # Invalid/unknown
    return 0


def text_to_label_codes(text: str) -> 'np.ndarray':
    """Convert text string to numpy array of label codes for preview.
    
    Includes spaces (as -1) and skips invalid characters.
    
    Args:
        text: Input text string
        
    Returns:
        numpy array of integer label codes
    """
    import numpy as np
    
    codes = []
    for char in filter_text(text):
        code = char_to_label_code(char)
        if code != 0:  # Skip invalid characters
            codes.append(code)
    
    return np.array(codes, dtype=int)
