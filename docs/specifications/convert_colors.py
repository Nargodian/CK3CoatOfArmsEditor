import colorsys
import re

def hsv_to_rgb(h, s, v):
    """Convert HSV (0-1 range) to RGB (0-1 range)"""
    return colorsys.hsv_to_rgb(h, s, v)

def parse_colors(filename):
    """Parse color definitions and convert to all formats"""
    with open(filename, 'r') as f:
        content = f.read()
    
    colors = []
    
    # Match hsv format: name = hsv { h s v }
    hsv_pattern = r'(\w+)\s*=\s*hsv\s*\{\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\}'
    for match in re.finditer(hsv_pattern, content):
        name, h, s, v = match.groups()
        h, s, v = float(h), float(s), float(v)
        
        # Convert to RGB (0-1)
        r, g, b = hsv_to_rgb(h, s, v)
        
        # Convert to RGB256
        r256, g256, b256 = int(r * 255), int(g * 255), int(b * 255)
        
        # Convert to hex
        hex_color = f"#{r256:02X}{g256:02X}{b256:02X}"
        
        # HSV360 format
        h360, s360, v360 = int(h * 360), int(s * 100), int(v * 100)
        
        colors.append({
            'name': name,
            'original_hsv': f"{h:.3f} {s:.2f} {v:.2f}",
            'hsv360': f"{h360:03d} {s360:03d} {v360:03d}",
            'rgb': f"{r:.3f} {g:.3f} {b:.3f}",
            'hex': hex_color,
            'rgb256': f"{r256:3d} {g256:3d} {b256:3d}"
        })
    
    # Match hsv360 format: name = hsv360 { h s v }
    hsv360_pattern = r'(\w+)\s*=\s*hsv360\s*\{\s*(\d+)\s+(\d+)\s+(\d+)\s*\}'
    for match in re.finditer(hsv360_pattern, content):
        name, h, s, v = match.groups()
        h, s, v = int(h), int(s), int(v)
        
        # Convert to 0-1 range
        h_norm = h / 360.0
        s_norm = s / 100.0
        v_norm = v / 100.0
        
        # Convert to RGB (0-1)
        r, g, b = hsv_to_rgb(h_norm, s_norm, v_norm)
        
        # Convert to RGB256
        r256, g256, b256 = int(r * 255), int(g * 255), int(b * 255)
        
        # Convert to hex
        hex_color = f"#{r256:02X}{g256:02X}{b256:02X}"
        
        colors.append({
            'name': name,
            'original_hsv': f"{h_norm:.3f} {s_norm:.2f} {v_norm:.2f}",
            'hsv360': f"{h:03d} {s:03d} {v:03d}",
            'rgb': f"{r:.3f} {g:.3f} {b:.3f}",
            'hex': hex_color,
            'rgb256': f"{r256:3d} {g256:3d} {b256:3d}"
        })
    
    return colors

# Parse and convert
colors = parse_colors('e:/Projects/CK3CoatOfArmsEditor/docs/specifications/default_colors.txt')

# Write output
with open('e:/Projects/CK3CoatOfArmsEditor/docs/specifications/color_conversions.txt', 'w') as f:
    f.write("# CK3 Color Conversions\n")
    f.write("# Format: color_name, original_hsv, hsv360, rgb, hex, rgb256\n\n")
    
    for color in colors:
        line = f"{color['name']:15} | {color['original_hsv']:15} | {color['hsv360']:11} | {color['rgb']:23} | {color['hex']:7} | {color['rgb256']:11}\n"
        f.write(line)

print("Conversion complete! Output written to color_conversions.txt")
