# CK3 Frame and CoA Sizing Analysis

## Frame File Dimensions

### Main Shield Frames
**Location:** `gfx/interface/coat_of_arms/frames/`

**Standard Frame Format:** 960×160 pixels (6x1 horizontal strip)
- Each frame contains 6 splendor levels: 160×160 each
- Files using this format: **33 frames total**
  - `dynasty.dds` (960×160)
  - `house.dds` (960×160)
  - `house_china.dds` (960×160)
  - `house_frame_02.dds` through `house_frame_30.dds` (960×160)
  - `house_japan.dds` (960×160)

**Special Frame Formats:**
- `bloc_frame.dds`: **160×160** (single frame, no splendor variants)
- `coa_topframe_bloc.dds`: **116×36** (top decoration)

### Frame Masks
**All mask files:** 160×160 pixels (single resolution)
- Files: 34 mask files total
- Format: `*_mask.dds`
- All use 160×160 regardless of source frame size

### Crown Decorations (Top Frames)
Multiple sizes based on UI scale:
- `crown_strip_28.dds` - 32×22 framesize
- `crown_strip_44.dds`
- `crown_strip_62.dds`
- `crown_strip_86.dds`
- `crown_strip_115.dds` - Largest variant
- `topframe_28.dds` through `topframe_115.dds` - Various sizes

## CoA Rendering Scale

### From CK3 GUI Configuration
**File:** `data_binding/tgp_data_bindings.txt`

```
DefaultCoATitleMaskOffset = "(CVector2f)0.0,0.04"
DefaultCoATitleMaskScale = "(CVector2f)0.9,0.9"
```

### Key Findings
1. **CoA Scale:** 0.9 (90% of shield area)
2. **Vertical Offset:** 0.04 (4% shift upward)
3. **Horizontal Offset:** 0.0 (centered)

## Implications for Editor

### Current Implementation
- Using `COMPOSITE_SCALE = 0.5` (50%) - **INCORRECT**
- Frame textures: 960×160 (6×160 horizontal strip)
- Frame masks: 160×160 (single resolution)

### Correct Implementation
Should use:
- **COMPOSITE_SCALE = 0.9** (matches CK3's 90% scale)
- **Vertical offset:** Apply 0.04 upward shift in composite shader
- Frame UV coordinates: Already correctly implemented (u0 = frame_index/6, u1 = (frame_index+1)/6)

### Frame Mask Coordinate System
- Masks are 160×160 single images
- Should sample mask at CoA coordinates (not frame sprite coordinates)
- Mask determines where CoA is visible within shield shape

## Size Categories

### Different CoA Display Sizes in CK3
1. **28px** - Smallest (character portraits, lists)
2. **44px** - Small (compact UI)
3. **62px** - Medium (standard UI)
4. **86px** - Large (detailed views)
5. **115px** - Extra large (character sheet, designer)

Each size has matching:
- Frame texture (e.g., `house_frame_*.dds` at 960×160 for all sizes)
- Crown decoration (e.g., `crown_strip_28.dds`)
- Top frame (e.g., `topframe_28.dds`)

## Colored Emblems with Frames
**Location:** `gfx/coat_of_arms/colored_emblems/`

These are decorative frame emblems (not shield frames):
- Norse/Viking frames: `ce_frame_circle_borre_*.dds`
- Indian frames: `ce_india_doted_frame*.dds`
- Kamon (Japanese) frames: `ce_kamon_frame_*.dds`
- African frames: `ce_african_frame*.dds`
- Islamic frames: `ce_rubh_el_hizb_iranian_frame.dds`
- Seal frames: `ce_seal_frame*.dds`, `ce_seal_pictorial_frame*.dds`

These are used as colored emblems/charges, not as actual shield frames.

## Recommendations

1. **Change COMPOSITE_SCALE from 0.5 to 0.9**
2. **Add vertical offset of 0.04** (4% upward shift)
3. **Verify frame mask sampling** uses CoA coordinates, not frame sprite coordinates
4. **Test with different frames** to ensure mask clipping works correctly
5. **Consider adding horizontal offset support** (currently 0.0, but may vary by culture)

## Culture-Specific Variations

From GUI references:
```
coat_of_arms_offset = "[Dynasty.GetCulture.GetCultureDynastyCoAOffset]"
coat_of_arms_scale = "[Dynasty.GetCulture.GetCultureDynastyCoAScale]"
```

Some cultures may have different offsets/scales:
- Dynasty CoAs
- Government-specific frames (realm frames)
- Asian frames (China, Japan) - already have separate frame files

The 0.9/0.04 values are **defaults** - specific frames may override these.
