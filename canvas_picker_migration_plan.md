# Canvas Picker Migration Plan: canvas_widget.py → canvas_widget_NEW.py

## Executive Summary

The layer picker functionality is **already implemented and working** via `CanvasToolsMixin`. This plan focuses on ensuring robust integration with `canvas_widget_NEW.py`, adding proper invalidation hooks, and improving the existing implementation where needed.

## Current Status

### ✅ What Already Works

1. **CanvasToolsMixin** - Complete picker implementation (727 lines)
   - Off-screen picker RTT rendering with unique RGB colors per layer UUID
   - Mouse event handlers for picking, paint selection (Ctrl+drag), and tooltips
   - Tool activation/deactivation with cursor management
   - Transform widget visibility coordination

2. **canvas_widget_NEW.py** - Already inherits from `CanvasToolsMixin`
   - Proper mouse event delegation (tools → pan → default)
   - Tool state initialization via `_init_tools()` call
   - Mouse position tracking for UV calculations

3. **Picker RTT Architecture**
   - Golden ratio HSV distribution for maximum color distinction
   - Tolerance-based RGB→UUID lookup (±1 per channel for float→int precision)
   - QImage caching with validity flag
   - OpenGL texture generation on demand

### ⚠️ What Needs Improvement

1. **Picker RTT Invalidation** - Missing systematic invalidation hooks
2. **Coordinate System Integration** - Needs to use `CanvasCoordinateMixin` methods
3. **Error Handling** - Silent failures in texture/shader availability
4. **Memory Management** - No cleanup on widget destruction

---

## Architecture Overview

### Picker RTT Workflow

```
1. USER ACTIVATES PICKER
   ↓
2. _activate_layer_picker()
   - Generate picker RTT
   - Hide transform widget
   ↓
3. _generate_picker_rtt()
   - Build UUID→RGB mapping (HSV distribution)
   - Call _render_picker_to_framebuffer()
   - Mark picker_rtt_valid = True
   ↓
4. _render_picker_to_framebuffer()
   - Bind framebuffer (512x512 RTT)
   - Clear to black (0,0,0 = no layer)
   - Disable blending for exact colors
   - For each layer:
     * Set indexColor uniform (RGB from mapping)
     * Bind emblem texture atlas
     * Bind pattern mask if present
     * Render quad with layer transforms
   - Read pixels to QImage
   - Unbind framebuffer
   ↓
5. MOUSE MOVE
   - _on_tool_mouse_move()
   - _sample_picker_at_mouse()
   - Convert widget→CoA→RTT pixel coords
   - Read RGB from QImage.pixel()
   - Look up UUID with tolerance matching
   - Show tooltip with layer name
   ↓
6. MOUSE CLICK
   - _on_tool_mouse_press()
   - Sample UUID at click position
   - Update layer_list selection
   - Paint select mode if Ctrl held
   - Deactivate tool if not Shift held
```

### Key Components

**Tool State Variables:**
```python
self.active_tool = None              # 'layer_picker', 'eyedropper', None
self.hovered_uuid = None             # Layer under mouse for tooltip
self.last_picker_mouse_pos = None   # For UV calculation

# Picker RTT
self.picker_rtt = None               # QImage with UUID colors
self.picker_rtt_valid = False        # Cache validity flag
self.picker_uuid_map = {}            # (r,g,b) → UUID
self.picker_color_map = {}           # layer_index → (r,g,b) float
self.picker_texture_id = None        # OpenGL texture ID

# Paint selection (Ctrl+drag)
self.paint_selecting = False         # Active paint mode
self.paint_select_mode = None        # 'select' or 'deselect'
self.paint_selected_uuids = set()    # UUIDs processed this session
```

---

## Migration Strategy

### Phase 1: Coordinate System Integration ✨ ROBUSTNESS IMPROVEMENT

**Issue:** `_render_picker_to_framebuffer()` calculates OpenGL coordinates manually

**Solution:** Use `CanvasCoordinateMixin.canvas_to_coa()` and ensure consistency

**Files to Modify:**
- `canvas_widgets/canvas_tools_mixin.py` - Line 168 `_render_picker_to_framebuffer()`

**Changes:**
```python
# BEFORE (manual calculation)
center_x = pos_x * 2.0 - 1.0
center_y = -(pos_y * 2.0 - 1.0)

# AFTER (use coordinate mixin if available, fallback to manual)
if hasattr(self, '_layer_pos_to_ndc'):
    center_x, center_y = self._layer_pos_to_ndc(pos_x, pos_y)
else:
    # Fallback for standalone usage
    center_x = pos_x * 2.0 - 1.0
    center_y = -(pos_y * 2.0 - 1.0)
```

### Phase 2: Systematic Picker RTT Invalidation ✨ ROBUSTNESS CRITICAL

**Issue:** `on_coa_structure_changed()` exists but isn't called systematically

**Invalidation Triggers:**
1. Layer added/removed
2. Layer reordered
3. Layer texture changed
4. Texture atlas reload
5. Frame change (affects visible area)
6. Zoom/pan (affects coordinate mapping) - **NO, picker uses CoA space**

**Solution:** Add invalidation hooks in canvas_widget_NEW.py

**Files to Modify:**
- `canvas_widget_NEW.py`

**New Method:**
```python
def _invalidate_picker_if_needed(self):
    """Invalidate picker RTT when CoA structure changes"""
    if hasattr(self, 'invalidate_picker_rtt'):
        self.invalidate_picker_rtt()
    # Force regeneration on next picker activation
    self.update()  # Repaint if picker is active
```

**Add Calls After:**
```python
# After texture reload
def reload_all_textures(self):
    # ... existing reload code ...
    self._invalidate_picker_if_needed()

# After CoA load
def load_coa_from_file(self, ...):
    # ... existing load code ...
    self._invalidate_picker_if_needed()

# After layer operations (if canvas_widget_NEW has direct layer ops)
# NOTE: Most layer ops go through CoA model, so may not need direct hooks
```

**Better Solution:** Hook into CoA change notifications
```python
# In canvas_widget_NEW.__init__()
if CoA.has_active():
    # Register for CoA change events (if event system exists)
    # OR check in paintGL() if CoA modified timestamp changed
    pass
```

### Phase 3: Error Handling & Validation ✨ ROBUSTNESS CRITICAL

**Issue:** Silent failures if shaders/textures not ready

**Files to Modify:**
- `canvas_widgets/canvas_tools_mixin.py` - `_render_picker_to_framebuffer()`

**Changes:**
```python
def _render_picker_to_framebuffer(self):
    """Render picker RTT using OpenGL picker shader"""
    # ... imports ...
    
    # VALIDATION CHECKS
    if not CoA.has_active():
        print("WARNING: Cannot generate picker RTT - no active CoA")
        return False
    
    if not hasattr(self, 'framebuffer_rtt') or not self.framebuffer_rtt:
        print("ERROR: Cannot generate picker RTT - no framebuffer")
        return False
    
    if not hasattr(self, 'picker_shader') or not self.picker_shader:
        print("ERROR: Cannot generate picker RTT - no picker shader")
        return False
    
    if not hasattr(self, 'vao') or not self.vao:
        print("ERROR: Cannot generate picker RTT - no VAO")
        return False
    
    if not hasattr(self, 'texture_uv_map') or not self.texture_uv_map:
        print("WARNING: Cannot generate picker RTT - no texture UV map")
        return False
    
    # ... existing render code ...
    
    return True  # Success

# Update _generate_picker_rtt() to check return value
def _generate_picker_rtt(self):
    # ... existing mapping code ...
    
    # Render and check success
    success = self._render_picker_to_framebuffer()
    self.picker_rtt_valid = success
    
    if success:
        print(f"Generated picker RTT: {len(self.picker_uuid_map)} layers mapped")
    else:
        print("ERROR: Failed to generate picker RTT")
```

### Phase 4: Memory Management ✨ ROBUSTNESS IMPROVEMENT

**Issue:** Picker RTT texture not cleaned up on widget destruction

**Files to Modify:**
- `canvas_widgets/canvas_tools_mixin.py`
- `canvas_widget_NEW.py`

**New Method in Mixin:**
```python
def _cleanup_picker_resources(self):
    """Clean up picker RTT OpenGL resources"""
    if hasattr(self, 'picker_texture_id') and self.picker_texture_id:
        try:
            import OpenGL.GL as gl
            self.makeCurrent()  # Ensure context active
            gl.glDeleteTextures([self.picker_texture_id])
            self.picker_texture_id = None
            self.picker_rtt = None
            self.picker_rtt_valid = False
            print("Cleaned up picker RTT resources")
        except Exception as e:
            print(f"WARNING: Error cleaning up picker resources: {e}")
```

**Call in canvas_widget_NEW.py:**
```python
def cleanup(self):
    """Clean up OpenGL resources (call before widget destruction)"""
    # ... existing cleanup ...
    
    # Clean up picker resources
    if hasattr(self, '_cleanup_picker_resources'):
        self._cleanup_picker_resources()
```

### Phase 5: Paint Selection Mode Polish ✨ ROBUSTNESS IMPROVEMENT

**Current Implementation:** Works but could be more robust

**Potential Improvements:**
1. Visual feedback for paint selection mode (cursor change?)
2. Escape key to cancel paint selection
3. Status bar message "Paint selecting: Click and drag to select/deselect layers"
4. Undo/redo integration for batch selection changes

**Priority:** Medium (current implementation functional)

### Phase 6: Performance Optimization (Optional)

**Current Performance:**
- Picker RTT generated on every activation (~512x512 render)
- Regenerates even if CoA unchanged

**Optimization Ideas:**
1. **Lazy Regeneration** - Only regenerate if `picker_rtt_valid == False`
   - Already implemented via `picker_rtt_valid` flag
   - Need to ensure invalidation hooks are comprehensive

2. **Incremental Updates** - Track which layers changed, update only those colors
   - Complex, low ROI
   - Current full regeneration is fast enough (<100ms for typical CoA)

3. **Texture Resolution** - Use lower res for picker RTT
   - Currently 512x512 (same as main RTT)
   - Could reduce to 256x256 if performance issue
   - Trade-off: Lower precision on small emblems

**Priority:** Low (no reported performance issues)

---

## Integration Checklist

### For canvas_widget_NEW.py

- [x] Inherit from `CanvasToolsMixin` ✅ Already done
- [x] Call `_init_tools()` in `__init__()` ✅ Already done
- [x] Delegate mouse events to tool handlers ✅ Already done
- [ ] Add `_invalidate_picker_if_needed()` method
- [ ] Call invalidation after texture reload
- [ ] Call invalidation after CoA load
- [ ] Add `cleanup()` method with picker resource cleanup
- [ ] Test picker activation/deactivation
- [ ] Test paint selection mode
- [ ] Test layer tooltip hover

### For canvas_tools_mixin.py

- [ ] Add coordinate system integration (use `_layer_pos_to_ndc()` if available)
- [ ] Add validation checks to `_render_picker_to_framebuffer()`
- [ ] Return success/failure from `_render_picker_to_framebuffer()`
- [ ] Check return value in `_generate_picker_rtt()`
- [ ] Add `_cleanup_picker_resources()` method
- [ ] Document invalidation triggers in docstring

### Testing Plan

1. **Basic Picker Functionality**
   - Activate picker tool (P key or button)
   - Click layer to select
   - Verify selection in layer list
   - Verify transform widget shows

2. **Paint Selection Mode**
   - Activate picker
   - Ctrl+drag over multiple layers
   - Verify batch selection works
   - Verify deselect mode (Ctrl+drag over selected layer first)

3. **Tooltip Hover**
   - Activate picker
   - Move mouse over layers
   - Verify tooltip shows layer name
   - Verify tooltip updates on hover

4. **Invalidation**
   - Load new CoA file
   - Activate picker
   - Verify all layers pickable
   - Add new layer
   - Activate picker again
   - Verify new layer pickable

5. **Edge Cases**
   - Picker with no layers
   - Picker with overlapping layers
   - Picker with invisible layers
   - Picker with masked layers
   - Picker during zoom/pan

6. **Memory/Performance**
   - Activate/deactivate picker 100 times
   - Monitor memory usage
   - Close widget, verify no OpenGL errors

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Coordinate mismatch between picker RTT and display | High | Low | Use same coordinate functions, add unit tests |
| Picker RTT not invalidated after layer change | Medium | Medium | Systematic invalidation hooks (Phase 2) |
| RGB collision (two layers get same color) | Medium | Very Low | Golden ratio distribution gives ~16M unique colors |
| OpenGL context issues on cleanup | Low | Low | Try/catch in cleanup, ensure context active |
| Performance degradation on large CoAs | Medium | Low | Profile and optimize if needed (Phase 6) |

---

## Recommendations

### Must Do (Critical for Robustness)

1. **Phase 2: Systematic Invalidation**
   - Add `_invalidate_picker_if_needed()` to canvas_widget_NEW.py
   - Call after texture reload and CoA load
   - Test that picker updates after layer operations

2. **Phase 3: Error Handling**
   - Add validation checks to `_render_picker_to_framebuffer()`
   - Return success/failure and check in caller
   - Print helpful error messages for debugging

3. **Phase 4: Memory Management**
   - Add `_cleanup_picker_resources()` to mixin
   - Call from canvas_widget_NEW.cleanup()
   - Test with repeated widget creation/destruction

### Should Do (Robustness Improvements)

4. **Phase 1: Coordinate Integration**
   - Use `CanvasCoordinateMixin` methods if available
   - Ensures consistency between picker and display
   - Low risk, high maintainability benefit

5. **Testing**
   - Run full test suite from Testing Plan
   - Document any edge cases discovered
   - Add automated tests if possible

### Nice to Have (Polish)

6. **Phase 5: Paint Selection Polish**
   - Better visual feedback
   - Escape key to cancel
   - Status bar messages

7. **Phase 6: Performance Optimization**
   - Only if performance issues reported
   - Profile first, optimize second

---

## Implementation Order

1. **Start:** Read this entire document
2. **Quick Win:** Phase 4 (Memory Management) - Simple, self-contained
3. **Critical:** Phase 2 (Invalidation) - Most important for correctness
4. **Safety:** Phase 3 (Error Handling) - Makes debugging easier
5. **Polish:** Phase 1 (Coordinate Integration) - Low risk cleanup
6. **Validate:** Run testing plan
7. **Optional:** Phase 5 & 6 as needed

---

## Migration Completion Criteria

✅ Canvas_widget_NEW.py can use picker tool without any issues
✅ Picker RTT invalidates correctly when CoA changes
✅ No OpenGL memory leaks on widget destruction
✅ Helpful error messages if picker can't render
✅ All tests pass from Testing Plan
✅ Code review with focus on edge cases
✅ Documentation updated (if any user-facing docs exist)

---

## Notes

- **No Breaking Changes Required:** Current implementation works, we're just making it more robust
- **Mixin Pattern Proven:** CanvasToolsMixin successfully separates concerns
- **Golden Ratio Color Distribution:** Clever algorithm, don't change without good reason
- **Paint Selection:** Unique feature, ensure it keeps working
- **Coordinate Systems:** Most complex part, handle with care

---

## Appendix: Key Code Locations

### CanvasToolsMixin (canvas_tools_mixin.py)
- Lines 15-28: Tool state initialization
- Lines 46-52: `set_tool_mode()` - Main entry point
- Lines 104-112: `_activate_layer_picker()` - Tool activation
- Lines 120-167: `_generate_picker_rtt()` - Build color mapping
- Lines 168-364: `_render_picker_to_framebuffer()` - OpenGL rendering
- Lines 427-440: `invalidate_picker_rtt()`, `on_coa_structure_changed()`
- Lines 445-490: `_sample_picker_at_mouse()` - UUID lookup
- Lines 493-564: `_on_tool_mouse_move()` - Hover and paint selection
- Lines 567-641: `_on_tool_mouse_press()` - Click handling
- Lines 644-658: `_on_tool_mouse_release()` - Paint mode cleanup

### canvas_widget_NEW.py
- Line 60: Inherits from CanvasToolsMixin
- Line 145: Calls `_init_tools()`
- Lines 679-725: Mouse event handlers with tool delegation

### Original canvas_widget.py (for reference)
- Line 144: Inherits from CanvasToolsMixin
- Similar mouse event pattern (can copy tested code)
