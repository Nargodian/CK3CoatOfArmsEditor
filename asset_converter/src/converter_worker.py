"""
Conversion worker thread.

QThread-based worker that runs the full asset conversion pipeline:
emblems, patterns, frames, realm frames, title frames, frame transforms,
mask textures, emblem layouts, and metadata.
"""

import json
import re
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from PyQt5.QtCore import QThread, pyqtSignal

from PIL import Image

from .ck3_parser import parse_ck3_file
from .atlas_baking import create_emblem_atlas, create_pattern_atlas
from .dds_loading import load_dds_image
from .mod_support import ModAssetSource, build_asset_sources, find_asset_files, merge_metadata_simple


class ConversionWorker(QThread):
    """Worker thread for asset conversion to keep GUI responsive."""
    
    progress = pyqtSignal(str, int, int)  # message, current, total
    finished = pyqtSignal(bool, str)      # success, message
    
    def __init__(self, ck3_dir: Path, output_dir: Path, mod_dir: Optional[Path] = None):
        super().__init__()
        self.ck3_dir = Path(ck3_dir)
        self.output_dir = Path(output_dir)
        self.mod_dir = Path(mod_dir) if mod_dir else None
        self.error_log = []
        
        # Build list of asset sources (base game + mods)
        self.asset_sources = build_asset_sources(self.ck3_dir, self.mod_dir)
        
        # Per-source asset counts for content manifest
        self.source_counts = {source.name: {} for source in self.asset_sources}
        
        for src in self.asset_sources:
            print(f"DEBUG Source: {src.name}")
            print(f"  Path: {src.path}")
            print(f"  has_emblems={src.has_emblems}, has_patterns={src.has_patterns}, has_frames={src.has_frames}")
    
    def log_error(self, message: str):
        """Add error to log."""
        self.error_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def _write_content_manifest(self):
        """Write content_manifest.json summarizing what was converted."""
        try:
            manifest = {
                'converted': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'sources': []
            }
            for source in self.asset_sources:
                counts = self.source_counts.get(source.name, {})
                manifest['sources'].append({
                    'name': source.name,
                    'emblems': counts.get('emblems', 0),
                    'patterns': counts.get('patterns', 0),
                    'frames': counts.get('frames', 0),
                    'realm_frames': counts.get('realm_frames', 0),
                    'title_frames': counts.get('title_frames', 0),
                })
            manifest_path = self.output_dir / 'content_manifest.json'
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
        except Exception as e:
            self.log_error(f"Failed to write content manifest: {e}")
    
    def run(self):
        """Main conversion process."""
        try:
            self.progress.emit(f"Processing {len(self.asset_sources)} asset source(s)", 0, 0)
            for source in self.asset_sources:
                self.progress.emit(f"  - {source.name}", 0, 0)
            
            total_steps = 6
            current_step = 0
            
            # Step 1: Process emblems
            current_step += 1
            self.progress.emit("Processing emblems...", current_step, total_steps)
            if not self.process_emblems_from_sources():
                self.finished.emit(False, "Emblem processing failed")
                return
            
            # Step 2: Process patterns
            current_step += 1
            self.progress.emit("Processing patterns...", current_step, total_steps)
            if not self.process_patterns_from_sources():
                self.finished.emit(False, "Pattern processing failed")
                return
            
            # Step 3: Process frames
            current_step += 1
            self.progress.emit("Processing frames...", current_step, total_steps)
            if not self.process_frames_from_sources():
                self.finished.emit(False, "Frame processing failed")
                return
            
            # Step 3.5: Process realm frames (government-specific)
            if not self.process_realm_frames_from_sources():
                self.log_error("Realm frame processing failed (non-critical)")
            
            # Step 3.6: Process title frames (crown_strip, title_mask, title, topframe + variants)
            if not self.process_title_frames_from_sources():
                self.log_error("Title frame processing failed (non-critical)")
            
            # Step 4: Extract frame transforms
            current_step += 1
            self.progress.emit("Extracting frame transforms...", current_step, total_steps)
            if not self.extract_frame_transforms_from_sources():
                self.finished.emit(False, "Frame transform extraction failed")
                return
            
            # Step 4.5: Extract mask texture
            if not self.extract_mask_texture():
                self.log_error("Mask texture extraction failed (non-critical)")
            
            # Step 4.6: Extract emblem layouts
            if not self.extract_emblem_layouts():
                self.log_error("Emblem layout extraction failed (non-critical)")
            
            # Step 5: Convert metadata
            current_step += 1
            self.progress.emit("Converting metadata...", current_step, total_steps)
            if not self.convert_metadata_from_sources():
                self.finished.emit(False, "Metadata conversion failed")
                return
            
            # Write error log if any errors occurred
            if self.error_log:
                error_log_path = self.output_dir / "conversion_errors.txt"
                with open(error_log_path, 'w') as f:
                    f.write('\n'.join(self.error_log))
                message = f"Conversion complete with {len(self.error_log)} errors. See conversion_errors.txt"
            else:
                mod_count = len(self.asset_sources) - 1
                if mod_count > 0:
                    message = f"Conversion completed successfully! Processed base game + {mod_count} mod(s)"
                else:
                    message = "Conversion completed successfully!"
            
            # Write content manifest for editor's Help > Content Loaded
            self._write_content_manifest()
            
            self.finished.emit(True, message)
            
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")
    
    # ========================================================================
    # GENERIC DDS PROCESSOR
    # ========================================================================
    
    def _process_dds_assets(
        self,
        asset_type: str,
        has_flag: str,
        output_subdir: str,
        label: str,
        atlas_fn: Optional[Callable] = None,
        source_size: Optional[Tuple[int, int]] = (256, 256),
    ) -> bool:
        """Generic DDS-to-PNG processor for all asset types.
        
        Args:
            asset_type: Key for find_asset_files ('emblems', 'patterns', 'frames', etc.)
            has_flag: ModAssetSource attribute name to check ('has_emblems', etc.)
            output_subdir: Output directory relative to self.output_dir
            label: Human-readable label for progress messages
            atlas_fn: Optional callable(np.ndarray) -> Image to bake an atlas per file
            source_size: Resize source PNG to this size, or None to keep original
        """
        try:
            out_dir = self.output_dir / output_subdir
            out_dir.mkdir(parents=True, exist_ok=True)
            
            atlas_out = None
            if atlas_fn:
                parts = output_subdir.split('/')
                if len(parts) == 2:  # e.g. "coa_emblems/source"
                    atlas_out = self.output_dir / parts[0] / "atlases"
                    atlas_out.mkdir(parents=True, exist_ok=True)
            
            total_processed = 0
            total_errors = 0
            
            for source in self.asset_sources:
                if not getattr(source, has_flag, False):
                    continue
                
                self.progress.emit(f"Processing {label} from {source.name}...", 0, 0)
                dds_files = find_asset_files(source, asset_type)
                
                if not dds_files:
                    self.progress.emit(f"  No {label} found in {source.name}", 0, 0)
                    continue
                
                self.progress.emit(f"  Found {len(dds_files)} {label} DDS files in {source.name}", 0, 0)
                processed = 0
                errors = 0
                
                for i, dds_file in enumerate(dds_files):
                    if i % 50 == 0:
                        self.progress.emit(f"Processing {label} from {source.name}... {i}/{len(dds_files)}", i, len(dds_files))
                    
                    base_name = dds_file.stem
                    source_png = out_dir / f"{base_name}.png"
                    atlas_png = atlas_out / f"{base_name}_atlas.png" if atlas_out else None
                    
                    img_array = load_dds_image(dds_file)
                    if img_array is None:
                        self.log_error(f"Failed to load DDS from {source.name}: {dds_file.name}")
                        errors += 1
                        continue
                    
                    try:
                        img = Image.fromarray(img_array, mode='RGBA')
                        if source_size and img.size != source_size:
                            img = img.resize(source_size, Image.Resampling.LANCZOS)
                        img.save(source_png, 'PNG')
                        
                        if atlas_png and atlas_fn:
                            atlas = atlas_fn(img_array)
                            atlas.save(atlas_png, 'PNG')
                        
                        processed += 1
                    except Exception as e:
                        self.log_error(f"Error processing {dds_file.name} from {source.name}: {str(e)}")
                        errors += 1
                
                total_processed += processed
                total_errors += errors
                self.source_counts.setdefault(source.name, {})[asset_type] = processed
                self.progress.emit(f"{source.name}: {processed} {label} processed, {errors} errors", 0, 0)
            
            self.progress.emit(f"Total {label}: {total_processed} processed, {total_errors} errors", 0, 0)
            return True
            
        except Exception as e:
            self.log_error(f"{label} processing error: {str(e)}")
            return False
    
    # ========================================================================
    # ASSET TYPE PROCESSORS (delegate to generic)
    # ========================================================================
    
    def process_emblems_from_sources(self) -> bool:
        return self._process_dds_assets('emblems', 'has_emblems', 'coa_emblems/source', 'emblems', atlas_fn=create_emblem_atlas)
    
    def process_patterns_from_sources(self) -> bool:
        return self._process_dds_assets('patterns', 'has_patterns', 'coa_patterns/source', 'patterns', atlas_fn=create_pattern_atlas)
    
    def process_frames_from_sources(self) -> bool:
        return self._process_dds_assets('frames', 'has_frames', 'coa_frames', 'frames', source_size=None)
    
    def process_realm_frames_from_sources(self) -> bool:
        return self._process_dds_assets('realm_frames', 'has_realm_frames', 'realm_frames', 'realm frames', source_size=None)
    
    def process_title_frames_from_sources(self) -> bool:
        return self._process_dds_assets('title_frames', 'has_title_frames', 'title_frames', 'title frames', source_size=None)
    
    # ========================================================================
    # FRAME TRANSFORMS
    # ========================================================================
    
    def extract_frame_transforms_from_sources(self) -> bool:
        """Extract frame scales and offsets from culture files in all sources."""
        try:
            frame_scales = defaultdict(list)
            frame_offsets = defaultdict(list)
            culture_to_frame = {}
            
            for source in self.asset_sources:
                if not source.has_culture_files:
                    continue
                
                self.progress.emit(f"Extracting frame transforms from {source.name}...", 0, 0)
                
                if source.is_base_game:
                    culture_dir = source.path / "game" / "common" / "culture" / "cultures"
                else:
                    culture_dir = source.path / "common" / "culture" / "cultures"
                
                if not culture_dir.exists():
                    continue
                
                culture_files = list(culture_dir.glob("*.txt"))
                
                for i, filepath in enumerate(culture_files):
                    self.progress.emit(f"Parsing {filepath.name} from {source.name}...", i, len(culture_files))
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8-sig') as f:
                            lines = f.read().split('\n')
                    except Exception as e:
                        self.log_error(f"Error reading {filepath.name} from {source.name}: {e}")
                        continue
                    
                    current_culture = None
                    current_frame = None
                    
                    for line in lines:
                        culture_match = re.match(r'^(\w+)\s*=\s*\{', line)
                        if culture_match:
                            current_culture = culture_match.group(1)
                            current_frame = None
                            continue
                        
                        frame_match = re.search(r'house_coa_frame\s*=\s*(house_frame_\d+)', line)
                        if frame_match and current_culture:
                            current_frame = frame_match.group(1)
                        
                        scale_match = re.search(r'house_coa_mask_scale\s*=\s*\{\s*([\d.]+)\s+([\d.]+)\s*\}', line)
                        if scale_match and current_culture and current_frame:
                            scale_x = float(scale_match.group(1))
                            scale_y = float(scale_match.group(2))
                            
                            frame_scales[current_frame].append((scale_x, scale_y))
                            culture_to_frame[current_culture] = {
                                'frame': current_frame,
                                'scale': [scale_x, scale_y]
                            }
                        
                        offset_match = re.search(r'house_coa_mask_offset\s*=\s*\{\s*([\d.-]+)\s+([\d.-]+)\s*\}', line)
                        if offset_match and current_culture and current_frame:
                            offset_x = float(offset_match.group(1))
                            offset_y = float(offset_match.group(2))
                            
                            frame_offsets[current_frame].append((offset_x, offset_y))
                            if current_culture in culture_to_frame:
                                culture_to_frame[current_culture]['offset'] = [offset_x, offset_y]
            
            # Build final dict with recommended scale/offset per frame
            frame_scale_dict = {}
            frame_offset_dict = {}
            
            for frame_name, scales in frame_scales.items():
                unique_scales = sorted(set(scales))
                if len(unique_scales) == 1:
                    frame_scale_dict[frame_name] = list(unique_scales[0])
                else:
                    scale_counts = Counter(scales)
                    most_common_scale = scale_counts.most_common(1)[0][0]
                    frame_scale_dict[frame_name] = list(most_common_scale)
                    self.log_error(f"Frame {frame_name} has multiple scales, using most common: {most_common_scale}")
            
            for frame_name, offsets in frame_offsets.items():
                unique_offsets = sorted(set(offsets))
                if len(unique_offsets) == 1:
                    frame_offset_dict[frame_name] = list(unique_offsets[0])
                else:
                    offset_counts = Counter(offsets)
                    most_common_offset = offset_counts.most_common(1)[0][0]
                    frame_offset_dict[frame_name] = list(most_common_offset)
                    self.log_error(f"Frame {frame_name} has multiple offsets, using most common: {most_common_offset}")
            
            output_data = {
                'frame_scales': frame_scale_dict,
                'frame_offsets': frame_offset_dict,
                'description': 'Auto-generated from CK3 culture files (base game + mods)',
                'scale_values_used': sorted(list(set(tuple(v) for v in frame_scale_dict.values())))
            }
            
            output_path = self.output_dir / "frame_transforms.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2)
            
            self.progress.emit(f"Frame transforms: {len(frame_scale_dict)} frames extracted", 0, 0)
            return True
            
        except Exception as e:
            self.log_error(f"Frame transform extraction error: {str(e)}")
            return False
    
    # ========================================================================
    # MASK TEXTURE
    # ========================================================================
    
    def extract_mask_texture(self) -> bool:
        """Extract the CoA mask texture from game files."""
        try:
            mask_source = self.ck3_dir / "game" / "gfx" / "coat_of_arms" / "coa_mask_texture.dds"
            if not mask_source.exists():
                self.log_error(f"Mask texture not found: {mask_source}")
                return False
            
            mask_dest = self.output_dir / "coa_mask_texture.png"
            
            img_array = load_dds_image(mask_source)
            if img_array is None:
                self.log_error("Failed to load mask texture DDS")
                return False
            
            img = Image.fromarray(img_array, mode='RGBA')
            img.save(mask_dest, 'PNG')
            
            self.progress.emit("Mask texture extracted", 0, 0)
            return True
            
        except Exception as e:
            self.log_error(f"Mask texture extraction error: {str(e)}")
            return False
    
    # ========================================================================
    # EMBLEM LAYOUTS
    # ========================================================================
    
    def extract_emblem_layouts(self) -> bool:
        """Extract CK3 emblem layout templates from game files.
        
        Parses emblem_layouts/*.txt files and converts instance templates
        to flattened position arrays stored in JSON format.
        """
        try:
            layouts_dict = {}
            
            for source in self.asset_sources:
                if source.is_base_game:
                    layouts_dir = source.path / "game" / "gfx" / "coat_of_arms" / "emblem_layouts"
                else:
                    layouts_dir = source.path / "gfx" / "coat_of_arms" / "emblem_layouts"
                
                self.progress.emit(f"Checking {layouts_dir}...", 0, 0)
                self.progress.emit(f"  Directory exists: {layouts_dir.exists()}", 0, 0)
                self.progress.emit(f"  Directory is_dir: {layouts_dir.is_dir() if layouts_dir.exists() else 'N/A'}", 0, 0)
                
                if not layouts_dir.exists():
                    self.progress.emit(f"  Directory not found: {layouts_dir}", 0, 0)
                    continue
                
                self.progress.emit(f"Extracting emblem layouts from {source.name}...", 0, 0)
                
                layout_files = list(layouts_dir.glob("*.txt"))
                self.progress.emit(f"  Found {len(layout_files)} layout files", 0, 0)
                
                if layout_files:
                    for i, f in enumerate(layout_files[:3]):
                        self.progress.emit(f"    -> {f.name}", 0, 0)
                    if len(layout_files) > 3:
                        self.progress.emit(f"    -> ... and {len(layout_files) - 3} more", 0, 0)
                else:
                    try:
                        all_files = list(layouts_dir.iterdir())
                        self.progress.emit(f"  Directory contains {len(all_files)} items total", 0, 0)
                        for item in list(all_files)[:5]:
                            self.progress.emit(f"    -> {item.name} ({'dir' if item.is_dir() else 'file'})", 0, 0)
                    except Exception as e:
                        self.progress.emit(f"  Error listing directory: {e}", 0, 0)
                
                for layout_file in layout_files:
                    self.progress.emit(f"  Processing {layout_file.name}...", 0, 0)
                    try:
                        with open(layout_file, 'r', encoding='utf-8-sig') as f:
                            content = f.read()
                        
                        file_layouts = self.parse_emblem_layout_file(content)
                        
                        for layout_name, instances in file_layouts.items():
                            layouts_dict[layout_name] = instances
                            
                        self.progress.emit(f"  Loaded {len(file_layouts)} layouts from {layout_file.name}", 0, 0)
                        
                    except Exception as e:
                        self.log_error(f"Error parsing layout file {layout_file.name}: {e}")
            
            if not layouts_dict:
                self.log_error("No emblem layouts found")
                return False
            
            output_path = self.output_dir / "emblem_layouts.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(layouts_dict, f, indent=2)
            
            self.progress.emit(f"Emblem layouts: {len(layouts_dict)} layouts extracted", 0, 0)
            return True
            
        except Exception as e:
            self.log_error(f"Emblem layout extraction error: {str(e)}")
            return False
    
    def parse_emblem_layout_file(self, content: str) -> Dict[str, List[List[float]]]:
        """Parse emblem layout file and extract instance positions.
        
        Args:
            content: Raw file content
            
        Returns:
            Dict mapping layout_name -> list of [x, y, scale_x, scale_y, rotation]
        """
        layouts = {}
        
        layout_pattern = r'(\w*coa_designer_\w+)\s*=\s*\{(.*?)\n\}'
        
        for layout_match in re.finditer(layout_pattern, content, re.DOTALL):
            layout_name = layout_match.group(1)
            layout_block = layout_match.group(2)
            
            instance_pattern = r'instance\s*=\s*\{\s*position\s*=\s*\{\s*([-\d.]+)\s+([-\d.]+)\s*\}\s*scale\s*=\s*\{\s*([-\d.]+)\s+([-\d.]+)\s*\}(?:\s*rotation\s*=\s*([-\d.]+))?\s*\}'
            
            instances = []
            for inst_match in re.finditer(instance_pattern, layout_block):
                x = float(inst_match.group(1))
                y = float(inst_match.group(2))
                scale_x = float(inst_match.group(3))
                scale_y = float(inst_match.group(4))
                rotation = float(inst_match.group(5)) if inst_match.group(5) else 0.0
                
                instances.append([x, y, scale_x, scale_y, rotation])
            
            if instances:
                layouts[layout_name] = instances
        
        return layouts
    
    # ========================================================================
    # METADATA CONVERSION
    # ========================================================================
    
    def convert_metadata_from_sources(self) -> bool:
        """Convert CK3 .txt metadata files to JSON from all sources."""
        try:
            emblems_metadata = {}
            patterns_metadata = {}
            
            for source in self.asset_sources:
                if source.is_base_game:
                    metadata_dir = source.path / "game" / "gfx" / "coat_of_arms"
                else:
                    metadata_dir = source.path / "gfx" / "coat_of_arms"
                
                self.progress.emit(f"Converting metadata from {source.name}...", 0, 0)
                
                if source.has_emblem_metadata:
                    emblems_dir = metadata_dir / "colored_emblems"
                    if emblems_dir.exists():
                        emblem_txt_files = list(emblems_dir.glob("*.txt"))
                        for txt_file in emblem_txt_files:
                            self.progress.emit(f"Parsing {txt_file.name} from {source.name}...", 0, 0)
                            try:
                                data = parse_ck3_file(txt_file)
                                emblems_metadata = merge_metadata_simple(emblems_metadata, data, source.name)
                            except Exception as e:
                                self.log_error(f"Error parsing {txt_file.name} from {source.name}: {e}")
                
                if source.has_pattern_metadata:
                    patterns_dir = metadata_dir / "patterns"
                    if patterns_dir.exists():
                        pattern_txt_files = list(patterns_dir.glob("*.txt"))
                        for txt_file in pattern_txt_files:
                            self.progress.emit(f"Parsing {txt_file.name} from {source.name}...", 0, 0)
                            try:
                                data = parse_ck3_file(txt_file)
                                patterns_metadata = merge_metadata_simple(patterns_metadata, data, source.name)
                            except Exception as e:
                                self.log_error(f"Error parsing {txt_file.name} from {source.name}: {e}")
            
            if emblems_metadata:
                output_path = self.output_dir / "coa_emblems" / "metadata" / "50_coa_designer_emblems.json"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(emblems_metadata, f, indent=2)
                self.progress.emit(f"Emblems metadata: {len(emblems_metadata)} entries", 0, 0)
            
            if patterns_metadata:
                output_path = self.output_dir / "coa_patterns" / "metadata" / "50_coa_designer_patterns.json"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(patterns_metadata, f, indent=2)
                self.progress.emit(f"Patterns metadata: {len(patterns_metadata)} entries", 0, 0)
            
            return True
            
        except Exception as e:
            self.log_error(f"Metadata conversion error: {str(e)}")
            self.progress.emit(f"Metadata error: {str(e)}", 0, 0)
            return False
