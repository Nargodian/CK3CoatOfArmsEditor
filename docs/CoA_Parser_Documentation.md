# CoA Parser/Serializer Documentation

## Overview

The CoA (Coat of Arms) parser/serializer is a utility for reading and writing CK3 (Crusader Kings 3) coat of arms definitions in the Clausewitz format.

## Location

- **Parser Module**: `src/utils/coa_parser.py`
- **Examples**: `examples/parser_example.py`

## Features

- ✅ Parse CK3 CoA files into Python dictionaries
- ✅ Serialize Python data back to CK3 format
- ✅ Support for both dict-style blocks (`key=value`) and array-style blocks (`{ 0.5 0.8 }`)
- ✅ Handle multiple emblems and instances
- ✅ Preserve nested structure (colored_emblem → instance → position/scale/rotation)
- ✅ Round-trip conversion (parse → modify → serialize)

## Data Structure

A parsed CoA has the following structure:

```python
{
    "coa_dynasty_12345": {                    # CoA ID (dynasty/title)
        "custom": True,                        # Boolean flag
        "pattern": "pattern_triangle_01.dds",  # Base pattern texture
        "color1": "white",                     # Primary color
        "color2": "black",                     # Secondary color
        "color3": "blue",                      # Tertiary color
        "colored_emblem": [                    # List of emblems
            {
                "color1": "white",             # Emblem color
                "texture": "ce_lion.dds",      # Emblem texture
                "instance": [                  # List of instances (placements)
                    {
                        "position": [0.5, 0.5],    # X, Y coordinates (0-1)
                        "scale": [1.0, 1.0],        # X, Y scale
                        "rotation": 90,             # Rotation in degrees
                        "depth": 1.0                # Layer depth
                    }
                ]
            }
        ]
    }
}
```

## Usage

### Parsing a CoA File

```python
from coa_parser import parse_coa_file

# Parse the file
coa_data = parse_coa_file("my_coat_of_arms.txt")

# Access the data
coa_id = list(coa_data.keys())[0]
coa = coa_data[coa_id]

print(f"Pattern: {coa['pattern']}")
print(f"Colors: {coa['color1']}, {coa['color2']}, {coa['color3']}")
print(f"Number of emblems: {len(coa['colored_emblem'])}")
```

### Parsing from String

```python
from coa_parser import parse_coa_string

coa_text = """
coa_test={
    pattern="pattern__solid_designer.dds"
    color1=red
    color2=white
}
"""

coa_data = parse_coa_string(coa_text)
```

### Accessing Emblem Data

```python
# Get first emblem
first_emblem = coa['colored_emblem'][0]
print(f"Texture: {first_emblem['texture']}")
print(f"Color: {first_emblem['color1']}")

# Get first instance
first_instance = first_emblem['instance'][0]
print(f"Position: {first_instance['position']}")  # [x, y]
print(f"Rotation: {first_instance.get('rotation', 0)}")  # Optional field
print(f"Scale: {first_instance.get('scale', [1.0, 1.0])}")  # Optional field
```

### Modifying CoA Data

```python
# Change base pattern
coa['pattern'] = "pattern_stripes_horizontal.dds"

# Change colors
coa['color1'] = "red"
coa['color2'] = "gold"

# Modify emblem position
first_emblem['instance'][0]['position'] = [0.3, 0.7]
first_emblem['instance'][0]['rotation'] = 45
```

### Creating New CoA from Scratch

```python
new_coa = {
    "coa_custom_001": {
        "custom": True,
        "pattern": "pattern__solid_designer.dds",
        "color1": "green",
        "color2": "gold",
        "color3": "black",
        "colored_emblem": [
            {
                "color1": "gold",
                "texture": "ce_lion.dds",
                "instance": [
                    {
                        "position": [0.5, 0.5],
                        "scale": [1.0, 1.0],
                        "rotation": 0,
                        "depth": 1.0
                    }
                ]
            }
        ]
    }
}
```

### Serializing to File

```python
from coa_parser import serialize_coa_to_file

serialize_coa_to_file(coa_data, "output_coat_of_arms.txt")
```

### Serializing to String

```python
from coa_parser import serialize_coa_to_string

coa_text = serialize_coa_to_string(coa_data)
print(coa_text)
```

## Field Reference

### Base Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `custom` | bool | Yes | Whether this is a custom CoA |
| `pattern` | string | Yes | Base pattern texture filename |
| `color1` | string | Yes | Primary color name |
| `color2` | string | Yes | Secondary color name |
| `color3` | string | Yes | Tertiary color name |
| `colored_emblem` | list | No | List of emblems to display |

### Colored Emblem Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `color1` | string | Yes | Emblem primary color |
| `color2` | string | No | Emblem secondary color |
| `color3` | string | No | Emblem tertiary color |
| `texture` | string | Yes | Emblem texture filename |
| `instance` | list | Yes | List of emblem placements |

### Instance Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `position` | [x, y] | No | Position (0-1 range), default [0.5, 0.5] |
| `scale` | [x, y] | No | Scale factors, default [1.0, 1.0] |
| `rotation` | int | No | Rotation in degrees, default 0 |
| `depth` | float | No | Layer depth for z-ordering |

### Color Names

Common CK3 color names include:
- `white`, `black`, `grey`, `grey_light`
- `red`, `dark_red`, `red_dark`
- `blue`, `dark_blue`, `blue_light`
- `green`, `dark_green`
- `yellow`, `gold`
- `orange`, `brown`
- `purple`, `pink`

## Integration with Editor

The parser can be integrated into the main CoA editor for save/load functionality:

```python
# In main_new.py

from src.utils.coa_parser import parse_coa_file, serialize_coa_to_file

def load_coa_from_file(self, filepath):
    """Load a CoA from file and apply to editor"""
    coa_data = parse_coa_file(filepath)
    coa_id = list(coa_data.keys())[0]
    coa = coa_data[coa_id]
    
    # Apply base pattern
    self.canvas_widget.set_base_texture(coa['pattern'])
    
    # Apply colors
    self.canvas_widget.set_base_colors([
        self.color_name_to_rgb(coa['color1']),
        self.color_name_to_rgb(coa['color2']),
        self.color_name_to_rgb(coa['color3'])
    ])
    
    # Apply emblems
    for emblem in coa.get('colored_emblem', []):
        for instance in emblem['instance']:
            self.add_layer_from_data(emblem['texture'], instance)

def save_coa_to_file(self, filepath):
    """Save current editor state to CoA file"""
    coa_data = {
        "coa_custom_editor": {
            "custom": True,
            "pattern": self.current_pattern,
            "color1": self.rgb_to_color_name(self.base_colors[0]),
            "color2": self.rgb_to_color_name(self.base_colors[1]),
            "color3": self.rgb_to_color_name(self.base_colors[2]),
            "colored_emblem": self.export_emblems()
        }
    }
    
    serialize_coa_to_file(coa_data, filepath)
```

## Testing

Run the test suite:

```bash
python src/utils/coa_parser.py
```

Run examples:

```bash
python examples/parser_example.py
```

## Known Limitations

- Color names are stored as strings (e.g., "white", "red") not RGB values
- Parser assumes well-formed input (minimal error recovery)
- Comments in files are not preserved during round-trip
- Anonymous blocks (blocks without keys) are not yet supported

## Future Enhancements

- [ ] Color name ↔ RGB conversion utilities
- [ ] Validation of texture filenames against asset database
- [ ] Support for advanced CoA features (masks, sub_blocks)
- [ ] Better error messages with line numbers
- [ ] Preserve comments in round-trip conversion
