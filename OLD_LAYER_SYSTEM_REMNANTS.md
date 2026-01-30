# OLD DICTIONARY-BASED LAYER SYSTEM REMNANTS

**Generated:** 2026-01-29  
**Analysis Scope:** All Python files connected to main.py

This report identifies remnants of the old dictionary-based layer system that need to be migrated to the new CoA object-based system.

---

## SUMMARY

The codebase is in the middle of a refactor from dictionary-based layers to object-based layers (CoA model). This analysis identifies ALL remaining dictionary patterns that need migration.

### Key Patterns to Eliminate:

1. **Dictionary access**: `layer['key']`, `layer.get('key')`
2. **Instance lists**: `layer['instances']`, `instance_count`, `selected_instance`
3. **Dict creation**: `{'filename': ..., 'pos_x': ..., 'color1': ...}`
4. **Layer list operations**: `layers.append()`, `layers[idx] = {...}`, `layers = []`
5. **Deep copies**: `dict(layer)`, `[dict(l) for l in layers]`
6. **Dict conversion from CoA**: Converting Layer objects back to dicts for old UI

---

## FILE: editor\src\main.py

**Status:** HEAVILY MIXED - Has CoA model but still converts to/from dicts everywhere

### Critical Issues:

#### 1. Layer Dict Conversion (Lines 718-741, 841-863, 1228-1250)
```python
# Converting CoA Layer objects back to dicts for old UI
for i in range(self.coa.get_layer_count()):
    layer = self.coa._layers[i]
    layer_dict = {
        'uuid': layer.uuid,
        'filename': layer.filename,
        'pos_x': layer.pos_x,
        'pos_y': layer.pos_y,
        'scale_x': layer.scale_x,
        'scale_y': layer.scale_y,
        'rotation': layer.rotation,
        'depth': layer.depth,
        'color1': layer.color1,
        'color2': layer.color2,
        'color3': layer.color3,
        'color1_name': layer.color1_name,
        'color2_name': layer.color2_name,
        'color3_name': layer.color3_name,
        'mask': layer.mask,
        'flip_x': layer.flip_x,
        'flip_y': layer.flip_y,
        'instance_count': layer.instance_count,
    }
    self.right_sidebar.layers.append(layer_dict)
```
**Impact:** HIGH - This conversion happens in load_coa, autosave recovery, and undo/redo

#### 2. Layer Dictionary Access (Lines 962-1005)
```python
# Still accessing layers as dicts throughout
old_layer = self.right_sidebar.layers[idx]
self.right_sidebar.layers[idx] = {
    **old_layer,
    'filename': dds_filename,
    'path': dds_filename,
    'colors': color_count
}
```

#### 3. New Layer Creation as Dict (Lines 984-1006)
```python
new_layer = {
    'filename': dds_filename,
    'path': dds_filename,
    'colors': color_count,
    'instances': [{
        'pos_x': 0.5,
        'pos_y': 0.5,
        'scale_x': DEFAULT_SCALE_X,
        'scale_y': DEFAULT_SCALE_Y,
        'rotation': DEFAULT_ROTATION,
        'depth': 0.0
    }],
    'selected_instance': 0,
    'flip_x': DEFAULT_FLIP_X,
    'flip_y': DEFAULT_FLIP_Y,
    'color1': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR1]['rgb'],
    'color2': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR2]['rgb'],
    'color3': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR3]['rgb'],
    'color1_name': DEFAULT_EMBLEM_COLOR1,
    'color2_name': DEFAULT_EMBLEM_COLOR2,
    'color3_name': DEFAULT_EMBLEM_COLOR3,
    'mask': None
}
```

#### 4. Instance List Access (Lines 1057-1065, 1685-1701)
```python
# Direct dict key access for instances
layer['pos_x'] = max(0.0, layer.get('pos_x', 0.5) - move_amount)
layer['pos_y'] = min(1.0, layer.get('pos_y', 0.5) + move_amount)
layer['rotation'] = (layer['rotation'] + angle_delta) % 360

# Checking for multi-instance layers
instances = layer.get('instances', [])
if len(instances) <= 1:
    return
```

**Total Dictionary Patterns:** ~150+ occurrences

---

## FILE: editor\src\components\property_sidebar.py

**Status:** CRITICAL - Core UI component still using dicts exclusively

### Critical Issues:

#### 1. Layer List Storage (Line 30)
```python
self.layers = []  # List of layer data dicts (OLD CODE: keep for now)
```

#### 2. Property Access Throughout (Lines 100-300+)
```python
# Hundreds of instances of dict access
layer = self.layers[idx]
value = layer.get('pos_x', 0.5)
layer['color1'] = new_color
layer['rotation'] = rotation_value
```

#### 3. Instance Management (Lines 150-250+)
```python
instances = layer.get('instances', [])
selected_inst_idx = layer.get('selected_instance', 0)
instance = instances[selected_inst_idx]
instance['pos_x'] = value
```

#### 4. Layer Manipulation
```python
self.layers.append(new_layer_dict)
self.layers.insert(idx, layer_dict)
self.layers.pop(idx)
self.layers[idx] = updated_dict
```

**Total Dictionary Patterns:** 300+ occurrences (this file is DENSE with dict operations)

---

## FILE: editor\src\components\canvas_widget.py

**Status:** MIXED - OpenGL rendering still expects dicts

### Critical Issues:

#### 1. Layer Rendering (Throughout)
```python
def set_layers(self, layers):
    # Expects list of layer dicts
    self.layers = layers

# In render loop
for layer in self.layers:
    texture = layer.get('filename')
    instances = layer.get('instances', [])
    for inst in instances:
        pos_x = inst.get('pos_x', 0.5)
        # ... render using dict values
```

#### 2. Instance Processing
```python
# Accessing instance dicts
scale_x = inst.get('scale_x', 1.0)
rotation = inst.get('rotation', 0)
flip_x = layer.get('flip_x', False)
```

**Total Dictionary Patterns:** 50+ occurrences

---

## FILE: editor\src\components\canvas_area.py

**Status:** MODERATE - Transform widget interaction with dicts

### Critical Issues:

#### 1. Transform Changes (Lines 150-250)
```python
def _on_transform_changed(self, delta_x, delta_y, scale_factor, rotation_delta):
    for idx in selected_indices:
        layer = self.property_sidebar.layers[idx]
        layer['pos_x'] += delta_x
        layer['pos_y'] += delta_y
        layer['scale_x'] *= scale_factor
        layer['rotation'] += rotation_delta
```

**Total Dictionary Patterns:** 20+ occurrences

---

## FILE: editor\src\components\property_sidebar_widgets\layer_list_widget.py

**Status:** HIGH IMPACT - Layer list UI completely dict-based

### Critical Issues:

#### 1. Layer Display
```python
def update_layer_item(self, index, layer):
    # layer is dict
    filename = layer.get('filename', 'Unknown')
    instances = layer.get('instances', [])
    colors = layer.get('colors', 3)
```

#### 2. Thumbnail Generation
```python
# Accessing layer dict for thumbnail rendering
color1 = layer.get('color1', [255, 255, 0])
flip_x = layer.get('flip_x', False)
```

**Total Dictionary Patterns:** 40+ occurrences

---

## FILE: editor\src\services\layer_operations.py

**Status:** CRITICAL - Service layer still creates/manipulates dicts

### Critical Issues:

#### 1. Layer Creation (Lines 53-98)
```python
def create_default_layer(filename, colors=3, **overrides):
    default_instance = {
        'pos_x': DEFAULT_POSITION_X,
        'pos_y': DEFAULT_POSITION_Y,
        'scale_x': DEFAULT_SCALE_X,
        'scale_y': DEFAULT_SCALE_Y,
        'rotation': DEFAULT_ROTATION,
        'depth': 0.0
    }
    
    layer_data = {
        'filename': filename,
        'path': filename,
        'colors': colors,
        'instances': [default_instance],
        'selected_instance': 0,
        'flip_x': False,
        'flip_y': False,
        'color1': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR1]['rgb'],
        'color2': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR2]['rgb'],
        'color3': CK3_NAMED_COLORS[DEFAULT_EMBLEM_COLOR3]['rgb'],
        'color1_name': DEFAULT_EMBLEM_COLOR1,
        'color2_name': DEFAULT_EMBLEM_COLOR2,
        'color3_name': DEFAULT_EMBLEM_COLOR3,
        'mask': None
    }
    return layer_data
```

#### 2. Instance Migration (Lines 101-129)
```python
def _migrate_layer_to_instances(layer_data):
    # Modifies dict in place
    instance = {
        'pos_x': layer_data.pop('pos_x', DEFAULT_POSITION_X),
        'pos_y': layer_data.pop('pos_y', DEFAULT_POSITION_Y),
        # ...
    }
    layer_data['instances'] = [instance]
```

#### 3. Layer Duplication (Lines 132-180)
```python
def duplicate_layer(layer, offset_x=0.0, offset_y=0.0):
    duplicated = dict(layer)  # Dict copy
    duplicated['instances'] = []
    for inst in layer.get('instances', []):
        inst_copy = dict(inst)  # Deep copy instances
        inst_copy['pos_x'] += offset_x
        duplicated['instances'].append(inst_copy)
    return duplicated
```

#### 4. Split/Merge Operations (Lines 200-400+)
```python
def split_layer_instances(layer):
    # Creates multiple layer dicts from one
    instances = layer.get('instances', [])
    new_layers = []
    for inst in instances:
        new_layer = dict(layer)
        new_layer['instances'] = [dict(inst)]
        new_layers.append(new_layer)
    return new_layers

def merge_layers_as_instances(layers, use_topmost_properties=False):
    # Merges layer dicts
    merged = dict(layers[0])
    merged['instances'] = []
    for layer in layers:
        merged['instances'].extend(layer.get('instances', []))
    return merged
```

**Total Dictionary Patterns:** 100+ occurrences

---

## FILE: editor\src\services\file_operations.py

**Status:** HIGH - File I/O still works with dicts

### Critical Issues:

#### 1. Build CoA for Save (Lines 58-136)
```python
def build_coa_for_save(base_colors, base_texture, layers, base_color_names):
    # layers parameter is list of dicts
    for depth_index, layer in enumerate(layers):
        texture = layer.get('filename', layer.get('path', ''))
        instances = []
        for inst in layer.get('instances', []):
            instance = {
                "position": [inst.get('pos_x', 0.5), inst.get('pos_y', 0.5)],
                "scale": [scale_x, scale_y],
                "rotation": int(inst.get('rotation', 0))
            }
            instances.append(instance)
```

#### 2. Clipboard Operations (Lines 138-200+)
```python
def build_coa_for_clipboard(base_colors, base_texture, layers, base_color_names):
    # Same pattern - expects layer dicts
    for layer in layers:
        instances = layer.get('instances', [])
```

#### 3. Layer Subblock Detection (Lines 210-250+)
```python
def is_layer_subblock(text):
    # Parses to dict
    return 'texture' in parsed_data and 'instance' in parsed_data
```

**Total Dictionary Patterns:** 60+ occurrences

---

## FILE: editor\src\services\coa_serializer.py

**Status:** HIGH - Serialization creates dicts

### Critical Issues:

#### 1. Extract Emblem Layers (Lines 89-160)
```python
def extract_emblem_layers(coa):
    # Creates layer dicts from parsed CoA
    emblem_instances = []
    for emblem in coa.get('colored_emblem', []):
        for instance in instances:
            layer_data = {
                'filename': filename,
                'path': filename,
                'colors': color_count,
                'pos_x': instance.get('position', [0.5, 0.5])[0],
                'pos_y': instance.get('position', [0.5, 0.5])[1],
                'scale_x': abs(scale_x_raw),
                'scale_y': abs(scale_y_raw),
                'flip_x': scale_x_raw < 0,
                'flip_y': scale_y_raw < 0,
                'rotation': instance.get('rotation', 0),
                'color1': color_name_to_rgb(color1_name),
                'color2': color_name_to_rgb(color2_name),
                'color3': color_name_to_rgb(color3_name),
                'color1_name': color1_name,
                'color2_name': color2_name,
                'color3_name': color3_name,
                'depth': depth
            }
            emblem_instances.append(layer_data)
    return emblem_instances
```

#### 2. Parse CoA for Editor (Lines 170-230)
```python
def parse_coa_for_editor(coa_data):
    # Returns dict structure with layer dicts
    layers = extract_emblem_layers(coa)
    # Migrate to instances format
    for layer in layers:
        _migrate_layer_to_instances(layer)
    return {
        'base': base_data,
        'layers': layers  # List of dicts
    }
```

**Total Dictionary Patterns:** 40+ occurrences

---

## FILE: editor\src\utils\coa_parser.py

**Status:** MODERATE - Parser outputs dict structure (may be OK)

### Issues:
- Parser creates dict representation of CK3 file format
- This might be fine as an intermediate format
- Main issue is that these dicts propagate to UI layer

**Total Dictionary Patterns:** 30+ occurrences

---

## FILE: editor\src\actions\layer_transform_actions.py

**Status:** HIGH - Transform actions work on layer dicts

### Critical Issues:

#### 1. All Transform Methods
```python
def flip_x(self):
    for idx in selected_indices:
        layer = self.main_window.right_sidebar.layers[idx]
        layer['flip_x'] = not layer.get('flip_x', False)

def align_layers(self, alignment):
    for idx in selected_indices:
        layer = layers[idx]
        instances = layer.get('instances', [])
        for inst in instances:
            inst['pos_x'] = aligned_x
            inst['pos_y'] = aligned_y
```

**Total Dictionary Patterns:** 50+ occurrences

---

## FILE: editor\src\actions\clipboard_actions.py

**Status:** MODERATE - Clipboard ops use dicts

### Issues:
- Serializes layer dicts to text
- Parses text back to layer dicts

**Total Dictionary Patterns:** 20+ occurrences

---

## MIGRATION PRIORITY

### Phase 1: CRITICAL (Blocks progress)
1. **property_sidebar.py** - Switch `self.layers` from dict list to use CoA model
2. **main.py** - Remove all Layer-to-dict conversions
3. **services/layer_operations.py** - Update to work with Layer objects

### Phase 2: HIGH (Major functionality)
4. **canvas_widget.py** - Accept Layer objects instead of dicts
5. **layer_list_widget.py** - Update UI to work with Layer objects
6. **file_operations.py** - Build save data from Layer objects

### Phase 3: MEDIUM (Actions and utilities)
7. **layer_transform_actions.py** - Operate on Layer objects
8. **canvas_area.py** - Update transform handlers
9. **clipboard_actions.py** - Serialize/deserialize Layer objects

### Phase 4: LOW (Parsing layer - maybe keep as-is)
10. **coa_serializer.py** - Consider if dict output is acceptable
11. **coa_parser.py** - Parser can stay dict-based as intermediate format

---

## TOTAL STATISTICS

- **Total Files Analyzed:** 12
- **Files with Dictionary Patterns:** 12 (100%)
- **Estimated Total Dictionary Patterns:** 900+
- **Critical Files Needing Immediate Attention:** 5
  - main.py
  - property_sidebar.py
  - services/layer_operations.py
  - canvas_widget.py
  - layer_list_widget.py

---

## RECOMMENDED APPROACH

1. **Start with data model**: Ensure CoA model has all needed Layer methods
2. **Update property_sidebar.py**: Store reference to CoA, not layer list
3. **Update main.py**: Remove all dict conversions
4. **Update services**: Work with Layer objects
5. **Update UI components**: Accept Layer objects
6. **Update actions**: Operate on Layer objects via CoA model
7. **Keep parsers**: File I/O can use dicts as intermediate format

---

## NOTES

- The CoA model exists but is barely used
- Most code still operates on the old dict-based layer system
- There's a "bridge" layer converting between CoA objects and dicts
- This bridge needs to be eliminated for the refactor to complete
- The instance-based system (multi-instance layers) is also dict-based and needs migration

**Status:** This is a MASSIVE refactor that's about 10% complete. The CoA model is implemented but not integrated.
