"""
Quick test of atlas compositor functionality
"""
from pathlib import Path
from utils.atlas_compositor import composite_emblem_atlas, composite_pattern_atlas, get_atlas_path

# Test emblem compositing
emblem_atlas = get_atlas_path("ce_boar_head.dds", "emblem")
print(f"Emblem atlas path: {emblem_atlas}")
print(f"Exists: {emblem_atlas.exists()}")

if emblem_atlas.exists():
    colors = {
        'color1': (0.9, 0.2, 0.1),  # Red
        'color2': (0.2, 0.8, 0.3),  # Green
        'color3': (0.2, 0.3, 0.9),  # Blue
        'background1': (0.95, 0.95, 0.95)
    }
    
    pixmap = composite_emblem_atlas(str(emblem_atlas), colors, size=128)
    print(f"Emblem pixmap created: {not pixmap.isNull()}, size: {pixmap.width()}x{pixmap.height()}")
    
    # Save test output
    pixmap.save("test_emblem_composite.png")
    print("Saved test_emblem_composite.png")

# Test pattern compositing  
pattern_atlas = get_atlas_path("pattern_solid.dds", "pattern")
print(f"\nPattern atlas path: {pattern_atlas}")
print(f"Exists: {pattern_atlas.exists()}")

if pattern_atlas.exists():
    bg_colors = {
        'background1': (0.9, 0.1, 0.1),  # Red
        'background2': (0.1, 0.9, 0.1),  # Green
        'background3': (0.1, 0.1, 0.9),  # Blue
    }
    
    pixmap = composite_pattern_atlas(str(pattern_atlas), bg_colors, size=(128, 64))
    print(f"Pattern pixmap created: {not pixmap.isNull()}, size: {pixmap.width()}x{pixmap.height()}")
    
    # Save test output
    pixmap.save("test_pattern_composite.png")
    print("Saved test_pattern_composite.png")

print("\nTest complete!")
