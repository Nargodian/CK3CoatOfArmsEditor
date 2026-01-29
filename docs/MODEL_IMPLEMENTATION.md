# CK3 CoA Editor - Model Layer Implementation

## Summary

Successfully implemented the complete **MODEL layer** for the CK3 Coat of Arms Editor following MVC architecture principles. This is a **standalone implementation** (not integrated with the existing codebase) with comprehensive unit tests.

## Components Created

### 1. Layer Model (`editor/src/models/layer.py`)
- **Layer class**: Object-oriented wrapper for layer data
  - UUID-based identification (stable across reordering)
  - Instance-aware property access
  - Auto-migration from old format to instances format
  - Method call tracking for debugging
  
- **Layers class**: Collection container for multiple layers
  - List-like access (indexing, iteration, len)
  - Layer management (add, remove, move)
  - UUID-based lookups (`get_by_uuid()`, `get_index_by_uuid()`)
  - Batch operations
  
- **LayerTracker class**: Debugging/accountability system
  - Caller registration
  - Method call logging
  - Filtered log retrieval

### 2. CoA Model (`editor/src/models/coa.py`)
**THE MODEL** in MVC architecture - owns all CoA data and operations.

#### Core Responsibilities:
- **State Management**: Base pattern, colors, layers collection
- **Layer Operations**: Add, remove, move, duplicate, merge, split
- **Instance Operations**: Add/remove/select instances per layer
- **Transform Operations**: Single-layer and multi-layer group transforms
- **Color Operations**: Set layer and base colors
- **Query API**: Provides data access for UI (no direct data exposure)
- **Snapshot API**: Get/set state for undo/redo support
- **Serialization**: CK3 format import/export (to_string implemented, from_string placeholder)

#### Key Features:
- **UUID-Based Layer Identification**: Stable across layer reordering
- **Group Transform Math**: AABB calculations, ferris wheel rotation
- **Merge Strategy**: First UUID kept, instances combined
- **Split Strategy**: Creates new UUID per instance
- **Snapshot Support**: Serializable dict for undo/redo
- **No UI Dependencies**: Pure data model, no Qt imports
- **No Selection State**: Selection managed by EditorState (separate concern)

### 3. Unit Tests

#### Layer Tests (`tests/test_layer.py`)
- 34 tests covering:
  - UUID generation and persistence
  - Layer property access (instance and shared)
  - Instance management
  - Auto-migration from old format
  - Layers collection operations
  - LayerTracker logging

#### CoA Tests (`tests/test_coa.py`)
- 61 tests covering:
  - Pattern and color properties
  - Layer management (add, remove, move, duplicate, merge, split)
  - Instance management
  - Single-layer transforms (position, scale, rotation, flip)
  - Multi-layer group transforms (translate, scale, ferris wheel rotation)
  - Color operations
  - Query API (properties, bounds, UUIDs)
  - Snapshot API (get/set, undo scenarios)
  - Serialization (to_string)
  - Helper methods (rotation math, bounds calculation)

**Total: 95 tests, all passing**

## Architecture Design

### MVC Separation
```
┌─────────────┐
│   MODEL     │  CoA class (this implementation)
│             │  - Owns all data
│             │  - Provides operation API
│             │  - No UI logic
└─────────────┘
      ↕
┌─────────────┐
│ CONTROLLER  │  (Not implemented - future integration)
│             │  - Handles user input
│             │  - Calls model methods
│             │  - Updates EditorState
└─────────────┘
      ↕
┌─────────────┐
│    VIEW     │  (Not implemented - future integration)
│             │  - Displays data from model
│             │  - Uses query API
│             │  - No direct data access
└─────────────┘
```

### State Management
```
CoA Model (owns data):
- Pattern and colors
- Layers collection
- Layer properties
- Instances

EditorState (separate, not implemented):
- Selected layer UUIDs
- Undo/redo stack (using CoA snapshots)
- UI state (zoom, pan, etc.)
```

## API Overview

### CoA Model Methods

#### Layer Management
```python
add_layer(emblem_path, pos_x, pos_y, colors) -> uuid
remove_layer(uuid)
move_layer(uuid, to_index)
duplicate_layer(uuid) -> new_uuid
merge_layers(uuids) -> first_uuid
split_layer(uuid) -> [new_uuids]
```

#### Instance Management
```python
add_instance(uuid, pos_x, pos_y) -> index
remove_instance(uuid, instance_index)
select_instance(uuid, instance_index)
```

#### Transform Operations (Single Layer)
```python
set_layer_position(uuid, x, y)
translate_layer(uuid, dx, dy)
set_layer_scale(uuid, scale_x, scale_y)
scale_layer(uuid, factor_x, factor_y)
set_layer_rotation(uuid, degrees)
rotate_layer(uuid, delta_degrees)
flip_layer(uuid, flip_x, flip_y)
```

#### Transform Operations (Multi-Layer Group)
```python
translate_layers_group(uuids, dx, dy)
scale_layers_group(uuids, factor, around_center)
rotate_layers_group(uuids, delta_degrees)  # Ferris wheel
```

#### Color Operations
```python
set_layer_color(uuid, color_index, rgb, name)
set_base_color(color_index, rgb, name)
```

#### Query API (for UI)
```python
get_layer_property(uuid, property_name) -> value
get_layer_bounds(uuid) -> {min_x, max_x, min_y, max_y, width, height}
get_layers_bounds(uuids) -> combined_bounds
get_all_layer_uuids() -> [uuids]
get_top_layer_uuid() -> uuid
get_bottom_layer_uuid() -> uuid
get_layer_above(uuid) -> uuid
get_layer_below(uuid) -> uuid
get_layer_count() -> int
```

#### Snapshot API (for undo/redo)
```python
get_snapshot() -> dict
set_snapshot(dict)
```

#### Serialization
```python
CoA.from_string(ck3_text) -> CoA  # Placeholder, needs parser integration
coa.to_string() -> ck3_text
```

## Usage Examples

### Basic Layer Management
```python
from models.coa import CoA

# Create CoA
coa = CoA()

# Set pattern
coa.pattern = "pattern_checked.dds"
coa.set_base_color(1, [255, 0, 0], "red")

# Add layers
uuid1 = coa.add_layer("emblem_cross.dds", pos_x=0.5, pos_y=0.5)
uuid2 = coa.add_layer("emblem_lion.dds", pos_x=0.3, pos_y=0.7)

# Transform layer
coa.set_layer_rotation(uuid1, 45.0)
coa.set_layer_scale(uuid1, 1.5, 1.5)

# Export to CK3
ck3_text = coa.to_string()
```

### Multi-Layer Group Operations
```python
# Select multiple layers
selected_uuids = [uuid1, uuid2, uuid3]

# Group transform (ferris wheel rotation)
coa.rotate_layers_group(selected_uuids, 90.0)

# Group scale around center
coa.scale_layers_group(selected_uuids, 1.5, around_center=True)
```

### Undo/Redo Support
```python
# Take snapshot before operation
snapshot = coa.get_snapshot()

# Make changes
coa.add_layer("emblem_star.dds")
coa.rotate_layer(uuid1, 45.0)

# Undo
coa.set_snapshot(snapshot)
```

### Instance Management
```python
# Add instances to create repeated pattern
uuid = coa.add_layer("emblem_flower.dds", pos_x=0.3, pos_y=0.3)
coa.add_instance(uuid, pos_x=0.7, pos_y=0.3)
coa.add_instance(uuid, pos_x=0.5, pos_y=0.7)

# Split into separate layers
new_uuids = coa.split_layer(uuid)  # Creates 3 layers, 1 instance each

# Merge back
merged_uuid = coa.merge_layers(new_uuids)  # Back to 1 layer, 3 instances
```

## Design Decisions

### 1. UUID-Based Identification
**Why**: Layer indices change when layers are reordered. UUIDs provide stable references.
**Impact**: Selection, undo, and UI can safely reference layers without tracking index changes.

### 2. Selection State Separation
**Why**: Selection is UI state, not data state. Model should be UI-agnostic.
**Impact**: EditorState (separate class) manages `selected_uuids`. Model provides UUID queries.

### 3. Snapshot API
**Why**: Clean undo/redo without model knowing about undo stack implementation.
**Impact**: EditorState manages undo stack with snapshots. Model just provides get/set_snapshot().

### 4. Group Transform Math in Model
**Why**: Complex calculations (AABB, ferris wheel) are business logic, not UI logic.
**Impact**: Model owns all transform math. Controllers just call methods with parameters.

### 5. Merge/Split UUID Strategy
**Why**: Clear ownership and minimal UUID churn.
**Impact**: Merge keeps first UUID (predictable). Split creates new UUIDs (clean separation).

### 6. No Frame Settings in Model
**Why**: Frame is UI preview concern, not part of CoA data.
**Impact**: Frame settings stay in EditorState or separate config.

## Next Steps (Future Integration)

### 1. EditorState Class
Create separate state manager:
```python
class EditorState:
    def __init__(self, coa: CoA):
        self.coa = coa
        self.selected_uuids = []
        self.undo_stack = []
        self.redo_stack = []
        self.frame = 'house'  # UI preview setting
    
    def push_undo(self):
        snapshot = self.coa.get_snapshot()
        self.undo_stack.append(snapshot)
    
    def undo(self):
        if self.undo_stack:
            current = self.coa.get_snapshot()
            self.redo_stack.append(current)
            snapshot = self.undo_stack.pop()
            self.coa.set_snapshot(snapshot)
```

### 2. Controller Integration
Update controllers to use CoA model:
```python
# In canvas_area.py (controller)
def rotate_selection(self, delta):
    if len(self.editor_state.selected_uuids) == 1:
        uuid = self.editor_state.selected_uuids[0]
        self.editor_state.push_undo()
        self.editor_state.coa.rotate_layer(uuid, delta)
    else:
        self.editor_state.push_undo()
        self.editor_state.coa.rotate_layers_group(
            self.editor_state.selected_uuids, delta
        )
    self.canvas.update()
```

### 3. View Integration
Update views to query model:
```python
# In property_sidebar.py (view)
def update_layer_properties(self, uuid):
    pos_x = self.editor_state.coa.get_layer_property(uuid, 'pos_x')
    pos_y = self.editor_state.coa.get_layer_property(uuid, 'pos_y')
    rotation = self.editor_state.coa.get_layer_property(uuid, 'rotation')
    
    self.pos_x_spinbox.setValue(pos_x)
    self.pos_y_spinbox.setValue(pos_y)
    self.rotation_slider.setValue(rotation)
```

### 4. Parser Integration
Complete CK3 format parsing:
```python
# In coa.py
@classmethod
def from_string(cls, ck3_text: str) -> 'CoA':
    from services.coa_parser import parse_coa
    
    parsed = parse_coa(ck3_text)
    coa = cls()
    
    # Set pattern
    coa.pattern = parsed['pattern']
    coa.pattern_color1 = parsed['color1']
    coa.pattern_color2 = parsed['color2']
    
    # Add layers
    for emblem in parsed['colored_emblems']:
        uuid = coa.add_layer(emblem['texture'])
        # Set colors, add instances, etc.
    
    return coa
```

## Testing Strategy

### Current Coverage
- ✅ Layer class (UUID, properties, instances, migration)
- ✅ Layers collection (operations, UUID lookups)
- ✅ LayerTracker (logging, filtering)
- ✅ CoA properties (pattern, colors)
- ✅ CoA layer management (add, remove, move, duplicate, merge, split)
- ✅ CoA instance management
- ✅ CoA transforms (single and group)
- ✅ CoA colors
- ✅ CoA query API
- ✅ CoA snapshot API
- ✅ CoA serialization (to_string)
- ✅ Helper methods (rotation math, bounds)

### Future Testing Needs
- Integration tests with EditorState
- Integration tests with controllers
- Integration tests with views
- Full parser integration tests (from_string)
- Performance tests (large CoAs with many layers)
- Snapshot serialization tests (JSON compatibility)

## Files Created

```
editor/src/models/
├── __init__.py          # Package initialization
├── layer.py             # Layer, Layers, LayerTracker classes (627 lines)
└── coa.py              # CoA model class (766 lines)

tests/
├── test_layer.py        # Layer unit tests (461 lines, 34 tests)
└── test_coa.py         # CoA unit tests (731 lines, 61 tests)
```

**Total Lines**: ~2,585 lines of heavily commented code and tests
**Test Coverage**: 95 passing tests

## Dependencies

### Required Imports
- Python standard library: `logging`, `uuid`, `math`, `copy`, `re`
- Project imports: `constants` (color definitions, defaults)

### No External Dependencies
- No Qt imports (UI-agnostic)
- No numpy/scipy (pure Python math)
- No third-party libraries

## Documentation

All code is **heavily commented** for easy review:
- Module-level docstrings explain purpose and usage
- Class docstrings detail responsibilities and properties
- Method docstrings include Args, Returns, Raises
- Complex algorithms have inline comments
- Design decisions documented in comments

## Standalone Implementation

This implementation is **NOT integrated** with existing codebase:
- Can be reviewed independently
- Can be tested in isolation
- No side effects on current functionality
- Ready for integration when approved

## Status

✅ **COMPLETE** - Ready for review
- All core functionality implemented
- All tests passing (95/95)
- Heavily commented
- Standalone (not integrated)
- Documented (this file + inline docs)

## Questions for Review

1. **UUID Strategy**: Is UUID persistence in CK3 format desired, or should UUIDs be regenerated on load?
2. **Bounds Calculation**: Current implementation is placeholder (assumes unit texture). Should integrate texture dimensions?
3. **Parser Integration**: from_string() is placeholder. Should integrate with existing parser now or later?
4. **EditorState Separation**: Confirm selection/undo should be separate class (not in CoA)?
5. **Snapshot Format**: Should snapshots be JSON-serializable, or is dict sufficient?
