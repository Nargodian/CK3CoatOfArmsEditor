"""Headless CoA Renderer Service.

Provides offscreen OpenGL rendering of Coat of Arms definitions to PNG images.
Uses QOffscreenSurface for headless GL context, then reuses the same shader
pipeline as the interactive editor (CanvasRenderingMixin).

Output is the raw RTT framebuffer: pattern + emblems only, no frame compositing.
"""

import sys
import os
import logging
import numpy as np
from PIL import Image
from pathlib import Path

import OpenGL.GL as gl
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QOpenGLContext, QSurfaceFormat
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QOffscreenSurface

from models.coa import CoA
from models.color import Color
from services.texture_loader import TextureLoader
from services.framebuffer_rtt import FramebufferRTT
from components.canvas_widgets.shader_manager import ShaderManager
from components.canvas_widgets.canvas_rendering_mixin import CanvasRenderingMixin
from utils.path_resolver import (
    get_pattern_metadata_path, get_emblem_metadata_path,
    get_pattern_source_dir, get_emblem_source_dir
)
from constants import DEFAULT_BASE_COLOR1, DEFAULT_BASE_COLOR2, DEFAULT_BASE_COLOR3

logger = logging.getLogger(__name__)


class HeadlessRenderer(CanvasRenderingMixin):
    """Offscreen renderer that produces raw CoA textures as PNG files.

    Inherits CanvasRenderingMixin to reuse the exact same shader uniform
    setup, instance transform math, symmetry handling, and mask logic
    as the interactive editor canvas.

    Provides the self.* attributes the mixin expects:
        base_shader, design_shader, vao, base_texture, base_colors,
        texture_uv_map, texture_atlases, default_mask_texture
    """

    # Output resolution (downsampled from 512x512 RTT)
    OUTPUT_SIZE = 256

    def __init__(self):
        """Boot headless OpenGL context, compile shaders, load atlases."""
        self._app = self._ensure_qapp()
        self._surface = None
        self._gl_context = None

        # GL resources
        self.base_shader = None
        self.design_shader = None
        self.vao = None
        self._vbo = None
        self._ebo = None
        self.framebuffer_rtt = None
        self.texture_atlases = []
        self.texture_uv_map = {}
        self.default_mask_texture = None
        self.base_texture = None
        self.base_colors = [
            Color.from_name(DEFAULT_BASE_COLOR1),
            Color.from_name(DEFAULT_BASE_COLOR2),
            Color.from_name(DEFAULT_BASE_COLOR3),
        ]

        self._init_gl_context()
        self._init_resources()

    # ------------------------------------------------------------------
    # Stubs required by CanvasRenderingMixin (no UI in headless mode)
    # ------------------------------------------------------------------

    def _should_show_selection_tint(self):
        return False

    def _is_layer_selected(self, uuid):
        return False

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_qapp():
        """Return existing QApplication or create a headless one."""
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        return app

    def _init_gl_context(self):
        """Create QOffscreenSurface + QOpenGLContext (OpenGL 3.3 Core)."""
        fmt = QSurfaceFormat()
        fmt.setVersion(3, 3)
        fmt.setProfile(QSurfaceFormat.CoreProfile)
        fmt.setRenderableType(QSurfaceFormat.OpenGL)
        fmt.setDepthBufferSize(0)
        fmt.setStencilBufferSize(0)
        fmt.setRedBufferSize(8)
        fmt.setGreenBufferSize(8)
        fmt.setBlueBufferSize(8)
        fmt.setAlphaBufferSize(8)

        self._surface = QOffscreenSurface()
        self._surface.setFormat(fmt)
        self._surface.create()
        if not self._surface.isValid():
            raise RuntimeError("Failed to create QOffscreenSurface")

        self._gl_context = QOpenGLContext()
        self._gl_context.setFormat(fmt)
        if not self._gl_context.create():
            raise RuntimeError("Failed to create QOpenGLContext")

        if not self._gl_context.makeCurrent(self._surface):
            raise RuntimeError("Failed to make OpenGL context current")

        logger.info(
            "Headless GL context ready: %s",
            gl.glGetString(gl.GL_VERSION).decode()
            if gl.glGetString(gl.GL_VERSION) else "unknown"
        )

    def _init_resources(self):
        """Compile shaders, load atlases, create FBO and quad geometry."""
        shader_mgr = ShaderManager()

        # Shaders — pass None as parent (headless, no QWidget)
        self.base_shader = shader_mgr.create_base_shader(None)
        self.design_shader = shader_mgr.create_design_shader(None)
        if not self.base_shader or not self.design_shader:
            raise RuntimeError("Shader compilation failed")

        # Unit quad VAO/VBO/EBO
        from utils.quad_renderer import QuadRenderer
        self.vao, self._vbo, self._ebo = QuadRenderer.create_unit_quad()

        # Texture atlases (patterns + emblems)
        self._load_texture_atlases()

        # Solid white fallback texture
        self.default_mask_texture = TextureLoader.create_solid_texture(
            (255, 255, 255, 255), size=64
        )

        # RTT framebuffer (512×512)
        self.framebuffer_rtt = FramebufferRTT()
        self.framebuffer_rtt.initialize()

    def _load_texture_atlases(self):
        """Load pattern + emblem atlases into GL textures (same logic as canvas)."""
        import json

        files = []

        # Patterns
        pattern_json = get_pattern_metadata_path()
        if pattern_json.exists():
            with open(pattern_json, "r", encoding="utf-8") as f:
                pattern_data = json.load(f)
            for filename, props in pattern_data.items():
                if props is None or filename in ("\ufeff", ""):
                    continue
                png = filename.replace(".dds", ".png")
                path = get_pattern_source_dir() / png
                if path.exists():
                    files.append((filename, str(path)))

        # Emblems
        emblem_json = get_emblem_metadata_path()
        if emblem_json.exists():
            with open(emblem_json, "r", encoding="utf-8") as f:
                emblem_data = json.load(f)
            for filename, props in emblem_data.items():
                if props is None or filename == "\ufeff":
                    continue
                png = filename.replace(".dds", ".png")
                path = get_emblem_source_dir() / png
                if path.exists():
                    files.append((filename, str(path)))

        self.texture_atlases, self.texture_uv_map = TextureLoader.load_texture_atlas(files)
        logger.info("Loaded %d textures into %d atlas(es)", len(files), len(self.texture_atlases))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render_coa(self, coa: CoA, output_path: str):
        """Render a CoA to the RTT framebuffer and save as 256×256 PNG.

        Args:
            coa: Populated CoA model instance.
            output_path: Destination PNG file path.
        """
        # Make sure GL context is current
        self._gl_context.makeCurrent(self._surface)

        # Set as the active CoA so the rendering mixin can query it
        CoA.set_active(coa)

        # Sync render state from model
        self.base_texture = coa.pattern
        self.base_colors = [coa.pattern_color1, coa.pattern_color2, coa.pattern_color3]

        # --- Render to FBO ---
        self.framebuffer_rtt.bind()
        self.framebuffer_rtt.clear(0.0, 0.0, 0.0, 0.0)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        self._render_base_pattern()
        self._render_emblem_layers()

        gl.glFlush()

        # --- Read pixels ---
        width = FramebufferRTT.COA_RTT_WIDTH
        height = FramebufferRTT.COA_RTT_HEIGHT
        pixels = gl.glReadPixels(0, 0, width, height, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE)
        pixel_array = np.frombuffer(pixels, dtype=np.uint8).reshape(height, width, 4)

        # OpenGL reads bottom-up; flip vertically
        pixel_array = np.flipud(pixel_array)

        self.framebuffer_rtt.unbind(0)

        # --- Save PNG ---
        img = Image.fromarray(pixel_array, "RGBA")
        img = img.resize((self.OUTPUT_SIZE, self.OUTPUT_SIZE), Image.Resampling.LANCZOS)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        img.save(output_path, "PNG")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup(self):
        """Release all OpenGL resources."""
        self._gl_context.makeCurrent(self._surface)

        if self.framebuffer_rtt:
            self.framebuffer_rtt.cleanup()

        for tex_id in self.texture_atlases:
            gl.glDeleteTextures([tex_id])
        self.texture_atlases.clear()

        if self.default_mask_texture:
            gl.glDeleteTextures([self.default_mask_texture])
            self.default_mask_texture = None

        if self._ebo is not None:
            self._ebo.destroy()
        if self._vbo is not None:
            self._vbo.destroy()
        if self.vao is not None:
            self.vao.destroy()

        self.base_shader = None
        self.design_shader = None

        self._gl_context.doneCurrent()

    def __del__(self):
        try:
            self.cleanup()
        except Exception:
            pass
