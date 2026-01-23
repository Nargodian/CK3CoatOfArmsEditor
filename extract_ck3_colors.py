"""
Extract CK3 Named Colors from Game Files

This script parses the CK3 named_colors file and generates Python code
for the color map in main_new.py.

Usage:
1. Copy 00_named_colors.txt from:
   <CK3_DIR>/game/common/named_colors/00_named_colors.txt
   
2. Run this script: python extract_ck3_colors.py

3. Copy the output into main_new.py's _color_name_to_rgb() method
"""

import re
import sys
import colorsys
from pathlib import Path


def hsv_to_rgb(h, s, v):
	"""Convert HSV (0-1 range) to RGB (0-1 range)"""
	return colorsys.hsv_to_rgb(h, s, v)


def parse_named_colors(filepath):
	"""Parse CK3 named_colors file and extract RGB values"""
	colors = {}
	
	with open(filepath, 'r', encoding='utf-8') as f:
		content = f.read()
	
	# Pattern for RGB: color_name = rgb { R G B }
	rgb_pattern = r'(\w+)\s*=\s*rgb\s*\{\s*(\d+)\s+(\d+)\s+(\d+)\s*\}'
	
	for match in re.finditer(rgb_pattern, content, re.MULTILINE):
		name = match.group(1)
		r = int(match.group(2))
		g = int(match.group(3))
		b = int(match.group(4))
		
		# Convert to 0-1 range
		colors[name] = [round(r / 255.0, 3), round(g / 255.0, 3), round(b / 255.0, 3)]
	
	# Pattern for HSV: color_name = hsv { H S V } (values 0-1)
	hsv_pattern = r'(\w+)\s*=\s*hsv\s*\{\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\}'
	
	for match in re.finditer(hsv_pattern, content, re.MULTILINE):
		name = match.group(1)
		h = float(match.group(2))
		s = float(match.group(3))
		v = float(match.group(4))
		
		# Convert HSV to RGB
		r, g, b = hsv_to_rgb(h, s, v)
		colors[name] = [round(r, 3), round(g, 3), round(b, 3)]
	
	# Pattern for HSV360: color_name = hsv360 { H S V } (H in 0-360, S/V in 0-100)
	hsv360_pattern = r'(\w+)\s*=\s*hsv360\s*\{\s*(\d+)\s+(\d+)\s+(\d+)\s*\}'
	
	for match in re.finditer(hsv360_pattern, content, re.MULTILINE):
		name = match.group(1)
		h = int(match.group(2)) / 360.0
		s = int(match.group(3)) / 100.0
		v = int(match.group(4)) / 100.0
		
		# Convert HSV to RGB
		r, g, b = hsv_to_rgb(h, s, v)
		colors[name] = [round(r, 3), round(g, 3), round(b, 3)]
	
	return colors


def generate_python_code(colors):
	"""Generate Python dictionary code for the color map"""
	lines = ["color_map = {"]
	
	# Sort by name for readability
	for name in sorted(colors.keys()):
		rgb = colors[name]
		lines.append(f"\t\t\t'{name}': {rgb},")
	
	lines.append("\t\t}")
	
	return '\n'.join(lines)


def main():
	# Check for named_colors file
	game_dir = Path("E:/Program Files (x86)/Steam/steamapps/common/Crusader Kings III/game")
	colors_file = game_dir / "common" / "named_colors" / "default_colors.txt"
	
	# Also check current directory
	if not colors_file.exists():
		colors_file = Path("default_colors.txt")
	
	if not colors_file.exists():
		print("ERROR: Could not find default_colors.txt")
		print("\nPlease copy the file from:")
		print("  <CK3_DIR>/game/common/named_colors/default_colors.txt")
		print("to the current directory and run again.")
		sys.exit(1)
	
	print(f"Parsing: {colors_file}")
	colors = parse_named_colors(colors_file)
	
	print(f"\nFound {len(colors)} colors\n")
	print("=" * 70)
	print("Copy the following into main_new.py's _color_name_to_rgb() method:")
	print("=" * 70)
	print()
	print(generate_python_code(colors))
	print()
	
	# Show some examples
	print("=" * 70)
	print("Sample colors:")
	print("=" * 70)
	for name in ['white', 'black', 'red', 'blue', 'green', 'yellow', 'gold']:
		if name in colors:
			rgb = colors[name]
			print(f"  {name:15s} = {rgb}")


if __name__ == "__main__":
	main()
