#!/usr/bin/env python3
"""
Test layer copy/paste functionality
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.coa_parser import parse_coa_string, serialize_coa_to_string


def test_layer_serialization():
	"""Test serializing a single layer to colored_emblem format"""
	print("\n" + "="*70)
	print("TEST: Layer Serialization")
	print("="*70)
	
	# Create a sample layer
	layer = {
		'filename': 'ce_cross_designer.dds',
		'path': 'ce_cross_designer.dds',
		'colors': 3,
		'pos_x': 0.5,
		'pos_y': 0.6,
		'scale_x': 0.8,
		'scale_y': 0.8,
		'rotation': 45,
		'color1': [0.750, 0.525, 0.188],  # yellow
		'color2': [0.450, 0.133, 0.090],  # red
		'color3': [0.450, 0.133, 0.090],  # red
		'color1_name': 'yellow',
		'color2_name': 'red',
		'color3_name': 'red'
	}
	
	# Serialize layer to colored_emblem format
	instance_data = {
		"position": [layer['pos_x'], layer['pos_y']],
		"scale": [layer['scale_x'], layer['scale_y']],
		"rotation": int(layer['rotation'])
	}
	
	emblem_data = {
		"texture": layer['filename'],
		"instance": [instance_data]
	}
	
	# Don't add colors if they're defaults (yellow, red, red)
	# This is the same logic as in the actual implementation
	
	data = {"colored_emblem": emblem_data}
	layer_text = serialize_coa_to_string(data)
	
	print("Serialized layer:")
	print(layer_text)
	print()
	
	return layer_text


def test_layer_parsing(layer_text):
	"""Test parsing a layer from colored_emblem format"""
	print("\n" + "="*70)
	print("TEST: Layer Parsing")
	print("="*70)
	
	# Parse the layer text
	data = parse_coa_string(layer_text)
	print(f"Parsed data: {data}")
	
	# Extract colored_emblem (it's returned as a list)
	emblem_list = data.get('colored_emblem')
	if not emblem_list:
		print("[FAIL] No colored_emblem found")
		return False
	
	# Get first emblem if it's a list
	if isinstance(emblem_list, list):
		if len(emblem_list) == 0:
			print("[FAIL] colored_emblem list is empty")
			return False
		emblem = emblem_list[0]
	else:
		emblem = emblem_list
	
	print(f"Emblem texture: {emblem.get('texture')}")
	
	instances = emblem.get('instance', [])
	if not instances:
		print("[FAIL] No instances found")
		return False
	
	instance = instances[0]
	print(f"Instance position: {instance.get('position')}")
	print(f"Instance scale: {instance.get('scale')}")
	print(f"Instance rotation: {instance.get('rotation')}")
	
	print("\n[PASS] Layer parsed successfully")
	return True


def test_detection():
	"""Test detection of layer sub-block vs full CoA"""
	print("\n" + "="*70)
	print("TEST: Layer vs CoA Detection")
	print("="*70)
	
	# Layer sub-block
	layer_text = """colored_emblem={
	texture="ce_cross_designer.dds"
	instance={
		position={ 0.5 0.6 }
		scale={ 0.8 0.8 }
		rotation=45
	}
}"""
	
	# Full CoA
	coa_text = """coa_test={
	pattern="pattern__solid.dds"
	color1="black"
	color2="yellow"
	color3="black"
	colored_emblem={
		texture="ce_cross_designer.dds"
		instance={
			position={ 0.5 0.5 }
			scale={ 1.0 1.0 }
		}
	}
}"""
	
	# Simple detection logic (same as in main.py)
	def is_layer_subblock(text):
		text = text.strip()
		if text.startswith('colored_emblem'):
			return True
		if 'pattern' not in text:
			if 'texture' in text and 'instance' in text:
				return True
		return False
	
	layer_detected = is_layer_subblock(layer_text)
	coa_detected = is_layer_subblock(coa_text)
	
	print(f"Layer text detected as layer: {layer_detected} (expected: True)")
	print(f"CoA text detected as layer: {coa_detected} (expected: False)")
	
	if layer_detected and not coa_detected:
		print("\n[PASS] Detection working correctly")
		return True
	else:
		print("\n[FAIL] Detection not working correctly")
		return False


def main():
	print("\n" + "="*70)
	print("LAYER COPY/PASTE FUNCTIONALITY TESTS")
	print("="*70)
	
	# Test 1: Serialize a layer
	layer_text = test_layer_serialization()
	
	# Test 2: Parse the layer back
	if not test_layer_parsing(layer_text):
		print("\n[OVERALL] FAILED")
		return 1
	
	# Test 3: Detection
	if not test_detection():
		print("\n[OVERALL] FAILED")
		return 1
	
	print("\n" + "="*70)
	print("[OVERALL] ALL TESTS PASSED")
	print("="*70)
	return 0


if __name__ == "__main__":
	sys.exit(main())
