"""
Unit tests for CoA Parser/Serializer

Tests parsing and serialization of CK3 coat of arms files.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.coa_parser import parse_coa_file, parse_coa_string, serialize_coa_to_string


def test_parse_sample_1():
	"""Test parsing coa_sample_1.txt"""
	try:
		data = parse_coa_file("samples/coa_sample_1.txt")
		assert data is not None, "Failed to parse coa_sample_1.txt"
		
		# Get first CoA definition
		coa = list(data.values())[0]
		
		# Check basic structure
		assert 'pattern' in coa, "Missing pattern"
		assert 'color1' in coa, "Missing color1"
		assert 'color2' in coa, "Missing color2"
		assert 'color3' in coa, "Missing color3"
		
		print(f"✓ Successfully parsed coa_sample_1.txt")
		print(f"  Pattern: {coa.get('pattern')}")
		print(f"  Colors: {coa.get('color1')}, {coa.get('color2')}, {coa.get('color3')}")
		print(f"  Emblems: {len(coa.get('colored_emblem', []))}")
		
		return True
	except Exception as e:
		print(f"✗ Error parsing coa_sample_1.txt: {e}")
		import traceback
		traceback.print_exc()
		return False


def test_parse_sample_2():
	"""Test parsing coa_sample_2.txt"""
	try:
		data = parse_coa_file("samples/coa_sample_2.txt")
		assert data is not None, "Failed to parse coa_sample_2.txt"
		
		# Get first CoA definition
		coa = list(data.values())[0]
		
		# Check basic structure
		assert 'pattern' in coa, "Missing pattern"
		assert 'color1' in coa, "Missing color1"
		
		print(f"✓ Successfully parsed coa_sample_2.txt")
		print(f"  Pattern: {coa.get('pattern')}")
		print(f"  Colors: {coa.get('color1')}, {coa.get('color2')}, {coa.get('color3')}")
		print(f"  Emblems: {len(coa.get('colored_emblem', []))}")
		
		return True
	except Exception as e:
		print(f"✗ Error parsing coa_sample_2.txt: {e}")
		import traceback
		traceback.print_exc()
		return False


def test_roundtrip():
	"""Test round-trip parsing -> serialization -> parsing"""
	try:
		# Parse original
		data1 = parse_coa_file("samples/coa_sample_1.txt")
		
		# Serialize
		serialized = serialize_coa_to_string(data1)
		assert serialized, "Serialization returned empty string"
		
		# Re-parse
		data2 = parse_coa_string(serialized)
		assert data2 is not None, "Failed to re-parse serialized data"
		
		print("✓ Round-trip test successful")
		return True
	except Exception as e:
		print(f"✗ Round-trip test failed: {e}")
		import traceback
		traceback.print_exc()
		return False


def run_all_tests():
	"""Run all CoA parser tests"""
	print("Testing CoA Parser/Serializer")
	print("=" * 60)
	
	results = []
	
	# Run tests
	print("\nTest 1: Parse sample 1")
	results.append(test_parse_sample_1())
	
	print("\nTest 2: Parse sample 2")
	results.append(test_parse_sample_2())
	
	print("\nTest 3: Round-trip")
	results.append(test_roundtrip())
	
	# Summary
	print("\n" + "=" * 60)
	passed = sum(results)
	total = len(results)
	print(f"Tests: {passed}/{total} passed")
	
	if passed == total:
		print("✓ All tests passed!")
		return 0
	else:
		print(f"✗ {total - passed} test(s) failed")
		return 1


if __name__ == "__main__":
	exit(run_all_tests())
