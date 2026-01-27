# CK3 CoA Editor - Development Roadmap

**Last Updated:** January 27, 2026  
**Status:** Pattern Mask Feature - ✅ Implemented  

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

### ✅ Completed Features
- **Pattern Mask System** (Phase 1)
  - Data model: `mask` field in layer data as `[int, int, int]` list
  - Serialization: Round-trip support for mask field
  - UI: Pattern Mask section with 3 checkboxes and color indicators
  - Shader: Bitwise flag system with exclusive masking (subtraction algorithm)
  - Canvas: Pattern texture UV mapping with atlas coordinates

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

### 🔄 PLANNED - High Priority

**Objective:** Support multiple instances per emblem layer (matches CK3's official file format).

### Current Limitation
```python
# Parser reads all instances but editor only uses first
instances = emblem.get('instance', [])
instance = instances[0]  # ❌ ONLY USES FIRST
```

### Target Architecture

#### Data Model Update
```python
layer_data = {
    'filename': 'ce_lion_rampant.dds',
    'instances': [  # List of instance dicts
        {
            'pos_x': 0.3,
            'pos_y': 0.3,
            'scale_x': 0.5,
            'scale_y': 0.5,
            'rotation': 0.0,
            'depth': 1.0
        },
        {
            'pos_x': 0.7,
            'pos_y': 0.7,
            'scale_x': 0.5,
            'scale_y': 0.5,
            'rotation': 0.0,
            'depth': 1.0
        }
    ],
    'color1': [...],  # Colors apply to all instances
    'mask': [1, 0, 0],  # Mask applies to all instances
}
```

#### Implementation Phases

**Phase 2A: Import/Export Support (4-6 hours)**
- Read all instances from emblems during import
- Store multiple instances in layer data
- Export all instances to CoA format
- Canvas renders all instances for each layer
- Backwards compatibility: migrate old single-instance format

**Phase 2B: Instance Management UI (8-12 hours)**
- Instance list view in property sidebar
- Add/Remove/Duplicate instance buttons
- Per-instance property editing (position, scale, rotation, depth)
- Visual indicators for multi-instance layers in layer list
- Canvas interaction: click to select individual instances

**Phase 2C: Advanced Features (6-8 hours)**
- **Break Apart**: Right-click → "Break Apart Instances" (ungroup to separate layers)
- **Manual Grouping**: Select multiple compatible layers → "Group as Instances"
- **Auto-Consolidation**: Preference setting to auto-group on export
  - Detects consecutive layers with same texture/colors/mask
  - Consolidates to single emblem with multiple instances
  - Reduces file size, matches CK3 convention

#### UI Mockup
```
┌─────────────────────────────┐
│ Instances (3)               │
├─────────────────────────────┤
│ ☑ #1: (0.3,0.3) s:0.5 r:0° │
│ ☐ #2: (0.7,0.3) s:0.5 r:0° │ ← disabled/hidden
│ ☑ #3: (0.5,0.7) s:0.5 r:0° │
├─────────────────────────────┤
│ Selected Instance #1:       │
│ Position: [0.30][0.30]      │
│ Scale:    [0.50][0.50]      │
│ Rotation: [0.00]°           │
│ Depth:    [1.00]            │
├─────────────────────────────┤
│ [Add] [Remove] [Break Apart]│
└─────────────────────────────┘
```

#### Files to Modify
- `editor/src/services/layer_operations.py` - Multi-instance data model
- `editor/src/components/canvas_widget.py` - Render all instances
- `editor/src/components/property_sidebar.py` - Instance manager UI
- `editor/src/services/file_operations.py` - Export multiple instances
- `editor/src/main.py` - Backwards compatibility migration

**Estimated Total Effort:** 18-26 hours

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

#### 4.4 Performance Optimization
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
        {'pos_x': 0.5, 'pos_y': 0.5, 'scale_x': 1.0, ...}
    ],
    'mask': None  # or [1, 0, 0]
}
```

**Migration strategy:**
```python
# On file load
if 'pos_x' in layer and 'instances' not in layer:
    # Convert old format to new
    layer['instances'] = [{
        'pos_x': layer.pop('pos_x'),
        'pos_y': layer.pop('pos_y'),
        'scale_x': layer.pop('scale_x'),
        'scale_y': layer.pop('scale_y'),
        'rotation': layer.pop('rotation', 0.0),
        'depth': layer.pop('depth', 1.0)
    }]

if 'mask' not in layer:
    layer['mask'] = None  # Default to all channels
```

### Instance Auto-Consolidation Logic

**Detection criteria:**
- Consecutive layers in stack
- Same `filename` (texture)
- Same `color1`, `color2`, `color3`
- Same `mask` value
- Only transforms differ

**Preference setting:**
- `Settings → Export → Auto-consolidate instances`
- Default: **OFF**
- When ON: Export consolidates matching layers into single `colored_emblem` with multiple `instance` blocks

**Important:** Pre-existing consolidated instances (from imported files) are always preserved regardless of setting.

---

## Priority Matrix

| Feature | Priority | Effort | Impact | Status |
|---------|----------|--------|--------|--------|
| Pattern Mask System | ⚠️ CRITICAL | 4-6h | High | ✅ Complete |
| Multi-Instance Import/Export | High | 4-6h | High | 📋 Planned |
| Multi-Instance UI | High | 8-12h | Very High | 📋 Planned |
| Instance Grouping/Ungrouping | Medium | 6-8h | High | 📋 Planned |
| Layout Templates (CK3) | Medium | 4-6h | Medium | 📋 Planned |
| Layout Templates (Procedural) | Medium | 4-6h | Medium | 📋 Planned |
| Pattern-as-Emblem | Low | 2-3h | Low | 📋 Planned |
| Optional Pattern Field | Low | 1h | Low | 📋 Planned |
| Performance Optimization | Low | 4-6h | Medium | 📋 As Needed |

---

## Testing Strategy

### Critical Tests
- ✅ Load all game samples (coa_sample_0 through coa_sample_11)
- ✅ Export and reimport - verify round-trip preservation
- ✅ Load official CK3 files from game directory
- ✅ Verify mask values preserved and functional
- 🔄 Verify all instances preserved (Phase 2)

### Integration Tests (Phase 2)
- Create multi-instance layer → export → verify structure
- Edit instances → verify changes persist
- Undo/redo with multi-instance layers
- Copy/paste layers with multiple instances
- Break apart instances → verify separate layers created
- Group layers as instances → verify consolidation
- Auto-consolidation on export (with preference enabled)

### Backwards Compatibility
- Load old project files (pre-Phase 2)
- Verify migration to new data format
- Export from migrated project works correctly
- No data loss during migration

---

## Open Questions

### 1. Instance Selection UI
**Question:** How should users select individual instances in multi-instance layers?

**Options:**
- A. Click cycles through overlapping instances
- B. Context menu lists all instances at click position
- C. Instance list in sidebar is primary selection method (click to select)
- D. Combination: sidebar list + canvas click highlights

**Recommendation:** Option D (sidebar list primary, canvas provides visual feedback)

### 2. Import Default Behavior
**Question:** When importing CoAs with multiple instances, default behavior?

**Options:**
- A. Always import grouped (preserves structure)
- B. Always import separated (easier editing)
- C. Ask user every time (flexible but annoying)
- D. User preference setting (best?)

**Recommendation:** Option D with default=grouped (preserves file structure, matches CK3 convention)

### 3. Instance Auto-Consolidation Sensitivity
**Question:** When detecting "same colors" for consolidation, how strict?

**Options:**
- A. Exact RGB match only
- B. Allow small tolerance (e.g., ±0.01 per channel)

**Recommendation:** Option A (exact match) - user can manually group if needed

### 4. Mask Channel Detection
**Question:** How to determine available mask channels in a pattern?

**Options:**
- A. Hard-code known patterns (fragile, requires maintenance)
- B. Probe pattern texture for mask channel data (runtime analysis)
- C. Default to 3 channels, disable unavailable ones in UI

**Recommendation:** Option C with future enhancement to Option B

---

## Development Timeline Estimate

### Week 1: Multi-Instance Foundation
- Implement multi-instance data model
- Update import/export logic
- Basic canvas rendering of all instances
- Backwards compatibility migration
- Testing and bug fixes

### Week 2: Instance Management UI
- Instance list view in property sidebar
- Add/Remove/Duplicate functionality
- Per-instance property editing
- Canvas selection interaction
- Layer list visual indicators

### Week 3: Advanced Instance Features
- Break apart instances
- Manual grouping
- Auto-consolidation preference and logic
- Testing complex scenarios

### Week 4: Layout Templates
- Hard-code CK3 official layouts
- Implement procedural generators
- Template selection dialog
- Parameter input dialogs for procedural
- Preview visualization (optional)

### Week 5: Polish & Documentation
- Pattern-as-emblem support
- Optional pattern field
- Performance profiling and optimization
- Update documentation
- Final testing and release

**Total Estimated Time:** 5-6 weeks (assuming part-time development)

---

## References

- Game Samples: `examples/game_samples/`
- Research Notes: `docs/NEW_FEATURES_INVESTIGATION.md`
- Format Specifications: `docs/specifications/`
- Architecture: `docs/ARCHITECTURE.md`
- Parser Documentation: `docs/CoA_Parser_Documentation.md`

---

**Document Status:** Living document - update as features are completed or priorities change.
