# New CoA Features Investigation

**Date:** January 27, 2026  
**Status:** ✅ COMPLETED - Empirical testing complete  
**Samples Analyzed:** 
- coa_sample_8.txt through coa_sample_11.txt (user-provided game exports)
- Official CK3 game files from `E:\Program Files (x86)\Steam\steamapps\common\Crusader Kings III\game\common\coat_of_arms\coat_of_arms\`
- Custom test cases validated in-game

## Features Discovered

### 1. **`mask={ ... }` Field** ⚠️ NOT CURRENTLY SUPPORTED ✅ FULLY UNDERSTOOD

**Location:** Inside `colored_emblem` blocks  
**Format:** Array of 1-3 integers (values 0-3)  

**Purpose:** ✅ CONFIRMED - Selects which pattern mask channels to render emblem in

**How It Works:**
- Patterns have built-in mask channels (mask1, mask2, mask3) defining different regions
- `mask = { X Y Z }` selects which channels from the pattern to render in
- Position in array maps to mask channel: first=channel1, second=channel2, third=channel3
- Value indicates which channel number to use (1, 2, 3) or 0 for none
- No mask = `{ 1 2 3 }` (render everywhere)

**Examples with Verified Behavior:**
```
# Render only where pattern's mask channel 1 is active
mask = { 1 0 0 }

# Render only where pattern's mask channel 2 is active  
mask = { 0 2 0 }

# Render in both mask channels 1 and 2 (combined regions)
mask = { 1 2 0 }

# No mask = render everywhere (all mask regions)
# (equivalent to { 1 2 3 })
```

**Common Pattern:** Multiple copies of same emblem with different colors, each masked to different pattern regions to create multi-colored striped/divided effects

**Tested Examples:**
- Three-color horizontal striped lion: 3 lions with masks `{ 1 0 0 }`, `{ 0 2 0 }`, `{ 0 0 3 }` = red/green/purple horizontal stripes
- Two-color diagonal lion: 2 lions with masks `{ 1 0 0 }`, `{ 0 2 0 }` = counterchanged colors across diagonal

**Official Game Files Use:**
- Single-value masks: `mask = { 1 }` or `mask = { 2 }` (shorthand for `{ 1 0 0 }` or `{ 0 2 0 }`)
- Three-value masks: `mask = { 1 0 0 }`, `{ 0 2 0 }` (full specification)

**Current Status:**
- ❌ Not stored in layer data structure
- ❌ Not displayed/editable in UI
- ❌ Not serialized when exporting
- ❌ Not used in shader rendering
- ✅ Parser can read it (generic field support)
- ✅ Behavior fully understood through empirical testing

**Implementation Requirements:**
- Add `mask` field to layer data structure (list of 1-3 integers)
- Pattern texture provides mask channel data (specific channels in DDS)
- Shader must sample pattern mask channels and use as alpha mask for emblem
- UI: Dropdown or checkboxes to select mask channels (1, 2, 3, or combinations)
- Default: No mask = render everywhere

---

### 2. **Multiple Instances Per Emblem** ⚠️ PARTIALLY SUPPORTED ✅ FULLY UNDERSTOOD

**Feature:** Single `colored_emblem` block containing multiple `instance` sub-blocks

**Examples From Official Files:**
```
# From 01_landed_titles.txt - b_st_davids
colored_emblem = {
    texture = "ce_cinquefoil.dds"
    color1 = "black"
    instance = { position = { 0.50 0.20 } scale = { 0.2 0.2 } } #top
    instance = { position = { 0.20 0.50 } scale = { 0.2 0.2 } } #middle
    instance = { position = { 0.50 0.50 } scale = { 0.2 0.2 } }
    instance = { position = { 0.80 0.50 } scale = { 0.2 0.2 } }
    instance = { position = { 0.50 0.80 } scale = { 0.2 0.2 } } #bottom
}

# From 01_landed_titles.txt - c_al_aqabah (8 instances!)
colored_emblem = {
    texture = "ce_clam.dds"
    color1 = "red"
    instance = { position = { 0.5 0.1 } scale = { 0.2 0.2 } }
    instance = { position = { 0.19 0.1 } scale = { 0.2 0.2 } }
    instance = { position = { 0.79 0.1 } scale = { 0.2 0.2 } }
    instance = { position = { 0.2 0.38 } scale = { 0.2 0.2 } }
    instance = { position = { 0.8 0.38 } scale = { 0.2 0.2 } }
    instance = { position = { 0.27 0.65 } scale = { 0.2 0.2 } }
    instance = { position = { 0.73 0.65 } scale = { 0.2 0.2 } }
    instance = { position = { 0.5 0.85 } scale = { 0.2 0.2 } }
}
```

**Verified Behavior:**
- ✅ Multiple instances work perfectly - all instances render at their specified positions
- ✅ Each instance can have independent position, scale, rotation, depth
- ✅ All instances share parent emblem's texture, colors, mask
- ✅ Depth layering: Lower depth values render in front (depth=1.0 on top, depth=3.0 in back)
- ✅ No instance block = defaults to center position (0.5, 0.5), scale 1.0
- ✅ Negative scale values create horizontal flip
- ✅ Rotation works per instance (in degrees)

**Benefit:** Allows placing the same emblem multiple times without duplicating the entire emblem definition. Reduces file size and maintains consistency.

**Frequency in Official Files:** Very common! Used extensively for:
- Repeating symbols (fleurs-de-lis, stars, crosses)
- Border decorations
- Pattern fills
- Symmetric designs

**Current Status:**
- ✅ Parser can read all instances
- ⚠️ Editor only imports **first instance** (ignores rest)
- ❌ Editor only exports **single instance** per layer
- ❌ No UI to add/manage multiple instances
- ❌ Would require architectural change (instances as sub-items of layers?)
- ✅ Behavior fully validated through in-game testing

---

### 3. **`color2` and `color3` on Emblems** ✅ ALREADY SUPPORTED

**Feature:** Emblems can define all three colors, not just `color1`

**Examples:**
```
colored_emblem={
    color1=red
    color2=yellow
    color3=white
    texture="ce_lion_rampant.dds"
}
```

**Current Status:**
- ✅ Fully supported in editor
- ✅ Parser handles it
- ✅ Serializer outputs it
- ✅ UI allows editing all three colors

---

### 4. **Title CoAs (without `custom=yes`)** ✅ ALREADY HANDLED

**Feature:** CoA definitions for titles that don't include the `custom=yes` flag

**Examples:**
- `coa_title_1185={...}`
- `coa_title_2457={...}`
- `coa_title_3364={...}`
- `coa_title_149={...}`

**Current Status:**
- ✅ Parser handles presence/absence of `custom=yes`
- ✅ Editor can work with both types

---

### 5. **Additional Pattern Files** ✅ ALREADY SUPPORTED

**New patterns observed:**
- `temp_pattern_bendy_special.dds`
- `pattern_diagonal_split_01.dds`
- `pattern_checkers_08.dds`
- `pattern_vertical_split_01.dds`

**Current Status:**
- ✅ Parser reads any pattern filename
- ⚠️ These specific textures may not be in asset library yet

---

## Priority Assessment

### HIGH PRIORITY - `mask` Field
**Impact:** ✅ CRITICAL - Required for accurate round-trip editing of existing CoAs  
**Complexity:** Medium
- Add `mask` field to layer data structure (list of 1-3 integers)
- UI widget to select mask channels (checkboxes or dropdown: mask1, mask2, mask3)
- Serialize/deserialize support
- Shader implementation: Sample pattern mask channels, use as alpha mask for emblem
- **Ground truth validated** - behavior fully understood from in-game testing

### MEDIUM-HIGH PRIORITY - Multiple Instances
**Impact:** Large - Many official CoAs use this feature extensively  
**Complexity:** High
- Requires architectural decision: How to represent in UI?
  - Option A: Expand single layer into multiple sub-instances (tree view)
  - Option B: Auto-duplicate layers on import, merge on export (hidden complexity)
  - Option C: New "instance manager" UI component per layer
- Would significantly improve efficiency for complex designs
- **Verified working** - All instance parameters tested and confirmed in-game

### LOW PRIORITY - Asset Library
**Impact:** User can manually add pattern files  
**Complexity:** Low - just asset collection

---

## Key Findings from Empirical Testing

### Mask System Architecture
✅ **Single pattern per CoA** - All emblems reference mask channels from THE pattern texture
✅ **Pattern provides mask regions** - Pattern DDS has mask channels built in (mask1, mask2, mask3)
✅ **Emblem selects which masks** - `mask = { 1 0 0 }` means "render where pattern's mask1 is active"
✅ **Simple implementation** - Just alpha masking: sample pattern mask channel, multiply with emblem alpha

### Instance System Architecture  
✅ **Multiple instances fully functional** - Tested 3-4 instances per emblem
✅ **Depth layering confirmed** - Lower depth = closer/in front (depth 1.0 > depth 3.0)
✅ **Independent transforms** - Each instance has own position, scale, rotation, depth
✅ **Negative scale = flip** - scale -1.0 mirrors horizontally
✅ **Default values work** - No instance block = center at (0.5, 0.5), scale 1.0

### Edge Cases Discovered
✅ **Empty instance block** - `instance = {}` same as no instance (uses defaults)
✅ **Pattern field optional** - Defaults to solid color1 if omitted
✅ **Mask with no pattern** - Behavior undefined (patterns provide mask data)
✅ **Rotation per instance** - Each instance can rotate independently

---

## Additional Findings from Official Game Files

### Variable Definitions
The official CoA files use variable definitions at the top:
```
@smCastleX = 0.27
@smCastleY = 0.23
@smLysX = 0.23
@smLysY = 0.26
@smCross = 0.22
```

These can be referenced in position/scale values but are not commonly used in the main definitions.

### CoAs Without Pattern
Some CoAs omit the `pattern` field entirely:
```
c_agen = {
    color1 = "red"
    color2 = "yellow"
    colored_emblem = {
        texture = "ce_pattern_vertical_split_01.dds"
        color1 = "red"
        color2 = "red"
    }
    ...
}
```

When `pattern` is omitted, the game likely uses a default pattern or treats `color1` as a solid background.

### Special Texture Names
Some emblems use pattern textures AS emblems:
```
texture = "ce_pattern_vertical_split_01.dds"
texture = "ce_horizontal_stripes_04.dds"
texture = "ce_diagonal_stripe_02_striped.dds"
texture = "ce_checkers_diagonal_02.dds"
```

These are pattern textures repurposed as colored emblems, allowing pattern-on-pattern effects.

### Color Inheritance
Sometimes only one or two colors are defined:
```
colored_emblem = {
    texture = "ce_tree.dds"
    color2 = "yellow"
}
```

Missing colors (color1, color3) likely inherit defaults or from parent CoA.

### Comments in Instance Blocks
Official files use inline comments for clarity:
```
instance = { position = { 0.50 0.20 } scale = { 0.2 0.2 } } #top
instance = { position = { 0.50 0.80 } scale = { 0.2 0.2 } } #bottom
```

Your parser should handle these (likely already does via comment skipping).

---

## Recommendations

1. **✅ IMPLEMENT `mask` field support FIRST** - This is essential for preserving CoA data integrity during round-trip editing. Without it, opening and saving a CoA will lose the mask information. Implementation is now straightforward with empirically validated behavior.

2. **✅ IMPLEMENT multiple instance support SECOND** - This is extensively used in official CK3 files and tested working in-game. Will require careful UX design but provides major functionality improvement.

3. **Document current limitations** - Until multi-instance is implemented, add note that multiple instances are flattened to first instance only on import. Users can work around by manually duplicating layers.

4. **Pattern validation is non-critical** - All patterns work the same way for mask purposes. No special validation needed beyond file existence checks.

5. **Reference TEST_RESULTS.md** - All empirical findings documented with specific test cases for future development reference.
