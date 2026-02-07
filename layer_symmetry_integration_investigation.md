# Layer Symmetry System - Integration Investigation Report

**Purpose:** Feasibility investigation ("dry run") to verify all integration points for the layer symmetry system implementation without writing code.

**Date:** January 2025  
**Status:** ✅ FEASIBLE - All integration points verified

---

## Executive Summary

✅ **Implementation is architecturally feasible** - no blocking issues discovered.

All critical integration points have been identified and verified:
1. **Layer Model** - Property storage pattern confirmed
2. **PropertySidebar UI** - Widget insertion point identified
3. **Canvas Rendering** - Instance loop extension approach verified
4. **Export/Import** - Serialization hooks located
5. **History Management** - Snapshot mechanism confirmed
6. **Layer Operations** - Operation hooks identified

---

## Integration Point 1: Layer Model (CoA/Layer)

### Location
- **File:** `editor/src/models/coa/_internal/layer.py`
- **Class:** `Layer` (line 139+)

### Current Architecture
```python
class Layer:
    def __init__(self, data: Optional[Dict] = None, caller: str = 'unknown'):
        self._data = data if data is not None else self._create_default()
        # _data stores: uuid, filename, colors, instances, color1/2/3, mask, etc.
    
    @property
    def color1(self) -> List[int]:
        return self._data.get('color1', [255, 255, 0])
    
    @color1.setter
    def color1(self, value: List[int]):
        self._data['color1'] = value
```

### Integration Pattern
**Add symmetry properties to `_data` dict following existing pattern:**

```python
# In Layer._create_default():
{
    'uuid': str(uuid_module.uuid4()),
    'filename': '',
    'colors': 3,
    'instances': [Instance()],
    'color1': [...],
    'mask': None,
    # NEW PROPERTIES:
    'symmetry_type': 'none',  # "none" | "bisector" | "rotational" | "grid"
    'symmetry_properties': []  # List[float] - type-specific parameters
}

# Add property decorators:
@property
def symmetry_type(self) -> str:
    return self._data.get('symmetry_type', 'none')

@symmetry_type.setter
def symmetry_type(self, value: str):
    self._data['symmetry_type'] = value

@property
def symmetry_properties(self) -> List[float]:
    return self._data.get('symmetry_properties', [])

@symmetry_properties.setter
def symmetry_properties(self, value: List[float]):
    self._data['symmetry_properties'] = value
```

### CoA Model Methods Needed
**Add to `models/coa/layer_mixin.py` (CoALayerMixin class):**

```python
def get_layer_symmetry_type(self, uuid: str) -> str:
    """Get layer symmetry type"""
    layer = self.get_layer_by_uuid(uuid)
    return layer.symmetry_type if layer else 'none'

def set_layer_symmetry_type(self, uuid: str, symmetry_type: str):
    """Set layer symmetry type"""
    layer = self.get_layer_by_uuid(uuid)
    if layer:
        layer.symmetry_type = symmetry_type

def get_layer_symmetry_properties(self, uuid: str) -> List[float]:
    """Get layer symmetry properties"""
    layer = self.get_layer_by_uuid(uuid)
    return layer.symmetry_properties if layer else []

def set_layer_symmetry_properties(self, uuid: str, properties: List[float]):
    """Set layer symmetry properties"""
    layer = self.get_layer_by_uuid(uuid)
    if layer:
        layer.symmetry_properties = properties

def get_symmetry_transforms(self, uuid: str, seed_transform: Transform) -> List[Transform]:
    """Calculate all transforms (seed + mirrors) for symmetry rendering
    
    Args:
        uuid: Layer UUID
        seed_transform: The seed instance transform
        
    Returns:
        List of transforms: [seed, mirror1, mirror2, ...]
    """
    # Implementation generates mirror transforms based on symmetry_type
    # and symmetry_properties using geometry calculations
    pass
```

**Status:** ✅ **CONFIRMED FEASIBLE**  
- Property storage pattern matches existing properties (color1, flip_x, mask)
- Property decorators follow established convention
- CoA methods fit naturally into existing layer_mixin structure

---

## Integration Point 2: PropertySidebar UI

### Location
- **File:** `editor/src/components/property_sidebar.py`
- **Class:** `PropertySidebar`
- **Method:** `_create_properties_tab()` (line 374+)

### Current Architecture
```python
def _create_properties_tab(self):
    # Create scrollable content area
    scroll_area = QScrollArea()
    scroll_widget = QWidget()
    self.content_layout = QVBoxLayout(scroll_widget)  # <-- Insertion point
    
    # Instance section (lines 397-437)
    instance_label = QLabel("Instance")
    self.content_layout.addWidget(instance_label)
    # ... PropertySlider widgets ...
    
    # Properties section (lines 439-465)
    props_label = QLabel("Properties")
    self.content_layout.addWidget(props_label)
    # ... color pickers, flip checkboxes ...
    
    # Pattern Mask section (lines 467-507)
    mask_label = QLabel("Pattern Mask")
    self.content_layout.addWidget(mask_label)
    # ... mask controls ...
    
    # <<< INSERTION POINT: Line 507+ >>>
    # Add symmetry section here:
    #   - Symmetry dropdown (None, Bisector, Rotational, Grid)
    #   - Dynamic widget container
    #   - Load/unload type-specific widgets based on dropdown selection
```

### Integration Pattern
**Insert after mask section (line 507+):**

```python
# Symmetry Section
symmetry_label = QLabel("Symmetry")
self.content_layout.addWidget(symmetry_label)

# Symmetry type dropdown
self.symmetry_dropdown = QComboBox()
self.symmetry_dropdown.addItems(["None", "Bisector", "Rotational", "Grid"])
self.symmetry_dropdown.currentTextChanged.connect(self._on_symmetry_type_changed)
self.content_layout.addWidget(self.symmetry_dropdown)

# Dynamic widget container
self.symmetry_widget_container = QWidget()
self.symmetry_widget_layout = QVBoxLayout(self.symmetry_widget_container)
self.content_layout.addWidget(self.symmetry_widget_container)

# Current active symmetry widget
self.active_symmetry_widget = None
```

### Widget Loading Pattern
**Follow generator settings pattern:**

```python
def _on_symmetry_type_changed(self, symmetry_type: str):
    # Unload current widget
    if self.active_symmetry_widget:
        self.symmetry_widget_layout.removeWidget(self.active_symmetry_widget)
        self.active_symmetry_widget.deleteLater()
        self.active_symmetry_widget = None
    
    # Load new widget based on type
    if symmetry_type == "Bisector":
        from components.symmetry.bisector_widget import BisectorSymmetryWidget
        self.active_symmetry_widget = BisectorSymmetryWidget(self.main_window)
        self.symmetry_widget_layout.addWidget(self.active_symmetry_widget)
    elif symmetry_type == "Rotational":
        from components.symmetry.rotational_widget import RotationalSymmetryWidget
        self.active_symmetry_widget = RotationalSymmetryWidget(self.main_window)
        self.symmetry_widget_layout.addWidget(self.active_symmetry_widget)
    elif symmetry_type == "Grid":
        from components.symmetry.grid_widget import GridSymmetryWidget
        self.active_symmetry_widget = GridSymmetryWidget(self.main_window)
        self.symmetry_widget_layout.addWidget(self.active_symmetry_widget)
```

### Widget Files to Create
- `editor/src/components/symmetry/bisector_widget.py` - Mode radio + rotation slider
- `editor/src/components/symmetry/rotational_widget.py` - Count spinner + kaleidoscope checkbox
- `editor/src/components/symmetry/grid_widget.py` - Count X/Y spinners + fill dropdown

**Status:** ✅ **CONFIRMED FEASIBLE**  
- Clear insertion point identified (after mask section)
- Dynamic widget loading follows generator pattern
- content_layout.addWidget() is standard approach

---

## Integration Point 3: Canvas Rendering

### Location
- **File:** `editor/src/components/canvas_rendering_mixin.py`
- **Method:** `_render_layer_instances()` (line 185+)

### Current Architecture
```python
def _render_layer_instances(self, coa, layer_uuid, gl, shader, texture_id):
    """Render all instances of a layer"""
    
    # Get instance count and loop through stored instances
    instance_count = coa.get_layer_instance_count(layer_uuid)
    
    for instance_idx in range(instance_count):  # <-- MODIFICATION POINT
        # Get instance transform
        instance = coa.get_layer_instance(layer_uuid, instance_idx)
        
        # Apply position, scale, rotation to shader uniforms
        rotation_rad = math.radians(-instance.rotation)
        scale_x = -instance.scale.x if instance.flip_x else instance.scale.x
        scale_y = -instance.scale.y if instance.flip_y else instance.scale.y
        
        # Set uniforms and draw
        gl.glUniform2f(pos_loc, instance.pos.x, instance.pos.y)
        gl.glUniform2f(scale_loc, scale_x, scale_y)
        gl.glUniform1f(rotation_loc, rotation_rad)
        gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
```

### Integration Pattern
**Modify instance loop to render seeds + calculated mirrors:**

```python
def _render_layer_instances(self, coa, layer_uuid, gl, shader, texture_id):
    """Render all instances of a layer (including symmetry mirrors)"""
    
    # Get symmetry type
    symmetry_type = coa.get_layer_symmetry_type(layer_uuid)
    
    if symmetry_type == 'none':
        # Original behavior: render only stored instances
        instance_count = coa.get_layer_instance_count(layer_uuid)
        for instance_idx in range(instance_count):
            instance = coa.get_layer_instance(layer_uuid, instance_idx)
            self._render_single_instance(gl, shader, instance)
    else:
        # NEW behavior: render seeds + calculated mirrors
        instance_count = coa.get_layer_instance_count(layer_uuid)
        
        for instance_idx in range(instance_count):
            # Get seed instance
            seed_instance = coa.get_layer_instance(layer_uuid, instance_idx)
            
            # Get all transforms (seed + mirrors)
            seed_transform = Transform(seed_instance.pos, seed_instance.scale, 
                                       seed_instance.rotation)
            all_transforms = coa.get_symmetry_transforms(layer_uuid, seed_transform)
            
            # Render each transform
            for transform in all_transforms:
                # Create temporary instance-like object for rendering
                temp_instance = Instance({
                    'pos_x': transform.pos.x,
                    'pos_y': transform.pos.y,
                    'scale_x': transform.scale.x,
                    'scale_y': transform.scale.y,
                    'rotation': transform.rotation,
                    'flip_x': seed_instance.flip_x,
                    'flip_y': seed_instance.flip_y
                })
                self._render_single_instance(gl, shader, temp_instance)

def _render_single_instance(self, gl, shader, instance):
    """Render a single instance (extracted for reuse)"""
    rotation_rad = math.radians(-instance.rotation)
    scale_x = -instance.scale.x if instance.flip_x else instance.scale.x
    scale_y = -instance.scale.y if instance.flip_y else instance.scale.y
    
    gl.glUniform2f(pos_loc, instance.pos.x, instance.pos.y)
    gl.glUniform2f(scale_loc, scale_x, scale_y)
    gl.glUniform1f(rotation_loc, rotation_rad)
    gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
```

### Visual Indicators
**Add paintGL overlay for symmetry axes/lines:**

```python
# In canvas_widget.py paintGL() method (after OpenGL rendering):
def paintGL(self):
    # ... existing OpenGL rendering ...
    
    # Draw symmetry visual indicators (Qt overlay)
    painter = QPainter(self)
    painter.setRenderHint(QPainter.Antialiasing)
    
    coa = self.main_window.coa
    if coa:
        selected_uuids = self.main_window.left_sidebar.layer_list_widget.get_selected_layer_uuids()
        for layer_uuid in selected_uuids:
            symmetry_type = coa.get_layer_symmetry_type(layer_uuid)
            if symmetry_type != 'none':
                self._draw_symmetry_indicators(painter, layer_uuid)
    
    painter.end()

def _draw_symmetry_indicators(self, painter, layer_uuid):
    """Draw symmetry axes/lines as Qt overlay"""
    symmetry_type = self.main_window.coa.get_layer_symmetry_type(layer_uuid)
    
    if symmetry_type == 'bisector':
        # Draw mirror line(s)
        pen = QPen(QColor(0, 255, 0, 128), 2, Qt.DashLine)
        painter.setPen(pen)
        # ... draw mirror line based on rotation_offset ...
    
    elif symmetry_type == 'rotational':
        # Draw rotation center + radial lines
        pen = QPen(QColor(0, 200, 255, 128), 2, Qt.DashLine)
        painter.setPen(pen)
        # ... draw center dot + radial lines ...
    
    elif symmetry_type == 'grid':
        # Draw grid cell boundaries
        pen = QPen(QColor(255, 200, 0, 128), 1, Qt.DotLine)
        painter.setPen(pen)
        # ... draw grid lines ...
```

**Status:** ✅ **CONFIRMED FEASIBLE**  
- Instance loop structure allows clean extension
- Extract _render_single_instance() for reuse with calculated mirrors
- Qt paintGL overlay for visual indicators follows existing pattern

---

## Integration Point 4: Export/Import (Serialization)

### Location
- **File:** `editor/src/models/coa/_internal/layer.py`
- **Method:** `Layer.serialize()` (line 650+)

### Current Architecture
```python
def serialize(self, caller: str = 'unknown') -> str:
    """Serialize layer to Clausewitz format"""
    
    lines = []
    lines.append('\tcolored_emblem = {')
    
    # Write metadata as special comments
    if self.container_uuid:
        lines.append(f'\t\t##META##container_uuid="{self.container_uuid}"')
    lines.append(f'\t\t##META##name="{self.name}"')
    
    # Write texture and colors
    lines.append(f'\t\ttexture = "{self.filename}"')
    lines.append(f'\t\tcolor1 = {format_color(...)}')
    # ...
    
    # Serialize mask if present
    if self.mask is not None:
        mask_str = ' '.join(map(str, self.mask))
        lines.append(f'\t\tmask = {{ {mask_str} }}')
    
    # Serialize all instances
    instances = self._data.get('instances', [])
    for inst in instances:
        if isinstance(inst, Instance):
            lines.append(inst.serialize())  # Writes instance { ... }
    
    lines.append('\t}')
    return '\n'.join(lines)
```

### Integration Pattern - Export (Write Meta Tags)
**Add symmetry metadata before instances:**

```python
def serialize(self, caller: str = 'unknown') -> str:
    """Serialize layer to Clausewitz format"""
    
    lines = []
    lines.append('\tcolored_emblem = {')
    
    # Existing metadata
    if self.container_uuid:
        lines.append(f'\t\t##META##container_uuid="{self.container_uuid}"')
    lines.append(f'\t\t##META##name="{self.name}"')
    
    # NEW: Symmetry metadata
    if self.symmetry_type != 'none':
        lines.append(f'\t\t##META##symmetry_type="{self.symmetry_type}"')
        # Format properties as space-separated list
        props_str = ' '.join(map(str, self.symmetry_properties))
        lines.append(f'\t\t##META##symmetry_properties={{{props_str}}}')
    
    # Mark seeds vs mirrors
    for idx, inst in enumerate(instances):
        is_seed = (idx < original_instance_count)  # Seeds are first N instances
        if is_seed and self.symmetry_type != 'none':
            lines.append(f'\t\t##META##symmetry_seed=true')
        elif not is_seed:
            lines.append(f'\t\t##META##mirrored=true')
        
        lines.append(inst.serialize())
    
    lines.append('\t}')
    return '\n'.join(lines)
```

### Integration Pattern - Import (Parse Meta Tags)
**Strip mirrors and restore symmetry properties:**

```python
@classmethod
def parse(cls, data: Dict[str, Any], caller: str = 'unknown', 
          regenerate_uuid: bool = False) -> 'Layer':
    """Parse layer from Clausewitz parser output"""
    
    # Parse symmetry metadata
    symmetry_type = data.get('symmetry_type', 'none')
    symmetry_properties = data.get('symmetry_properties', [])
    
    # Filter instances: keep only seeds (marked with symmetry_seed=true)
    instances_data = data.get('instance', [])
    if symmetry_type != 'none':
        # Keep only instances marked as seeds
        seed_instances = [inst for inst in instances_data 
                         if inst.get('symmetry_seed', False)]
        instances_data = seed_instances if seed_instances else instances_data[:1]
    
    # Convert to Instance objects
    instances = [Instance.parse(inst_data) for inst_data in instances_data]
    
    layer_data = {
        'uuid': layer_uuid,
        # ... existing properties ...
        'symmetry_type': symmetry_type,
        'symmetry_properties': symmetry_properties,
        'instances': instances
    }
    
    return Layer(layer_data, caller=caller)
```

### Parser Integration
**File:** `editor/src/models/coa/_internal/coa_parser.py`

```python
class CoAParser:
    def _parse_colored_emblem(self, data: Dict) -> Dict:
        """Parse colored_emblem block"""
        result = {}
        
        # Extract ##META## comments
        for key, value in data.items():
            if key.startswith('##META##'):
                meta_key = key.replace('##META##', '')
                result[meta_key] = value
        
        # ... existing parsing (texture, colors, instances) ...
        
        return result
```

**Status:** ✅ **CONFIRMED FEASIBLE**  
- Meta tag pattern already used for container_uuid and name
- Layer.serialize() easily extended to write symmetry metadata
- Layer.parse() can filter seed instances using meta tags
- CoAParser already handles ##META## comments

---

## Integration Point 5: History Management

### Location
- **File:** `editor/src/utils/history_manager.py`
- **Class:** `HistoryManager`

### Current Architecture
```python
class HistoryManager:
    def save_state(self, state_data, description=""):
        """Save a new state to history"""
        snapshot = {
            'data': copy.deepcopy(state_data),  # <-- Full state snapshot
            'description': description
        }
        self.history.append(snapshot)
        self.current_index += 1
    
    def undo(self):
        """Move back one state in history"""
        if not self.can_undo():
            return None
        self.current_index -= 1
        state = self.history[self.current_index]['data']
        return copy.deepcopy(state)
```

### Integration Pattern
**Symmetry properties automatically captured in layer snapshots:**

```python
# In actions that modify symmetry settings:
def set_layer_symmetry(self, layer_uuid, symmetry_type, properties):
    # Save state BEFORE modification
    self.main_window.history_manager.save_state(
        self.main_window.coa.get_snapshot(),
        f"Change symmetry: {symmetry_type}"
    )
    
    # Modify symmetry properties
    self.main_window.coa.set_layer_symmetry_type(layer_uuid, symmetry_type)
    self.main_window.coa.set_layer_symmetry_properties(layer_uuid, properties)
    
    # Update UI
    self.main_window.update_canvas()
```

### CoA Snapshot Method
**File:** `editor/src/models/coa/serialization_mixin.py`

```python
class CoASerializationMixin:
    def get_snapshot(self) -> Dict:
        """Get complete state snapshot (for undo)"""
        return {
            'pattern': self._pattern,
            'pattern_color1': self._pattern_color1,
            # ... all pattern properties ...
            'layers': [layer.to_dict(caller='CoA') for layer in self._layers],
            # ↑ Layer.to_dict() includes symmetry_type and symmetry_properties
            'selected_uuids': list(self._selected_layer_uuids)
        }
    
    def set_snapshot(self, snapshot: Dict):
        """Restore state from snapshot (for undo)"""
        self._pattern = snapshot['pattern']
        # ... restore all pattern properties ...
        
        # Restore layers (symmetry properties included in layer dicts)
        self._layers.clear()
        for layer_dict in snapshot['layers']:
            self._layers.append(Layer(layer_dict, caller='CoA'))
        
        self._selected_layer_uuids = set(snapshot.get('selected_uuids', []))
```

**Status:** ✅ **CONFIRMED FEASIBLE**  
- Layer.to_dict() automatically includes all _data properties
- Symmetry properties (symmetry_type, symmetry_properties) captured in snapshots
- No special handling required - standard snapshot mechanism works

---

## Integration Point 6: Layer Operations

### Location
- **File:** `editor/src/models/coa/layer_mixin.py`
- **Methods:** `duplicate_layer()`, `merge_layers()`, `split_layer()`

### Current Architecture
```python
class CoALayerMixin:
    def duplicate_layer(self, uuid: str) -> str:
        """Duplicate a layer with new UUID"""
        layer = self.get_layer_by_uuid(uuid)
        if not layer:
            return ""
        
        # Layer.duplicate() creates deep copy with new UUID
        duplicated = layer.duplicate(caller='CoA', offset_x=0.02, offset_y=0.02)
        # ↑ Automatically copies ALL _data properties including symmetry
        
        self._layers.append(duplicated)
        return duplicated.uuid
```

### Integration Pattern - Duplicate
**Symmetry properties automatically preserved:**

```python
# In Layer.duplicate():
def duplicate(self, caller: str = 'unknown', offset_x: float = 0.0, 
              offset_y: float = 0.0) -> 'Layer':
    """Create duplicate with new UUID"""
    import copy
    duplicated = copy.deepcopy(self._data)
    # ↑ symmetry_type and symmetry_properties copied automatically
    
    duplicated['uuid'] = str(uuid_module.uuid4())
    
    # Apply offset to instances
    for inst in duplicated['instances']:
        if isinstance(inst, Instance):
            inst.pos = Vec2(inst.pos.x + offset_x, inst.pos.y + offset_y)
    
    return Layer(duplicated, caller=caller)
```

### Integration Pattern - Merge
**Handle symmetry during merge:**

```python
def merge_layers(self, uuids: List[str]) -> str:
    """Merge multiple layers into one multi-instance layer"""
    
    # Check if all layers have same symmetry settings
    first_layer = self.get_layer_by_uuid(uuids[0])
    symmetry_type = first_layer.symmetry_type
    symmetry_properties = first_layer.symmetry_properties
    
    has_mixed_symmetry = False
    for uuid in uuids[1:]:
        layer = self.get_layer_by_uuid(uuid)
        if (layer.symmetry_type != symmetry_type or 
            layer.symmetry_properties != symmetry_properties):
            has_mixed_symmetry = True
            break
    
    if has_mixed_symmetry:
        # Option 1: Reset to 'none' with warning
        self._logger.warning("Merging layers with different symmetry - resetting to none")
        first_layer.symmetry_type = 'none'
        first_layer.symmetry_properties = []
        
        # Option 2: Show dialog to user asking which symmetry to keep
        # (Implement in UI action layer)
    
    # Merge instances from other layers
    for layer in layers[1:]:
        for i in range(layer.instance_count):
            instance = layer.get_instance(i, caller='CoA')
            first_layer.add_instance(instance.pos.x, instance.pos.y, caller='CoA')
            # ... copy other properties ...
    
    # Remove other layers
    for uuid in uuids[1:]:
        self.remove_layer(uuid)
    
    return first_layer.uuid
```

### Integration Pattern - Split
**Create new layer with same symmetry:**

```python
def split_layer(self, uuid: str, instance_indices: List[int]) -> str:
    """Split instances into new layer"""
    
    original_layer = self.get_layer_by_uuid(uuid)
    if not original_layer:
        return ""
    
    # Create new layer with same properties INCLUDING symmetry
    new_layer_data = {
        'uuid': str(uuid_module.uuid4()),
        'filename': original_layer.filename,
        'colors': original_layer.colors,
        'color1': original_layer.color1,
        'color2': original_layer.color2,
        'color3': original_layer.color3,
        'mask': original_layer.mask,
        'symmetry_type': original_layer.symmetry_type,  # Preserve symmetry
        'symmetry_properties': list(original_layer.symmetry_properties),  # Copy list
        'instances': []
    }
    
    # Move specified instances to new layer
    for idx in sorted(instance_indices, reverse=True):
        instance = original_layer.get_instance(idx, caller='CoA')
        new_layer_data['instances'].append(instance)
        original_layer.remove_instance(idx, caller='CoA')
    
    new_layer = Layer(new_layer_data, caller='CoA')
    self._layers.append(new_layer)
    
    return new_layer.uuid
```

**Status:** ✅ **CONFIRMED FEASIBLE**  
- Duplicate: deepcopy automatically includes symmetry properties
- Merge: Can check for mixed symmetry and handle appropriately
- Split: Explicitly copy symmetry settings to new layer
- Operations follow existing patterns with minimal additions

---

## Summary of Findings

### ✅ No Blocking Issues Discovered

All integration points confirmed feasible:

| Integration Point | Status | Complexity | Notes |
|-------------------|--------|------------|-------|
| **Layer Model** | ✅ Feasible | Low | Add 2 properties to _data dict + property decorators |
| **PropertySidebar UI** | ✅ Feasible | Medium | Insert after mask section, dynamic widget loading |
| **Canvas Rendering** | ✅ Feasible | Medium | Extend instance loop, add QPainter overlay |
| **Export/Import** | ✅ Feasible | Low | Meta tags already used, strip mirrors on import |
| **History Management** | ✅ Feasible | Low | Automatic - snapshot includes all _data properties |
| **Layer Operations** | ✅ Feasible | Low | deepcopy handles symmetry, merge needs logic |

### Key Architectural Patterns Confirmed

1. **Property Storage:** Layer._data dict with @property decorators
2. **UI Widgets:** content_layout.addWidget() with dynamic loading/unloading
3. **Rendering:** Instance loop extension + Qt paintGL overlay
4. **Serialization:** ##META## comment tags for editor-specific data
5. **History:** CoA.get_snapshot() includes all layer properties automatically
6. **Operations:** deepcopy preserves properties, explicit handling for merge/split

### Implementation Readiness

**Ready to Proceed with Implementation Checklist:**

✅ **Phase 1 (CoA Model)** - Integration pattern verified  
✅ **Phase 2 (PropertySidebar UI)** - Insertion point identified  
✅ **Phase 3 (Canvas Rendering)** - Extension approach confirmed  
✅ **Phase 4 (Export/Import)** - Meta tag handling located  
✅ **Phase 5 (Layer Operations)** - Operation hooks identified  
✅ **Phase 6 (History)** - Snapshot mechanism confirmed  

**No architectural changes needed** - all features integrate cleanly with existing patterns.

---

## Code Locations Reference

### Files to Modify
- `editor/src/models/coa/_internal/layer.py` - Add symmetry properties
- `editor/src/models/coa/layer_mixin.py` - Add symmetry CoA methods
- `editor/src/components/property_sidebar.py` - Add symmetry UI section (line 507+)
- `editor/src/components/canvas_rendering_mixin.py` - Extend instance rendering (line 185+)
- `editor/src/components/canvas_widget.py` - Add symmetry visual indicators (paintGL)

### Files to Create
- `editor/src/components/symmetry/bisector_widget.py` - Bisector UI
- `editor/src/components/symmetry/rotational_widget.py` - Rotational UI
- `editor/src/components/symmetry/grid_widget.py` - Grid UI
- `editor/src/services/symmetry_calculator.py` - Geometry calculations

### Files Requiring No Changes
- `editor/src/utils/history_manager.py` - Works automatically
- `editor/src/models/coa/serialization_mixin.py` - get_snapshot() includes symmetry
- `editor/src/models/coa/_internal/coa_parser.py` - Already handles ##META## tags

---

## Conclusion

**Implementation is architecturally sound and ready to proceed.**

All integration points have been verified, code locations identified, and patterns confirmed. The layer symmetry system fits naturally into the existing codebase architecture without requiring fundamental changes.

**Recommendation:** Proceed with Phase 1 (CoA Model) implementation as outlined in `layer_symmetry_implementation_checklist.md`.
