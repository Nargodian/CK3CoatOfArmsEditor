# Layer Symmetry System - Draft Discussion

## Core Concept

**Placement Symmetry** - per-layer property that automatically generates mirrored/repeated instances from a single "seed" emblem by **replicating whole emblems in symmetrical positions**. The seed emblem is the one the user directly manipulates - all symmetry instances update live as the seed moves.

**Important Constraints:**
- **No bisecting/clipping/cutoffs** - out of scope for CK3 CoA system
- **Placement only** - we replicate complete emblems, not halves or masked portions
- **Must work with CK3's bespoke transform system** - position, scale, rotation values

## Symmetry Types (Simplified)

### 1. Bisector
Cuts through the center with a mirror line.

**Properties:**
- `rotation_offset` - Angle to rotate the bisector line(s)
- `mode` - Single (one mirror line) or Double (cross - two perpendicular lines)

**Modes:**
- **Single (Mirror)** - One line of symmetry, generates 1 mirrored instance
- **Double (Cross)** - Two perpendicular lines, generates 3 mirrored instances

**Examples:**
- Bisector Single, 0° → Vertical mirror
- Bisector Single, 90° → Horizontal mirror
- Bisector Double, 0° → Cross (vertical + horizontal)
- Bisector Single, 45° → Diagonal mirror
- Bisector Double, 45° → Diagonal X (both diagonals)

### 2. Rotational
Rotates instances around the center point.

**Properties:**
- `count` - Number of instances around the circle (including seed)
- `rotation_offset` - Starting angle offset
- `kaleidoscope` - Boolean: if true, also mirrors each instance (mirrored + rotated)

**Examples:**
- Rotational, count=6, offset=0°, kaleidoscope=false → 6 instances in circle
- Rotational, count=8, offset=22.5°, kaleidoscope=true → 8 mirrored wedges

### 3. Grid
Tiled pattern arranging instances in a grid.

**Properties:**
- `count_x` - Number of columns
- `count_y` - Number of rows
- `fill` - Fill pattern type

**Fill Modes:**
- **Full** - Every cell filled
- **Diamond** - Checkerboard pattern (like chess board)
- **Alt-Diamond** - Inverted checkerboard (opposite cells)

## Meta Tag System

**Default (None):**
- If `symmetry_type = "none"` (default/disabled), **no meta tags written**
- Only active symmetry types generate meta tags on export
- Empty file = no symmetry, no tags

**Mirrored Instances** are marked with minimal meta tags:
```
##META##mirrored = true
##META##symmetry = vertical
```

**Seed Instance** stores the symmetry type and parameters:
```
##META##symmetry_seed = true
##META##symmetry_type = cross
```

**For Parameterized Types**, use compact list format:
```
##META##symmetry_seed = true
##META##symmetry_type = bisector
##META##symmetry_properties = { 0 0 45 0 }  # offset_x, offset_y, rotation_offset, mode
```

```
##META##symmetry_seed = true
##META##symmetry_type = rotational
##META##symmetry_properties = { 0 0 8 0 1 }  # offset_x, offset_y, count, rotation_offset, kaleidoscope
```

```
##META##symmetry_seed = true
##META##symmetry_type = grid
##META##symmetry_properties = { 0 0 5 5 1 }  # offset_x, offset_y, count_x, count_y, fill
```

**Properties List Format:**
- Compact: avoid creating many individual tags
- Order-dependent: each symmetry type defines its own property order
- Numeric values only (degrees, counts, indices)
- Parser maps list indices to property names based on symmetry_type

## Instance Generation

**In CoA Model (Internal Storage):**
- Layer stores only seed instances (regular instances from user)
- No mirrored instances stored in model - they don't exist internally
- `symmetry_type` and `symmetry_properties` are layer metadata

**On Canvas (Rendering):**
- Canvas widget queries layer for symmetry settings
- For each seed instance, calculates mirrored transforms on-the-fly
- Renders all instances (seeds + calculated mirrors) visually
- **No visual distinction between seeds and mirrors** - rendered identically
- **No feedback when clicking mirrors** - click passes through, no highlight
- Mirrors are just pixels - not selectable, not in model

**Symmetry Visual Indicators (Bespoke per Type):**
- **Cannot be derived from matrices** - each type needs custom visual
- **Only show when layer with symmetry is selected**
- **Rendered using Qt** (similar to transform widget overlay)
- Dashed lines or overlay graphics drawn on canvas
- Rendered on overlay layer above emblems

**Universal Offset Property:**
- **ALL symmetry types have offset XY** property
- Allows shifting symmetry center/structure regardless of type
- Applied before matrix calculations
- Properties list always starts with: `[offset_x, offset_y, ...]`

**Visual Examples:**
```python
# Bisector (single, 0°) → vertical dashed line at x=(0.5 + offset_x)
# Bisector (single, 90°) → horizontal dashed line at y=(0.5 + offset_y)  
# Bisector (double, 0°) → cross (both vertical and horizontal), shifted by offset
# Bisector (single, 45°) → diagonal dashed line, shifted by offset
# Rotational (count=8) → 8 radial dashed lines from center, shifted by offset
# Rotational (kaleidoscope) → radial lines + mirror lines between wedges
# Grid (4x4, full) → dashed grid showing 4×4 cells, shifted by offset
# Grid (4x4, diamond) → dashed grid with checkerboard shading on filled cells
```

**Implementation:**
- Each symmetry type has `get_visual_indicators(offset_x, offset_y)` method
- Returns Qt drawable primitives (QPainterPath, QLineF, etc.)
- Canvas overlay renders using QPainter when layer selected
- Transform widget-style rendering (Qt graphics, not shader)

**At Export (Serialization):**
- Layer with symmetry enabled generates full instance list
- For each seed instance:
  - Write seed instance normally
  - Calculate N mirrored instances based on `symmetry_type` and `symmetry_properties`
  - Write mirrored instances with `##META##mirrored = true` tags
- Example: Layer with 3 seed instances + "cross" symmetry (3 mirrors per seed)
  - Export generates: 3 seeds + (3 × 3) mirrors = 12 total instance blocks

**Merged Layers with Symmetry:**
- ALL instances in merged layer act as seeds
- Each seed generates its own symmetry group
- Transform any seed → its mirrors update
- Example: 5 merged instances + "vertical" mirror = 10 instances on export

## Live Updates

When user transforms the seed emblem:
- Position changes → symmetry instances recalculate positions
- Rotation changes → symmetry instances mirror rotation
- Scale changes → symmetry instances mirror scale
- Color/texture changes → all instances update

**Performance:**
- Renderer just draws what's in front (same graphic repeatedly)
- Efficient **transform stack** swapping on property changes
- No complex update triggers needed - canvas redraws on CoA model change
- Drawing N copies of same emblem is cheap (GPU instancing)

## Interaction Model

**Transform Widget / Seed Selection:**
- Transform widget **only operates on seed instances** (never on mirrored instances)
- User selects and transforms seeds - mirrored instances update automatically
- **Clicking on mirrored instance → does nothing** (mirrors aren't selectable, not in hitbox)
- Mirrors are purely visual - **shouldn't be in the way** of interaction
- Selection highlighting only shows seed instances

**Picker Texture (Click-to-Select):**
- Picker texture renders ALL instances (seeds + calculated mirrors)
- **All instances use the same color ID - the layer ID** (layer defines symmetry)
- When user clicks:
  - Read color ID from picker texture
  - Selects the layer (all instances share layer ID)
  - Transform widget operates on seed instances within selected layer
- No per-instance mapping needed - symmetry is layer-level property

**Mirrored Instances as "Graphic Quirk":**
- While editing in the system, mirrored instances are **not real instances in CoA model**
- They exist only as a **visual/rendering quirk** on the canvas
- Canvas widget calculates and renders them on-the-fly based on:
  - Layer's `symmetry_type` and `symmetry_properties`
  - Current seed instance transforms
- Mirrored instances are **ephemeral** - just pixels on screen

**Only Real at Export Time:**
- When serializing/exporting to CK3 format, mirrored instances are **generated and written**
- CoA model calculates all mirrored transforms from seeds
- Writes them as actual `instance = {...}` blocks with `##META##mirrored = true` tags
- On import, those mirrored instances are **stripped immediately** - back to seeds only

## Property UI

**Location:** Property Sidebar → Layer Properties tab

**UI Element:** Dropdown (for simple types) + Dynamic sub-UI (for parameterized types)

```
Symmetry: [None ▼]
```

**Dynamic Sub-UI Loading (Similar to Layer Generators):**

Like the generator system, symmetry parameters will load/unload dynamically:

**On Layer Selection Change:**
- Property sidebar reads `layer.symmetry_type` from CoA model
- If symmetry type needs parameters → **load** appropriate sub-UI widget
- If no parameters needed → **unload** any existing sub-UI widget

**On Symmetry Type Change (dropdown):**
- User selects new type from dropdown
- Old sub-UI widget **unloaded** (if any)
- New sub-UI widget **loaded** (if type needs parameters)
- Sub-UI initializes with current parameter values from layer

**Sub-UI Widget Lifecycle:**
1. Create widget for specific symmetry type (GridSymmetryWidget, KaleidoscopeSymmetryWidget, etc.)
2. Insert into property panel layout below dropdown
3. Connect parameter changes to CoA model updates
4. On layer change or type change → remove widget from layout, destroy

**Widget Implementation:**
- **Follow layer generator pattern** for widget types and behavior
- Use `self.settings` dict to store parameter values (like generators)
- Use `self._controls` dict to track widgets mapped to parameter names
- Use QSpinBox for integer counts, QDoubleSpinBox for floats
- Use QSlider + spinbox combination for visual feedback
- Use QRadioButton for mode selection (single/double)
- Use QCheckBox for boolean flags (kaleidoscope)
- Use QComboBox for fill pattern dropdown
- Debounce updates during slider drags (edit lock pattern)
- Save settings to cache for persistence across sessions

**Settings Structure Example:**
```python
# Bisector widget settings
self.settings = {
    'offset_x': 0.0,
    'offset_y': 0.0,
    'rotation_offset': 0,  # degrees
    'mode': 0  # 0=single, 1=double
}

# Rotational widget settings
self.settings = {
    'offset_x': 0.0,
    'offset_y': 0.0,
    'count': 6,
    'rotation_offset': 0,  # degrees
    'kaleidoscope': False  # boolean
}

# Grid widget settings
self.settings = {
    'offset_x': 0.0,
    'offset_y': 0.0,
    'count_x': 4,
    'count_y': 4,
    'fill': 0  # 0=full, 1=diamond, 2=alt-diamond
}
```

**Example UI States:**

```
Symmetry: [Bisector ▼]
┌─────────────────────────┐
│ Mode: ⦿Single ○Double   │  ← BisectorSymmetryWidget loaded
│ Rotation: [0°] slider   │
│ Offset X: [0.0]         │
│ Offset Y: [0.0]         │
└─────────────────────────┘
```

```
Symmetry: [Rotational ▼]
┌─────────────────────────┐
│ Count:    [6]           │  ← RotationalSymmetryWidget loaded
│ Rotation: [0°] slider   │
│ ☐ Kaleidoscope          │
│ Offset X: [0.0]         │
│ Offset Y: [0.0]         │
└─────────────────────────┘
```

```
Symmetry: [Grid ▼]
┌─────────────────────────┐
│ Columns:  [4]           │  ← GridSymmetryWidget loaded
│ Rows:     [4]           │
│ Fill: [Full ▼]          │
│       (Full/Diamond/    │
│        Alt-Diamond)     │
│ Offset X: [0.0]         │
│ Offset Y: [0.0]         │
└─────────────────────────┘
```

```
Symmetry: [None ▼]
                           ← No sub-UI
```

**Dropdown Main Options:**
- None
- Bisector...
- Rotational...
- Grid...

(All types except "None" are parameterized and spawn sub-UI widgets)

## CoA Model Requirements

### New Layer Properties

```python
# In Layer class
symmetry_type: str = "none"  # Type of symmetry
symmetry_properties: List[float] = []  # Parameters (grid size, segment count, etc.)
# Note: No need for symmetry_seed_uuid - only seed is stored in model
```

**Property List Definitions by Type:**

**Universal First Two Properties (ALL types):**
- `offset_x` - Horizontal offset from default center (0.0 = default)
- `offset_y` - Vertical offset from default center (0.0 = default)

```python
# Bisector
"bisector"
# properties = [offset_x, offset_y, rotation_offset, mode]
# mode: 0=single (mirror), 1=double (cross)
# Example: [0.0, 0.0, 0, 0] = centered, vertical mirror
# Example: [0.0, 0.0, 45, 0] = centered, 45° diagonal mirror
# Example: [0.0, 0.0, 0, 1] = centered, cross (vertical + horizontal)
# Example: [0.1, -0.05, 90, 0] = offset, horizontal mirror

# Rotational
"rotational"
# properties = [offset_x, offset_y, count, rotation_offset, kaleidoscope]
# kaleidoscope: 0=false (rotate only), 1=true (mirror + rotate)
# Example: [0.0, 0.0, 6, 0, 0] = centered, 6 instances rotated, no mirroring
# Example: [0.0, 0.0, 8, 22.5, 1] = centered, 8 wedges, mirrored + rotated
# Example: [0.2, 0.1, 4, 0, 0] = offset, 4 instances rotated

# Grid
"grid"
# properties = [offset_x, offset_y, count_x, count_y, fill]
# fill: 0=full, 1=diamond (checkerboard), 2=alt-diamond (inverted checkerboard)
# Example: [0.0, 0.0, 4, 4, 0] = centered 4x4 grid, all cells filled
# Example: [0.0, 0.0, 5, 5, 1] = centered 5x5, checkerboard pattern
# Example: [-0.1, 0.0, 3, 3, 2] = shifted left, 3x3, alt-checkerboard
```

### CoA Model Methods Needed

```python
def get_symmetry_matrices(layer_uuid: str) -> List[mat3]:
    """Generate list of mat3 transformation matrices for layer's symmetry.
    
    Returns empty list if symmetry_type is "none".
    Each mat3 represents one mirror/replication transform.
    
    Rules enforced:
    - No scaling above 1.0
    - No skewing (only rotation, translation, scale ≤ 1.0)
    - Placement symmetry only (no clipping)
    """
    pass

def apply_symmetry(layer_uuid: str, symmetry_type: str, properties: List[float]) -> None:
    """Set symmetry type and properties on layer."""
    pass

def remove_symmetry(layer_uuid: str) -> None:
    """Remove symmetry from layer (set to "none")."""
    pass

def apply_matrix_to_transform(matrix: mat3, transform: Transform) -> Transform:
    """Apply a transformation matrix to a Transform object.
    
    Used to calculate mirrored instance transforms from seeds.
    This is CPU-side math - outside shader.
    Returns Transform with CK3-compatible values.
    """
    pass

def to_ck3_transform(transform: Transform) -> dict:
    """Convert Transform to CK3 export format.
    
    Returns: {
        'position': {'x': float, 'y': float},
        'scale': {'x': float, 'y': float},
        'rotation': float  # degrees
    }
    
    Respects CK3's bespoke transform system.
    """
    pass

def generate_mirrored_instances_for_export(layer_uuid: str) -> List[dict]:
    """Generate full list of instances for serialization in CK3 format.
    
    Returns: [
        {'position': {...}, 'scale': {...}, 'rotation': ...},  # seed1
        {'position': {...}, 'scale': {...}, 'rotation': ...},  # mirror1a
        ...
    ]
    Each seed followed by its mirrors (if any), in CK3's format.
    """
    pass
```

## Export Format

When exporting to CK3 format:

```
colored_emblem = {
    texture = "ce_lion.dds"
    color1 = red
    
    # Seed instance with meta tags
    ##META##symmetry_seed = true
    ##META##symmetry_type = cross
    instance = { position = { 0.5 0.3 } scale = { 0.8 0.8 } }
    
    # Symmetry-generated instances (with minimal tags)
    ##META##mirrored = true
    ##META##symmetry = vertical
    instance = { position = { 0.5 0.7 } scale = { 0.8 0.8 } }
    
    ##META##mirrored = true  
    ##META##symmetry = horizontal
    instance = { position = { 0.3 0.5 } scale = { 0.8 0.8 } }
    
    ##META##mirrored = true
    ##META##symmetry = cross  
    instance = { position = { 0.7 0.5 } scale = { 0.8 0.8 } }
}
```

**With Parameters (Rotational Example):**
```
colored_emblem = {
    texture = "ce_star.dds"
    color1 = blue
    
    # Seed with properties
    ##META##symmetry_seed = true
    ##META##symmetry_type = rotational
    ##META##symmetry_properties = { 0 0 6 0 1 }
    instance = { position = { 0.5 0.2 } scale = { 0.3 0.3 } }
    
    # 5 mirrored instances generated from rotational count=6...
    ##META##mirrored = true
    ##META##symmetry = rotational
    instance = { position = { 0.7 0.35 } scale = { 0.3 0.3 } rotation = 60 }
    
    # ... etc (total 6 instances including seed)
}
```

## Import Behavior

**Design Decision: Delete/Ignore Mirror Instances on Load**

When loading a CoA with `##META##mirrored = true` tags:
- Parse meta tags to detect symmetry instances
- **Delete/ignore all mirrored instances** - do not store them in internal CoA model
- Only keep the seed instance
- Set layer's `symmetry_type` property based on meta tags
- Mirror instances will be **re-expressed during serialization** - generated fresh from seed

**Rationale:**
- Single source of truth (seed instance only)
- No duplicate data storage
- No sync issues between seed and mirrors
- Simpler undo/redo (only track seed changes)
- Mirrors always computed fresh from current seed state

## Layer Operations with Symmetry

**Load/Import:**
- File contains seed + mirrored instances with meta tags
- Parser reads all instances
- Identifies symmetry type from meta tags
- **Strips mirrored instances** before adding to CoA model
- Only seed instance stored with symmetry_type property

**Copy/Paste:**
- When copying: serialize with mirrored instances (full export)
- When pasting: parse like import - strip mirrors, keep only seed + symmetry_type

**Duplicate Layer:**
- Duplicates only seed instances + symmetry_type property
- New layer maintains symmetry behavior with duplicated seeds

**Convert to Instances ("Realize Mirrors"):**
- Right-click menu option: "Convert to Instances" or "Realize Symmetry"
- **Bakes all mirror instances into real instances** in CoA model
- Sets `symmetry_type = "none"` (disables symmetry)
- Result: Layer becomes regular instance layer with all positions realized
- Implementation: Similar to merge operation (generates all instances, discards symmetry metadata)
- Use case: User wants to manually tweak individual mirror positions

**Split Layer:**
- If layer has active symmetry (`symmetry_type != "none"`):
  - **Warning dialog**: "Splitting will break the symmetry. Do you want to do this?"
  - If user confirms → convert to instances first (realize all mirrors), then split
  - If user cancels → abort split operation
- Implementation: Treats symmetry layer as if "Convert to Instances" was called first, then splits the resulting instance layer
- Rationale: Can't split symmetry property across layers cleanly - must realize mirrors into instances first

**Merge Layers:**
- Merging **any layers** (symmetry or not) → **disables symmetry**
- Result: Combined layer becomes full instance layer (all instances are independent)
- All seed instances from symmetry layers become regular instances
- All mirrored instances are discarded (not realized)
- New merged layer has `symmetry_type = "none"`
- Rationale: 
  - Multiple symmetry systems can't coexist on one layer
  - Merging implies user wants manual control over all instances
  - Cleaner to disable symmetry than try to preserve/combine it

## Open Questions

1. **Symmetry center point**: **Always canvas center (0.5, 0.5) + offset**
   - Base symmetry structure centered at (0.5, 0.5)
   - Offset properties shift the entire symmetry structure
   - Not dependent on layer position or seed positions

2. **Rotation mirroring**: **Follows mirror transform logic**
   - Vertical mirror: rotation → -rotation (flip horizontal axis)
   - Horizontal mirror: rotation → 180 - rotation (flip vertical axis)
   - Transform applied, then rotated according to mirror axis

3. **Flip state**: **Flips follow the mirror transform**
   - Mirrors flip and rotate based on symmetry type
   - Vertical mirror: flip_x inverted, flip_y maintained
   - Horizontal mirror: flip_y inverted, flip_x maintained
   - Flips are part of the mirror calculation, not inherited directly

4. **Kaleidoscope parameters**: 
   - Fixed counts (4, 6, 8) or user-configurable?
   - Rotation offset configurable?

5. **Radial patterns**:
   - Radius from center - how to specify?
   - Rotation behavior around circle?
   - **Parameter ranges/limits TBD during implementation**

6. **Layer List Display**:
   - Show **duplicate badge** on bottom corner (similar to instance count badge)
   - Badge shows total mirror count (e.g., "×3" for cross symmetry with 1 seed)
   - Format: seed count + mirror count = total visual instances
   - No sub-items - mirrors aren't real instances, just visual indicator

7. **Undo/Redo**:
   - **Symmetry settings changes** tracked in history (type, properties)
   - **Seed instance movements** tracked in history (position, rotation, scale)
   - History captures layer state including symmetry metadata
   - Mirrors regenerate automatically from saved seed state

8. **Performance Limits**:
   - **Maximum 100 total instances** (seeds + mirrors combined) per layer
   - Example: 10 seeds × kaleidoscope(8) = 80 mirrors = 90 total ✓
   - Example: 50 seeds × cross = 150 mirrors = 200 total ✗ (limit exceeded)
   - UI validation prevents exceeding limit when changing symmetry settings
   - **Exact error messages/warnings TBD during implementation**

9. **Masking**: Do symmetry instances inherit mask state from seed? (Likely yes - mirrors copy all visual properties)

10. **Symmetry Per Layer**:
    - **One symmetry setting per layer** (symmetry_type applies to whole layer)
    - All instances in layer are seeds (merged layers → all instances generate mirrors)
    - No "batch operations" needed - changing symmetry affects entire layer uniformly
    - User can still add/remove seed instances normally - each generates its own mirror set

## Implementation Phases (Rough)

### Phase 1: Basic Vertical/Horizontal Mirrors
- Add symmetry_type property to Layer
- Implement vertical and horizontal mirror math
- Add dropdown to Property Sidebar
- Update canvas to show symmetry instances
- Export/import with meta tags

### Phase 2: Cross and Diagonal
- Add cross symmetry (both axes)
- Add diagonal mirrors (\ and /)
- Rotation transform calculations

### Phase 3: Kaleidoscope
- Radial symmetry around center
- Fixed counts (4, 6, 8)

### Phase 4: Advanced Patterns
- Radial circular arrangements
- Custom parameters (count, radius, offset)
- Advanced UI (dialog for parameters)

## Related Systems

- **Instance System**: Symmetry builds on existing instance system
- **Transform Widget**: Seed editing uses existing transform tools
- **Layer Selection**: Need to handle symmetry instance selection
- **Canvas Rendering**: Show symmetry instances with visual distinction (lighter? dashed outline?)
- **History Manager**: Symmetry changes create history entries
- **Clipboard**: Copy/paste seed or whole symmetry group?
- **Layer Generators** (`services/layer_generator`): 
  - Reference implementation for property widgets and settings management
  - See `BaseGenerator` class for settings dict pattern
  - See individual generators for UI control examples (QSpinBox, QSlider, QCheckBox, QComboBox)
  - Settings cache pattern for persistence across sessions

## Math Notes - Transform Calculations

**Symmetry Transforms (Simple Math):**

For this use case, **mat3 matrices are overkill** - the math is simple enough to work directly with Transform objects.

**Calculation Approach:**
- Work directly with `Transform(pos, scale, rotation)` objects
- Apply symmetry-specific math to position/rotation/scale components
- No intermediate matrix representation needed
- CPU-side calculations (outside shader)

**Strict Rules:**
- **No scaling above 1.0** - symmetry can only maintain or reduce scale, never enlarge
- **No skewing** - only rotation, translation, and uniform scale ≤ 1.0
- **Placement symmetry only** - no bisecting/clipping/masking

**CK3 Transform System:**
- Work directly with CK3's format: `{ position = { x y } scale = { sx sy } rotation = r }`
- Position: (0-1 normalized)
- Scale: float (0-1 for symmetry)
- Rotation: degrees

**Example - Vertical Mirror (Placement):**
```python
# Mirror across x=0.5 (vertical center line)
# Places whole emblem on opposite side, no clipping
mirror_pos = Vec2(1.0 - seed.pos.x, seed.pos.y)  # Flip X around center
mirror_scale = seed.scale  # Maintain scale
mirror_rotation = -seed.rotation  # Mirror rotation angle
```

**Application Flow:**
```python
# For each seed instance
for seed in layer.get_instances():
    # Generate mirror transforms based on symmetry type
    mirror_transforms = calculate_symmetry_transforms(
        seed.get_transform(),
        layer.symmetry_type,
        layer.symmetry_properties
    )
    
    # Render/export each mirror
    for mirror_transform in mirror_transforms:
        render_instance(layer.texture, mirror_transform, layer.colors)
```

---

*This is a draft discussion document - not final specification*
