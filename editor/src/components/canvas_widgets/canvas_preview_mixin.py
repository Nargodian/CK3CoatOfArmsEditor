"""Canvas preview rendering system - government and title previews"""
import numpy as np
import OpenGL.GL as gl
from PyQt5.QtGui import QVector2D


class CanvasPreviewMixin:
    """Mixin for rendering government and title preview graphics
    
    Keeps canvas_widget.py from growing too large by separating preview functionality.
    """
    
    def get_preview_dimensions(self, preview_size_px=None, viewport_size=None):
        """Calculate preview dimensions in NDC coordinates
        
        Args:
            preview_size_px: Size in pixels (uses self.preview_size if None)
            viewport_size: (width, height) tuple (uses widget size if None)
        
        Returns:
            dict with:
                - size_ndc: (width, height) in NDC coordinates
                - crown_height_ndc: height of crown in NDC
                - total_height_ndc: preview + crown height
        """
        if preview_size_px is None:
            preview_size_px = self.preview_size
        
        if viewport_size is None:
            viewport_width = self.width()
            viewport_height = self.height()
        else:
            viewport_width, viewport_height = viewport_size
        
        # Convert to NDC (normalized device coordinates: -1 to 1)
        size_x = preview_size_px / viewport_width
        size_y = preview_size_px / viewport_height
        
        # Crown height is 80/128 of preview height
        crown_height = size_y * 2.0 * (80.0 / 128.0)
        
        # Total height including crown
        total_height = size_y * 2.0 + crown_height
        
        return {
            'size_ndc': (size_x * 2.0, size_y * 2.0),
            'crown_height_ndc': crown_height,
            'total_height_ndc': total_height
        }
    
    def _render_government_preview_at(self, ndc_left, ndc_top, viewport_size=None):
        """Render government preview at specified NDC position
        
        Args:
            ndc_left: Left edge in NDC coordinates (-1 to 1)
            ndc_top: Top edge in NDC coordinates (-1 to 1)
            viewport_size: Optional (width, height) tuple for export rendering
        """
        if not self.composite_shader or not self.vao:
            return
        
        # Get government mask
        gov_mask = self.realm_frame_masks.get(self.preview_government)
        if not gov_mask:
            return
        
        # Get dimensions
        if viewport_size is None:
            viewport_width = self.width()
            viewport_height = self.height()
        else:
            viewport_width, viewport_height = viewport_size
        
        dims = self.get_preview_dimensions(viewport_size=viewport_size)
        size_x, size_y = dims['size_ndc']
        crown_height = dims['crown_height_ndc']
        
        # Calculate bounds from top-left anchor
        left = ndc_left
        right = left + size_x
        top = ndc_top
        bottom = top - size_y
        
        # Shift entire preview down to accommodate crown above
        top -= crown_height
        bottom -= crown_height
        
        # Render CoA with government mask
        self.vao.bind()
        self.composite_shader.bind()
        
        # Bind RTT texture (same CoA)
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.framebuffer_rtt.get_texture())
        self.composite_shader.setUniformValue("coaTextureSampler", 0)
        
        # Bind government mask
        gl.glActiveTexture(gl.GL_TEXTURE1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, gov_mask)
        self.composite_shader.setUniformValue("frameMaskSampler", 1)
        
        # Bind material and noise textures
        if self.texturedMask:
            gl.glActiveTexture(gl.GL_TEXTURE2)
            gl.glBindTexture(gl.GL_TEXTURE_2D, self.texturedMask)
            self.composite_shader.setUniformValue("texturedMaskSampler", 2)
        
        if self.noiseMask:
            gl.glActiveTexture(gl.GL_TEXTURE3)
            gl.glBindTexture(gl.GL_TEXTURE_2D, self.noiseMask)
            self.composite_shader.setUniformValue("noiseMaskSampler", 3)
        
        # Set CoA scale and offset
        self.composite_shader.setUniformValue("coaScale", QVector2D(0.9, 0.9))
        self.composite_shader.setUniformValue("coaOffset", QVector2D(0.0, 0.1))
        self.composite_shader.setUniformValue("bleedMargin", 1.0)
        
        # Render quad
        vertices = np.array([
            left, bottom, 0.0,  0.0, 0.0,
            right, bottom, 0.0,  1.0, 0.0,
            right, top, 0.0,  1.0, 1.0,
            left, top, 0.0,  0.0, 1.0,
        ], dtype=np.float32)
        
        self.vbo.write(0, vertices.tobytes(), vertices.nbytes)
        gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
        
        self.composite_shader.release()
        
        # Render government frame on top (flipped vertically)
        gov_frame = self.realm_frame_frames.get((self.preview_government, self.preview_size))
        if gov_frame and self.basic_shader:
            self.basic_shader.bind()
            
            gl.glActiveTexture(gl.GL_TEXTURE0)
            gl.glBindTexture(gl.GL_TEXTURE_2D, gov_frame)
            self.basic_shader.setUniformValue("textureSampler", 0)
            
            # Flip V coordinates
            frame_verts = np.array([
                left, bottom, 0.0,  0.0, 1.0,  # Flipped V
                right, bottom, 0.0,  1.0, 1.0,
                right, top, 0.0,  1.0, 0.0,
                left, top, 0.0,  0.0, 0.0,
            ], dtype=np.float32)
            
            self.vbo.write(0, frame_verts.tobytes(), frame_verts.nbytes)
            gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
            
            self.basic_shader.release()
        
        # Render crown strip (rank-based UV from 7x1 atlas)
        crown_strip = self.crown_strips.get(self.preview_size)
        if crown_strip and self.basic_shader:
            u0, u1 = self._get_rank_uv(self.preview_rank)
            self.basic_shader.bind()
            
            gl.glActiveTexture(gl.GL_TEXTURE0)
            gl.glBindTexture(gl.GL_TEXTURE_2D, crown_strip)
            self.basic_shader.setUniformValue("textureSampler", 0)
            
            # Crown offset
            crown_offset_px = (7.5 / 115.0) * self.preview_size
            crown_offset = (crown_offset_px / viewport_height) * 2.0
            crown_bottom = top + crown_offset
            crown_top = top + crown_height + crown_offset
            
            # Use rank-specific UV coordinates, flipped vertically
            crown_verts = np.array([
                left, crown_bottom, 0.0,  u0, 1.0,
                right, crown_bottom, 0.0,  u1, 1.0,
                right, crown_top, 0.0,  u1, 0.0,
                left, crown_top, 0.0,  u0, 0.0,
            ], dtype=np.float32)
            
            self.vbo.write(0, crown_verts.tobytes(), crown_verts.nbytes)
            gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
            
            self.basic_shader.release()
        
        # Render topframe
        topframe = self.topframes.get(self.preview_size)
        if topframe and self.basic_shader:
            u0, u1 = self._get_rank_uv(self.preview_rank)
            self.basic_shader.bind()
            
            gl.glActiveTexture(gl.GL_TEXTURE0)
            gl.glBindTexture(gl.GL_TEXTURE_2D, topframe)
            self.basic_shader.setUniformValue("textureSampler", 0)
            
            # Topframe offset
            topframe_offset_px = (10.0 / 115.0) * self.preview_size + (6.0 / 115.0) * self.preview_size
            topframe_offset = (topframe_offset_px / viewport_height) * 2.0
            topframe_bottom = bottom + topframe_offset
            topframe_top = top + topframe_offset
            
            # Use rank-specific UV coordinates, flipped vertically
            topframe_verts = np.array([
                left, topframe_bottom, 0.0,  u0, 1.0,
                right, topframe_bottom, 0.0,  u1, 1.0,
                right, topframe_top, 0.0,  u1, 0.0,
                left, topframe_top, 0.0,  u0, 0.0,
            ], dtype=np.float32)
            
            self.vbo.write(0, topframe_verts.tobytes(), topframe_verts.nbytes)
            gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
            
            self.basic_shader.release()
        
        self.vao.release()
    
    def _render_title_preview_at(self, ndc_left, ndc_top, viewport_size=None):
        """Render title preview at specified NDC position
        
        Args:
            ndc_left: Left edge in NDC coordinates (-1 to 1)
            ndc_top: Top edge in NDC coordinates (-1 to 1)
            viewport_size: Optional (width, height) tuple for export rendering
        """
        if not self.composite_shader or not self.vao:
            return
        
        # Get title mask
        if not self.title_mask:
            return
        
        # Get dimensions
        if viewport_size is None:
            viewport_width = self.width()
            viewport_height = self.height()
        else:
            viewport_width, viewport_height = viewport_size
        
        dims = self.get_preview_dimensions(viewport_size=viewport_size)
        size_x, size_y = dims['size_ndc']
        crown_height = dims['crown_height_ndc']
        
        # Calculate bounds from top-left anchor
        left = ndc_left
        right = left + size_x
        top = ndc_top
        bottom = top - size_y
        
        # Shift entire preview down to accommodate crown above
        top -= crown_height
        bottom -= crown_height
        
        # Render CoA with title mask
        self.vao.bind()
        self.composite_shader.bind()
        
        # Bind RTT texture (same CoA)
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.framebuffer_rtt.get_texture())
        self.composite_shader.setUniformValue("coaTextureSampler", 0)
        
        # Bind title mask
        gl.glActiveTexture(gl.GL_TEXTURE1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.title_mask)
        self.composite_shader.setUniformValue("frameMaskSampler", 1)
        
        # Bind material and noise textures
        if self.texturedMask:
            gl.glActiveTexture(gl.GL_TEXTURE2)
            gl.glBindTexture(gl.GL_TEXTURE_2D, self.texturedMask)
            self.composite_shader.setUniformValue("texturedMaskSampler", 2)
        
        if self.noiseMask:
            gl.glActiveTexture(gl.GL_TEXTURE3)
            gl.glBindTexture(gl.GL_TEXTURE_2D, self.noiseMask)
            self.composite_shader.setUniformValue("noiseMaskSampler", 3)
        
        # Set CoA scale and offset
        self.composite_shader.setUniformValue("coaScale", QVector2D(0.9, 0.9))
        self.composite_shader.setUniformValue("coaOffset", QVector2D(0.0, 0.04))
        self.composite_shader.setUniformValue("bleedMargin", 1.0)
        
        # Render quad
        vertices = np.array([
            left, bottom, 0.0,  0.0, 0.0,
            right, bottom, 0.0,  1.0, 0.0,
            right, top, 0.0,  1.0, 1.0,
            left, top, 0.0,  0.0, 1.0,
        ], dtype=np.float32)
        
        self.vbo.write(0, vertices.tobytes(), vertices.nbytes)
        gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
        
        self.composite_shader.release()
        
        # Render crown strip
        crown_strip = self.crown_strips.get(self.preview_size)
        if crown_strip and self.basic_shader:
            u0, u1 = self._get_rank_uv(self.preview_rank)
            self.basic_shader.bind()
            
            gl.glActiveTexture(gl.GL_TEXTURE0)
            gl.glBindTexture(gl.GL_TEXTURE_2D, crown_strip)
            self.basic_shader.setUniformValue("textureSampler", 0)
            
            # Crown offset
            base_offset_px = (1.5 / 115.0) * self.preview_size
            size_adjustment = -2.0 * (115.0 - self.preview_size) / 93.0
            crown_offset_px = base_offset_px + size_adjustment
            crown_offset = (crown_offset_px / viewport_height) * 2.0
            crown_bottom = top + crown_offset
            crown_top = top + crown_height + crown_offset
            
            # Use rank-specific UV coordinates, flipped vertically
            crown_verts = np.array([
                left, crown_bottom, 0.0,  u0, 1.0,
                right, crown_bottom, 0.0,  u1, 1.0,
                right, crown_top, 0.0,  u1, 0.0,
                left, crown_top, 0.0,  u0, 0.0,
            ], dtype=np.float32)
            
            self.vbo.write(0, crown_verts.tobytes(), crown_verts.nbytes)
            gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
            
            self.basic_shader.release()
        
        # Title frame (flipped vertically, scaled 1.1x)
        title_frame = self.title_frames.get(self.preview_size)
        # Fallback: if title_115 missing, use title_86 scaled up
        if not title_frame and self.preview_size == 115:
            title_frame = self.title_frames.get(86)
        
        if title_frame and self.basic_shader:
            self.basic_shader.bind()
            
            gl.glActiveTexture(gl.GL_TEXTURE0)
            gl.glBindTexture(gl.GL_TEXTURE_2D, title_frame)
            self.basic_shader.setUniformValue("textureSampler", 0)
            
            # Apply 1.1x scale to title frame
            scale_factor = 1.1
            frame_width = (right - left) * scale_factor
            frame_height = (top - bottom) * scale_factor
            frame_center_x = (left + right) / 2.0
            frame_center_y = (top + bottom) / 2.0
            frame_left = frame_center_x - frame_width / 2.0
            frame_right = frame_center_x + frame_width / 2.0
            frame_bottom = frame_center_y - frame_height / 2.0
            frame_top = frame_center_y + frame_height / 2.0
            
            # Flip V coordinates
            title_frame_verts = np.array([
                frame_left, frame_bottom, 0.0,  0.0, 1.0,
                frame_right, frame_bottom, 0.0,  1.0, 1.0,
                frame_right, frame_top, 0.0,  1.0, 0.0,
                frame_left, frame_top, 0.0,  0.0, 0.0,
            ], dtype=np.float32)
            
            self.vbo.write(0, title_frame_verts.tobytes(), title_frame_verts.nbytes)
            gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
            
            self.basic_shader.release()
        
        self.vao.release()
    
    def _render_government_preview(self):
        """Render government preview in top-left corner (wrapper for backward compatibility)"""
        # Calculate top-left position with 20px padding
        viewport_width = self.width()
        viewport_height = self.height()
        
        padding_x = 20.0 / viewport_width
        padding_y = 20.0 / viewport_height
        
        ndc_left = -1.0 + padding_x * 2.0
        ndc_top = 1.0 - padding_y * 2.0
        
        self._render_government_preview_at(ndc_left, ndc_top)
    
    def _render_title_preview(self):
        """Render title preview in top-right corner (wrapper for backward compatibility)"""
        # Calculate top-right position with 20px padding
        viewport_width = self.width()
        viewport_height = self.height()
        
        dims = self.get_preview_dimensions()
        size_x, _ = dims['size_ndc']
        
        padding_x = 20.0 / viewport_width
        padding_y = 20.0 / viewport_height
        
        ndc_left = 1.0 - padding_x * 2.0 - size_x
        ndc_top = 1.0 - padding_y * 2.0
        
        self._render_title_preview_at(ndc_left, ndc_top)
