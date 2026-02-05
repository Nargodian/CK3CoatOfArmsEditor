---
applyTo: '**'
---

# Coding Standards

## CoA Model Architecture

### Knowledge Boundaries
**CoA Should Know:**
- Layer data: UUIDs, ordering, positions, scales, rotations, colors, flip states
- Instance data: counts, selected instance index
- Mask data, visibility state, texture filenames
- Serialization/operations: add, remove, duplicate, move, reorder
- Transform history for undo/redo

**CoA Should NOT Know:**
- UI state, rendering details, asset paths, metadata
- How many color pickers to display (query metadata cache)
- Mouse/keyboard interaction, window layout

### Access Patterns
- Use `CoA.get_active()` for singleton access (not `CoA()` directly)
- Identify layers by **UUID**, never by index
- Use specific methods (`get_layer_name`, `set_layer_opacity`) not generic getters/setters
- Never access `coa._layers` directly - use CoA methods
- Use Vec2 properties (`.pos`, `.scale`) not legacy component access (see Vec2/Transform Rules below)

### Module Imports
Import from `models.coa` only:
```python
# ✅ CORRECT
from models.coa import CoA, Layer, Layers, LayerTracker

# ❌ FORBIDDEN - Internal implementation
from models.coa.coa_parser import *
from models.coa.layer import *
```
Everything in `models/coa/` is private. Use CoA API methods only.

## Vec2 and Transform Rules

### NO BACKWARD COMPATIBILITY - SCORCHED EARTH
All legacy position/scale component properties have been **completely removed**. There is no backward compatibility.

### Vec2 Dataclass
```python
@dataclass
class Vec2:
    x: float
    y: float
    
    def __iter__(self):
        return iter((self.x, self.y))  # Allows tuple unpacking
```

### Transform Dataclass
```python
@dataclass
class Transform:
    pos: Vec2      # Position vector (NOT pos_x/pos_y)
    scale: Vec2    # Scale vector (NOT scale_x/scale_y)
    rotation: float
```

### Instance and Layer Properties
**ONLY Vec2 properties exist:**
```python
# ✅ CORRECT - Use Vec2 properties
instance.pos       # Vec2(x, y)
instance.scale     # Vec2(x, y)
layer.pos          # Vec2(x, y) - proxies to instance
layer.scale        # Vec2(x, y) - proxies to instance

# ❌ FORBIDDEN - These properties DO NOT EXIST
instance.pos_x     # AttributeError!
instance.pos_y     # AttributeError!
instance.scale_x   # AttributeError!
instance.scale_y   # AttributeError!
layer.pos_x        # AttributeError!
layer.pos_y        # AttributeError!
```

### Usage Patterns

**Reading Position/Scale:**
```python
# ✅ CORRECT - Access Vec2 components
x = instance.pos.x
y = instance.pos.y
sx = instance.scale.x
sy = instance.scale.y

# ✅ CORRECT - Unpack entire Vec2
x, y = instance.pos
sx, sy = instance.scale

# ❌ WRONG - Legacy component access
x = instance.pos_x  # Does not exist!
```

**Setting Position/Scale:**
```python
# ✅ CORRECT - Assign entire Vec2
instance.pos = Vec2(0.5, 0.3)
instance.scale = Vec2(1.2, 1.2)

# ✅ CORRECT - Modify existing Vec2 (creates new instance)
instance.pos = Vec2(instance.pos.x + delta, instance.pos.y)

# ❌ WRONG - Legacy component assignment
instance.pos_x = 0.5      # Does not exist!
instance.pos_y = 0.3      # Does not exist!
```

**CoA API Methods:**
```python
# ✅ CORRECT - CoA methods return Vec2
pos = coa.get_layer_pos(uuid)          # Returns Vec2
scale = coa.get_layer_scale(uuid)      # Returns Vec2
x, y = coa.get_layer_position(uuid)    # Returns tuple (for convenience)

# ✅ CORRECT - CoA methods accept components or Vec2
coa.set_layer_position(uuid, 0.5, 0.3)           # Individual components
coa.set_layer_pos(uuid, Vec2(0.5, 0.3))          # Vec2 object
```

**Transform Construction:**
```python
# ✅ CORRECT - Always use Vec2 for Transform
transform = Transform(Vec2(x, y), Vec2(sx, sy), rotation)

# ✅ CORRECT - From layer properties
pos = coa.get_layer_pos(uuid)
scale = coa.get_layer_scale(uuid)
rotation = coa.get_layer_rotation(uuid)
transform = Transform(pos, scale, rotation)

# ❌ WRONG - Passing individual components
transform = Transform(x, y, sx, sy, rotation)  # Type error!
```

**Unpacking for Function Calls:**
```python
# ✅ CORRECT - Unpack Vec2 when needed
widget.set_position(transform.pos.x, transform.pos.y)

# ✅ CORRECT - Use tuple unpacking
x, y = transform.pos
widget.set_position(x, y)
```

### Migration Checklist
When working with position/scale code:
- [ ] Import Vec2 from models.transform
- [ ] Replace all `.pos_x/.pos_y` with `.pos.x/.pos.y`
- [ ] Replace all `.scale_x/.scale_y` with `.scale.x/.scale.y`
- [ ] Use `Vec2(x, y)` constructor for assignments
- [ ] Update Transform construction to use Vec2
- [ ] Never access legacy properties (they don't exist)

## Component Responsibility

Components query and set their own display properties. Don't pass display state through callbacks.

**Selection Callbacks For:**
- Cross-component coordination (property sidebar updates when layer selected)
- System-level events (reordering, deletion affecting multiple components)

**NOT For:**
- Component's own display properties
- Properties component can query directly from CoA

```python
# ❌ WRONG - Callback sets display state
def _on_selection_changed():
    colors = coa.get_layer_colors(uuid)
    property_panel.set_emblem_color_count(colors)

# ✅ CORRECT - Component queries its own state
def _load_layer_properties():
    colors = self.main_window.coa.get_layer_colors(uuid)
    self.set_emblem_color_count(colors)
```

`update_selection_visuals()` should trigger `on_selection_changed` callback automatically.

## Transform Types

**Shallow:** Work per selected layer, instances move as rigid bodies with parent
**Deep:** Work across all instances in all layers, instances move independently

## Error Handling

Use `loggerRaise(e, 'context message')` not silent message boxes. We want errors in logs for debugging.

## Avoid "Rogue Mathematics"

**Definition:** Business logic (especially geometric/mathematical calculations) that has leaked out of the domain model into UI/presentation layers, often duplicated across multiple locations.

**Red Flags:**
- **Parameter Explosion** - Methods with 9+ parameters passing primitives instead of domain objects
- **Duplicate Math** - Same geometric calculations (rotation, scaling, AABB) in multiple files
- **UI Doing Math** - Coordinate transforms, ferris wheel rotations, or instance positioning in components/mixins
- **Math Imports in UI** - `import math` in presentation layer files (components, widgets, mixins)

**Examples:**

```python
# ❌ ROGUE - UI component doing domain math
def _apply_rotation_to_layer(self, offset_x, offset_y, scale_x, scale_y,
                              rotation_delta, center_x, center_y, delta_x, delta_y):
    rotation_rad = math.radians(rotation_delta)
    cos_r = math.cos(rotation_rad)
    sin_r = math.sin(rotation_rad)
    new_offset_x = offset_x * cos_r - offset_y * sin_r  # Ferris wheel math in mixin!
    # ...

# ✅ CORRECT - Delegate to CoA model
def _handle_rotation_transform(self, selected_uuids, rotation):
    rotation_mode = self.get_rotation_mode()
    self.main_window.coa.apply_rotation_transform(selected_uuids, rotation, rotation_mode)
```

**Where Math Belongs:**
- **CoA Model** - All transform calculations, AABB computation, ferris wheel rotations, instance positioning
- **Canvas Widgets** - Only coordinate space conversions (pixel ↔ CoA space, widget ↔ canvas)
- **UI Components** - None - just coordinate and delegate

**Cleanup Pattern:**
1. Identify duplicate math (search for `math.cos`, `math.sin`, `offset_x * factor`)
2. Check if CoA model already has the method (it usually does)
3. Replace local math with CoA method calls
4. Delete the rogue implementation
5. Remove `import math` from UI files

**Example Cleanup:**
Before: 344 lines with rotation/scaling math duplicated in mixin
After: 276 lines delegating to `CoA.apply_rotation_transform()` and `CoA.transform_instances_as_group()`
