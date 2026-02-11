"""
CK3 data format parser.

Recursive descent parser for CK3/Paradox script files.
Handles key=value pairs, nested blocks, arrays, strings, numbers, and booleans.
"""

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
            if self.text[self.pos] in ' \t\n\r':
                self.pos += 1
                continue
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
        
        self.pos += 1
        start = self.pos
        
        while self.pos < self.length and self.text[self.pos] != '"':
            if self.text[self.pos] == '\\':
                self.pos += 2
            else:
                self.pos += 1
        
        result = self.text[start:self.pos]
        self.pos += 1
        return result
    
    def read_identifier(self) -> str:
        """Read an unquoted identifier or value."""
        self.skip_whitespace()
        start = self.pos
        
        while self.pos < self.length and self.text[self.pos] not in ' \t\n\r={}#':
            self.pos += 1
        
        return self.text[start:self.pos]
    
    # Color type keywords that precede a { values } block
    _COLOR_TYPES = {'rgb', 'hsv', 'hsv360'}
    
    def read_value(self) -> Any:
        """Read a value (string, number, bool, or identifier)."""
        self.skip_whitespace()
        
        if self.peek() == '"':
            return self.read_string()
        
        if self.peek() == '{':
            return self.read_block()
        
        value = self.read_identifier()
        
        # Handle color type prefixes: rgb { 74 201 202 }, hsv { 0.02 0.8 0.45 }
        if value.lower() in self._COLOR_TYPES and self.peek() == '{':
            components = self.read_block()  # reads the { ... } array
            return {'type': value.lower(), 'values': components}
        
        if value.lower() in ('yes', 'true'):
            return True
        elif value.lower() in ('no', 'false'):
            return False
        
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        return value
    
    def read_array_or_block(self) -> Union[List, Dict]:
        """Read a block that could be an array or a dict."""
        self.consume('{')
        self.skip_whitespace()
        
        items = []
        has_keys = False
        
        while self.peek() != '}':
            start_pos = self.pos
            key = self.read_identifier()
            
            self.skip_whitespace()
            if self.peek() == '=':
                has_keys = True
                self.consume('=')
                value = self.read_value()
                items.append((key, value))
            else:
                self.pos = start_pos
                value = self.read_value()
                items.append(value)
        
        self.consume('}')
        
        if has_keys:
            result = {}
            for item in items:
                if isinstance(item, tuple):
                    key, value = item
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
            
            key = self.read_identifier()
            if not key:
                break
            
            self.skip_whitespace()
            
            if self.consume('='):
                value = self.read_value()
            else:
                value = None
            
            if key in result:
                if not isinstance(result[key], list):
                    result[key] = [result[key]]
                result[key].append(value)
            else:
                result[key] = value
        
        return result


def parse_ck3_file(file_path: Path) -> Dict:
    """Parse a CK3 format file to dictionary."""
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        text = f.read()
    parser = CK3Parser(text)
    return parser.parse_file()
