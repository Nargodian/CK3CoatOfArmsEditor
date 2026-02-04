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
- Use property access (`.pos_x`) not dictionary lookup (`['pos_x']`)

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
