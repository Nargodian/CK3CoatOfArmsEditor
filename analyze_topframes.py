"""
Analyze topframe images to determine vertical content positioning
"""
from PIL import Image
import os

def analyze_topframe(filepath, size):
    """Analyze a topframe image to find content boundaries"""
    if not os.path.exists(filepath):
        print(f"Missing: {filepath}")
        return
    
    img = Image.open(filepath)
    width, height = img.size
    
    # Convert to RGBA if needed
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Check at half the width
    check_x = width // 2
    
    # Find first non-transparent row from top
    first_content = None
    for y in range(height):
        pixel = img.getpixel((check_x, y))
        if len(pixel) == 4 and pixel[3] > 10:  # Alpha > 10
            first_content = y
            break
    
    # Find last non-transparent row from bottom
    last_content = None
    for y in range(height - 1, -1, -1):
        pixel = img.getpixel((check_x, y))
        if len(pixel) == 4 and pixel[3] > 10:  # Alpha > 10
            last_content = y
            break
    
    if first_content is not None and last_content is not None:
        content_height = last_content - first_content + 1
        print(f"Size {size}:")
        print(f"  Image dimensions: {width}x{height}")
        print(f"  First content at: {first_content}px from top ({first_content/height*100:.1f}%)")
        print(f"  Last content at: {last_content}px from top ({last_content/height*100:.1f}%)")
        print(f"  Content height: {content_height}px ({content_height/height*100:.1f}%)")
        print(f"  Empty space at top: {first_content}px")
        print(f"  Empty space at bottom: {height - last_content - 1}px")
        print()
    else:
        print(f"Size {size}: No content found")
        print()

# Analyze all topframe sizes
base_path = "ck3_assets/title_frames"
sizes = [28, 44, 62, 86, 115]

print("=" * 60)
print("TOPFRAME CONTENT ANALYSIS")
print("=" * 60)
print()

for size in sizes:
    # Topframes are 7x1 atlases, so we need to extract one section
    # For analysis, just look at the full image since all sections should be identical
    filepath = os.path.join(base_path, f"topframe_{size}.png")
    analyze_topframe(filepath, size)

print("=" * 60)
print("ANALYSIS COMPLETE")
print("=" * 60)
