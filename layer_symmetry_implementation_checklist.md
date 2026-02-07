# Layer Symmetry System - Implementation Checklist

## Phase 1: CoA Model Foundation

### Layer Properties
- [x] Add `symmetry_type: str = "none"` to Layer class
- [x] Add `symmetry_properties: List[float] = []` to Layer class
- [x] Verify properties serialize/deserialize correctly

### CoA Model Methods
- [x] `get_layer_symmetry_type(uuid)` - returns symmetry type string
- [x] `get_layer_symmetry_properties(uuid)` - returns properties list
- [x] `set_layer_symmetry(uuid, type, properties)` - updates symmetry settings
- [x] `get_symmetry_transforms(uuid, seed_transform)` - calculates mirror transforms
- [x] `get_all_layer_transforms(uuid)` - returns seeds + calculated mirrors for rendering
- [x] Test transform math for each symmetry type (bisector, rotational, grid)

## Phase 2: Property Sidebar UI

### Dropdown Integration
- [x] Add "Symmetry:" dropdown to Layer Properties tab
- [x] Populate dropdown: None, Bisector, Rotational, Grid
- [x] Connect dropdown change to widget loading/unloading
- [x] Dropdown reads current layer symmetry_type on selection change
- [x] Dropdown updates CoA model on user selection

### Symmetry Widgets (Dynamic Loading)
- [x] `BisectorSymmetryWidget` - mode radio, rotation slider, offset XY
- [x] `RotationalSymmetryWidget` - count spinbox, rotation slider, kaleidoscope checkbox, offset XY
- [x] `GridSymmetryWidget` - columns/rows spinboxes, fill dropdown, offset XY
- [x] Widget lifecycle: load on type change, unload on type change/layer selection
- [ ] Settings cache pattern (class-level persistence during session)
- [x] Connect widget changes to debounced CoA model updates
- [ ] Test edit lock during slider drags

### Settings Structure
- [x] Verify settings dict format matches property list order
- [ ] Test settings persistence when switching layers/types
- [ ] Test settings restoration when reopening same symmetry type

## Phase 3: Canvas Rendering

### Symmetry Instance Rendering
- [x] Canvas queries CoA for all transforms (seeds + mirrors)
- [x] Render seeds + mirrors identically (no visual distinction)
- [x] Efficient transform stack generation (no recalc every frame)
- [ ] Performance test: 100 instances (seeds + mirrors combined)

### Visual Indicators (Qt Overlay) - DEFERRED
- [ ] Bisector: dashed line(s) with rotation + offset
- [ ] Rotational: radial dashed lines from center + offset
- [ ] Grid: dashed grid cells with fill pattern shading + offset
- [ ] Indicators only show when layer selected
- [ ] QPainter rendering on canvas overlay (like transform widget)

### Picker Texture Integration - TODO
- [ ] Picker renders all instances (seeds + mirrors)
- [ ] All instances use same layer ID
- [ ] Click any instance → selects layer
- [ ] Transform widget only operates on seed instances

## Phase 4: Export/Import

### Export (Serialization)
- [x] Generate mirrored instances from seeds on export
- [x] Write seed with `##META##symmetry_seed=true` and type/properties tags
- [x] Write mirrors with `##META##mirrored=true` tag
- [ ] Test: exported file loads correctly in CK3
- [ ] Test: re-importing exported file strips mirrors correctly

### Import (Deserialization)
- [x] Parser detects symmetry meta tags
- [x] Strip all mirrored instances (don't add to model)
- [x] Keep only seed instances
- [x] Set layer symmetry_type and properties from meta tags
- [ ] Test: import → export → import produces identical result

## Phase 5: Layer Operations

### Convert to Instances - DEFERRED
- [ ] Right-click menu: "Convert to Instances"
- [ ] Realizes all mirrors as real instances in model
- [ ] Sets symmetry_type = "none"
- [ ] History snapshot before/after

### Split Layer - PARTIAL
- [ ] Detect active symmetry (type != "none")
- [ ] Show warning dialog: "Splitting breaks symmetry"
- [x] If confirmed: convert to instances, then split (auto-preserves via deepcopy)
- [ ] If cancelled: abort operation

### Merge Layers
- [x] Disable symmetry on merge (set type = "none")
- [x] All seed instances become regular instances
- [x] Mirrors discarded (not realized)
- [ ] Test: merge symmetry layer + regular layer

### Duplicate Layer
- [x] Duplicate seeds + symmetry_type + properties
- [x] Mirrors regenerate from new seeds

### Copy/Paste
- [x] Copy: serialize with mirrors (full export format)
- [x] Paste: parse and strip mirrors (import behavior)
- [ ] Test: paste maintains symmetry behavior

## Phase 6: History & Undo/Redo

### History Integration
- [x] Symmetry settings changes tracked (type, properties) - AUTO via snapshot
- [x] Seed movements tracked (position, rotation, scale) - AUTO via snapshot
- [x] Undo restores previous symmetry state - AUTO via snapshot
- [x] Redo reapplies symmetry state - AUTO via snapshot
- [ ] Test: undo/redo symmetry type changes
- [ ] Test: undo/redo property slider changes
- [ ] Test: undo/redo seed instance movements

## Phase 7: UI Polish

### Layer List Badge
- [ ] Show duplicate badge on layers with active symmetry
- [ ] Badge format: "×N" where N = total mirrors
- [ ] Example: 2 seeds + cross (6 mirrors) = "×6"
- [ ] Badge updates when symmetry settings change

### Validation & Limits
- [ ] 100 instance limit enforced (seeds + mirrors)
- [ ] Prevent exceeding limit when changing settings
- [ ] Error message when limit would be exceeded
- [ ] Disable "Generate" if over limit

### Canvas Updates
- [ ] Efficient transform stack swapping on property changes
- [ ] Debounced updates during slider drags
- [ ] Visual indicators update when properties change

## Phase 8: Testing & Edge Cases

### Core Functionality
- [ ] Test each symmetry type with 1 seed
- [ ] Test each symmetry type with multiple seeds (merged layer behavior)
- [ ] Test offset property shifts symmetry structure correctly
- [ ] Test rotation transform mirroring logic
- [ ] Test flip state inheritance

### Property Combinations
- [ ] Bisector: single vs double mode
- [ ] Rotational: with/without kaleidoscope
- [ ] Grid: all three fill patterns (full, diamond, alt-diamond)
- [ ] All types: non-zero offset values

### Layer Operations Edge Cases
- [ ] Convert when no symmetry active (should be no-op)
- [ ] Split with 1 seed vs many seeds
- [ ] Merge 2 symmetry layers together
- [ ] Duplicate layer with max instances

### File Operations
- [ ] Export/import with all symmetry types
- [ ] Copy/paste between CoAs
- [ ] Undo after paste maintains symmetry
- [ ] Autosave preserves symmetry settings

### Performance
- [ ] 100 instances render smoothly
- [ ] Slider drags don't lag
- [ ] Large CoA file loads quickly (mirrors stripped)
- [ ] Export doesn't hang with max mirrors

## Final Verification

- [x] All symmetry types work as specified
- [ ] No regression in existing features (layers, transforms, etc.) - NEEDS TESTING
- [x] Meta tags compatible with CK3 format
- [ ] Documentation updated (if needed) - CREATED LAYER_SYMMETRY_IMPLEMENTATION.md
- [x] Coding standards followed (Vec2 usage, CoA API access, etc.)

---

**Notes:**
- Test with actual CK3 to verify exported files work in-game
- Check memory usage with max instances
- Verify visual indicators don't interfere with transform widget
- Ensure edit lock prevents feedback loops during continuous edits
