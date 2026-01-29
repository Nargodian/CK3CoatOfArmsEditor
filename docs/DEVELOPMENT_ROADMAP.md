# CK3 CoA Editor - Development Roadmap

**Last Updated:** January 29, 2026  
**Status:** Phase 1 Complete - Ready for Phase 2  

This document consolidates the feature implementation plan and development priorities for the CK3 Coat of Arms Editor.

---

## Table of Contents

1. [Current Status](#current-status)
2. [Phase 1: Pattern Mask System](#phase-1-pattern-mask-system)
3. [Phase 2: Multi-Instance Support](#phase-2-multi-instance-support)
4. [Phase 3: Layout Templates](#phase-3-layout-templates)
5. [Phase 4: Quality of Life Enhancements](#phase-4-quality-of-life-enhancements)
6. [Technical Implementation Notes](#technical-implementation-notes)
7. [Priority Matrix](#priority-matrix)

---

## Current Status

### ✅ Phase 1 Complete (January 2026)
**Pattern Mask System** - Fully implemented and tested
- ✅ Data model: `mask` field in layer data as `[int, int, int]` list
- ✅ Serialization: Round-trip support for mask field
- ✅ UI: Pattern Mask section with 3 checkboxes and color indicators
- ✅ Shader: Bitwise flag system with exclusive masking (subtraction algorithm)
- ✅ Canvas: Pattern texture UV mapping with atlas coordinates
- ✅ All game samples tested and working
- ✅ Export/import round-trip verified

### 🎯 Next Up: Phase 2 - Multi-Instance Support
Focus on expanding emblem capabilities to match CK3's multi-instance format.

---

## Phase 1: Pattern Mask System

### ✅ COMPLETED - January 2026

**Objective:** Allow emblems to render only in specific pattern mask channels (regions).

**Implementation Details:**

#### Data Model
```python
layer_data = {
    'mask': [1, 0, 0]  # Channel 1 only, or None for all channels
}
```
- Format: Fixed-length list of 3 integers
- Values: Each element is 0 (off) or non-zero (on)
- Examples:
  - `[1, 0, 0]` = Channel 1 only (red mask region)
  - `[0, 2, 0]` = Channel 2 only (green mask region)
  - `[1, 2, 0]` = Channels 1 and 2 (red + green regions)
  - `[1, 2, 3]` or `None` = All channels (render everywhere)

#### Shader Implementation
- Uniform: `int patternFlag` (bitwise flags 0-7)
- Conversion: `mask[0]→bit 0 (1), mask[1]→bit 1 (2), mask[2]→bit 2 (4)`
- Exclusive masking via subtraction:
  - Channel 1 only: `R - G - B`
  - Channel 2 only: `G - B`
  - Channel 3 only: `B`
- Pattern texture sampled with UV coordinates from atlas

#### UI Components
- Location: Property sidebar, below rotation controls
- 3 checkboxes with color-coded indicators (synced from base pattern colors)
- Updates on layer selection and pattern color changes

#### Files Modified
- `editor/src/services/layer_operations.py` - Data model and serialization
- `editor/src/services/file_operations.py` - Export with mask field
- `editor/src/components/property_sidebar.py` - Mask UI controls
- `editor/src/components/canvas_widget.py` - Pattern texture binding and uniform passing
- `editor/src/shaders/design.frag` - Mask shader logic
- `editor/src/main.py` - Layer creation with mask field

---

## Phase 2: Multi-Instance Support

### 🔄 IN PROGRESS - High Priority

**Objective:** Support multiple instances per emblem layer (matches CK3's official file format).

### Current Status
**Phase 2A: Complete ✅** - Import/Export and rendering support for multi-instance layers
- ✅ Data model with instances list
- ✅ Import all instances from CoA files
- ✅ Export all instances to CoA files
- ✅ Canvas renders all instances
- ✅ Backwards compatibility migration

**Phase 2B: In Progress** - User interface and instance management

### Design Constraints

**Important:** Multi-instance layers are treated as **atomic groups** in the editor:
- All instances transform together as a unit
- Individual instances cannot be selected or edited separately on canvas
- Per-instance editing requires splitting the layer first
- This simplifies the UI and prevents accidental desynchronization

### Target Architecture

#### Data Model (Complete)
```python
layer_data = {
    'filename': 'ce_lion_rampant.dds',
    'instances': [  # List of instance dicts
        {
            'pos_x': 0.3, 'pos_y': 0.3,
            'scale_x': 0.5, 'scale_y': 0.5,
            'rotation': 0.0, 'depth': 1.0
        },
        {
            'pos_x': 0.7, 'pos_y': 0.7,
            'scale_x': 0.5, 'scale_y': 0.5,
            'rotation': 0.0, 'depth': 1.0
        }
    ],
    'selected_instance': 0,  # Currently selected instance (for properties)
    'color1': [...],  # Colors apply to all instances
    'mask': [1, 0, 0],  # Mask applies to all instances
    'flip_x': False,  # Flip applies to all instances
    'flip_y': False
}
```

#### Implementation Phases

**Phase 2B: UI Indicators and Basic Management (4-6 hours)**
- Visual indicator in layer list for multi-instance layers
  - Badge/icon showing instance count (e.g., "×3" or special character)
  - Hover tooltip: "Multi-instance layer (3 instances)"
- Layer operations behavior:
  - **Duplicate Layer**: Creates separate layer with copies of all instances
  - **Delete Layer**: Removes entire multi-instance layer and all instances
  - **Add Layer**: Always creates single-instance layer (cannot add instances via this button)
- Transform widget: Operates on all instances as a group
- Property editors: Show properties of selected instance but editing affects first instance only

**Phase 2C: Split and Merge Commands (6-8 hours)**
- **Menu: Layers → Split Instances**
  - Enabled only when single multi-instance layer is selected
  - Breaks layer into N separate single-instance layers
  - Each layer preserves its instance's position, scale, rotation
  - Colors, mask, flip state copied to all new layers
- **Menu: Layers → Merge as Instances**
  - Enabled when 2+ compatible layers are selected
  - **Compatibility check:**
    - Same texture (`filename`)
    - Same colors (`color1`, `color2`, `color3`)
    - Same mask value
  - **Warning dialog if incompatible:**
    - "Selected layers have different properties (texture/colors/mask)."
    - "Merging will use the topmost layer's properties for all instances."
    - "Continue? [Yes] [No]"
  - Creates single layer with multiple instances
  - Each original layer becomes one instance (preserves pos/scale/rotation/depth)
  - Non-instance properties (color, mask, flip) taken from topmost selected layer

#### UI Mockup
```
┌─────────────────────────────┐
│ Layers                      │
├─────────────────────────────┤
│ [✓] Lion ×3                 │ ← Badge shows instance count
│ [ ] Shield                  │
│ [✓] Cross ×2                │ ← Hover: "Multi-instance layer (2 instances)"
│ [ ] Border                  │
├─────────────────────────────┤
│ [Add] [Delete] [Duplicate]  │
└─────────────────────────────┘

Properties Tab:
┌─────────────────────────────┐
│ Instance 1 of 3             │ ← Info label (read-only)
│ Position: [0.30][0.30]      │
│ Scale:    [0.50][0.50]      │
│ Rotation: [0.00]°           │
├─────────────────────────────┤
│ Applies to all instances:   │
│ Colors: [■][■][■]           │
│ Pattern Mask: [☑][☐][☐]    │
│ Flip: [☐ X] [☐ Y]           │
└─────────────────────────────┘
```

#### Files to Modify
- `editor/src/components/property_sidebar_widgets/layer_list_widget.py` - Add instance count badge
- `editor/src/components/property_sidebar.py` - Update property display for multi-instance
- `editor/src/main.py` - Add Split/Merge menu commands
- `editor/src/services/layer_operations.py` - Add split_layer() and merge_layers() functions
- `editor/src/components/dialogs/` - Create merge warning dialog (new file)

**Estimated Total Effort:** 10-14 hours

---

## Phase 3: Layout Templates

### 📋 PLANNED - Medium Priority

**Objective:** Provide quick insertion of multi-instance patterns from CK3 templates plus procedural generation.

### Template Sources

#### 1. CK3 Official Layouts (Hardcoded)
Extracted from `game/gfx/coat_of_arms/emblem_layouts/50_coa_designer_emblem_layouts.txt`:

- **single_centre**: 1 instance at center
- **diagonal_duo**: 2 instances diagonal
- **diagonal_trio**: 3 instances diagonal
- **layout_9**: 33 instances in 5×7 grid
- **layout_11**: Mirrored pair (negative scale)
- **layout_14-34**: Various decorative arrangements

Stored as Python dictionaries (no runtime file parsing):
```python
LAYOUTS = {
    'single_centre': [{'position': (0.5, 0.5), 'scale': (0.7, 0.7)}],
    'diagonal_duo': [
        {'position': (0.3, 0.3), 'scale': (0.4, 0.4)},
        {'position': (0.7, 0.7), 'scale': (0.4, 0.4)}
    ],
    # ... 30+ more layouts
}
```

#### 2. Procedural Generators
User-configurable parametric patterns:

- **50 Stars**: American flag canton (alternating 6-5-6-5 rows)
- **Circle**: Even distribution around circle (user specifies count)
- **Star Path**: Emblems arranged along star outline (user specifies points)
- **Triangle**: Emblems along triangle perimeter
- **Spiral**: Emblems spiral outward from center
- **Grid**: User-specified rows × columns
- **Border**: Emblems around shield perimeter
- **Line**: Straight line arrangement

**Generator Options (shown in dialog):**
- Count/Dimensions (number of emblems, rows, cols, points)
- Rotation Mode:
  - **Same**: All emblems same rotation (0° or user angle)
  - **Path-Aligned**: Rotate to face outward/follow path tangent
- Scale Fade:
  - **None**: Uniform scale (default)
  - **Linear**: Smooth gradient from start to end
  - **Exponential**: Non-linear progression

**Important:** Generated instances are static - no parametric metadata stored. To change parameters, user must undo and regenerate.

### UI Flow
1. Menu: **Insert → Emblem Layout Template**
2. Dialog shows two categories:
   - CK3 Official (instant application)
   - Procedural (opens parameter dialog)
3. User selects emblem texture and colors
4. System generates layer(s) with multiple instances

### Implementation
- Create: `editor/src/utils/layout_templates.py`
  - Hardcoded CK3 layout definitions
  - Procedural generator functions
- Modify: `editor/src/main.py` - Add menu action
- Create: `editor/src/components/layout_template_dialog.py` - Template picker + parameter UI

**Estimated Effort:** 8-12 hours

---

## Phase 4: Quality of Life Enhancements

### 📌 PLANNED - Low to Medium Priority

#### 4.1 Pattern-as-Emblem Support
**Problem:** Some CK3 emblems use pattern textures:
```
texture = "ce_pattern_vertical_split_01.dds"
texture = "ce_horizontal_stripes_04.dds"
```

**Solution:**
- Add pattern textures to emblem asset library
- Tag as "pattern-type" emblems
- Allow selection in emblem picker

**Files:** `ck3_assets/coa_emblems/metadata/*.json`, asset collection script  
**Effort:** 2-3 hours

#### 4.2 Optional Pattern Field
**Problem:** Some official CoAs omit `pattern` field

**Solution:**
- Make pattern optional in UI (currently may be required)
- Default to solid pattern if omitted
- Don't serialize if default

**Files:** `editor/src/services/file_operations.py`, `editor/src/main.py`  
**Effort:** 1 hour

#### 4.3 Variable Definitions Support
**Status:** Already works (parser ignores them)

Official CK3 files use variables:
```
@smCastleX = 0.27
@smCastleY = 0.23
```

Parser already handles these by skipping non-block lines. No action needed.

#### 4.4 Rotation Mode Selector for Group Transforms
**Problem:** Group rotation needs different behaviors depending on whether users want layer-level or instance-level transforms, especially for multi-instance layers.

**Solution:**
- Add dropdown selector (QComboBox) for rotation mode
- Located near "Minimal Transform" button in transform controls
- 6 modes covering shallow (layer-level) and deep (instance-level) transforms

**Rotation Modes:**

**Shallow Modes** (operate on layers as units):
1. **Rotate Only**
   - Each layer rotates around its own center
   - Multi-instance layers: instances orbit within layer (ferris wheel effect)
   - Single-instance layers: just rotate in place
   
2. **Orbit Only**
   - Layers orbit around selection center
   - No layer rotation applied
   - Instances maintain positions within their layers
   
3. **Both** (Orbit + Rotate)
   - Layers orbit around selection center AND rotate
   - Multi-instance layers: instances orbit within while layer group orbits
   - Combined ferris wheel effect

**Deep Modes** (operate on individual instances):
4. **Rotate Only Deep**
   - Every instance rotates around its own center
   - No position changes at all (pure spin)
   - Multi-instance layers: instances rotate independently, no orbital motion
   
5. **Orbit Only Deep**
   - Every instance orbits around selection center
   - No rotation changes (orientations preserved)
   - Treats all instances as independent entities
   
6. **Both Deep** (Orbit + Rotate)
   - Every instance orbits around selection center AND rotates individually
   - Complete independence - no layer grouping

**Key Distinction:**
- **Shallow**: Layer-level transforms. Multi-instance layers behave as groups.
- **Deep**: Instance-level transforms. Every instance is independent regardless of layer structure.

**Implementation:**
- Add QComboBox with 6 options
- Labels match mode names above for clarity
- Modify `CoA.rotate_selection()` to accept `rotation_mode` parameter
- Model layer handles transform routing based on mode
- UI passes selected mode from dropdown to model
- State persists per session

**Files:** 
- `editor/src/models/coa.py` - Add rotation_mode parameter to rotate_selection()
- `editor/src/components/transform_widget.py` - Add mode dropdown
- `editor/src/components/canvas_area.py` - Pass mode to model
**Effort:** 4-6 hours

#### 4.5 Performance Optimization
- Profile rendering with 33+ instance layers
- Consider GPU instanced rendering if needed
- Cache instance transforms
- Shader optimization (mask calculation)

**Effort:** 4-6 hours (as needed)

---

## Technical Implementation Notes

### Mask Rendering - Exclusive Masking Algorithm

CK3 pattern masks are **layered** (channels overlap), not independent regions.

**Critical:** To render "Channel 1 only", we must subtract overlapping channels:
```glsl
// For patternFlag = 1 (Channel 1 only)
patternMask = patternTexture.r - patternTexture.g - patternTexture.b;

// For patternFlag = 2 (Channel 2 only)  
patternMask = patternTexture.g - patternTexture.b;

// For patternFlag = 4 (Channel 3 only)
patternMask = patternTexture.b;

// For patternFlag = 3 (Channels 1 + 2)
patternMask = (patternTexture.r - patternTexture.g - patternTexture.b) 
            + (patternTexture.g - patternTexture.b);
            = patternTexture.r - patternTexture.b;
```

**Result:** Emblems render only in exclusive regions of selected channels.

### Pattern Texture Atlas Mapping

Patterns and emblems share texture atlases. Pattern UV coordinates must be passed to emblem shader:

```python
# Canvas widget binds pattern texture with UV coords
pattern_atlas_idx, p_u0, p_v0, p_u1, p_v1 = self.texture_uv_map[self.base_texture]
self.design_shader.setUniformValue("patternUV", p_u0, p_v0, p_u1, p_v1)
```

```glsl
// Shader maps screen-space to pattern UV space
uniform vec4 patternUV; // (u0, v0, u1, v1)
vec2 patternCoord = mix(patternUV.xy, patternUV.zw, maskCoord);
vec4 patternTexture = texture(patternSampler, patternCoord);
```

### Backwards Compatibility

**Old layer format:**
```python
layer = {
    'pos_x': 0.5,
    'pos_y': 0.5,
    'scale_x': 1.0,
    ...
}
```

**New format (Phase 2):**
```python
layer = {
    'instances': [
        {'pos_x': 0.5, 'pos_y': 0.5, 'scale_x': 1.0, 'scale_y': 1.0, 'rotation': 0.0, 'depth': 0.0}
    ],
    'selected_instance': 0,  # Index of currently selected instance
    'mask': None  # or [1, 0, 0]
}
```

**Migration strategy (Complete ✅):**
```python
# Automatic migration in _migrate_layer_to_instances()
if 'pos_x' in layer and 'instances' not in layer:
    # Convert old format to new
    layer['instances'] = [{
        'pos_x': layer.pop('pos_x'),
        'pos_y': layer.pop('pos_y'),
        'scale_x': layer.pop('scale_x'),
        'scale_y': layer.pop('scale_y'),
        'rotation': layer.pop('rotation', 0.0),
        'depth': layer.pop('depth', 0.0)
    }]
    layer['selected_instance'] = 0

if 'mask' not in layer:
    layer['mask'] = None  # Default to all channels
```

### Instance Layer Behavior

#### Layer Operations
- **Add Layer**: Creates new single-instance layer (no option to add instances)
- **Duplicate Layer**: Creates separate multi-instance layer with all instances copied
- **Delete Layer**: Removes entire layer and all its instances
- **Move Up/Down**: Moves entire multi-instance layer as a unit

#### Transform Operations
- All instances transform together as a group
- Canvas transform widget affects all instances uniformly
- **Implementation:** Reuse existing multi-selection group transform logic from `canvas_area.py`
  - Multi-instance layers treated as "permanent multi-selection"
  - AABB-based group transform already handles this case
- No individual instance selection on canvas
- Properties tab shows first instance's transform values

#### Split and Merge
- **Split Instances**: Menu command (Layers → Split Instances) breaks multi-instance layer into N single-instance layers
- **Merge as Instances**: Menu command (Layers → Merge as Instances) combines selected layers into one multi-instance layer
  - Compatibility check: same texture, colors, and mask
  - Warning dialog if properties don't match
  - Merge uses topmost layer's properties for all instances

**Note:** Auto-consolidation feature removed. Multi-instance layers are explicitly managed via Split/Merge commands only.

---

## Priority Matrix

| Feature | Priority | Effort | Impact | Status |
|---------|----------|--------|--------|--------|
| Pattern Mask System | ⚠️ CRITICAL | 4-6h | High | ✅ Complete |
| Multi-Instance Import/Export | High | 4-6h | High | ✅ Complete |
| Multi-Instance UI Indicators | High | 4-6h | High | 📋 Planned |
| Split/Merge Commands | High | 6-8h | High | 📋 Planned |
| Layout Templates (CK3) | Medium | 4-6h | Medium | 📋 Planned |
| Layout Templates (Procedural) | Medium | 4-6h | Medium | 📋 Planned |
| Pattern-as-Emblem | Low | 2-3h | Low | 📋 Planned |
| Optional Pattern Field | Low | 1h | Low | 📋 Planned |
| Performance Optimization | Low | 4-6h | Medium | 📋 As Needed |

---

## Testing Strategy

### Critical Tests
- ✅ Load all game samples (coa_sample_0 through coa_sample_12)
- ✅ Export and reimport - verify round-trip preservation
- ✅ Load official CK3 files from game directory
- ✅ Verify mask values preserved and functional
- ✅ Verify all instances preserved and rendered (Phase 2A)

### Integration Tests (Phase 2B/C)
- Load multi-instance CoA file (e.g., coa_sample_1.txt with 2 instances)
- Verify instance count badge displays correctly
- Split multi-instance layer → verify N separate layers created
- Select multiple compatible layers → merge as instances → verify single layer
- Attempt merge with incompatible layers → verify warning dialog appears
- Merge with override → verify topmost layer's properties applied
- Transform multi-instance layer → verify all instances move together
- Duplicate multi-instance layer → verify separate layer created
- Delete multi-instance layer → verify all instances removed

### Backwards Compatibility
- ✅ Load old project files (pre-Phase 2)
- ✅ Verify automatic migration to new data format
- ✅ Export from migrated project works correctly
- ✅ No data loss during migration

---

## Open Questions

### 1. Instance Count Badge Display
**Question:** What character/icon should represent multi-instance layers?

**Options:**
- A. "×N" (e.g., "×3") - Simple, clear, uses multiplication symbol
- B. "⚏ N" or "▤ N" - Icon + number
- C. "[N]" - Brackets around count
- D. Superscript number in parentheses

**Recommendation:** Option A ("×3") - Clear, compact, universally understood

### 2. Split Instance Naming
**Question:** How should split layers be named?

**Options:**
- A. "Lion #1", "Lion #2", "Lion #3" - Numbered suffix
- B. "Lion (1 of 3)", "Lion (2 of 3)", "Lion (3 of 3)" - Position indicator
- C. Original name for all - Let user rename if needed

**Recommendation:** Option A - Simple, follows common conventions

### 3. Merge Order Behavior
**Question:** Which layer's non-instance properties take precedence when merging?

**Answer (Decided):** Topmost selected layer's properties override all others.
- Consistent with "top layer wins" mental model
- User warned via dialog before merge

### 4. Transform Widget Multi-Instance Feedback
**Question:** Should transform widget visually indicate when operating on multi-instance?

**Options:**
- A. No special indication (current behavior)
- B. Show "[×N]" in widget header
- C. Different color/style for multi-instance transform

**Recommendation:** Option B - Subtle reminder without cluttering UI

---

## Development Timeline Estimate

### ✅ Completed: Phase 1 & Phase 2A (January 2026)
- Pattern Mask System fully implemented
- Multi-instance data model and migration
- Import/export all instances
- Canvas rendering all instances
- Backwards compatibility

### Week 1-2: Phase 2B - UI Indicators
- Instance count badge in layer list
- Hover tooltips
- Property display updates
- Testing with real game files

### Week 3-4: Phase 2C - Split/Merge Commands
- Split Instances menu command
- Merge as Instances menu command
- Compatibility checking
- Warning dialog for incompatible merges
- Testing complex scenarios

### Week 5-6: Layout Templates (Phase 3)
- Hard-code CK3 official layouts
- Implement procedural generators
- Template selection dialog
- Parameter input dialogs for procedural
- Preview visualization (optional)

### Week 7: Polish & Documentation
- Pattern-as-emblem support
- Optional pattern field
- Performance profiling and optimization
- Update documentation
- Final testing and release

**Total Estimated Time:** 6-7 weeks (assuming part-time development)

---

## References

- Game Samples: `examples/game_samples/`
- Research Notes: `docs/NEW_FEATURES_INVESTIGATION.md`
- Format Specifications: `docs/specifications/`
- Architecture: `docs/ARCHITECTURE.md`
- Parser Documentation: `docs/CoA_Parser_Documentation.md`

---

**Document Status:** Living document - update as features are completed or priorities change.
