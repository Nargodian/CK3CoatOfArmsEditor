"""Mixin for loading textures in the CoA canvas.

Handles loading of:
- Texture atlases (emblems, patterns)
- Frame textures and masks
- Material/noise masks
- Preview frame textures (realm, title)
"""

import OpenGL.GL as gl
import json
from pathlib import Path
import os

from services.texture_loader import TextureLoader
from utils.path_resolver import (
    get_pattern_metadata_path, get_emblem_metadata_path,
    get_pattern_source_dir, get_emblem_source_dir, 
    get_frames_dir, get_assets_dir, get_resource_path
)


class CanvasTextureLoaderMixin:
    """Mixin providing texture loading functionality for canvas."""
    
    def _load_texture_atlases(self):
        """Load emblem and pattern texture atlases."""
        try:
            files = []
            
            # Load patterns
            pattern_json_path = get_pattern_metadata_path()
            if pattern_json_path.exists():
                with open(pattern_json_path, 'r', encoding='utf-8') as f:
                    pattern_data = json.load(f)
                
                for filename, props in pattern_data.items():
                    if props is None or filename in ("\ufeff", ""):
                        continue
                    png_filename = filename.replace('.dds', '.png')
                    image_path = get_pattern_source_dir() / png_filename
                    if image_path.exists():
                        files.append((filename, str(image_path)))
            
            # Load emblems
            emblem_json_path = get_emblem_metadata_path()
            if emblem_json_path.exists():
                with open(emblem_json_path, 'r', encoding='utf-8') as f:
                    emblem_data = json.load(f)
                
                for filename, props in emblem_data.items():
                    if props is None or filename == "\ufeff":
                        continue
                    png_filename = filename.replace('.dds', '.png')
                    image_path = get_emblem_source_dir() / png_filename
                    if image_path.exists():
                        files.append((filename, str(image_path)))
            
            # Build atlas using TextureLoader
            self.texture_atlases, self.texture_uv_map = TextureLoader.load_texture_atlas(files)
            
        except Exception as e:
            print(f"Error loading texture atlases: {e}")
            import traceback
            traceback.print_exc()
    
    def _load_frame_textures(self):
        """Load frame textures and masks."""
        try:
            frame_dir = get_frames_dir()
            if not frame_dir.exists():
                return
            
            # Frame files to load
            frame_files = {"dynasty": "dynasty.png", "house": "house.png",
                           "house_china": "house_china.png", "house_japan": "house_japan.png"}
            for i in range(2, 31):
                frame_files[f"house_frame_{i:02d}"] = f"house_frame_{i:02d}.png"
            
            for name, filename in frame_files.items():
                path = frame_dir / filename
                if not path.exists():
                    continue
                
                # Load frame texture
                texture_id = TextureLoader.load_texture(path)
                if texture_id:
                    self.frameTextures[name] = texture_id
                
                # Load mask
                mask_path = frame_dir / filename.replace('.png', '_mask.png')
                if mask_path.exists():
                    mask_id = TextureLoader.load_texture(
                        mask_path, 
                        wrap_mode=gl.GL_CLAMP_TO_BORDER,
                        resize=(800, 800)
                    )
                    if mask_id:
                        self.frame_masks[name] = mask_id
                        
                        # Set frame scale/offset from official data
                        if name in self.official_frame_scales:
                            scale_data = self.official_frame_scales[name]
                            self.frame_scales[name] = (scale_data[0]/1.05, scale_data[1]/1.05)
                            offset_data = self.official_frame_offsets.get(name, [0.0, 0.0])
                            self.frame_offsets[name] = (offset_data[0], offset_data[1])
                        else:
                            self.frame_scales[name] = (1.0, 1.0)
                            self.frame_offsets[name] = (0.0, 0.0)
        
        except Exception as e:
            print(f"Error loading frame textures: {e}")
    
    def _load_official_frame_transforms(self):
        """Load official frame scales and offsets from JSON."""
        try:
            transform_path = get_assets_dir() / "frame_transforms.json"
            if transform_path.exists():
                with open(transform_path, 'r') as f:
                    data = json.load(f)
                    self.official_frame_scales = data.get('frame_scales', {})
                    self.official_frame_offsets = data.get('frame_offsets', {})
        except Exception as e:
            print(f"Error loading frame transforms: {e}")
    
    def _load_default_mask_texture(self):
        """Create default white mask texture."""
        self.default_mask_texture = TextureLoader.create_solid_texture(
            (255, 255, 255, 255), size=128
        )
    
    def _load_material_mask_texture(self):
        """Load CK3 material mask texture."""
        try:
            material_path = get_assets_dir() / 'coa_mask_texture.png'
            if material_path.exists():
                self.texturedMask = TextureLoader.load_texture(
                    material_path,
                    wrap_mode=gl.GL_REPEAT,
                    min_filter=gl.GL_LINEAR_MIPMAP_LINEAR,
                    generate_mipmaps=True,
                    resize=(128, 128)
                )
            else:
                self.texturedMask = TextureLoader.create_solid_texture((255, 255, 255, 255))
        except Exception as e:
            print(f"Error loading material mask: {e}")
            self.texturedMask = TextureLoader.create_solid_texture((255, 255, 255, 255))
    
    def _load_noise_texture(self):
        """Load noise texture for grain effect."""
        try:
            noise_path = get_resource_path('assets', 'noise.png')
            if os.path.exists(noise_path):
                self.noiseMask = TextureLoader.load_texture(noise_path, wrap_mode=gl.GL_REPEAT)
            else:
                self.noiseMask = TextureLoader.create_solid_texture((255, 255, 255, 255), size=64)
        except Exception as e:
            print(f"Error loading noise texture: {e}")
            self.noiseMask = TextureLoader.create_solid_texture((255, 255, 255, 255), size=64)
    
    def _load_realm_frame_textures(self):
        """Load government-specific realm frame textures."""
        try:
            realm_frames_dir = get_assets_dir() / 'realm_frames'
            if not realm_frames_dir.exists():
                return
            
            # Load masks
            for mask_file in Path(realm_frames_dir).glob("*_mask.png"):
                gov_name = mask_file.stem.replace("_mask", "")
                texture_id = TextureLoader.load_texture(mask_file)
                if texture_id:
                    self.realm_frame_masks[gov_name] = texture_id
            
            # Load frames and shadows
            for frame_file in Path(realm_frames_dir).glob("*_frame.png"):
                stem = frame_file.stem.replace("_frame", "")
                parts = stem.rsplit("_", 1)
                if len(parts) == 2:
                    gov_name, size_str = parts
                    try:
                        size = int(size_str)
                        texture_id = TextureLoader.load_texture(frame_file)
                        if texture_id:
                            self.realm_frame_frames[(gov_name, size)] = texture_id
                    except ValueError:
                        pass
            
            for shadow_file in Path(realm_frames_dir).glob("*_shadow.png"):
                stem = shadow_file.stem.replace("_shadow", "")
                parts = stem.rsplit("_", 1)
                if len(parts) == 2:
                    gov_name, size_str = parts
                    try:
                        size = int(size_str)
                        texture_id = TextureLoader.load_texture(shadow_file)
                        if texture_id:
                            self.realm_frame_shadows[(gov_name, size)] = texture_id
                    except ValueError:
                        pass
            
            print(f"Loaded {len(self.realm_frame_masks)} government masks")
        except Exception as e:
            print(f"Error loading realm frames: {e}")
    
    def _load_title_frame_textures(self):
        """Load title frame assets."""
        try:
            title_frames_dir = get_assets_dir() / 'title_frames'
            if not title_frames_dir.exists():
                return
            
            # Load title mask
            title_mask_path = Path(title_frames_dir) / "title_mask.png"
            if title_mask_path.exists():
                self.title_mask = TextureLoader.load_texture(title_mask_path)
            
            # Load crown strips, title frames, topframes
            sizes = [28, 44, 62, 86, 115]
            self.crown_strips = TextureLoader.load_sized_textures(title_frames_dir, "crown_strip", sizes)
            self.title_frames = TextureLoader.load_sized_textures(title_frames_dir, "title", sizes)
            self.topframes = TextureLoader.load_sized_textures(title_frames_dir, "topframe", sizes)
            
            # Single-image topframe variants (not 7x1 atlas strips)
            self.adventurer_topframes = TextureLoader.load_sized_textures(title_frames_dir, "landless_adventurer_topframe", sizes)
            self.holyorder_topframes = TextureLoader.load_sized_textures(title_frames_dir, "holyorder_topframe", sizes)
            self.mercenary_topframes = TextureLoader.load_sized_textures(title_frames_dir, "mercenary_topframe", sizes)
            
            print(f"Loaded title textures")
        except Exception as e:
            print(f"Error loading title frames: {e}")
