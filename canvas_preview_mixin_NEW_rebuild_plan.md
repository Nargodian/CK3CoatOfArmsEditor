# Canvas Preview Mixin NEW - Rebuild Plan

## Executive Summary
Rebuild preview system to work with new canvas infrastructure (canvas_widget_NEW.py) while removing bespoke positioning calculations in favor of manageable constants. Previews render CoA into frame with masking but without selection/interface effects.

## Current State Analysis

### Old Implementation (canvas_preview_mixin.py)
- **Positioning**: Bespoke pixel calculations scattered throughout methods
  - Crown offset: `(7.5 / 115.0) * preview_size`
  - Topframe offset: `(10.0 / 115.0) * preview_size + (6.0 / 115.0) * preview_size`
  - Title crown offset: `(1.5 / 115.0) * preview_size` with size adjustment
  - Preview padding: hardcoded `20.0` pixels
  - Crown height ratio: `80.0 / 128.0`
- **Rendering**: Direct VBO writes with NDC coordinate calculations
- **Dependencies**: Uses `composite_shader` and `basic_shader`
- **Features**:
  - Government preview (top-left)
  - Title preview (top-right)
  - Crown strips (rank-based UV from 7x1 atlas)
  - Topframes (government only)
  - Frame masks and frames

### New Infrastructure (canvas_widget_NEW.py)
- **Shaders**: `main_composite_shader`, `tilesheet_shader`, `basic_shader`
- **Rendering**: Pixel-based coordinate system with GPU transforms
- **Geometry**: Static unit quad via `QuadRenderer.create_unit_quad()`
- **Dependencies**: 
  - `CanvasRenderingMixin`: CoA RTT rendering
  - `CanvasCoordinateMixin`: Coordinate transformations
  - `FramebufferRTT`: RTT texture source
- **Constants**:
  - `FRAME_FUDGE_SCALE = 0.98`
  - `FRAME_COA_RATIO = 1.3`
  - `COA_BASE_SIZE_PX = 256.0`
  - `FRAME_SIZE_PX = COA_BASE_SIZE_PX * FRAME_COA_RATIO * FRAME_FUDGE_SCALE`

### Shader Requirements Analysis
- **Main composite shader**: Too complex for previews (picker overlay, selection effects, CoA bounds system)
- **Need**: Stripped-down preview composite shader with only essential features

### Shared Texture Architecture
All preview rendering uses the **same CoA RTT texture** rendered once per frame:
```python
# In paintGL() - single render pass:
self._render_coa_to_framebuffer()  # Renders CoA layers once to 512x512 RTT

# Then composited multiple times with different masks:
self._composite_to_viewport()       # Main canvas (uses main_composite_shader + main frame mask)
self._render_government_preview()   # Government preview (uses preview_composite_shader + realm mask)
self._render_title_preview()        # Title preview (uses preview_composite_shader + title mask)
```

**Benefits:**
- CoA layers rendered once, reused three times
- Efficient GPU usage
- Consistent CoA appearance across all views
- Different masks/positioning per view without re-rendering layers
implified shader**: Create stripped-down preview composite shader (no picker, no selection, minimal uniforms)
4. **No selection effects**: Render pure CoA without UI overlays
5. **Clean API**: Maintain backward-compatible public methods
6. **Self-contained**: Preview mixin manages its own shader creation constants at module level
2. **Pixel-based rendering**: Use same pixel-coordinate approach as main canvas
3. **Shader consistency**: Use same shaders as main rendering pipeline
4. **No selection effects**: Render pure CoA without UI overlays
5. **Clean API**: Maintain backward-compatible public methods

## Implementation Plan
0: Create Preview Composite Shader
Create a simplified shader in `ShaderManager.create_preview_composite_shader()`:

**Vertex Shader** (same as tilesheet_shader - pixel-based transforms):
```glsl
#version 330 core
layout(location = 0) in vec3 position;
layout(location = 1) in vec2 texCoord;

out vec2 fragTexCoord;

uniform vec2 screenRes;      // Viewport size in pixels
uniform vec2 position;       // Quad position in pixels (center-origin)
uniform vec2 scale;          // Quad size in pixels
uniform float rotation;      // Rotation in radians

void main() {
    // Convert pixel position to normalized device coordinates
    vec2 pixelPos = position + texCoord * scale;
    vec2 normalizedPos = (pixelPos / (screenRes * 0.5));
    gl_Position = vec4(normalizedPos, 0.0, 1.0);
    fragTexCoord = texCoord;
}
```

**Fragment Shader** (simplified composite - no picker, no viewport bounds):
```glsl
#version 330 core
in vec2 fragTexCoord;
out vec4 fragColor;

uniform sampler2D coaTextureSampler;   // RTT CoA texture
uniform sampler2D frameMaskSampler;    // Frame/preview mask
uniform vec2 coaScale;                 // CoA scale within mask (simple constant, e.g., 0.9)
uniform vec2 coaOffset;                // CoA offset within mask (simple constant, e.g., 0.0, 0.1)
uniform bool useMask;                  // Whether to apply mask

void main() {
    // Apply CoA scale and offset to UV coordinates (relative positioning)
    vec2 coaUV = (fragTexCoord - 0.5 - coaOffset) / coaScale + 0.5;
    
    // Sample CoA (clamp to avoid edge bleeding)
    vec4 coaColor = texture(coaTextureSampler, coaUV);
    
    // Discard fragments outside CoA bounds (after scale/offset)
    if (coaUV.x < 0.0 || coaUV.x > 1.0 || coaUV.y < 0.0 || coaUV.y > 1.0) {
        coaColor = vec4(0.0);
    }
    
    if (useMask) {
        // Sample mask (use red channel)
        float maskValue = texture(frameMaskSampler, fragTexCoord).r;
        coaColor.a *= maskValue;
    }
    
    fragColor = coaColor;
}
```

**Key Simplifications vs Main Composite:**
- No material/noise textures (pure CoA rendering)
- No picker overlay
- No CoA viewport bounds checking (pixel-based bounds system removed)
- No bleed margin
- Simple mask application using red channel only
- CoA scale/offset using simple constants (not derived from frame transforms)
  - Main canvas: Complex frame-relative calculations for precise pixel alignment
  - Previews: Simple relative constants (0.9 scale, small offset) - good enough for small preview sizes

### Step 
### Step 1: Define Preview Constants
Create constants at top of `canvas_preview_mixin_NEW.py`:

```python
# Preview base dimensions
PREVIEW_DEFAULT_SIZE_PX = 86.0
PREVIEW_LARGE_SIZE_PX = 115.0

# CoA scaling within preview frames (simplified constants, not frame-derived)
# Previews use fixed relative positioning rather than complex main canvas bounds
PREVIEW_COA_SCALE_GOVERNMENT = 0.9  # 90% of mask area
PREVIEW_COA_SCALE_TITLE = 0.9       # 90% of mask area

# CoA offset within preview frames (Y-axis, normalized, relative to preview)
PREVIEW_COA_OFFSET_GOVERNMENT_Y = 0.1   # Slight downward shift for government
PREVIEW_COA_OFFSET_TITLE_Y = 0.04       # Minimal shift for title

# Crown dimensions and positioning
PREVIEW_CROWN_HEIGHT_RATIO = 80.0 / 128.0  # Crown is 80/128 of preview height

# Government preview crown strip offset
PREVIEW_CROWN_OFFSET_GOVT_BASE = 7.5 / 115.0  # Base offset as fraction of reference size

# Title preview crown strip offset (with size adjustment)
PREVIEW_CROWN_OFFSET_TITLE_BASE = 1.5 / 115.0
PREVIEW_CROWN_OFFSET_TITLE_ADJUSTMENT_FACTOR = -2.0 / 93.0  # Per-pixel scaling factor

# Topframe positioning (government only)
PREVIEW_TOPFRAME_OFFSET_BASE = 10.0 / 115.0
PREVIEW_TOPFRAME_OFFSET_SPACING = 6.0 / 115.0

# Title frame scaling
PREVIEW_TITLE_FRAME_SCALE = 1.1

# Corner positioning
PREVIEW_CORNER_PADDING_PX = 20.0

# Rank UV mapping (7x1 atlas)
PREVIEW_RANK_ATLAS_COLS = 7
PREVIEW_RANK_MAP = {
    "Baron": 1,
    "Count": 2,
    "Duke": 3,
    "King": 4,preview_composite_shader
    self._render_preview_coa(
        center_x_px, center_y_px, width_px, height_px,
        mask_texture=self.realm_frame_masks.get(self.preview_government

### Step 2: Create Helper Methods
Reusable calculation methods that use constants:

```python
def _calculate_preview_dimensions(self, preview_size_px):
    """Calculate preview quad dimensions in pixels.
    
    Returns: (width_px, height_px, crown_height_px, total_height_px)
    """
    width_px = preview_size_px
    height_px = preview_size_px
    crown_height_px = height_px * PREVIEW_CROWN_HEIGHT_RATIO
    total_height_px = height_px + crown_height_px
    return width_px, height_px, crown_height_px, total_height_px

def _calculate_crown_offset_government(self, preview_size_px):
    """Calculate crown strip offset for government preview."""
    return PREVIEW_CROWN_OFFSET_GOVT_BASE * preview_size_px

def _calculate_crown_offset_title(self, preview_size_px):
    """Calculate crown strip offset for title preview with size adjustment."""
    base_offset = PREVIEW_CROWN_OFFSET_TITLE_BASE * preview_size_px
    size_adjustment = PREVIEW_CROWN_OFFSET_TITLE_ADJUSTMENT_FACTOR * (PREVIEW_LARGE_SIZE_PX - preview_size_px)
    return base_offset + size_adjustment

def _calculate_topframe_offset(self, preview_size_px):
    """Calculate topframe offset for government preview."""
    return (PREVIEW_TOPFRAME_OFFSET_BASE + PREVIEW_TOPFRAME_OFFSET_SPACING) * preview_size_px

def _get_rank_uv(self, rank_name):
    """Get UV coordinates for rank in 7x1 crown atlas."""
    rank_index = PREVIEW_RANK_MAP.get(rank_name, PREVIEW_RANK_DEFAULT)
    u0 = rank_index / float(PREVIEW_RANK_ATLAS_COLS)
    u1 = (rank_index + 1) / float(PREVIEW_RANK_ATLAS_COLS)
    return u0, u1
```

### Step 3: Core Rendering Methods
Replace NDC calculations with pixel-based rendering using shaders:

#### Government Preview Rendering
```python
def _render_government_preview_at_px(self, left_px, top_px):
    """Render government preview at pixel position (top-left anchor)."""
    # Calculate dimensions
    width_px, height_px, crown_height_px, total_height_px = self._calculate_preview_dimensions(self.preview_size)
    
    # Calculate center position for quad rendering
    center_x_px = left_px + width_px / 2.0
    center_y_px = top_px + (height_px + crown_height_px) / 2.0
    
    # Render CoA with government mask using preview_composite_shader
    self._render_preview_coa(
        center_x_px, center_y_px, width_px, height_px,
        mask_texture=self.realm_frame_masks.get(self.preview_government),
        coa_scale=(PREVIEW_COA_SCALE_GOVERNMENT, PREVIEW_COA_SCALE_GOVERNMENT),
        coa_offset=(0.0, PREVIEW_COA_OFFSET_GOVERNMENT_Y)
    )
    
    # Render government frame using tilesheet_shader
    gov_frame = self.realm_frame_frames.get((self.preview_government, self.preview_size))
    if gov_frame:
        self._render_preview_frame(center_x_px, center_y_px, width_px, height_px, gov_frame)
    
    # Render crown strip using tilesheet_shader
    crown_strip = self.crown_strips.get(self.preview_size)
    if crown_strip:
        u0, u1 = self._get_rank_uv(self.preview_rank)
        crown_offset_px = self._calculate_crown_offset_government(self.preview_size)
        crown_center_y_px = top_px + crown_offset_px + crown_height_px / 2.0
        self._render_preview_crown(center_x_px, crown_center_y_px, width_px, crown_height_px, crown_strip, u0, u1)
    
    # Render topframe using tilesheet_shader
    topframe = self.topframes.get(self.preview_size)
    if topframe:
        u0, u1 = self._get_rank_uv(self.preview_rank)
        topframe_offset_px = self._calculate_topframe_offset(self.preview_size)
        # Topframe spans entire preview height
        self._render_preview_topframe(center_x_px, center_y_px, width_px, height_px, topframe, u0, u1, topframe_offset_px)
```

#### Title Preview Rendering
```python
def _render_title_preview_at_px(self, left_px, top_px):
    """Render title preview at pixel position (top-left anchor)."""
    # Calculate dimensions
    width_px, height_px, crown_height_px, total_height_px = self._calculate_preview_dimensions(self.preview_size)
    
    # Calculate center position
    center_x_px = left_px + width_px / 2.0
    center_y_px = top_px + (height_px + crown_height_px) / 2.0
    
    # Render CoA with title mask
    if self.title_mask:
        self._render_preview_coa(
            center_x_px, center_y_px, width_px, height_px,
            mask_texture=self.title_mask,
            coa_scale=(PREVIEW_COA_SCALE_TITLE, PREVIEW_COA_SCALE_TITLE),
            coa_offset=(0.0, PREVIEW_COA_OFFSET_TITLE_Y)
        )
    
    # Render crown strip
    crown_strip = self.crown_strips.get(self.preview_size)
    if crown_strip:
        u0, u1 = self._get_rank_uv(self.preview_rank)
        crown_offset_px = self._calculate_crown_offset_title(self.preview_size)
        crown_center_y_px = top_px + crown_offset_px + crow
    
    Uses the shared CoA RTT texture already rendered by _render_coa_to_framebuffer().
    This method just composites it with a different mask and positioning.
    """
    if not self.preview_composite_shader or not mask_texture:
        return
    
    self.vao.bind()
    self.preview_composite_shader.bind()
    
    # Bind shared CoA RTT texture (same texture used by main canvas)
        scaled_width = width_px * PREVIEW_TITLE_FRAME_SCALE
        scaled_height = height_px * PREVIEW_TITLE_FRAME_SCALE
        self._render_preview_frame(center_x_px, center_y_px, scaled_width, scaled_height, title_frame)
```

### Step 4: Shader-Based Rendering Primitives
Single-purpose rendering methods for clear, maintainable code.

**Design Philosophy:** Each method renders ONE thing. The high-level preview methods become readable stacks where you can easily comment out, reorder, or conditionally skip any element:
```python
# Want to hide topframe? Just comment out one line:
# self._render_preview_topframe(...)
```

```python
def _render_preview_coa(self, center_x_px, center_y_px, width_px, height_px, mask_texture, coa_scale, coa_offset):
    """Render CoA with mask using preview_composite_shader."""
    if not self.preview_composite_shader or not mask_texture:
        return
    
    self.vao.bind()
    self.preview_composite_shader.bind()
    
    # Bind RTT texture
    gl.glActiveTexture(gl.GL_TEXTURE0)
    gl.glBindTexture(gl.GL_TEXTURE_2D, self.framebuffer_rtt.get_texture())
    self.preview_composite_shader.setUniformValue("coaTextureSampler", 0)
    
    # Bind mask texture
    gl.glActiveTexture(gl.GL_TEXTURE1)
    gl.glBindTexture(gl.GL_TEXTURE_2D, mask_texture)
    self.preview_composite_shader.setUniformValue("frameMaskSampler", 1)
    
    # Set transform uniforms (pixel-based, center-origin)
    self.preview_composite_shader.setUniformValue("screenRes", QVector2D(self.width(), self.height()))
    self.preview_composite_shader.setUniformValue("position", QVector2D(center_x_px - self.width()/2.0, self.height()/2.0 - center_y_px))
    self.preview_composite_shader.setUniformValue("scale", QVector2D(width_px, height_px))
    self.preview_composite_shader.setUniformValue("rotation", 0.0)
    
    # Set CoA positioning within mask
    self.preview_composite_shader.setUniformValue("coaScale", QVector2D(coa_scale[0], coa_scale[1]))
    self.preview_composite_shader.setUniformValue("coaOffset", QVector2D(coa_offset[0], coa_offset[1]))
    
    # Enable masking
    self.preview_composite_shader.setUniformValue("useMask", True)
    
    gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
    
    self.preview_composite_shader.release()
    self.vao.release()
    self.preview_composite_shader.setUniformValue("rotation", 0.0)
    
    # Enable masking
    self.preview_composite_shader.setUniformValue("useMask", True)
    
    gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
    
    self.preview_offset_px = self._calculate_crown_offset_title(self.preview_size)
        crown_center_y_px = top_px + crown_offset_px + crown_height_px / 2.0
        self._render_preview_crown(center_x_px, crown_center_y_px, width_px, crown_height_px, crown_strip, u0, u1)
    
    # Render title frame (scaled)
    title_frame = self.title_frames.get(self.preview_size)
    if not title_frame and self.preview_size == 115:
        title_frame = self.title_frames.get(86)
    if title_frame:
        scaled_width = width_px * PREVIEW_TITLE_FRAME_SCALE
        scaled_height = height_px * PREVIEW_TITLE_FRAME_SCALE
        self._render_preview_frame(center_x_px, center_y_px, scaled_width, scaled_height, title_frame)
```

### Step 4: Shader-Based Rendering Primitives
Use existing shaders with pixel-based coordinates:

```python
def _render_preview_coa(self, center_x_px, center_y_px, width_px, height_px, mask_texture, coa_scale, coa_offset):
    """Render CoA with mask using main_composite_shader."""
    if not self.main_composite_shatilesheet_shader (single tile)."""
    if not self.tilesheet_shader or not frame_texture:
        return
    
    self.vao.bind()
    self.tilesheet_shader.bind()
    
    gl.glActiveTexture(gl.GL_TEXTURE0)
    gl.glBindTexture(gl.GL_TEXTURE_2D, frame_texture)
    self.tilesheet_shader.setUniformValue("tilesheetSampler", 0)
    
    # Single tile (1x1 tilesheet)
    self.tilesheet_shader.setUniformValue("tileCols", 1)
    self.tilesheet_shader.setUniformValue("tileRows", 1)
    self.tilesheet_shader.setUniformValue("tileIndex", 0)
    
    # Set transform uniforms (pixel-based, center-origin)
    self.tilesheet_shader.setUniformValue("screenRes", QVector2D(self.width(), self.height()))
    self.tilesheet_shader.setUniformValue("position", QVector2D(center_x_px - self.width()/2.0, self.height()/2.0 - center_y_px))
    self.tilesheet_shader.setUniformValue("scale", QVector2D(width_px, height_px))
    self.tilesheet_shader.setUniformValue("rotation", 0.0)
    self.tilesheet_shader.setUniformValue("uvOffset", QVector2D(0.0, 0.0))
    self.tilesheet_shader.setUniformValue("uvScale", QVector2D(1.0, 1.0))
    self.tilesheet_shader.setUniformValue("flipU", False)
    self.tilesheet_shader.setUniformValue("flipV", True)  # Flip vertically for correct orientation
    
    gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
    
    self.tilesheetcomposite_shader.setUniformValue("frameMaskSampler", 1)
    
    # Set transform uniforms (pixel-based)
    self.main_composite_shader.setUniformValue("screenRes", QVector2D(self.width(), self.height()))
    self.main_composite_shader.setUniformValue("position", QVector2D(center_x_px - self.width()/2.0, self.height()/2.0 - center_y_px))
    self.main_composite_shader.setUniformValue("scale", QVector2D(width_px, height_px))
    self.main_composite_shader.setUniformValue("rotation", 0.0)
    self.main_composite_shader.setUniformValue("uvOffset", QVector2D(0.0, 0.0))
    self.main_composite_shader.setUniformValue("uvScale", QVector2D(1.0, 1.0))
    self.main_composite_shader.setUniformValue("flipU", False)
    self.main_composite_shader.setUniformValue("flipV", False)
    
    # Set CoA viewport bounds (for mask application)
    self.main_composite_shader.setUniformValue("coaTopLeft", 0.0, 0.0)
    self.main_composite_shader.setUniformValue("coaBottomRight", float(self.width()), float(self.height()))
    
    # Enable masking
    self.main_composite_shader.setUniformValue("useMask", True)
    
    # Disable picker overlay
    self.main_composite_shader.setUniformValue("mouseUV", QVector2D(-1.0, -1.0))
    
    gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
    
    self.main_composite_shader.release()
    self.vao.release()

def _render_preview_frame(self, center_x_px, center_y_px, width_px, height_px, frame_texture):
    """Render preview frame using basic_shader."""
    if not self.basic_shader or not frame_texture:
        return
    
    self.vao.bind()
    self.basic_shader.bind()
    
    gl.glActiveTexture(gl.GL_TEXTURE0)
    gl.glBindTexture(gl.GL_TEXTURE_2D, frame_texture)
    self.basic_shader.setUniformValue("textureSampler", 0)
    
    # TODO: Need to determine if basic_shader uses pixel transforms or needs NDC calculation
    # If basic_shader doesn't have pixel transform uniforms, create quad vertices manually
    
    self.basic_shader.release()
    self.vao.release()

def _render_preview_crown(self, center_x_px, center_y_px, width_px, height_px, crown_texture, u0, u1):
    """Render crown strip with rank-specific UV using tilesheet_shader."""
    if not self.tilesheet_shader or not crown_texture:
        return
    
    self.vao.bind()
    self.tilesheet_shader.bind()
    
    gl.glActiveTexture(gl.GL_TEXTURE0)
    gl.glBindTexture(gl.GL_TEXTURE_2D, crown_texture)
    self.tilesheet_shader.setUniformValue("tilesheetSampler", 0)
    
    # Set tilesheet properties
    rank_index = int(u0 * PREVIEW_RANK_ATLAS_COLS)
    self.tilesheet_shader.setUniformValue("tileCols", PREVIEW_RANK_ATLAS_COLS)
    self.tilesheet_shader.setUniformValue("tileRows", 1)
    self.tilesheet_shader.setUniformValue("tileIndex", rank_index)
    
    # Set transform uniforms
    self.tilesheet_shader.setUniformValue("screenRes", QVector2D(self.width(), self.height()))
    self.tilesheet_shader.setUniformValue("position", QVector2D(center_x_px - self.width()/2.0, self.height()/2.0 - center_y_px))
    self.tilesheet_shader.setUniformValue("scale", QVector2D(width_px, height_px))
    self.tilesheet_shader.setUniformValue("rotation", 0.0)
    self.tilesheet_shader.setUniformValue("uvOffset", QVector2D(0.0, 0.0))
    self.tilesheet_shader.setUniformValue("uvScale", QVector2D(1.0, 1.0))
    self.tilesheet_shader.setUniformValue("flipU", False)
    self.tilesheet_shader.setUniformValue("flipV", False)
    
    gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
    
    self.tilesheet_shader.release()
    self.vao.release()

def _render_preview_topframe(self, center_x_px, center_y_px, width_px, height_px, topframe_texture, u0, u1, offset_px):
    """Render topframe overlay with rank-specific UV using tilesheet_shader."""
    if not self.tilesheet_shader or not topframe_texture:
        return
    
    self.vao.bind()
    self.tilesheet_shader.bind()
    
    gl.glActiveTexture(gl.GL_TEXTURE0)
    gl.glBindTexture(gl.GL_TEXTURE_2D, topframe_texture)
    self.tilesheet_shader.setUniformValue("tilesheetSampler", 0)
    
    # Set tilesheet properties (7x1 atlas for rank)
    rank_index = int(u0 * PREVIEW_RANK_ATLAS_COLS)
    self.tilesheet_shader.setUniformValue("tileCols", PREVIEW_RANK_ATLAS_COLS)
    self.tilesheet_shader.setUniformValue("tileRows", 1)
    self.tilesheet_shader.setUniformValue("tileIndex", rank_index)
    
    # Apply vertical offset
    offset_y_px = center_y_px + offset_px
    
    # Set transform uniforms
    self.tilesheet_shader.setUniformValue("screenRes", QVector2D(self.width(), self.height()))
    self.tilesheet_shader.setUniformValue("position", QVector2D(center_x_px - self.width()/2.0, self.height()/2.0 - offset_y_px))
    self.tilesheet_shader.setUniformValue("scale", QVector2D(width_px, height_px))
    self.tilesheet_shader.setUniformValue("rotation", 0.0)
    self.tilesheet_shader.setUniformValue("uvOffset", QVector2D(0.0, 0.0))
    self.tilesheet_shader.setUniformValue("uvScale", QVector2D(1.0, 1.0))
    self.tilesheet_shader.setUniformValue("flipU", False)
    self.tilesheet_shader.setUniformValue("flipV", True)
    
    gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
    
    self.tilesheet_shader.release()
    self.vao.release()
```

**Note**: Each primitive method is independent and self-contained. This creates readable high-level methods where each line clearly states what it renders.

### Step 5: Public API Methods
Maintain backward compatibility:

```python

2. **Create canvas_preview_mixin_NEW.py**
   - Add all constants at module level
   - Implement `_init_preview_shader()` to create shader
   - Implement helper calculation methods
   - Implement shader-based rendering primitives
   - Implement government/title preview methods
   - Add public API methods

### Step 5: Public API Methods
Maintain backward compatibility:

```python
def _render_government_preview(self):
    """Render government preview in top-left corner."""
    width_px, height_px, crown_height_px, total_height_px = self._calculate_preview_dimensions(self.preview_size)
    left_px = PREVIEW_CORNER_PADDING_PX
    top_px = PREVIEW_CORNER_PADDING_PX
    self._render_government_preview_at_px(left_px, top_px)

def _render_title_preview(self):
    """Render title preview in top-right corner."""
    width_px, height_px, crown_height_px, total_height_px = self._calculate_preview_dimensions(self.preview_size)
    left_px = self.width() - width_px - PREVIEW_CORNER_PADDING_PX
    top_px = PREVIEW_CORNER_PADDING_PX
    self._render_title_preview_at_px(left_px, top_px)

def set_preview_enabled(self, enabled):
    """Toggle preview rendering."""
    sDedicated Shader**: Stripped-down preview composite shader (not main_composite_shader)
4. **Simplified Rendering**: No picker, no selection, no CoA bounds, no material/noise
5. **No NDC Calculations**: Shaders handle coordinate space conversions
6. **Constants First**: All magic numbers extracted to named constants
7ef set_preview_government(self, government):
    """Set government type for preview."""
    self.preview_government = government
    if self.preview_enabled:
        self.update()

def set_preview_rank(self, rank):
    """Set rank for crown strip."""
    self.preview_rank = rank
    if self.preview_enabled:
        self.update()

def set_preview_size(self, size):
    """Set preview size in pixels."""
    self.preview_size = size
    if self.preview_enabled:
        self.update()
```

### Step 6: Preview Export Methods
Add export functionality to render previews to PNG files with viewport override support:

```python
def export_government_preview(self, filepath, export_size=None):
    """Export government preview to PNG file.
    
    Args:
        filepath: Output file path (e.g., "output_government.png")
        export_size: Optional export size in pixels (uses self.preview_size if None)
    """
    if export_size is None:
        export_size = self.preview_size
    
    # Calculate dimensions
    width_px, height_px, crown_height_px, total_height_px = self._calculate_preview_dimensions(export_size)
    
    # Store original viewport dimensions
    original_width = self.width()
    original_height = self.height()
    
    # Create temporary framebuffer for export
    from services.framebuffer_rtt import FramebufferRTT
    export_fbo = FramebufferRTT()
    export_fbo.initialize(int(width_px), int(total_height_px))
    
    # Bind export framebuffer and set viewport
    export_fbo.bind()
    export_fbo.clear(0.0, 0.0, 0.0, 0.0)
    gl.glViewport(0, 0, int(width_px), int(total_height_px))
    
    # Temporarily override width()/height() for coordinate calculations during export
    self._export_viewport_override = (int(width_px), int(total_height_px))
    
    # Render government preview at origin (0, 0 top-left)
    self._render_government_preview_at_px(0, 0)
    
    # Clear override
    self._export_viewport_override = None
    
    # Read pixels and save
    import numpy as np
    from PIL import Image
    pixels = np.frombuffer(gl.glReadPixels(0, 0, int(width_px), int(total_height_px), 
                                            gl.GL_RGBA, gl.GL_UNSIGNED_BYTE), dtype=np.uint8)
    pixels = pixels.reshape(int(total_height_px), int(width_px), 4)
    pixels = np.flipud(pixels)  # Flip Y-axis
    
    image = Image.fromarray(pixels, 'RGBA')
    image.save(filepath)
    
    # Cleanup and restore
    export_fbo.unbind(self.defaultFramebufferObject())
    gl.glViewport(0, 0, original_width, original_height)
    export_fbo.cleanup()

def export_title_preview(self, filepath, export_size=None):
    """Export title preview to PNG file.
    
    Args:
        filepath: Output file path (e.g., "output_title.png")
        export_size: Optional export size in pixels (uses self.preview_size if None)
    """
    if export_size is None:
        export_size = self.preview_size
    
    # Calculate dimensions
    width_px, height_px, crown_height_px, total_height_px = self._calculate_preview_dimensions(export_size)
    
    # Store original viewport dimensions
    original_width = self.width()
    original_height = self.height()
    
    # Create temporary framebuffer for export
    from services.framebuffer_rtt import FramebufferRTT
    export_fbo = FramebufferRTT()
    export_fbo.initialize(int(width_px), int(total_height_px))
    
    # Bind export framebuffer and set viewport
    export_fbo.bind()
    export_fbo.clear(0.0, 0.0, 0.0, 0.0)
    gl.glViewport(0, 0, int(width_px), int(total_height_px))
    
    # Temporarily override width()/height() for coordinate calculations during export
    self._export_viewport_override = (int(width_px), int(total_height_px))
    
    # Render title preview at origin (0, 0 top-left)
    self._render_title_preview_at_px(0, 0)
    
    # Clear override
    self._export_viewport_override = None
    
    # Read pixels and save
    import numpy as np
    from PIL import Image
    pixels = np.frombuffer(gl.glReadPixels(0, 0, int(width_px), int(total_height_px), 
                                            gl.GL_RGBA, gl.GL_UNSIGNED_BYTE), dtype=np.uint8)
    pixels = pixels.reshape(int(total_height_px), int(width_px), 4)
    pixels = np.flipud(pixels)  # Flip Y-axis
    
    image = Image.fromarray(pixels, 'RGBA')
    image.save(filepath)
    
    # Cleanup and restore
    export_fbo.unbind(self.defaultFramebufferObject())
    gl.glViewport(0, 0, original_width, original_height)
    export_fbo.cleanup()

def width(self):
    """Override to support export viewport override."""
    if hasattr(self, '_export_viewport_override') and self._export_viewport_override:
        return self._export_viewport_override[0]
    return super().width()

def height(self):
    """Override to support export viewport override."""
    if hasattr(self, '_export_viewport_override') and self._export_viewport_override:
        return self._export_viewport_override[1]
    return super().height()
```
    export_fbo.cleanup()

def export_title_preview(self, filepath, export_size=None):
    """Export title preview to PNG file.
    
    Args:
        filepath: Output file path (e.g., "output_title.png")
        export_size: Optional export size in pixels (uses self.preview_size if None)
    """
    if export_size is None:
        export_size = self.preview_size
    
    # Calculate dimensions
    width_px, height_px, crown_height_px, total_height_px = self._calculate_preview_dimensions(export_size)
    
    # Store original viewport dimensions
    original_width = self.width()
    original_height = self.height()
    
    # Create temporary framebuffer for export
    from services.framebuffer_rtt import FramebufferRTT
    export_fbo = FramebufferRTT()
    export_fbo.initialize(int(width_px), int(total_height_px))
    
    # Bind export framebuffer and set viewport
    export_fbo.bind()
    export_fbo.clear(0.0, 0.0, 0.0, 0.0)
    gl.glViewport(0, 0, int(width_px), int(total_height_px))
    
    # Temporarily override width()/height() for coordinate calculations during export
    self._export_viewport_override = (int(width_px), int(total_height_px))
    
    # Render title preview at origin (0, 0 top-left)
    self._render_title_preview_at_px(0, 0)
    
    # Clear override
    self._export_viewport_override = None
    
    # Read pixels and save
    import numpy as np
    from PIL import Image
    pixels = np.frombuffer(gl.glReadPixels(0, 0, int(width_px), int(total_height_px), 
                                            gl.GL_RGBA, gl.GL_UNSIGNED_BYTE), dtype=np.uint8)
    pixels = pixels.reshape(int(total_height_px), int(width_px), 4)
    pixels = np.flipud(pixels)  # Flip Y-axis
    
    image = Image.fromarray(pixels, 'RGBA')
    image.save(filepath)
    
    # Cleanup and restore
    export_fbo.unbind(self.defaultFramebufferObject())
    gl.glViewport(0, 0, original_width, original_height)
    export_fbo.cleanup()

def width(self):
    """Override to support export viewport override."""
    if hasattr(self, '_export_viewport_override') and self._export_viewport_override:
        return self._export_viewport_override[0]
    return super().width()

def height(self):
    """Override to support export viewport override."""
    if hasattr(self, '_export_viewport_override') and self._export_viewport_override:
        return self._export_viewport_override[1]
    return super().height()
```

## Implementation Steps

1. **Create canvas_preview_mixin_NEW.py**
   - Add all constants at module level
   - Implement helper calculation methods
   - Implement shader-based rendering primitives
   - Implement government/title preview methods
   - Add public API methods

2. **Verify Shader Compatibility**
   - Check if `basic_shader` supports pixel-based transforms
   - If not, implement manual vertex calculation for frames
   - Ensure `main_composite_shader` mask parameters work correctly

3. **Update canvas_widget_NEW.py**
   - Import `CanvasPreviewMixin` → `CanvasPreviewMixinNew` (if renamed)
   - Verify mixin inheritance order
   - Ensure texture loading methods are called in `initializeGL`

4. **Test Rendering**
   - Verify CoA RTT is shared correctly (all previews show same CoA)
   - Enable preview mode
   - Verify government preview renders correctly with realm mask
   - Verify title preview renders correctly with title mask
   - Test different ranks and sizes
   - Verify no selection/UI overlays appear
   - Confirm efficient rendering (CoA rendered once, composited multiple times)

5. **Cleanup**
   - Remove old `canvas_preview_mixin.py` references if needed
   - Update any imports in other files
   - Document new constants

## Critical Differences from Old Implementation

1. **No VBO Writes**: Use static unit quad, GPU transforms only
2. **Pixel Coordinates**: All positioning in pixels, shaders handle normalization
3. **Dedicated Shader**: Stripped-down preview composite shader (not main_composite_shader)
4. **Simplified Rendering**: No picker, no selection, no viewport bounds checking, no material/noise
5. **Relative CoA Positioning**: Simple constant scale/offset (not frame-derived calculations)
   - Main canvas must derive positioning from frame transforms for pixel-perfect alignment
   - Previews use fixed relative constants - simpler and sufficient for small preview sizes
6. **No NDC Calculations**: Shaders handle coordinate space conversions
7. **Constants First**: All magic numbers extracted to named constants
8. **No Selection**: Pure CoA rendering without UI overlays

## Dependencies Required from Parent

```python
# Fropreview_composite_shader  # Created by mixin in _init_preview_shader()
self.tilesheetheet_shader
self.basic_shader
self.vao, self.vbo, self.ebo
self.framebuffer_rtt
self.realm_frame_masks
self.realm_frame_frames
- Preview export generates correct PNG files with _government and _title suffixes
- Export workflow integrated with main canvas export (conditional on preview_enabled flag)
self.crown_strips
self.title_mask
self.title_frames
self.topframes
self.preview_enabled
self.preview_government
self.preview_rank
self.preview_size
self.width(), self.height()
```

## Open Questions to Resolve During Implementation

1. ~~Does `basic_shader` support pixel-based transform uniforms?~~ → Using `tilesheet_shader` for all frame rendering
2. ~~Should we include material/noise textures?~~ → No, simplified preview composite doesn't need them
3. ~~Should preview composite shader include CoA scale/offset uniforms?~~ → Yes, essential for CoA positioning within masks
4. Should topframe use rank-based UV or render full texture? → Keep rank-based UV via tilesheet

## Success Criteria

- Previews render correctly in corners without positioning artifacts
- All magic numbers replaced with named constants
- No manual VBO writes (use shaders for all transforms)
- No selection or UI effects visible in previews
- Public API maintains backward compatibility
- Code is reusable and maintainable
