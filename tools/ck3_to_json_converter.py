#!/usr/bin/env python3
"""
CK3 Coat of Arms Format to JSON Converter

Converts CK3's custom data format files to JSON.
Handles the specific structure used in coat of arms definition files.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Union


class CK3Parser:
    """Parser for CK3 data format files."""
    
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.length = len(text)
    
    def skip_whitespace(self):
        """Skip whitespace and comments."""
        while self.pos < self.length:
            # Skip whitespace
            if self.text[self.pos] in ' \t\n\r':
                self.pos += 1
                continue
            
            # Skip comments (# to end of line)
            if self.text[self.pos] == '#':
                while self.pos < self.length and self.text[self.pos] != '\n':
                    self.pos += 1
                continue
            
            break
    
    def peek(self) -> str:
        """Look at current character without advancing."""
        self.skip_whitespace()
        if self.pos < self.length:
            return self.text[self.pos]
        return ''
    
    def consume(self, char: str):
        """Consume expected character."""
        self.skip_whitespace()
        if self.pos < self.length and self.text[self.pos] == char:
            self.pos += 1
            return True
        return False
    
    def read_string(self) -> str:
        """Read a quoted string."""
        self.skip_whitespace()
        if self.pos >= self.length or self.text[self.pos] != '"':
            return None
        
        self.pos += 1  # Skip opening quote
        start = self.pos
        
        while self.pos < self.length and self.text[self.pos] != '"':
            if self.text[self.pos] == '\\':
                self.pos += 2  # Skip escape sequence
            else:
                self.pos += 1
        
        result = self.text[start:self.pos]
        self.pos += 1  # Skip closing quote
        return result
    
    def read_identifier(self) -> str:
        """Read an unquoted identifier or value."""
        self.skip_whitespace()
        start = self.pos
        
        # Read until we hit whitespace, =, {, }, or #
        while self.pos < self.length and self.text[self.pos] not in ' \t\n\r={}#':
            self.pos += 1
        
        return self.text[start:self.pos]
    
    def read_value(self) -> Any:
        """Read a value (string, number, bool, or identifier)."""
        self.skip_whitespace()
        
        # Check for quoted string
        if self.peek() == '"':
            return self.read_string()
        
        # Check for block
        if self.peek() == '{':
            return self.read_block()
        
        # Read identifier/number/bool
        value = self.read_identifier()
        
        # Try to convert to appropriate type
        if value.lower() in ('yes', 'true'):
            return True
        elif value.lower() in ('no', 'false'):
            return False
        
        # Try to parse as number
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def read_array_or_block(self) -> Union[List, Dict]:
        """Read a block that could be an array or a dict."""
        self.consume('{')
        self.skip_whitespace()
        
        items = []
        has_keys = False
        
        while self.peek() != '}':
            # Try to read a key=value pair
            start_pos = self.pos
            key = self.read_identifier()
            
            self.skip_whitespace()
            if self.peek() == '=':
                # This is a key=value pair
                has_keys = True
                self.consume('=')
                value = self.read_value()
                items.append((key, value))
            else:
                # This is just a value (array item)
                self.pos = start_pos
                value = self.read_value()
                items.append(value)
        
        self.consume('}')
        
        # If all items have keys, return as dict
        # If some items are just values, we have a mixed structure
        if has_keys:
            result = {}
            for item in items:
                if isinstance(item, tuple):
                    key, value = item
                    # Handle duplicate keys by converting to list
                    if key in result:
                        if not isinstance(result[key], list):
                            result[key] = [result[key]]
                        result[key].append(value)
                    else:
                        result[key] = value
            return result
        else:
            return items
    
    def read_block(self) -> Union[List, Dict]:
        """Read a block (could be array or object)."""
        return self.read_array_or_block()
    
    def parse_file(self) -> Dict:
        """Parse entire file as a root-level block."""
        result = {}
        
        while self.pos < self.length:
            self.skip_whitespace()
            if self.pos >= self.length:
                break
            
            # Read key
            key = self.read_identifier()
            if not key:
                break
            
            self.skip_whitespace()
            
            # Check for = or block
            if self.consume('='):
                value = self.read_value()
            else:
                # Standalone identifier (shouldn't happen in well-formed files)
                value = None
            
            # Handle duplicate keys
            if key in result:
                if not isinstance(result[key], list):
                    result[key] = [result[key]]
                result[key].append(value)
            else:
                result[key] = value
        
        return result


def convert_file(input_path: Path, output_path: Path):
    """Convert a CK3 format file to JSON."""
    print(f"Converting: {input_path.name}")
    
    # Read input file
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse CK3 format
    parser = CK3Parser(content)
    data = parser.parse_file()
    
    # Write JSON output
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"  → {output_path.name}")


def main():
    """Main conversion process."""
    source_dir = Path("ck3_assets")
    output_dir = Path("json_output")
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Find all .txt files
    txt_files = list(source_dir.rglob("*.txt"))
    
    print(f"Found {len(txt_files)} text files to convert\n")
    
    for txt_file in txt_files:
        # Calculate relative path
        rel_path = txt_file.relative_to(source_dir)
        
        # Create output path with .json extension
        output_path = output_dir / rel_path.parent / (rel_path.stem + ".json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            convert_file(txt_file, output_path)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
    
    print(f"\nConversion complete! Output in: {output_dir}")


if __name__ == "__main__":
    main()
