#!/usr/bin/env python3
"""
Round-trip test for CoA parser/serializer
Loads all coa_sample files, serializes them, and compares output to original
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.coa_parser import parse_coa_file, serialize_coa_to_string


def load_file(filepath):
    """Load file contents as string"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def compare_files(original, serialized, sample_name):
    """Compare original and serialized content"""
    print(f"\n{'='*70}")
    print(f"Testing: {sample_name}")
    print(f"{'='*70}")
    
    if original == serialized:
        print(f"[PASS] PERFECT MATCH")
        return True
    else:
        print(f"[FAIL] MISMATCH")
        print(f"\n--- ORIGINAL ({len(original)} chars) ---")
        print(original)
        print(f"\n--- SERIALIZED ({len(serialized)} chars) ---")
        print(serialized)
        print(f"\n--- DIFFERENCES ---")
        
        # Show line-by-line differences
        orig_lines = original.split('\n')
        ser_lines = serialized.split('\n')
        
        max_lines = max(len(orig_lines), len(ser_lines))
        for i in range(max_lines):
            orig_line = orig_lines[i] if i < len(orig_lines) else "<MISSING>"
            ser_line = ser_lines[i] if i < len(ser_lines) else "<MISSING>"
            
            if orig_line != ser_line:
                print(f"Line {i+1}:")
                print(f"  ORIG: {repr(orig_line)}")
                print(f"  SER:  {repr(ser_line)}")
        
        return False


def main():
    """Run round-trip tests on all samples"""
    print("CoA Parser/Serializer Round-Trip Test")
    print("="*70)
    
    # Find all coa_sample files
    samples = []
    for i in range(1, 7):
        filepath = f"coa_sample_{i}.txt"
        if os.path.exists(filepath):
            samples.append(filepath)
        else:
            print(f"Warning: {filepath} not found")
    
    if not samples:
        print("Error: No sample files found!")
        return 1
    
    # Test each sample
    results = []
    for sample_path in samples:
        try:
            # Load original
            original = load_file(sample_path)
            
            # Parse
            data = parse_coa_file(sample_path)
            
            # Serialize
            serialized = serialize_coa_to_string(data)
            
            # Compare
            match = compare_files(original, serialized, sample_path)
            results.append((sample_path, match))
            
        except Exception as e:
            print(f"\n{'='*70}")
            print(f"ERROR testing {sample_path}: {e}")
            print(f"{'='*70}")
            import traceback
            traceback.print_exc()
            results.append((sample_path, False))
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    passed = sum(1 for _, match in results if match)
    total = len(results)
    
    for sample, match in results:
        status = "[PASS]" if match else "[FAIL]"
        print(f"{status}: {sample}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
