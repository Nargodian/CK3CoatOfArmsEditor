# Canvas Area Violations

## CRITICAL
1. **Wrong coordinate space** - Lines 471, 493, 501, 553: Uses `transform_widget.width()` instead of `canvas_widget.width()`
2. **Business logic in UI** - Mixin contains ferris wheel math, group scaling → belongs in CoA model
3. **Dynamic attribute hack** - Lines 606-612: `dir(self)` iteration to find `_instance_transform_begun_{uuid}` → use dict

## BUGS
4. **Duplicate comment** - Line 505-506
5. **Wrong layer** - Lines 535-538: Frame transform logic in canvas_area (belongs in canvas_widget)
6. **Too long** - `update_transform_widget_for_layer()` 138 lines → split into `_update_single_selection()` / `_update_multi_selection()`

## ARCHITECTURE
7. **Dependency injection** - Lines 22-24: Properties set by MainWindow instead of constructor
8. **Circular reference** - Line 66: `canvas_widget.canvas_area = self`
9. **Unused code** - Lines 704-784: Coordinate conversion methods (dead code?)
10. **Wrong responsibility** - Line 140: File I/O in canvas_area (`_discover_government_types`)

## STATE MESS
11. **Conflicting caches** - 6+ state variables with unclear lifecycle:
   - `_drag_start_layers`, `_drag_start_aabb`, `_single_layer_aabb`
   - `_initial_group_center`, `_rotation_start`, `_single_layer_initial_state`
   
## REFACTOR PLAN
- Fix coordinate space (use `canvas_widget.width()`)
- Move transform math to CoA model (`transform_selection_as_group()`)
- Replace dynamic attributes with `_instance_transforms` dict
- Split `update_transform_widget_for_layer()` 
- Remove dead coordinate conversion methods
- Consolidate state management
