"""Global metadata cache for emblem and pattern color information.

This module provides globally accessible metadata for assets, loaded once
and cached for the entire application lifecycle.
"""

import json
from pathlib import Path
from typing import Optional, Dict

# Global cache
_EMBLEM_METADATA: Optional[Dict[str, dict]] = None
_PATTERN_METADATA: Optional[Dict[str, dict]] = None


def load_metadata():
	"""Load metadata from JSON files into global cache."""
	global _EMBLEM_METADATA, _PATTERN_METADATA
	
	if _EMBLEM_METADATA is None or _PATTERN_METADATA is None:
		from utils.path_resolver import get_emblem_metadata_path, get_pattern_metadata_path
		
		_EMBLEM_METADATA = {}
		_PATTERN_METADATA = {}
		
		# Load emblems
		emblem_json = get_emblem_metadata_path()
		if emblem_json.exists():
			with open(emblem_json, 'r', encoding='utf-8') as f:
				_EMBLEM_METADATA = json.load(f)
		
		# Load patterns
		pattern_json = get_pattern_metadata_path()
		if pattern_json.exists():
			with open(pattern_json, 'r', encoding='utf-8') as f:
				_PATTERN_METADATA = json.load(f)


def get_texture_color_count(filename: str) -> int:
	"""Get the color count for a texture file.
	
	Args:
		filename: Texture filename (e.g., 'ce_lion_passant_guardant.dds')
		
	Returns:
		Number of colors (1-3), defaults to 3 if not found
	"""
	load_metadata()
	
	# Check emblems first
	if filename in _EMBLEM_METADATA:
		return _EMBLEM_METADATA[filename].get('colors', 3)
	
	# Check patterns
	if filename in _PATTERN_METADATA:
		return _PATTERN_METADATA[filename].get('colors', 1)
	
	# Default to 3 colors for unknown emblems
	return 3


def get_texture_category(filename: str) -> Optional[str]:
	"""Get the category for a texture file.
	
	Args:
		filename: Texture filename (e.g., 'ce_lion_passant_guardant.dds')
		
	Returns:
		Category name or None if not found
	"""
	load_metadata()
	
	# Check emblems first
	if filename in _EMBLEM_METADATA:
		return _EMBLEM_METADATA[filename].get('category')
	
	# Check patterns
	if filename in _PATTERN_METADATA:
		return _PATTERN_METADATA[filename].get('category')
	
	return None


def get_emblem_metadata() -> Dict[str, dict]:
	"""Get all emblem metadata.
	
	Returns:
		Dictionary mapping filenames to metadata dicts
	"""
	load_metadata()
	return _EMBLEM_METADATA.copy()


def get_pattern_metadata() -> Dict[str, dict]:
	"""Get all pattern metadata.
	
	Returns:
		Dictionary mapping filenames to metadata dicts
	"""
	load_metadata()
	return _PATTERN_METADATA.copy()


def clear_cache():
	"""Clear the metadata cache (useful for testing or reloading)."""
	global _EMBLEM_METADATA, _PATTERN_METADATA
	_EMBLEM_METADATA = None
	_PATTERN_METADATA = None
