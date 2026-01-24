"""
CK3 Coat of Arms Parser/Serializer

Parses and serializes CK3 coat of arms definitions in the Clausewitz format.
Supports the simplified CoA structure with pattern, colors, and colored_emblem blocks.
"""

import re
from typing import Dict, List, Any, Union, Tuple


class CoAParser:
	"""Parser for CK3 Coat of Arms files"""
	
	def __init__(self):
		self.pos = 0
		self.text = ""
	
	def parse_file(self, filepath: str) -> Dict[str, Any]:
		"""Parse a CoA file and return the structured data"""
		with open(filepath, 'r', encoding='utf-8') as f:
			self.text = f.read()
		self.pos = 0
		return self.parse_block()
	
	def parse_string(self, text: str) -> Dict[str, Any]:
		"""Parse a CoA string and return the structured data"""
		self.text = text
		self.pos = 0
		return self.parse_block()
	
	def skip_whitespace(self):
		"""Skip whitespace and comments"""
		while self.pos < len(self.text):
			if self.text[self.pos].isspace():
				self.pos += 1
			elif self.text[self.pos] == '#':
				# Skip comment until end of line
				while self.pos < len(self.text) and self.text[self.pos] != '\n':
					self.pos += 1
			else:
				break
	
	def peek_char(self) -> str:
		"""Peek at current character without consuming"""
		self.skip_whitespace()
		if self.pos < len(self.text):
			return self.text[self.pos]
		return ''
	
	def read_identifier(self) -> str:
		"""Read an identifier (key name)"""
		self.skip_whitespace()
		start = self.pos
		
		# Identifiers can contain letters, numbers, underscores, and hyphens
		while self.pos < len(self.text):
			c = self.text[self.pos]
			if c.isalnum() or c in ('_', '-'):
				self.pos += 1
			else:
				break
		
		return self.text[start:self.pos]
	
	def read_string(self) -> str:
		"""Read a quoted string"""
		self.skip_whitespace()
		if self.text[self.pos] != '"':
			raise ValueError(f"Expected quote at position {self.pos}")
		
		self.pos += 1  # Skip opening quote
		start = self.pos
		
		while self.pos < len(self.text):
			if self.text[self.pos] == '"':
				result = self.text[start:self.pos]
				self.pos += 1  # Skip closing quote
				return result
			self.pos += 1
		
		raise ValueError("Unterminated string")
	
	def read_value(self) -> Union[str, int, float, bool, Dict, List]:
		"""Read a value (string, number, bool, or block)"""
		self.skip_whitespace()
		
		if self.pos >= len(self.text):
			return None
		
		c = self.text[self.pos]
		
		# String value
		if c == '"':
			return self.read_string()
		
		# Block value
		if c == '{':
			return self.parse_block()
		
		# Check for UNKNOWN_TYPE like "rgb { 74 201 202 }"
		# Save position to potentially read identifier + block
		saved_pos = self.pos
		identifier = ""
		
		# Try to read identifier
		while self.pos < len(self.text):
			c = self.text[self.pos]
			if c.isalnum() or c in ('_', '-'):
				identifier += c
				self.pos += 1
			else:
				break
		
		# Check if identifier is followed by '{'
		self.skip_whitespace()
		if identifier and self.pos < len(self.text) and self.text[self.pos] == '{':
			# This is an UNKNOWN_TYPE (e.g., "rgb { ... }")
			# Read the entire construct as a string
			start_pos = saved_pos
			self.pos += 1  # Skip '{'
			brace_count = 1
			
			while self.pos < len(self.text) and brace_count > 0:
				if self.text[self.pos] == '{':
					brace_count += 1
				elif self.text[self.pos] == '}':
					brace_count -= 1
				self.pos += 1
			
			# Return the entire construct as a string
			return self.text[start_pos:self.pos].strip()
		
		# Not an UNKNOWN_TYPE, restore position and parse as simple value
		self.pos = saved_pos
		
		# Negative numbers or identifiers
		start = self.pos
		if c == '-':
			self.pos += 1
		
		# Number or identifier
		while self.pos < len(self.text):
			c = self.text[self.pos]
			if c.isspace() or c in ('=', '{', '}', '#'):
				break
			self.pos += 1
		
		value_str = self.text[start:self.pos].strip()
		
		if not value_str:
			return None
		
		# Try to parse as number
		try:
			if '.' in value_str:
				return float(value_str)
			else:
				return int(value_str)
		except ValueError:
			pass
		
		# Boolean values
		if value_str == 'yes':
			return True
		if value_str == 'no':
			return False
		
		# Return as string identifier
		return value_str
	
	def parse_block(self) -> Union[Dict[str, Any], List[Any]]:
		"""Parse a block {...} - can be dict-style or array-style"""
		self.skip_whitespace()
		
		# Check for opening brace
		if self.pos < len(self.text) and self.text[self.pos] == '{':
			self.pos += 1
		
		# Try to determine if this is an array block or dict block
		# Look ahead to see if we have key=value or just values
		saved_pos = self.pos
		is_array = False
		
		self.skip_whitespace()
		if self.pos < len(self.text) and self.text[self.pos] != '}':
			# Peek ahead to see if we have an identifier followed by =
			test_key = self.read_identifier()
			self.skip_whitespace()
			if self.pos < len(self.text) and self.text[self.pos] != '=':
				# No '=' means this is likely an array block
				is_array = True
		
		# Restore position
		self.pos = saved_pos
		
		if is_array:
			return self.parse_array_block()
		else:
			return self.parse_dict_block()
	
	def parse_array_block(self) -> List[Any]:
		"""Parse an array-style block like { 0.5 0.8 }"""
		result = []
		
		while self.pos < len(self.text):
			self.skip_whitespace()
			
			if self.pos >= len(self.text):
				break
			
			# Check for closing brace
			if self.text[self.pos] == '}':
				self.pos += 1
				break
			
			# Read value
			value = self.read_value()
			if value is not None:
				result.append(value)
		
		return result
	
	def parse_dict_block(self) -> Dict[str, Any]:
		"""Parse a dict-style block like { key=value }"""
		result = {}
		
		while self.pos < len(self.text):
			self.skip_whitespace()
			
			if self.pos >= len(self.text):
				break
			
			# Check for closing brace
			if self.text[self.pos] == '}':
				self.pos += 1
				break
			
			# Read key
			key = self.read_identifier()
			if not key:
				break
			
			self.skip_whitespace()
			
			# Expect '='
			if self.pos < len(self.text) and self.text[self.pos] == '=':
				self.pos += 1
			else:
				raise ValueError(f"Expected '=' after key '{key}' at position {self.pos}")
			
			# Read value
			value = self.read_value()
			
			# Handle multiple entries for certain keys (colored_emblem, instance)
			if key in ('colored_emblem', 'instance'):
				if key not in result:
					result[key] = []
				result[key].append(value)
			else:
				result[key] = value
		
		return result


class CoASerializer:
	"""Serializer for CK3 Coat of Arms data"""
	
	def __init__(self):
		self.indent_level = 0
		self.indent_str = "\t"
	
	def serialize_to_file(self, data: Dict[str, Any], filepath: str):
		"""Serialize CoA data to a file"""
		text = self.serialize_to_string(data)
		with open(filepath, 'w', encoding='utf-8') as f:
			f.write(text)
	
	def serialize_to_string(self, data: Dict[str, Any]) -> str:
		"""Serialize CoA data to a string"""
		self.indent_level = 0
		lines = []
		
		# Assume single top-level key (e.g., "coa_dynasty_28014")
		for key, value in data.items():
			lines.append(f"{key}={{")
			self.indent_level += 1
			lines.extend(self._serialize_block(value))
			self.indent_level -= 1
			lines.append("}")
		
		return '\n'.join(lines) + '\n'
	
	def _indent(self) -> str:
		"""Get current indentation string"""
		return self.indent_str * self.indent_level
	
	def _serialize_value(self, value: Any) -> str:
		"""Serialize a single value"""
		if isinstance(value, bool):
			return "yes" if value else "no"
		elif isinstance(value, str):
			# Don't quote rgb { } format
			if value.startswith('rgb {') or value.startswith('rgb{'):
				return value
			# Quote strings if they contain special characters or spaces
			if any(c in value for c in (' ', '.', '/', '\\')):
				return f'"{value}"'
			return value
		elif isinstance(value, (int, float)):
			# Format floats with 6 decimal places if needed
			if isinstance(value, float):
				return f"{value:.6f}"
			return str(value)
		else:
			return str(value)
	
	def _serialize_block(self, data: Union[Dict[str, Any], List]) -> List[str]:
		"""Serialize a block's contents"""
		lines = []
		
		# Handle array-style blocks
		if isinstance(data, list):
			# Array blocks serialize on one line
			values = [self._serialize_value(v) for v in data]
			return [' '.join(values)]
		
		# Handle dict-style blocks
		for key, value in data.items():
			indent = self._indent()
			
			if key == 'colored_emblem' and isinstance(value, list):
				# Handle multiple colored_emblem entries
				for emblem in value:
					lines.append(f"{indent}{key}={{")
					self.indent_level += 1
					lines.extend(self._serialize_block(emblem))
					self.indent_level -= 1
					lines.append(f"{indent}}}")
					lines.append("")  # Empty line after each colored_emblem
			elif key == 'instance' and isinstance(value, list):
				# Handle multiple instances
				for inst in value:
					lines.append(f"{indent}{key}={{")
					self.indent_level += 1
					lines.extend(self._serialize_block(inst))
					self.indent_level -= 1
					lines.append(f"{indent}}}")
					lines.append("")  # Empty line after each instance
			elif isinstance(value, dict):
				# Nested dict block
				lines.append(f"{indent}{key}={{")
				self.indent_level += 1
				lines.extend(self._serialize_block(value))
				self.indent_level -= 1
				lines.append(f"{indent}}}")
			elif isinstance(value, list):
				# Array block (like position or scale)
				array_values = ' '.join([self._serialize_value(v) for v in value])
				lines.append(f"{indent}{key}={{ {array_values} }}")
			else:
				# Simple key=value
				lines.append(f"{indent}{key}={self._serialize_value(value)}")
		
		return lines


# Utility functions for easy use

def parse_coa_file(filepath: str) -> Dict[str, Any]:
	"""Parse a CoA file and return structured data"""
	parser = CoAParser()
	return parser.parse_file(filepath)


def parse_coa_string(text: str) -> Dict[str, Any]:
	"""Parse a CoA string and return structured data"""
	parser = CoAParser()
	return parser.parse_string(text)


def serialize_coa_to_file(data: Dict[str, Any], filepath: str):
	"""Serialize CoA data to a file"""
	serializer = CoASerializer()
	serializer.serialize_to_file(data, filepath)


def serialize_coa_to_string(data: Dict[str, Any]) -> str:
	"""Serialize CoA data to a string"""
	serializer = CoASerializer()
	return serializer.serialize_to_string(data)
