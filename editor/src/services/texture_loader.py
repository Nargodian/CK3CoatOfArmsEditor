"""Texture loading utilities for OpenGL.

Provides methods to load individual textures and texture atlases from files.
All methods return OpenGL texture IDs and associated metadata.
"""

import OpenGL.GL as gl
import numpy as np
from PIL import Image
from pathlib import Path
import json


class TextureLoader:
    """Utility for loading OpenGL textures from files."""
    
    @staticmethod
    def load_texture(image_path, wrap_mode=gl.GL_CLAMP_TO_EDGE, min_filter=gl.GL_LINEAR, mag_filter=gl.GL_LINEAR, generate_mipmaps=False, resize=None):
        """Load a single texture from file.
        
        Args:
            image_path: Path to image file
            wrap_mode: OpenGL wrap mode (GL_CLAMP_TO_EDGE, GL_REPEAT, etc.)
            min_filter: Minification filter (GL_LINEAR, GL_NEAREST, etc.)
            mag_filter: Magnification filter
            generate_mipmaps: Whether to generate mipmaps
            resize: Optional (width, height) to resize texture
            
        Returns:
            int: OpenGL texture ID, or None if loading failed
        """
        try:
            img = Image.open(image_path).convert('RGBA')
            
            if resize:
                img = img.resize(resize, Image.Resampling.LANCZOS)
            
            img_data = np.array(img)
            
            texture_id = gl.glGenTextures(1)
            gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
            
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, wrap_mode)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, wrap_mode)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, min_filter)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, mag_filter)
            
            if wrap_mode == gl.GL_CLAMP_TO_BORDER:
                gl.glTexParameterfv(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_BORDER_COLOR, [0.0, 0.0, 0.0, 0.0])
            
            gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, img.width, img.height,
                           0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, img_data.tobytes())
            
            if generate_mipmaps:
                gl.glGenerateMipmap(gl.GL_TEXTURE_2D)
            
            return texture_id
            
        except Exception as e:
            print(f"Error loading texture from {image_path}: {e}")
            return None
    
    @staticmethod
    def create_solid_texture(color_rgba, size=64):
        """Create a solid color texture.
        
        Args:
            color_rgba: Tuple (r, g, b, a) with values 0-255
            size: Texture size in pixels (default 64)
            
        Returns:
            int: OpenGL texture ID
        """
        texture_data = np.full((size, size, 4), color_rgba, dtype=np.uint8)
        
        texture_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
        
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, size, size,
                       0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, texture_data.tobytes())
        
        return texture_id
    
    @staticmethod
    def load_texture_atlas(files, tile_size=256, atlas_size=8192):
        """Build texture atlas from multiple image files.
        
        Args:
            files: List of (key, filepath) tuples
            tile_size: Size of each tile in pixels (default 256)
            atlas_size: Total atlas size in pixels (default 8192)
            
        Returns:
            tuple: (atlas_textures, uv_map) where:
                - atlas_textures: List of OpenGL texture IDs
                - uv_map: Dict mapping keys to (atlas_idx, u0, v0, u1, v1)
        """
        tiles_per_row = atlas_size // tile_size
        tiles_per_atlas = tiles_per_row * tiles_per_row
        num_atlases = (len(files) + tiles_per_atlas - 1) // tiles_per_atlas
        
        atlas_textures = []
        uv_map = {}
        
        for atlas_idx in range(num_atlases):
            # Create atlas texture
            atlas_data = np.zeros((atlas_size, atlas_size, 4), dtype=np.uint8)
            
            start_idx = atlas_idx * tiles_per_atlas
            end_idx = min((atlas_idx + 1) * tiles_per_atlas, len(files))
            
            # Pack textures into atlas
            for i in range(start_idx, end_idx):
                key, image_path = files[i]
                local_idx = i - start_idx
                
                # Calculate position in atlas
                row = local_idx // tiles_per_row
                col = local_idx % tiles_per_row
                x = col * tile_size
                y = row * tile_size
                
                # Load and resize image
                img = Image.open(image_path).convert('RGBA')
                img = img.resize((tile_size, tile_size), Image.Resampling.LANCZOS)
                img_array = np.array(img)
                
                # Place in atlas
                atlas_data[y:y+tile_size, x:x+tile_size, :] = img_array
                
                # Calculate UV coordinates
                u0 = x / atlas_size
                v0 = y / atlas_size
                u1 = (x + tile_size) / atlas_size
                v1 = (y + tile_size) / atlas_size
                
                uv_map[key] = (atlas_idx, u0, v0, u1, v1)
            
            # Create OpenGL texture
            texture_id = gl.glGenTextures(1)
            gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
            
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            
            gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, atlas_size, atlas_size,
                           0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, atlas_data.tobytes())
            
            atlas_textures.append(texture_id)
        
        return atlas_textures, uv_map
    
    @staticmethod
    def load_texture_strip(directory, file_pattern, wrap_mode=gl.GL_CLAMP_TO_EDGE):
        """Load multiple related textures from a directory.
        
        Args:
            directory: Path to directory
            file_pattern: Glob pattern (e.g., "frame_*.png")
            wrap_mode: OpenGL wrap mode
            
        Returns:
            dict: Mapping from stem to texture ID
        """
        textures = {}
        
        for file_path in Path(directory).glob(file_pattern):
            stem = file_path.stem
            texture_id = TextureLoader.load_texture(file_path, wrap_mode=wrap_mode)
            if texture_id:
                textures[stem] = texture_id
        
        return textures
    
    @staticmethod
    def load_sized_textures(directory, base_name, sizes):
        """Load textures at multiple sizes (e.g., crown_strip_28.png, crown_strip_44.png).
        
        Args:
            directory: Path to directory
            base_name: Base filename (e.g., "crown_strip")
            sizes: List of sizes (e.g., [28, 44, 62, 86, 115])
            
        Returns:
            dict: Mapping from size to texture ID
        """
        textures = {}
        
        for size in sizes:
            filename = f"{base_name}_{size}.png"
            file_path = Path(directory) / filename
            if file_path.exists():
                texture_id = TextureLoader.load_texture(file_path)
                if texture_id:
                    textures[size] = texture_id
        
        return textures
