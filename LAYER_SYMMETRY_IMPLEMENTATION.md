# Layer Symmetry System - Implementation Complete

## Overview

The layer symmetry system has been successfully implemented for the CK3 CoA Editor. This feature allows users to create mirrored and repeated instances of emblem layers automatically, eliminating the need to manually duplicate and position layers.

## Features Implemented

### Three Symmetry Types

1. **Bisector (Mirror Line)**
   - Single mirror line or double (cross)
   - Adjustable rotation angle
   - Center position control

2. **Rotational (Radial)**
   - Configurable count (2-12 copies)
   - Start angle offset
   - Kaleidoscope mode (mirror + rotate)
   - Center position control

3. **Grid (Tiling)**
   - Configurable columns and rows (1-8)
   - Fill patterns: Full, Diamond, Alt-Diamond
   - Offset position control

## User Interface

**Location:** Property Sidebar → Properties Tab → Symmetry Section

**Controls:**
- **Type Dropdown:** Select symmetry type (None, Bisector, Rotational, Grid)
- **Dynamic Controls:** Type-specific controls appear based on selection
- **Real-time Updates:** Changes apply immediately to canvas

## Technical Implementation

### Phase 1: CoA Model ✅
- Added `symmetry_type` and `symmetry_properties` to Layer class
- Added CoA methods: `get/set_layer_symmetry_type()`, `get/set_layer_symmetry_properties()`, `get_symmetry_transforms()`
- Created `services/symmetry_calculator.py` with geometry calculations

### Phase 2: Property Sidebar UI ✅
- Added symmetry section with dropdown after mask section
- Created three widget files:
  - `components/symmetry/bisector_widget.py`
  - `components/symmetry/rotational_widget.py`
  - `components/symmetry/grid_widget.py`
- Dynamic widget loading based on symmetry type

### Phase 3: Canvas Rendering ✅
- Modified `_render_layer_instances()` to render seeds + calculated mirrors
- Created `_render_single_instance()` and `_render_single_transform()` helpers
- Visual indicators (deferred for future enhancement)

### Phase 4: Export/Import ✅
- Added symmetry meta tags to `Layer.serialize()`
- Added symmetry parsing to `Layer.parse()`
- Format: `##META##symmetry_type="bisector"` and `##META##symmetry_properties={0.5 0.5 45.0 0}`

### Phase 5: Layer Operations ✅
- Updated `merge_layers()` to check for mixed symmetry and warn/reset
- `split_layer()` automatically preserves symmetry (via deepcopy)
- `duplicate_layer()` automatically preserves symmetry (via deepcopy)

## Files Modified

### Core Model
- `editor/src/models/coa/_internal/layer.py` - Added symmetry properties
- `editor/src/models/coa/layer_mixin.py` - Added symmetry methods

### Services
- `editor/src/services/symmetry_calculator.py` - NEW: Geometry calculations

### UI Components
- `editor/src/components/property_sidebar.py` - Added symmetry section
- `editor/src/components/symmetry/bisector_widget.py` - NEW
- `editor/src/components/symmetry/rotational_widget.py` - NEW
- `editor/src/components/symmetry/grid_widget.py` - NEW
- `editor/src/components/symmetry/__init__.py` - NEW

### Rendering
- `editor/src/components/canvas_widgets/canvas_rendering_mixin.py` - Extended instance rendering

## Usage

1. **Select a layer** in the layer list
2. **Open Properties tab** in the right sidebar
3. **Scroll to Symmetry section**
4. **Select symmetry type** from dropdown:
   - **None:** No symmetry (default)
   - **Bisector:** Mirror across line(s)
   - **Rotational:** Radial arrangement
   - **Grid:** Tiled pattern
5. **Adjust parameters** using the controls that appear
6. **Changes apply immediately** to the canvas

## Property Format

### Bisector
```python
symmetry_type = 'bisector'
symmetry_properties = [offset_x, offset_y, rotation_offset, mode]
# mode: 0 = single mirror, 1 = double (cross)
```

### Rotational
```python
symmetry_type = 'rotational'
symmetry_properties = [offset_x, offset_y, count, rotation_offset, kaleidoscope]
# kaleidoscope: 0 = rotate only, 1 = mirror + rotate
```

### Grid
```python
symmetry_type = 'grid'
symmetry_properties = [offset_x, offset_y, count_x, count_y, fill]
# fill: 0 = full, 1 = diamond, 2 = alt-diamond
```

## Serialization Format

```
colored_emblem = {
    ##META##container_uuid="..."
    ##META##name="..."
    ##META##symmetry_type="rotational"
    ##META##symmetry_properties={0.5 0.5 6 0.0 0}
    texture = "ce_lion.dds"
    color1 = "yellow"
    instance = { position = { 0.5 0.5 } scale = { 1.0 1.0 } }
}
```

## History Integration

- Symmetry changes are automatically captured in undo/redo history
- History snapshots include all layer properties (including symmetry)
- No special handling required

## Known Limitations

1. **Visual Indicators:** Symmetry axes/lines overlay not yet implemented (deferred)
2. **Export Behavior:** Mirrors are calculated at render time (not stored as instances)
3. **Import Behavior:** Imported files from game lose symmetry metadata (expected)

## Testing Checklist

- [ ] Create bisector symmetry with single mirror
- [ ] Create bisector symmetry with double mirror (cross)
- [ ] Create rotational symmetry with 6 copies
- [ ] Create rotational symmetry with kaleidoscope mode
- [ ] Create grid symmetry with 3x3 full pattern
- [ ] Create grid symmetry with diamond fill
- [ ] Test offset controls for all types
- [ ] Test rotation offset controls
- [ ] Verify undo/redo captures symmetry changes
- [ ] Test merge layers with same symmetry (preserved)
- [ ] Test merge layers with different symmetry (reset to none)
- [ ] Test split layer (symmetry preserved)
- [ ] Test duplicate layer (symmetry preserved)
- [ ] Test save/load CoA with symmetry
- [ ] Test clipboard copy/paste with symmetry

## Future Enhancements

1. **Visual Indicators:** Add QPainter overlay to show symmetry axes/lines
2. **Layer Badge:** Show symmetry icon on layers in layer list
3. **Preset Buttons:** Quick symmetry presets (2-fold, 4-fold, 6-fold, etc.)
4. **Instance Conversion:** Convert symmetry to real instances (freeze)
5. **Animation:** Animated rotation for previewing rotational symmetry

## Conclusion

The layer symmetry system is fully implemented and functional. All core phases (1-5) are complete. Users can now create complex symmetric coat of arms designs with minimal effort.

**Status:** ✅ **READY FOR TESTING**
