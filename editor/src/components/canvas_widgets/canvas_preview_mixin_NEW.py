"""Canvas preview rendering system - government and title previews (NEW)

Rebuilt preview system using simplified shader and pixel-based rendering.
All positioning uses manageable constants rather than bespoke calculations.
"""
import numpy as np
import OpenGL.GL as gl
from PyQt5.QtGui import QVector2D


# ========================================
# Constants
# ========================================

# Preview base dimensions (lerp range)
PREVIEW_SIZE_MIN = 22.0
PREVIEW_SIZE_MAX = 115.0
PREVIEW_DEFAULT_SIZE_PX = 86.0
PREVIEW_LARGE_SIZE_PX = 115.0

# CoA scaling within preview frames (simplified constants, not frame-derived)
# Previews use fixed relative positioning rather than complex main canvas bounds
PREVIEW_COA_SCALE_GOVERNMENT = 0.9  # 90% of mask area
PREVIEW_COA_SCALE_TITLE = 0.9       # 90% of mask area

# CoA offset within preview frames (Y-axis, normalized, relative to preview)
PREVIEW_COA_OFFSET_GOVERNMENT_Y = -0.11   # Slight downward shift for government
PREVIEW_COA_OFFSET_TITLE_Y = -0.04       # Minimal shift for title

# Crown dimensions and positioning
PREVIEW_CROWN_HEIGHT_RATIO = 0.625  # Crown is 80/128 of preview height

# Government preview crown strip offset (pixels, lerps from min to max size)
PREVIEW_CROWN_OFFSET_GOVT_MIN = -7  # Offset at size 22px
PREVIEW_CROWN_OFFSET_GOVT_MAX = -41    # Offset at size 115px

# Title preview crown strip offset (pixels, lerps from min to max size)
PREVIEW_CROWN_OFFSET_TITLE_MIN = -6  # Offset at size 22px (negative = above preview)
PREVIEW_CROWN_OFFSET_TITLE_MAX = -36     # Offset at size 115px

# Topframe positioning (pixels, lerps from min to max size)
PREVIEW_TOPFRAME_OFFSET_MIN = -3  # Offset at size 22px
PREVIEW_TOPFRAME_OFFSET_MAX = -15  # Offset at size 115px

# Title frame scaling
PREVIEW_TITLE_FRAME_SCALE = 1.1

# Corner positioning
PREVIEW_CORNER_PADDING_PX = 20.0
PREVIEW_VERTICAL_OFFSET_PX = 50.0  # Additional offset to move previews down from top edge

# Rank UV mapping (7x1 atlas)
PREVIEW_RANK_ATLAS_COLS = 7
PREVIEW_RANK_MAP = {
    "Baron": 1,
    "Count": 2,
    "Duke": 3,
    "King": 4,
    "Emperor": 5,
    "Hegemon": 6
}
PREVIEW_RANK_DEFAULT = 3  # Duke


class CanvasPreviewMixin:
    """Mixin for rendering government and title preview graphics.
    
    Uses simplified preview_composite_shader and pixel-based rendering.
    All previews share the same CoA RTT texture rendered once per frame.
    """
    
    # ========================================
    # Initialization
    # ========================================
    
    def _init_preview_shader(self):
        """Initialize preview composite shader. Call after OpenGL context is ready."""
        from components.canvas_widgets.shader_manager import ShaderManager
        shader_manager = ShaderManager()
        self.preview_composite_shader = shader_manager.create_preview_composite_shader(self)
    
    # ========================================
    # Helper Methods
    # ========================================
    
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
        """Calculate crown strip offset for government preview using lerp."""
        t = (preview_size_px - PREVIEW_SIZE_MIN) / (PREVIEW_SIZE_MAX - PREVIEW_SIZE_MIN)
        return PREVIEW_CROWN_OFFSET_GOVT_MIN + t * (PREVIEW_CROWN_OFFSET_GOVT_MAX - PREVIEW_CROWN_OFFSET_GOVT_MIN)
    
    def _calculate_crown_offset_title(self, preview_size_px):
        """Calculate crown strip offset for title preview using lerp."""
        t = (preview_size_px - PREVIEW_SIZE_MIN) / (PREVIEW_SIZE_MAX - PREVIEW_SIZE_MIN)
        return PREVIEW_CROWN_OFFSET_TITLE_MIN + t * (PREVIEW_CROWN_OFFSET_TITLE_MAX - PREVIEW_CROWN_OFFSET_TITLE_MIN)
    
    def _calculate_topframe_offset(self, preview_size_px):
        """Calculate topframe offset for government preview using lerp."""
        t = (preview_size_px - PREVIEW_SIZE_MIN) / (PREVIEW_SIZE_MAX - PREVIEW_SIZE_MIN)
        return PREVIEW_TOPFRAME_OFFSET_MIN + t * (PREVIEW_TOPFRAME_OFFSET_MAX - PREVIEW_TOPFRAME_OFFSET_MIN)
    
    def _get_rank_uv(self, rank_name):
        """Get UV coordinates for rank in 7x1 crown atlas."""
        rank_index = PREVIEW_RANK_MAP.get(rank_name, PREVIEW_RANK_DEFAULT)
        u0 = rank_index / float(PREVIEW_RANK_ATLAS_COLS)
        u1 = (rank_index + 1) / float(PREVIEW_RANK_ATLAS_COLS)
        return u0, u1
    
    # ========================================
    # Rendering Primitives (single-purpose methods)
    # ========================================
    
    def _render_preview_coa(self, center_x_px, center_y_px, width_px, height_px, mask_texture, coa_scale, coa_offset):
        """Render CoA with mask using preview_composite_shader.
        
        Uses the shared CoA RTT texture already rendered by _render_coa_to_framebuffer().
        This method just composites it with a different mask and positioning.
        """
        if not self.preview_composite_shader or not mask_texture:
            return
        
        self.vao.bind()
        self.preview_composite_shader.bind()
        
        # Bind shared CoA RTT texture (same texture used by main canvas)
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
        self.preview_composite_shader.setUniformValue("uvOffset", QVector2D(0.0, 0.0))
        self.preview_composite_shader.setUniformValue("uvScale", QVector2D(1.0, 1.0))
        self.preview_composite_shader.setUniformValue("flipU", False)
        self.preview_composite_shader.setUniformValue("flipV", False)
        
        # Set CoA positioning within mask
        self.preview_composite_shader.setUniformValue("coaScale", QVector2D(coa_scale[0], coa_scale[1]))
        self.preview_composite_shader.setUniformValue("coaOffset", QVector2D(coa_offset[0], coa_offset[1]))
        
        gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
        
        self.preview_composite_shader.release()
        self.vao.release()
    
    def _render_tilesheet_quad(self, center_x_px, center_y_px, width_px, height_px, texture, 
                               tile_cols = 1, tile_rows = 1, tile_index = 0, flip_v = False):
        """Shared quad rendering for all tilesheet-based elements.
        
        Args:
            center_x_px, center_y_px: Pixel position (center)
            width_px, height_px: Quad dimensions
            texture: OpenGL texture ID
            tile_cols, tile_rows: Tilesheet dimensions
            tile_index: Which tile to render
            flip_v: Vertical flip flag
        """
        if not self.tilesheet_shader or not texture:
            return
        
        self.vao.bind()
        self.tilesheet_shader.bind()
        
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
        self.tilesheet_shader.setUniformValue("tilesheetSampler", 0)
        
        # Tilesheet properties
        self.tilesheet_shader.setUniformValue("tileCols", tile_cols)
        self.tilesheet_shader.setUniformValue("tileRows", tile_rows)
        self.tilesheet_shader.setUniformValue("tileIndex", tile_index)
        
        # Transform uniforms
        self.tilesheet_shader.setUniformValue("screenRes", QVector2D(self.width(), self.height()))
        self.tilesheet_shader.setUniformValue("position", QVector2D(center_x_px - self.width()/2.0, self.height()/2.0 - center_y_px))
        self.tilesheet_shader.setUniformValue("scale", QVector2D(width_px, height_px))
        self.tilesheet_shader.setUniformValue("rotation", 0.0)
        self.tilesheet_shader.setUniformValue("uvOffset", QVector2D(0.0, 0.0))
        self.tilesheet_shader.setUniformValue("uvScale", QVector2D(1.0, 1.0))
        self.tilesheet_shader.setUniformValue("flipU", False)
        self.tilesheet_shader.setUniformValue("flipV", flip_v)
        
        gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
        
        self.tilesheet_shader.release()
        self.vao.release()
    
    def _render_preview_frame(self, center_x_px, center_y_px, width_px, height_px, frame_texture):
        """Render preview frame (single texture, no atlas)."""
        self._render_tilesheet_quad(center_x_px, center_y_px, width_px, height_px, 
                                     frame_texture, tile_cols=1, tile_rows=1, tile_index=0, flip_v=True)
    
    def _render_ranked_element(self, center_x_px, center_y_px, width_px, height_px, texture, rank_name, flip_v):
        """Render rank-based element (crown or topframe) from 7x1 atlas."""
        if not texture:
            return
        u0, u1 = self._get_rank_uv(rank_name)
        rank_index = int(u0 * PREVIEW_RANK_ATLAS_COLS)
        self._render_tilesheet_quad(center_x_px, center_y_px, width_px, height_px,
                                     texture, tile_cols=PREVIEW_RANK_ATLAS_COLS, tile_rows=1, 
                                     tile_index=rank_index, flip_v=flip_v)
    
    # ========================================
    # Core Rendering Methods (readable stacks)
    # ========================================
    
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
        
        # Render government frame
        gov_frame = self.realm_frame_frames.get((self.preview_government, self.preview_size))
        if gov_frame:
            self._render_preview_frame(center_x_px, center_y_px, width_px, height_px, gov_frame)
        
        # Render crown strip
        crown_strip = self.crown_strips.get(self.preview_size)
        if crown_strip:
            crown_offset_px = self._calculate_crown_offset_government(self.preview_size)
            crown_center_y_px = top_px + crown_offset_px + crown_height_px / 2.0
            self._render_ranked_element(center_x_px, crown_center_y_px, width_px, crown_height_px, 
                                        crown_strip, self.preview_rank, flip_v=True)
        
        # Render topframe
        topframe = self.topframes.get(self.preview_size)
        if topframe:
            topframe_offset_px = self._calculate_topframe_offset(self.preview_size)
            topframe_center_y_px = center_y_px + topframe_offset_px
            self._render_ranked_element(center_x_px, topframe_center_y_px, width_px, height_px, 
                                        topframe, self.preview_rank, flip_v=True)
    
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
            crown_offset_px = self._calculate_crown_offset_title(self.preview_size)
            crown_center_y_px = top_px + crown_offset_px + crown_height_px / 2.0
            self._render_ranked_element(center_x_px, crown_center_y_px, width_px, crown_height_px,
                                        crown_strip, self.preview_rank, flip_v=True)
        
        # Render title frame (scaled)
        title_frame = self.title_frames.get(self.preview_size)
        if not title_frame and self.preview_size == 115:
            title_frame = self.title_frames.get(86)
        if title_frame:
            scaled_width = width_px * PREVIEW_TITLE_FRAME_SCALE
            scaled_height = height_px * PREVIEW_TITLE_FRAME_SCALE
            self._render_preview_frame(center_x_px, center_y_px, scaled_width, scaled_height, title_frame)
    
    # ========================================
    # Public API Methods
    # ========================================
    
    def _render_government_preview(self):
        """Render government preview in top-left corner."""
        width_px, height_px, crown_height_px, total_height_px = self._calculate_preview_dimensions(self.preview_size)
        left_px = PREVIEW_CORNER_PADDING_PX
        top_px = PREVIEW_CORNER_PADDING_PX + PREVIEW_VERTICAL_OFFSET_PX
        self._render_government_preview_at_px(left_px, top_px)
    
    def _render_title_preview(self):
        """Render title preview in top-right corner."""
        width_px, height_px, crown_height_px, total_height_px = self._calculate_preview_dimensions(self.preview_size)
        left_px = self.width() - width_px - PREVIEW_CORNER_PADDING_PX
        top_px = PREVIEW_CORNER_PADDING_PX + PREVIEW_VERTICAL_OFFSET_PX
        self._render_title_preview_at_px(left_px, top_px)
    
    def set_preview_enabled(self, enabled):
        """Toggle preview rendering."""
        self.preview_enabled = enabled
        self.update()
    
    def set_preview_government(self, government):
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
    
    # ========================================
    # Export Methods
    # ========================================
    
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
