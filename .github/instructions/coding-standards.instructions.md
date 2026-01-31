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
