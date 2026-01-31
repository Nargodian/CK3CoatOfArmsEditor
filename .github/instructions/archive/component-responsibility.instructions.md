---
applyTo: '**'
---

# Component Responsibility Principle

## Core Rule
Components query and set their own display properties. Don't pass display state through callbacks.

## Selection Callbacks
Use selection callbacks ONLY for:
- Cross-component coordination (property sidebar updates when layer selected)
- System-level events (reordering, deletion affecting multiple components)

Do NOT use selection callbacks for:
- Component's own display properties
- Properties that component can query directly from CoA

## Implementation Pattern

### ❌ WRONG - Callback sets display state
```python
def _on_selection_changed():
    colors = coa.get_layer_colors(uuid)
    property_panel.set_emblem_color_count(colors)  # External setting
```

### ✅ CORRECT - Component queries its own state
```python
def _load_layer_properties():
    colors = self.main_window.coa.get_layer_colors(uuid)
    self.set_emblem_color_count(colors)  # Self query and set
```

## Callback Triggers
`update_selection_visuals()` should trigger `on_selection_changed` callback.
Don't require manual callback invocation after selection changes.

## Summary
If a property is entirely within component's view (color count, visibility, enabled state), component queries and sets it. Callbacks are for "something changed that you need to know about", not "here's your new state".
