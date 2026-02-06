"""Compare methods between coa_backup.py and coa/ folder"""
import re
import os
from pathlib import Path

# Methods from coa_backup.py (from user's list)
backup_methods = [
    'set_active', 'get_active', 'has_active', '__init__', 'clear',
    '_layers', 'pattern', 'pattern_color1', 'pattern_color2', 
    'pattern_color1_name', 'pattern_color2_name', 'pattern_color3', 
    'pattern_color3_name', 'layers', 'parse', 'from_string', 
    'from_layers_string', 'serialize', 'to_string', 'serialize_layers_to_string',
    'add_layer', 'remove_layer', 'duplicate_layer', 'duplicate_layer_below',
    'duplicate_layer_above', 'merge_layers_into_first', 'move_layer_below',
    'move_layer_above', 'move_layer_to_bottom', 'move_layer_to_top',
    'shift_layer_up', 'shift_layer_down', 'review_merge', 'merge_layers',
    'split_layer', 'add_instance', 'remove_instance', 'select_instance',
    'get_layer_position', 'set_layer_position', 'translate_layer',
    'adjust_layer_positions', 'get_layer_centroid', 'set_layer_scale',
    'scale_layer', 'set_layer_rotation', 'set_layer_visible',
    'get_layer_visible', 'set_layer_mask', 'translate_all_instances',
    'scale_all_instances', 'rotate_all_instances', 'begin_instance_group_transform',
    'end_instance_group_transform', 'transform_instances_as_group',
    'begin_rotation_transform', 'apply_rotation_transform', '_apply_both_shallow',
    '_apply_orbit_only_shallow', 'end_rotation_transform', '_get_rotation_groups',
    '_rotate_point_around', 'rotate_layer', 'flip_layer', 'flip_selection',
    'align_layers', 'move_layers_to', 'translate_layers_group',
    'scale_layers_group', 'rotate_selection', '_rotate_auto',
    '_rotate_only_shallow', '_orbit_only_shallow', '_rotate_only_deep',
    '_orbit_only_deep', '_rotate_regular_layers_group',
    '_rotate_instance_layers_group', 'rotate_layers_group',
    'begin_transform_group', 'end_transform_group', 'apply_transform_group',
    'get_cached_transform', 'set_layer_color', 'set_base_color',
    'get_layer_property', 'get_layer_name', 'set_layer_name',
    'get_layer_container', 'set_layer_container', 'get_layers_by_container',
    'get_all_containers', 'generate_container_uuid', 'regenerate_container_uuid',
    'duplicate_container', 'create_container_from_layers',
    'validate_container_contiguity', 'get_layer_bounds', 'get_layers_bounds',
    'get_all_layer_uuids', 'get_top_layer_uuid', 'get_bottom_layer_uuid',
    'get_last_added_uuid', 'get_last_added_uuids', 'set_last_added_uuids',
    'get_layer_above', 'get_layer_below', 'get_layer_count',
    'get_layer_by_uuid', 'get_layer_by_index', 'get_layer_uuid_by_index',
    'get_layer_index_by_uuid', 'add_layer_object', 'insert_layer_at_index',
    'get_uuid_at_index', 'get_uuids_from_indices', 'get_snapshot',
    'set_snapshot', 'check_merge_compatibility', '_calculate_bounds',
    '_get_bounds_center', '__repr__'
]

# Read all Python files in coa/ folder
coa_path = Path('editor/src/models/coa')
refactored_methods = set()

for py_file in coa_path.glob('*.py'):
    if py_file.name.startswith('_'):
        continue  # Skip _internal files
    
    with open(py_file, 'r', encoding='utf-8') as f:
        content = f.read()
        # Find all method definitions
        pattern = r'^\s+def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        for match in re.finditer(pattern, content, re.MULTILINE):
            method_name = match.group(1)
            refactored_methods.add(method_name)

# Find missing methods
missing = []
for method in backup_methods:
    if method not in refactored_methods:
        missing.append(method)

# Separate public and private
public_missing = [m for m in missing if not m.startswith('_')]
private_missing = [m for m in missing if m.startswith('_')]

print("=" * 80)
print("MISSING PUBLIC METHODS")
print("=" * 80)
for method in sorted(public_missing):
    print(f"- {method}")

print("\n" + "=" * 80)
print("MISSING PRIVATE METHODS")
print("=" * 80)
for method in sorted(private_missing):
    print(f"- {method}")

print(f"\n\nTotal missing: {len(missing)} ({len(public_missing)} public, {len(private_missing)} private)")
print(f"Total in backup: {len(backup_methods)}")
print(f"Total in refactored: {len(refactored_methods)}")
