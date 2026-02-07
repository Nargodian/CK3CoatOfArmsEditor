"""Canvas rendering mixin for shared rendering logic.

This mixin provides shared rendering methods for both normal CoA rendering
and picker RTT rendering, eliminating duplicate transform calculations.
"""

import math
import OpenGL.GL as gl
from PyQt5.QtGui import QVector2D, QVector3D, QVector4D
from models.coa import CoA


class CanvasRenderingMixin:
    """Mixin providing shared rendering logic for CoA and picker."""
    
    # ========================================
    # Core CoA Rendering
    # ========================================
    
    def _render_base_pattern(self):
        """Render the base pattern layer."""
        if not self.base_shader or not self.default_mask_texture:
            return
        
        # Get pattern texture
        u0, v0, u1, v1 = 0.0, 0.0, 1.0, 1.0
        pattern_texture_id = self.default_mask_texture
        if self.base_texture and self.base_texture in self.texture_uv_map:
            atlas_index, u0, v0, u1, v1 = self.texture_uv_map[self.base_texture]
            if 0 <= atlas_index < len(self.texture_atlases):
                pattern_texture_id = self.texture_atlases[atlas_index]
        
        # Render full-screen quad (no transforms needed)
        self.vao.bind()
        self.base_shader.bind()
        
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, pattern_texture_id)
        self.base_shader.setUniformValue("patternMaskSampler", 0)
        self.base_shader.setUniformValue("color1", QVector3D(*self.base_colors[0]))
        self.base_shader.setUniformValue("color2", QVector3D(*self.base_colors[1]))
        self.base_shader.setUniformValue("color3", QVector3D(*self.base_colors[2]))
        
        # Calculate tile index from UV offset (32x32 grid)
        tile_x = int(u0 * 32.0)
        tile_y = int(v0 * 32.0)
        tile_index_loc = self.base_shader.uniformLocation("tileIndex")
        if tile_index_loc != -1:
            gl.glUniform2ui(tile_index_loc, tile_x, tile_y)
        
        gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
        
        self.base_shader.release()
        self.vao.release()
    
    def _render_emblem_layers(self):
        """Render all emblem layers from CoA model."""
        coa = CoA.get_active() if CoA.has_active() else None
        if not coa or not self.design_shader or coa.get_layer_count() == 0:
            return
        
        self.vao.bind()
        self.design_shader.bind()
        
        # Bind pattern texture once for mask channels
        self._bind_pattern_for_masks()
        
        # Iterate through layers
        for layer_uuid in coa.get_all_layer_uuids():
            if not coa.get_layer_visible(layer_uuid):
                continue
            
            filename = coa.get_layer_filename(layer_uuid)
            if not filename or filename not in self.texture_uv_map:
                continue
            
            atlas_idx, u0, v0, u1, v1 = self.texture_uv_map[filename]
            if atlas_idx >= len(self.texture_atlases):
                continue
            
            # Bind emblem texture
            gl.glActiveTexture(gl.GL_TEXTURE0)
            gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_atlases[atlas_idx])
            self.design_shader.setUniformValue("emblemMaskSampler", 0)
            
            # Set emblem tile index (32×32 grid)
            tile_index_loc = self.design_shader.uniformLocation("emblemTileIndex")
            if tile_index_loc != -1:
                tile_x = int(u0 * 32.0)
                tile_y = int(v0 * 32.0)
                gl.glUniform2ui(tile_index_loc, tile_x, tile_y)
            
            # Set layer properties
            self._set_layer_uniforms(coa, layer_uuid)
            
            # Render all instances
            self._render_layer_instances(coa, layer_uuid, (u0, v0, u1, v1), self.design_shader)
        self.design_shader.release()
        self.vao.release()

    def _bind_pattern_for_masks(self):
        """Bind pattern texture for emblem mask channels."""
        if self.base_texture and self.base_texture in self.texture_uv_map:
            pattern_atlas_idx, p_u0, p_v0, p_u1, p_v1 = self.texture_uv_map[self.base_texture]
            if pattern_atlas_idx < len(self.texture_atlases):
                gl.glActiveTexture(gl.GL_TEXTURE2)
                gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_atlases[pattern_atlas_idx])
                if self.design_shader.uniformLocation("patternMaskSampler") != -1:
                    self.design_shader.setUniformValue("patternMaskSampler", 2)
                
                # Use tileIndex instead of patternUV (32×32 grid for patterns)
                tile_index_loc = self.design_shader.uniformLocation("patternTileIndex")
                if tile_index_loc != -1:
                    tile_x = int(p_u0 * 32.0)
                    tile_y = int(p_v0 * 32.0)
                    gl.glUniform2ui(tile_index_loc, tile_x, tile_y)
    
    def _set_layer_uniforms(self, coa, layer_uuid):
        """Set shader uniforms for a layer."""
        # Colors
        color1 = coa.get_layer_color(layer_uuid, 1)
        color2 = coa.get_layer_color(layer_uuid, 2)
        color3 = coa.get_layer_color(layer_uuid, 3)
        self.design_shader.setUniformValue("primaryColor", color1[0], color1[1], color1[2])
        self.design_shader.setUniformValue("secondaryColor", color2[0], color2[1], color2[2])
        self.design_shader.setUniformValue("tertiaryColor", color3[0], color3[1], color3[2])
        
        # Selection tint
        show_tint = self._should_show_selection_tint()
        is_selected = self._is_layer_selected(layer_uuid)
        self.design_shader.setUniformValue("selectionTint", 1.0 if (show_tint and is_selected) else 0.0)
        
        # Pattern mask
        mask = coa.get_layer_mask(layer_uuid)
        pattern_flag = self._calculate_pattern_flag(mask)
        self.design_shader.setUniformValue("patternFlag", pattern_flag)
    
    def _calculate_pattern_flag(self, mask):
        """Calculate pattern flag from mask array."""
        if mask is None or len(mask) == 0:
            return 0
        pattern_flag = 0
        if len(mask) > 0 and mask[0] != 0:
            pattern_flag |= 1
        if len(mask) > 1 and mask[1] != 0:
            pattern_flag |= 2
        if len(mask) > 2 and mask[2] != 0:
            pattern_flag |= 4
        return pattern_flag
    
    # ========================================
    # Shared Instance Rendering
    # ========================================
    
    def _render_layer_instances(self, coa, layer_uuid, uv_coords, shader):
        """Render all instances of a layer using the specified shader.
        
        Args:
            coa: CoA model instance
            layer_uuid: UUID of the layer to render
            uv_coords: Tuple of (u0, v0, u1, v1) texture coordinates
            shader: Shader program to use for rendering
        """
        instance_count = coa.get_layer_instance_count(layer_uuid)
        u0, v0, u1, v1 = uv_coords
        
        # Check if layer has symmetry
        symmetry_type = coa.get_layer_symmetry_type(layer_uuid)
        
        for instance_idx in range(instance_count):
            instance = coa.get_layer_instance(layer_uuid, instance_idx)
            
            if symmetry_type != 'none':
                # Get transform plugin and calculate mirrors
                from services.symmetry_transforms import get_transform
                from models.transform import Transform, Vec2
                
                transform_plugin = get_transform(symmetry_type)
                if transform_plugin:
                    # Load properties from layer
                    properties = coa.get_layer_symmetry_properties(layer_uuid)
                    if properties:
                        transform_plugin.set_properties(properties)
                    
                    # Create seed transform from instance
                    seed_transform = Transform(
                        Vec2(instance.pos.x, instance.pos.y),
                        Vec2(instance.scale.x, instance.scale.y),
                        instance.rotation
                    )
                    
                    # Render seed
                    self._render_single_instance(instance, shader)
                    
                    # Calculate and render mirrors
                    mirror_transforms = transform_plugin.calculate_transforms(seed_transform)
                    for mirror_transform in mirror_transforms:
                        self._render_single_transform(mirror_transform, instance, shader)
                else:
                    # Fallback if plugin not found
                    self._render_single_instance(instance, shader)
            else:
                # Normal rendering - just the instance
                self._render_single_instance(instance, shader)
    
    def _render_single_instance(self, instance, shader):
        """Render a single instance (extracted for reuse)
        
        Args:
            instance: Instance object with pos, scale, rotation, flip_x, flip_y
            shader: Shader program to use
        """
        # quad.vert expects pixel-based coordinates in 512×512 framebuffer
        # Convert CoA space (0-1) to pixel position (0-512)
        center_x_coa = instance.pos.x - 0.5  # Center around 0
        center_y_coa = instance.pos.y - 0.5  # Center around 0
        
        # Convert to pixels (CoA center is at 256, 256)
        center_x_px = center_x_coa * 512.0  # Offset from center in pixels
        center_y_px = -center_y_coa * 512.0  # Invert Y, offset from center in pixels
        
        # Scale is in CoA coordinates (0-1 range = full width/height)
        # Convert to pixels: scale * 512
        scale_x_px = instance.scale.x * 512.0
        scale_y_px = instance.scale.y * 512.0
        
        # Negate rotation: CK3 uses Y-down (clockwise positive), OpenGL uses Y-up (counterclockwise positive)
        rotation_rad = math.radians(-instance.rotation)
        
        # Apply per-instance flip via negative scale
        if instance.flip_x:
            scale_x_px = -scale_x_px
        if instance.flip_y:
            scale_y_px = -scale_y_px
        
        # Set transform uniforms for emblem.vert (pixel-based)
        shader.setUniformValue("screenRes", QVector2D(512.0, 512.0))
        shader.setUniformValue("position", QVector2D(center_x_px, center_y_px))
        shader.setUniformValue("scale", QVector2D(scale_x_px, scale_y_px))
        shader.setUniformValue("rotation", rotation_rad)
        
        gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
    
    def _render_single_transform(self, transform, seed_instance, shader):
        """Render a transform (used for symmetry mirrors)
        
        Args:
            transform: Transform object with pos, scale, rotation
            seed_instance: Original instance (for flip_x, flip_y)
            shader: Shader program to use
        """
        from models.coa._internal.instance import Instance
        
        # Create temporary instance-like object for rendering
        # Use transform's pos/scale/rotation, seed's flip_x/flip_y
        temp_data = {
            'pos_x': transform.pos.x,
            'pos_y': transform.pos.y,
            'scale_x': transform.scale.x,
            'scale_y': transform.scale.y,
            'rotation': transform.rotation,
            'flip_x': seed_instance.flip_x,
            'flip_y': seed_instance.flip_y,
            'depth': 0.0
        }
        temp_instance = Instance(temp_data)
        
        # Render using standard method
        self._render_single_instance(temp_instance, shader)
