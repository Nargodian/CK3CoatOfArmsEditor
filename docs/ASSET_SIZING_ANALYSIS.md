# CK3 Coat of Arms - Asset Sizing & Scaling Analysis

**Date:** January 27, 2026  
**Purpose:** Investigate the proper sizing relationships between patterns, emblems, frames, and masks to eliminate arbitrary scaling factors.

---

## Executive Summary

**Current Problem:** The editor uses arbitrary scaling factors (e.g., `1.62` for masks, `0.8` for base quad, `0.6` for emblem size) with no clear relationship to CK3's actual asset system.

**Root Cause:** Mixing different asset resolutions without understanding CK3's coordinate space conventions.

**Recommended Solution:** Adopt CK3's canonical coordinate system where all assets use normalized 0.0-1.0 space, with proper understanding of how different asset types relate.

---

## Asset Dimensions Analysis

### Actual Asset Sizes (Game Files)

| Asset Type | Typical Size | Examples |
|------------|--------------|----------|
| **Patterns** | 128×128 or 256×256 | `pattern__solid_designer.dds` (128×128), `pattern_barruly_08.dds` (256×256) |
| **Colored Emblems** | 128×128 or 256×256 | `ce_aegishjalmr.dds` (128×128), `ce__empty_designer.dds` (256×256) |
| **Textured Emblems** | 96×96 | `_default.dds` (96×96) |
| **CoA Mask** | 256×256 | `coa_mask_texture.dds` (256×256) |
| **Frames** | Variable | `bloc_frame.png` (160×160), `dynasty.png` (960×160) |

### Key Observations

1. **No universal asset size** - CK3 uses multiple resolutions (96, 128, 256 pixels)
2. **Patterns can be 128 OR 256** - not standardized
3. **CoA mask is 256×256** - this is the "canonical" resolution for the shield shape
4. **Emblems are mostly 128×128** - smaller than patterns and masks

---

## CK3's Coordinate System

### From Game Shaders & GUI Files

The game uses **normalized coordinates (0.0 to 1.0)** for all CoA positioning:

```cpp
// From gui_coatofarms.shader
UV = CoALeftTop_WidthHeight.xy + UV.xy * CoALeftTop_WidthHeight.zw;
```

```gui
// From coat_of_arms.gui
coat_of_arms = "[Character.GetPrimaryTitle.GetTitleCoA.GetTexture('(int32)56','(int32)56')]"
coat_of_arms_offset = "[GovernmentType.GetRealmMaskOffset]"
coat_of_arms_scale = "[GovernmentType.GetRealmMaskScale]"
```

**Key Insight:** CK3 positions and scales everything in **UV space (0.0-1.0)**, not pixel space. The actual texture resolution is irrelevant to positioning logic.

### CoA Rendering Pipeline

```
1. Pattern Layer (background)
   ├─ Texture: 128×128 or 256×256
   ├─ Coordinate space: 0.0-1.0 (fills entire shield)
   └─ Mask applied: coa_mask_texture.dds (256×256)

2. Emblem Layers (foreground)
   ├─ Texture: 128×128 or 256×256
   ├─ Instance position: (pos_x, pos_y) in 0.0-1.0 space
   ├─ Instance scale: (scale_x, scale_y) as multipliers
   ├─ Mask applied: SAME coa_mask_texture.dds
   └─ Pattern mask: samples pattern texture for channel masking

3. Frame Layer (border/overlay)
   ├─ Drawn on top
   ├─ Different sizes per government/title tier
   └─ No coordinate transformation
```

### The CoA Mask's Role

The `coa_mask_texture.dds` (256×256) defines the **shield shape**. Key properties:

- **Coordinate mapping:** Screen-space or CoA-space coordinates are transformed to 0.0-1.0
- **Wrapping:** Coordinates outside 0.0-1.0 are clamped or wrapped
- **Scale factor:** GUI files show different scales for different contexts (28×28, 44×44, 56×56 pixel displays)

From the shader:
```cpp
// Center and scale the mask coordinates
maskCoord -= 0.5;  // Center around origin
maskCoord *= scale_factor;  // Scale based on context
maskCoord += 0.5;  // Re-center to 0.0-1.0
```

**The magic number:** The mask needs to be scaled to match the aspect ratio and "coverage" of the shield shape in the rendered quad.

---

## Current Editor Issues

### Problem 1: Hardcoded Scale Factor `1.62`

```glsl
// design.frag, line 47
maskCoord*=1.62;// Scale to cover more area
```

**Why 1.62?** This appears to be a **fudge factor** to make the mask "look right" empirically.

**Actual reason:** The mask texture (256×256) needs to map correctly onto the base quad (which is rendered at `0.8 * zoom_level` in clip space, or 80% of viewport).

**Proper calculation:**
```
Rendered quad size in clip space: 0.8 × 2 = 1.6 units (-0.8 to +0.8)
Viewport normalized: 1.6 / 2.0 = 0.8 coverage
Mask needs to fill this: 1.0 / 0.8 = 1.25 scale factor
```

**Why 1.62 works:** It's close enough to make the shield look correct, but doesn't account for aspect ratio or proper UV mapping.

### Problem 2: Inconsistent Emblem Scaling

```python
# canvas_widget.py, line 332
half_width = scale_x * 0.6 * self.zoom_level
```

**Why 0.6?** Another empirical fudge to make emblems "look right" relative to the pattern.

**Issue:** This assumes emblems should be 60% the size of the base quad, but CK3's actual sizing is based on:
- Instance `scale` property (default 1.0)
- Relative to the CoA canvas (0.0-1.0 space)
- Not relative to viewport clip space

### Problem 3: Mixed Coordinate Systems

The editor mixes three coordinate systems:

1. **OpenGL clip space** (-1.0 to +1.0) - used for base quad vertices
2. **CoA UV space** (0.0 to 1.0) - used for positions in CoA data files
3. **Screen pixel space** - used for `gl_FragCoord` in shaders

**Conversions:**
```python
# Current (line 320)
center_x = (pos_x - 0.5) * 1.1 * self.zoom_level
```

This converts CoA UV (0.0-1.0) → clip space (-0.55 to +0.55 at zoom 1.0), but the `1.1` factor is arbitrary.

---

## How CK3 Actually Does It

### From Game Shaders

```cpp
// coat_of_arms.fxh
TextureSampler MaskMap {
    File = "gfx/coat_of_arms/coa_mask_texture.dds"
}

// UV clamping to prevent repeating at edges
UV = clamp(UV, TexelSize / 2, float2(1.0, 1.0) - TexelSize / 2);
UV = CoALeftTop_WidthHeight.xy + UV.xy * CoALeftTop_WidthHeight.zw;
```

**Key insight:** CK3 uses **atlas coordinates** (`CoALeftTop_WidthHeight`) to map into texture atlases, then applies the mask in the same UV space.

### Mask Coordinate Transformation

The game's GUI definitions show:
```
coat_of_arms_offset = "[GovernmentType.GetRealmMaskOffset]"
coat_of_arms_scale = "[GovernmentType.GetRealmMaskScale]"
```

These are **per-context adjustments**, not universal scaling factors. Different frame types (realm, dynasty, title) have different mask scales.

### The "Canonical" CoA Space

Based on the shader code and GUI definitions:

1. **CoA canvas is 1.0 × 1.0 units** - all positions/scales are relative to this
2. **Mask texture maps 1:1 to this space** - no inherent scaling needed
3. **Emblems position in this space** - `position = { 0.5 0.5 }` is center
4. **Emblem scale is a multiplier** - `scale = { 0.5 0.5 }` means 50% size
5. **"Size" is relative to the CoA canvas** - not to viewport pixels

---

## Recommended Solution

### Step 1: Define a Canonical Coordinate System

**Adopt CK3's convention:**
- CoA canvas is **1.0 × 1.0 logical units**
- All assets (patterns, emblems, masks) map into this space
- Viewport rendering scales this canvas to fit the window

### Step 2: Remove Arbitrary Scaling Factors

Replace:
```python
# OLD: Arbitrary factors
center_x = (pos_x - 0.5) * 1.1 * self.zoom_level
half_width = scale_x * 0.6 * self.zoom_level
```

With:
```python
# NEW: Direct mapping from CoA space to clip space
coa_to_clip_scale = 1.6  # CoA canvas fills 80% of viewport (-0.8 to +0.8 = 1.6)
center_x = (pos_x - 0.5) * coa_to_clip_scale * self.zoom_level
half_width = scale_x * (coa_to_clip_scale / 2.0) * self.zoom_level
```

**Rationale:** 
- Base quad is rendered at ±0.8 clip space (80% of viewport)
- CoA space 0.0-1.0 maps to clip space -0.8 to +0.8
- Conversion factor: `1.6 = 0.8 * 2`

### Step 3: Fix Mask Coordinate Mapping

Replace:
```glsl
// OLD: Arbitrary scale
maskCoord *= 1.62;
```

With:
```glsl
// NEW: Proper aspect ratio and coverage
vec2 maskCoord = gl_FragCoord.xy / viewportSize;  // 0.0-1.0 screen space
maskCoord.y = 1.0 - maskCoord.y;  // Flip Y (OpenGL bottom-up)

// Transform to CoA space (centered)
maskCoord -= 0.5;  // Center around origin
maskCoord *= 2.0 / 1.6;  // Adjust for base quad size (0.8 * 2 = 1.6)
maskCoord += 0.5;  // Re-center to 0.0-1.0

// Now maskCoord is in CoA UV space, sample mask directly
float coaMaskValue = texture(coaMaskSampler, maskCoord).r;
```

**Rationale:**
- Screen-space coordinates (pixels) → normalized 0.0-1.0
- Account for base quad only covering 80% of viewport
- Map directly to CoA space without arbitrary factors

### Step 4: Consistent Emblem Sizing

```python
# NEW: Scale relative to CoA canvas size
coa_canvas_size = 1.6  # Clip space size of CoA canvas
emblem_half_width = scale_x * (coa_canvas_size / 2.0) * self.zoom_level
emblem_half_height = scale_y * (coa_canvas_size / 2.0) * self.zoom_level
```

**Default emblem scale:**
- CK3 defaults: `scale = { 1.0 1.0 }` fills the CoA canvas
- Our default: `scale_x = 0.5` means emblem is 50% of canvas size
- To match CK3: We should use `scale_x = 1.0` as default, but that may be too large for UI

**Recommendation:** Keep `0.5` as default but understand it means "50% of CoA canvas".

### Step 5: Pattern-to-Emblem Relationship

**Current issue:** Pattern mask sampling uses screen-space coordinates that may not align with pattern rendering.

**Solution:** Use the **same coordinate transformation** for both:

```glsl
// Pattern rendering (base.frag) - already correct
vec2 patternCoord = vTexCoord;  // Direct UV from vertex shader

// Emblem mask sampling (design.frag)
vec2 patternCoord = mix(patternUV.xy, patternUV.zw, maskCoord);
```

The `maskCoord` must be in CoA UV space (0.0-1.0), then remapped to pattern atlas UV.

---

## Proposed Implementation Changes

### File: `canvas_widget.py`

```python
# Define canonical constants at top of file
COA_CANVAS_CLIP_SIZE = 1.6  # CoA canvas size in OpenGL clip space (-0.8 to +0.8)
COA_CANVAS_COVERAGE = 0.8   # Percentage of viewport covered by CoA

# Update base quad rendering (currently 0.8)
base_size = COA_CANVAS_COVERAGE * self.zoom_level  # More explicit

# Update emblem positioning (currently 1.1 factor)
center_x = (pos_x - 0.5) * COA_CANVAS_CLIP_SIZE * self.zoom_level
center_y = -(pos_y - 0.5) * COA_CANVAS_CLIP_SIZE * self.zoom_level

# Update emblem scaling (currently 0.6 factor)
half_width = scale_x * (COA_CANVAS_CLIP_SIZE / 2.0) * self.zoom_level
half_height = scale_y * (COA_CANVAS_CLIP_SIZE / 2.0) * self.zoom_level
```

**Benefit:** All sizing derives from one constant (`COA_CANVAS_CLIP_SIZE`), making it easy to adjust if needed.

### File: `design.frag`

```glsl
// Update mask coordinate calculation
vec2 maskCoord = gl_FragCoord.xy / viewportSize;
maskCoord.y = 1.0 - maskCoord.y;  // Flip Y for OpenGL

// Transform screen space to CoA UV space
maskCoord -= 0.5;  // Center
maskCoord *= 2.0 / 1.6;  // Scale for CoA canvas coverage (1.6 = 0.8 * 2)
maskCoord += 0.5;  // Re-center

// Sample mask (no additional scaling needed)
vec4 maskSample = texture(coaMaskSampler, maskCoord);
float coaMaskValue = max(max(maskSample.r, maskSample.g), max(maskSample.b, maskSample.a));

// Pattern sampling uses same maskCoord
vec2 patternCoord = mix(patternUV.xy, patternUV.zw, maskCoord);
vec4 patternTexture = texture(patternSampler, patternCoord);
```

**Benefit:** Removes arbitrary `1.62` factor, uses proper coordinate transformation.

### File: `base.frag`

No changes needed - base pattern already renders correctly using vertex UVs.

---

## Verification Strategy

### Test 1: Circle Pattern Alignment

1. Load a coat of arms with circular pattern (e.g., `pattern_solid.dds`)
2. Add centered emblem at position `(0.5, 0.5)`, scale `(0.5, 0.5)`
3. **Expected:** Emblem is perfectly centered in pattern
4. **Current:** May be slightly off-center due to coordinate mismatch

### Test 2: Mask Edge Alignment

1. Load coat of arms with emblem near edge of shield
2. Verify emblem is clipped by shield mask, not by viewport edges
3. **Expected:** Clean clipping following shield shape
4. **Current:** May have artifacts if mask scaling is wrong

### Test 3: Multi-Instance Spacing

1. Load official CK3 file with multi-instance emblem (e.g., `layout_9` with 33 instances)
2. Compare spacing and positioning to game rendering
3. **Expected:** Identical layout to game
4. **Current:** Likely off due to coordinate system issues

### Test 4: Frame Overlay

1. Add frame to coat of arms
2. Verify frame aligns with pattern and emblem edges
3. **Expected:** Frame perfectly outlines the shield
4. **Current:** Unknown (frames not yet implemented)

---

## Aspect Ratio Considerations

### Current Assumption: Square Canvas

The editor currently assumes CoA is square (1:1 aspect ratio). This matches most CK3 patterns and the mask texture (256×256).

### Potential Issue: Non-Square Frames

Some CK3 frames are not square:
- `dynasty.png`: 960×160 (6:1 ratio)
- `coa_topframe_bloc.png`: 116×36 (3.2:1 ratio)

**Question:** Are these frames overlays, or do they define the CoA canvas shape?

**Answer from GUI files:**
```gui
framesize = { 32 32 }  // Most CoA displays are square
framesize = { 52 52 }  // Larger square
```

**Conclusion:** Frames are **overlays** on a square CoA canvas. The canvas itself is always 1:1 aspect ratio.

---

## Material Mask & Noise Texture

These use the same coordinate system as the CoA mask:

```glsl
// Currently in design.frag
vec4 materialMask = texture(materialMaskSampler, maskCoord);
float noise = texture(noiseSampler, maskCoord).r;
```

**Status:** Should work correctly once `maskCoord` is fixed (Step 3 above).

---

## Summary of Arbitrary Factors

| Current Factor | Location | Purpose | Recommended Replacement |
|----------------|----------|---------|-------------------------|
| `0.8` | `canvas_widget.py:212` | Base quad size | Keep (defines viewport coverage) |
| `1.1` | `canvas_widget.py:320` | Emblem position scale | Replace with `1.6` (COA_CANVAS_CLIP_SIZE) |
| `0.6` | `canvas_widget.py:332` | Emblem size scale | Replace with `0.8` (half of COA_CANVAS_CLIP_SIZE) |
| `1.62` | `design.frag:47` | Mask coordinate scale | Replace with `2.0 / 1.6` (inverse of canvas coverage) |

---

## Action Items

### High Priority
1. ✅ **Document current state** (this document)
2. ⚠️ **Define canonical constants** (`COA_CANVAS_CLIP_SIZE`, etc.)
3. ⚠️ **Update `canvas_widget.py`** with proper coordinate conversion
4. ⚠️ **Update `design.frag`** with proper mask coordinate transformation
5. ⚠️ **Test with official CK3 files** to verify positioning accuracy

### Medium Priority
6. Add coordinate system diagram to documentation
7. Create test cases for edge alignment
8. Verify pattern mask alignment with new coordinates

### Low Priority
9. Profile performance impact of coordinate calculations
10. Consider pre-calculating coordinate transforms on CPU

---

## Appendix A: Coordinate System Diagram

```
┌─────────────────────────────────────────┐
│         OpenGL Clip Space               │
│   (-1, +1)          (+1, +1)            │
│      ┌─────────────────┐                │
│      │                 │                │
│      │  CoA Canvas     │                │
│      │  (-0.8, +0.8)   │  (+0.8, +0.8) │
│(-1,0)│     ╔═══════╗   │           (+1,0)│
│      │    ╔╝       ╚╗  │                │
│      │   ╔╝  (0,0)  ╚╗ │  ← CoA UV     │
│      │   ║           ║ │     Space      │
│      │   ╚╗         ╔╝ │   (0.0-1.0)   │
│      │    ╚╗       ╔╝  │                │
│      │     ╚═══════╝   │                │
│      │                 │                │
│      │  (-0.8, -0.8)   │  (+0.8, -0.8) │
│      └─────────────────┘                │
│   (-1, -1)          (+1, -1)            │
└─────────────────────────────────────────┘

Transformations:
1. CoA UV (0.0-1.0) → Clip Space (-0.8 to +0.8):
   clip_x = (uv_x - 0.5) * 1.6
   clip_y = (uv_y - 0.5) * 1.6

2. Screen Pixels → CoA UV:
   uv_x = (pixel_x / viewport_width - 0.5) * (2.0 / 1.6) + 0.5
   uv_y = (1.0 - pixel_y / viewport_height - 0.5) * (2.0 / 1.6) + 0.5
```

---

## Appendix B: CK3 Pattern Mask System

The pattern mask system uses **RGB channels** of the pattern texture to define up to 3 regions:

```
Pattern Texture:
- R channel (mask 1): First color region
- G channel (mask 2): Second color region  
- B channel (mask 3): Third color region
```

**Exclusive masking:** Channels overlap, so to render "only in red region":
```glsl
float mask1_exclusive = patternTexture.r - patternTexture.g - patternTexture.b;
```

**Coordinate alignment:** Pattern and emblem must sample at the **same CoA UV coordinates** for masks to align correctly.

**Current status:** Implemented in `design.frag` with bitwise flags, uses `patternCoord` derived from `maskCoord`.

---

## Appendix C: Frame System (Not Yet Implemented)

CK3 frames consist of multiple layers:

1. **Frame Shadow** (`coa_realm_shadow`): Soft shadow behind CoA
2. **Frame Border** (`coa_realm_overlay`): Main frame graphic
3. **Top Frame** (`coa_realm_topframe`): Crown or decorative top piece

**Rendering order:**
```
1. Shadow (behind CoA)
2. Pattern + Emblems (CoA content)
3. Frame overlay (on top of CoA)
4. Top frame (on top of everything)
```

**Size variants:** 28×28, 44×44, 52×52, 56×56 (pixels) - these are GUI display sizes, not asset resolutions.

**Coordinate system:** Frames use same UV space as CoA canvas but may have offset and scale adjustments.

---

**End of Analysis**
