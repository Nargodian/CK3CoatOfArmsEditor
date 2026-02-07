"""Coordinate transformation mixin for canvas widget.

Provides atomic and composite coordinate transformation methods:
- Atomic: Single-step conversions (Vec2 in, Vec2 out)
- Helpers: Chain only atomics (never call other helpers)

Coordinate spaces:
- CoA: 0-1 normalized space (0.5 is center)
- Frame: CoA space with frame scale/offset applied
- Canvas: Qt pixel coordinates with zoom/pan applied
"""
from models.transform import Transform, Vec2


class CanvasCoordinateMixin:
    """Mixin providing coordinate transformation methods.
    
    Requires the following from the parent class:
    - self.get_frame_transform() -> (scale_tuple, offset_tuple)
    - self.zoom_level (float)
    - self.pan_x, self.pan_y (float)
    - self.width(), self.height() (methods returning int)
    """
    
    # ========================================
    # ATOMICS: Origin conversions
    # ========================================
    
    def center_origin_to_topleft(self, center_pos):
        """Convert center-origin coordinates to top-left origin (ATOMIC).
        
        Args:
            center_pos: Vec2 in center-origin space (0,0 at center)
            
        Returns:
            Vec2 in top-left origin space
        """
        half_width = self.width() / 2
        half_height = self.height() / 2
        return Vec2(center_pos.x + half_width, center_pos.y + half_height)
    
    def topleft_to_center_origin(self, topleft_pos):
        """Convert top-left origin to center-origin coordinates (ATOMIC).
        
        Args:
            topleft_pos: Vec2 in top-left origin space
            
        Returns:
            Vec2 in center-origin space (0,0 at center)
        """
        half_width = self.width() / 2
        half_height = self.height() / 2
        return Vec2(topleft_pos.x - half_width, topleft_pos.y - half_height)
    
    # ========================================
    # ATOMICS: Pan/zoom/normalize
    # ========================================
    
    def remove_pan(self, canvas_pos):
        """Remove pan offset from canvas coordinates (ATOMIC).
        
        Args:
            canvas_pos: Vec2 in canvas pixels
            
        Returns:
            Vec2 in canvas pixels (without pan)
        """
        return Vec2(canvas_pos.x - self.pan_x, canvas_pos.y - self.pan_y)
    
    def apply_pan(self, canvas_pos):
        """Apply pan offset to canvas coordinates (ATOMIC).
        
        Args:
            canvas_pos: Vec2 in canvas pixels (without pan)
            
        Returns:
            Vec2 in canvas pixels (with pan applied)
        """
        return Vec2(canvas_pos.x + self.pan_x, canvas_pos.y + self.pan_y)
    
    def normalize_by_viewport(self, viewport_pos):
        """Normalize center-origin pixels by viewport size to ±1 range (ATOMIC).
        
        Does NOT undo zoom - just normalizes by physical size.
        
        Args:
            viewport_pos: Vec2 pixels from center
            
        Returns:
            Vec2 normalized by viewport size (still zoomed)
        """
        from components.canvas_widget import COA_BASE_SIZE_PX
        # Use COA_BASE_SIZE_PX as reference, not viewport size, to match compositing shader
        return Vec2(
            viewport_pos.x / (COA_BASE_SIZE_PX / 2),
            -viewport_pos.y / (COA_BASE_SIZE_PX / 2)  # Flip Y (Qt Y-down)
        )
    
    def denormalize_by_viewport(self, normalized_pos):
        """Convert ±1 range to center-origin pixels by viewport size (ATOMIC).
        
        Does NOT apply zoom - just denormalizes by physical size.
        
        Args:
            normalized_pos: Vec2 in ±1 range (still zoomed)
            
        Returns:
            Vec2 pixels from center
        """
        from components.canvas_widget import COA_BASE_SIZE_PX
        # Use COA_BASE_SIZE_PX as reference, not viewport size, to match compositing shader
        return Vec2(
            normalized_pos.x * (COA_BASE_SIZE_PX / 2),
            -normalized_pos.y * (COA_BASE_SIZE_PX / 2)  # Flip Y
        )
    
    def undo_zoom(self, normalized_pos):
        """Divide out zoom magnification (ATOMIC).
        
        Args:
            normalized_pos: Vec2 normalized (zoomed)
            
        Returns:
            Vec2 normalized at zoom=1.0
        """
        return Vec2(normalized_pos.x / self.zoom_level, normalized_pos.y / self.zoom_level)
    
    def apply_zoom(self, normalized_pos):
        """Multiply by zoom magnification (ATOMIC).
        
        Args:
            normalized_pos: Vec2 normalized at zoom=1.0
            
        Returns:
            Vec2 normalized with zoom applied
        """
        return Vec2(normalized_pos.x * self.zoom_level, normalized_pos.y * self.zoom_level)
    
    # ========================================
    # HELPERS: Frame ↔ Canvas (use atomics only)
    # ========================================
    
    def frame_to_canvas(self, frame_pos, clamp=False):
        """Convert frame space to canvas pixel coordinates (HELPER - uses atomics only).
        
        Args:
            frame_pos: Vec2 in frame space (0-1)
            clamp: If True, clamp result to canvas bounds
            
        Returns:
            Vec2 in canvas pixel coordinates
        """
        # Frame 0-1 → ±1 normalized
        normalized_pos = Vec2(frame_pos.x * 2.0 - 1.0, -(frame_pos.y * 2.0 - 1.0))
        
        # Apply zoom
        normalized_pos = self.apply_zoom(normalized_pos)
        
        # Denormalize by viewport
        viewport_pos = self.denormalize_by_viewport(normalized_pos)
        
        # Center-origin → top-left
        canvas_pos = self.center_origin_to_topleft(viewport_pos)
        
        # Apply pan
        canvas_pos = self.apply_pan(canvas_pos)
        
        if clamp:
            width, height = self.width(), self.height()
            canvas_pos = Vec2(
                max(0, min(width, canvas_pos.x)),
                max(0, min(height, canvas_pos.y))
            )
        
        return canvas_pos
    
    def canvas_to_frame(self, canvas_pos):
        """Convert canvas pixel coordinates to frame space (HELPER - uses atomics only).
        
        Args:
            canvas_pos: Vec2 in canvas pixels
            
        Returns:
            Vec2 in frame space (0-1)
        """
        # Remove pan
        canvas_pos = self.remove_pan(canvas_pos)
        
        # Top-left → center-origin
        viewport_pos = self.topleft_to_center_origin(canvas_pos)
        
        # Normalize by viewport
        normalized_pos = self.normalize_by_viewport(viewport_pos)
        
        # Undo zoom
        normalized_pos = self.undo_zoom(normalized_pos)
        
        # ±1 normalized → frame 0-1
        frame_pos = Vec2(
            (normalized_pos.x + 1.0) / 2.0,
            (-normalized_pos.y + 1.0) / 2.0  # Flip Y back
        )
        
        return frame_pos
    
    # ========================================
    # HELPERS: CoA ↔ Frame (use atomics only)
    # ========================================
    
    def coa_to_frame(self, coa_pos):
        """Convert CoA space to frame-adjusted space (ATOMIC).
        
        Args:
            coa_pos: Vec2 in CoA space (0-1)
            
        Returns:
            Vec2 in frame space (0-1)
        """
        frame_scales, frame_offsets = self.get_frame_transform()
        
        # Move to origin
        frame_pos = Vec2(coa_pos.x - 0.5, coa_pos.y - 0.5)
        
        # Apply frame scale
        frame_pos = Vec2(frame_pos.x * frame_scales[0], frame_pos.y * frame_scales[1])
        
        # Move back from origin
        frame_pos = Vec2(frame_pos.x + 0.5, frame_pos.y + 0.5)
        
        # Apply frame offset (subtract to shift content)
        frame_pos = Vec2(frame_pos.x - frame_offsets[0] * frame_scales[0], 
                         frame_pos.y - frame_offsets[1] * frame_scales[1])
        
        return frame_pos
    
    def frame_to_coa(self, frame_pos):
        """Convert frame-adjusted space back to CoA space (ATOMIC).
        
        Args:
            frame_pos: Vec2 in frame space (0-1)
            
        Returns:
            Vec2 in CoA space (0-1)
        """
        frame_scales, frame_offsets = self.get_frame_transform()
        
        # Move to origin
        coa_pos = Vec2(frame_pos.x - 0.5, frame_pos.y - 0.5)
        
        # Remove frame offset (add back to reverse subtraction)
        coa_pos = Vec2(coa_pos.x + frame_offsets[0] * frame_scales[0], 
                       coa_pos.y + frame_offsets[1] * frame_scales[1])
        
        # Remove frame scale
        coa_pos = Vec2(coa_pos.x / frame_scales[0], coa_pos.y / frame_scales[1])
        
        # Move back from origin
        coa_pos = Vec2(coa_pos.x + 0.5, coa_pos.y + 0.5)
        
        return coa_pos
    
    # ========================================
    # HELPERS: CoA ↔ Canvas (composite chains)
    # ========================================
    
    def coa_to_canvas(self, coa_pos, clamp=False):
        """Convert CoA space (0-1) to canvas pixel coordinates (HELPER).
        
        Args:
            coa_pos: Vec2 in CoA space (0-1, where 0.5 is center)
            clamp: If True, clamp result to canvas bounds
            
        Returns:
            Vec2 in canvas pixel coordinates
        """
        frame_pos = self.coa_to_frame(coa_pos)
        return self.frame_to_canvas(frame_pos, clamp)
    
    def canvas_to_coa(self, canvas_pos, clamp=False):
        """Convert canvas pixel coordinates to CoA space (0-1) (HELPER).
        
        Args:
            canvas_pos: Vec2 in canvas pixels
            clamp: If True, clamp result to 0-1 range
            
        Returns:
            Vec2 in CoA space (0-1 range)
        """
        frame_pos = self.canvas_to_frame(canvas_pos)
        coa_pos = self.frame_to_coa(frame_pos)
        
        if clamp:
            coa_pos = Vec2(
                max(0.0, min(1.0, coa_pos.x)),
                max(0.0, min(1.0, coa_pos.y))
            )
        
        return coa_pos
    
    # ========================================
    # HELPERS: Viewport bounds (chains atomics only)
    # ========================================
    
    def get_coa_viewport_bounds(self):
        """Get viewport pixel bounds of CoA rendering area (HELPER - uses atomics only).
        
        Calculates the AABB where CoA RTT (0-1 space) appears in viewport pixels.
        
        Returns:
            tuple: (left_px, right_px, bottom_px, top_px) in viewport pixels (OpenGL origin)
        """
        # CoA corners in CoA space (0-1 range)
        top_left_coa = Vec2(0.0, 0.0)
        bottom_right_coa = Vec2(1.0, 1.0)
        
        # Convert to canvas pixels using existing helper
        top_left_canvas = self.coa_to_canvas(top_left_coa)
        bottom_right_canvas = self.coa_to_canvas(bottom_right_coa)
        
        # Extract bounds (canvas is Qt top-left origin, need to flip to OpenGL bottom-left)
        left_px = top_left_canvas.x
        right_px = bottom_right_canvas.x
        
        # Flip Y to OpenGL coordinates (bottom-left origin)
        viewport_height = self.height()
        top_px = viewport_height - top_left_canvas.y
        bottom_px = viewport_height - bottom_right_canvas.y
        
        return (left_px, right_px, bottom_px, top_px)
    
    # ========================================
    # Scale transformations (atomic + composite)
    # ========================================
    
    def coa_scale_to_frame_scale(self, scale_x, scale_y):
        """Convert CoA scale to frame-adjusted scale.
        
        Args:
            scale_x: CoA scale multiplier (1.0 = normal size)
            scale_y: CoA scale multiplier (1.0 = normal size)
            
        Returns:
            (frame_scale_x, frame_scale_y): Frame-adjusted scale multipliers
        """
        frame_scales, _ = self.get_frame_transform()
        return scale_x * frame_scales[0], scale_y * frame_scales[1]
    
    def frame_scale_to_pixels(self, frame_scale_x, frame_scale_y):
        """Convert frame-adjusted scale to pixel AABB half-dimensions.
        
        Args:
            frame_scale_x: Frame-adjusted scale multiplier
            frame_scale_y: Frame-adjusted scale multiplier
            
        Returns:
            (half_w, half_h): Pixel radius of AABB (half width, half height)
        """
        from components.canvas_widget import COA_BASE_SIZE_PX
        
        half_w = abs(frame_scale_x) * COA_BASE_SIZE_PX * self.zoom_level / 2.0
        half_h = abs(frame_scale_y) * COA_BASE_SIZE_PX * self.zoom_level / 2.0
        
        return half_w, half_h
    
    def coa_scale_to_pixels(self, scale_x, scale_y):
        """Convert CoA scale to pixel AABB half-dimensions (composite).
        
        Chains coa_scale_to_frame_scale() → frame_scale_to_pixels()
        
        Args:
            scale_x: CoA scale multiplier (1.0 = normal size)
            scale_y: CoA scale multiplier (1.0 = normal size)
            
        Returns:
            (half_w, half_h): Pixel radius of AABB
        """
        frame_scale_x, frame_scale_y = self.coa_scale_to_frame_scale(scale_x, scale_y)
        return self.frame_scale_to_pixels(frame_scale_x, frame_scale_y)
    
    def coa_to_transform_widget(self, coa_transform, is_aabb_dimension=False):
        """Convert CoA space to transform widget center-origin coordinates (HELPER).
        
        Args:
            coa_transform: Transform in CoA space (0-1 normalized)
            is_aabb_dimension: If True, scale is an AABB dimension (not a multiplier)
            
        Returns:
            Transform in widget pixel space (center-origin)
        """
        # Convert position to canvas top-left pixels
        canvas_pos = self.coa_to_canvas(coa_transform.pos)
        
        # Convert scale to pixels
        if is_aabb_dimension:
            # For AABB dimensions, treat as raw CoA space spans (no frame compensation)
            # Convert dimension to pixels: dimension * viewport_size
            from components.canvas_widget import COA_BASE_SIZE_PX
            half_w = coa_transform.scale.x * COA_BASE_SIZE_PX * self.zoom_level / 2.0
            half_h = coa_transform.scale.y * COA_BASE_SIZE_PX * self.zoom_level / 2.0
        else:
            # For instance scales, apply frame compensation
            half_w, half_h = self.coa_scale_to_pixels(coa_transform.scale.x, coa_transform.scale.y)
        
        # Shift to center-origin (transform widget coordinate system)
        widget_pos = Vec2(canvas_pos.x - self.width() / 2, canvas_pos.y - self.height() / 2)
        widget_scale = Vec2(half_w, half_h)
        
        return Transform(widget_pos, widget_scale, coa_transform.rotation)
    
    def pixels_to_frame_scale(self, half_w, half_h):
        """Convert pixel AABB half-dimensions to frame-adjusted scale.
        
        Args:
            half_w: Pixel AABB half-width
            half_h: Pixel AABB half-height
            
        Returns:
            (frame_scale_x, frame_scale_y): Frame-adjusted scale multipliers
        """
        from components.canvas_widget import COA_BASE_SIZE_PX
        
        frame_scale_x = (half_w * 2.0) / (COA_BASE_SIZE_PX * self.zoom_level)
        frame_scale_y = (half_h * 2.0) / (COA_BASE_SIZE_PX * self.zoom_level)
        
        return frame_scale_x, frame_scale_y
    
    def frame_scale_to_coa_scale(self, frame_scale_x, frame_scale_y):
        """Convert frame-adjusted scale back to CoA scale.
        
        Args:
            frame_scale_x: Frame-adjusted scale multiplier
            frame_scale_y: Frame-adjusted scale multiplier
            
        Returns:
            (scale_x, scale_y): CoA scale multipliers (1.0 = normal)
        """
        frame_scales, _ = self.get_frame_transform()
        return frame_scale_x / frame_scales[0], frame_scale_y / frame_scales[1]
    
    def pixels_to_coa_scale(self, half_w, half_h):
        """Convert pixel AABB half-dimensions to CoA scale (composite).
        
        Chains pixels_to_frame_scale() → frame_scale_to_coa_scale()
        
        Args:
            half_w: Pixel AABB half-width
            half_h: Pixel AABB half-height
            
        Returns:
            (scale_x, scale_y): CoA scale multipliers (1.0 = normal)
        """
        frame_scale_x, frame_scale_y = self.pixels_to_frame_scale(half_w, half_h)
        return self.frame_scale_to_coa_scale(frame_scale_x, frame_scale_y)
