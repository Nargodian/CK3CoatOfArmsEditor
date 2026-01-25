#!/usr/bin/env python3
"""
CK3 Coat of Arms Asset Converter

Unified GUI tool to extract and convert CK3 game assets for use with the Coat of Arms Editor.
Extracts DDS textures, converts to PNG, bakes emblem/pattern atlases, and converts metadata.
"""

import sys
import os
import json
import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any, Callable, Union
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QProgressBar,
    QTextEdit, QGroupBox, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

import numpy as np
from PIL import Image

try:
    import imageio
    import imageio.v3 as iio
    HAS_IMAGEIO = True
except ImportError:
    HAS_IMAGEIO = False


# ============================================================================
# CK3 PARSER (for metadata conversion)
# ============================================================================

class CK3Parser:
    """Parser for CK3 data format files."""
    
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.length = len(text)
    
    def skip_whitespace(self):
        """Skip whitespace and comments."""
        while self.pos < self.length:
            if self.text[self.pos] in ' \t\n\r':
                self.pos += 1
                continue
            if self.text[self.pos] == '#':
                while self.pos < self.length and self.text[self.pos] != '\n':
                    self.pos += 1
                continue
            break
    
    def peek(self) -> str:
        """Look at current character without advancing."""
        self.skip_whitespace()
        if self.pos < self.length:
            return self.text[self.pos]
        return ''
    
    def consume(self, char: str):
        """Consume expected character."""
        self.skip_whitespace()
        if self.pos < self.length and self.text[self.pos] == char:
            self.pos += 1
            return True
        return False
    
    def read_string(self) -> str:
        """Read a quoted string."""
        self.skip_whitespace()
        if self.pos >= self.length or self.text[self.pos] != '"':
            return None
        
        self.pos += 1
        start = self.pos
        
        while self.pos < self.length and self.text[self.pos] != '"':
            if self.text[self.pos] == '\\':
                self.pos += 2
            else:
                self.pos += 1
        
        result = self.text[start:self.pos]
        self.pos += 1
        return result
    
    def read_identifier(self) -> str:
        """Read an unquoted identifier or value."""
        self.skip_whitespace()
        start = self.pos
        
        while self.pos < self.length and self.text[self.pos] not in ' \t\n\r={}#':
            self.pos += 1
        
        return self.text[start:self.pos]
    
    def read_value(self) -> Any:
        """Read a value (string, number, bool, or identifier)."""
        self.skip_whitespace()
        
        if self.peek() == '"':
            return self.read_string()
        
        if self.peek() == '{':
            return self.read_block()
        
        value = self.read_identifier()
        
        if value.lower() in ('yes', 'true'):
            return True
        elif value.lower() in ('no', 'false'):
            return False
        
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        return value
    
    def read_array_or_block(self) -> Union[List, Dict]:
        """Read a block that could be an array or a dict."""
        self.consume('{')
        self.skip_whitespace()
        
        items = []
        has_keys = False
        
        while self.peek() != '}':
            start_pos = self.pos
            key = self.read_identifier()
            
            self.skip_whitespace()
            if self.peek() == '=':
                has_keys = True
                self.consume('=')
                value = self.read_value()
                items.append((key, value))
            else:
                self.pos = start_pos
                value = self.read_value()
                items.append(value)
        
        self.consume('}')
        
        if has_keys:
            result = {}
            for item in items:
                if isinstance(item, tuple):
                    key, value = item
                    if key in result:
                        if not isinstance(result[key], list):
                            result[key] = [result[key]]
                        result[key].append(value)
                    else:
                        result[key] = value
            return result
        else:
            return items
    
    def read_block(self) -> Union[List, Dict]:
        """Read a block (could be array or object)."""
        return self.read_array_or_block()
    
    def parse_file(self) -> Dict:
        """Parse entire file as a root-level block."""
        result = {}
        
        while self.pos < self.length:
            self.skip_whitespace()
            if self.pos >= self.length:
                break
            
            key = self.read_identifier()
            if not key:
                break
            
            self.skip_whitespace()
            
            if self.consume('='):
                value = self.read_value()
            else:
                value = None
            
            if key in result:
                if not isinstance(result[key], list):
                    result[key] = [result[key]]
                result[key].append(value)
            else:
                result[key] = value
        
        return result


def parse_ck3_file(file_path: Path) -> Dict:
    """Parse a CK3 format file to dictionary."""
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        text = f.read()
    parser = CK3Parser(text)
    return parser.parse_file()


# ============================================================================
# EMBLEM ATLAS BAKING
# ============================================================================

def extract_red_channel(img_array: np.ndarray) -> np.ndarray:
    """White image (1,1,1) with r*a as alpha"""
    if len(img_array.shape) == 3:
        red = img_array[:, :, 0].astype(np.float32)
        alpha = img_array[:, :, 3].astype(np.float32) if img_array.shape[2] == 4 else np.full(red.shape, 255.0, dtype=np.float32)
    else:
        red = img_array.astype(np.float32)
        alpha = np.full(red.shape, 255.0, dtype=np.float32)
    
    h, w = red.shape
    result = np.ones((h, w, 4), dtype=np.uint8) * 255
    result[:, :, 3] = np.clip((red / 255.0) * (alpha / 255.0) * 255.0, 0, 255).astype(np.uint8)
    return result


def extract_green_channel(img_array: np.ndarray) -> np.ndarray:
    """White image (1,1,1) with g*a as alpha"""
    if len(img_array.shape) == 3:
        green = img_array[:, :, 1].astype(np.float32)
        alpha = img_array[:, :, 3].astype(np.float32) if img_array.shape[2] == 4 else np.full(green.shape, 255.0, dtype=np.float32)
    else:
        green = img_array.astype(np.float32)
        alpha = np.full(green.shape, 255.0, dtype=np.float32)
    
    h, w = green.shape
    result = np.ones((h, w, 4), dtype=np.uint8) * 255
    result[:, :, 3] = np.clip((green / 255.0) * (alpha / 255.0) * 255.0, 0, 255).astype(np.uint8)
    return result


def extract_blue_channel(img_array: np.ndarray) -> np.ndarray:
    """Blue*2 for RGB ((b*2),(b*2),(b*2)), original alpha"""
    if len(img_array.shape) == 3:
        blue = img_array[:, :, 2].astype(np.float32)
        alpha = img_array[:, :, 3] if img_array.shape[2] == 4 else np.full(blue.shape, 255, dtype=np.uint8)
    else:
        blue = img_array.astype(np.float32)
        alpha = np.full(blue.shape, 255, dtype=np.uint8)
    
    h, w = blue.shape
    blue_scaled = np.clip(blue * 2.0, 0, 255).astype(np.uint8)
    result = np.zeros((h, w, 4), dtype=np.uint8)
    result[:, :, 0] = blue_scaled
    result[:, :, 1] = blue_scaled
    result[:, :, 2] = blue_scaled
    result[:, :, 3] = alpha
    return result


def extract_alpha_channel(img_array: np.ndarray) -> np.ndarray:
    """White image (1,1,1) with (1-a) as alpha"""
    if len(img_array.shape) == 3 and img_array.shape[2] == 4:
        alpha = img_array[:, :, 3]
    else:
        alpha = np.full((img_array.shape[0], img_array.shape[1]), 255, dtype=np.uint8)
    
    h, w = alpha.shape
    result = np.ones((h, w, 4), dtype=np.uint8) * 255
    result[:, :, 3] = 255 - alpha
    return result


QUADRANT_EXTRACTORS: Dict[str, Callable[[np.ndarray], np.ndarray]] = {
    'red': extract_red_channel,
    'green': extract_green_channel,
    'blue': extract_blue_channel,
    'alpha': extract_alpha_channel
}


def create_emblem_atlas(img_array: np.ndarray) -> Image.Image:
    """Create 512x512 emblem atlas with 4 quadrants."""
    atlas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
    
    # Resize source to 256x256 if needed
    h, w = img_array.shape[:2]
    if h != 256 or w != 256:
        img = Image.fromarray(img_array)
        img = img.resize((256, 256), Image.Resampling.LANCZOS)
        img_array = np.array(img)
    
    # Quadrant positions: red (0,0), green (256,0), blue (0,256), alpha (256,256)
    positions = {
        'red': (0, 0),
        'green': (256, 0),
        'blue': (0, 256),
        'alpha': (256, 256)
    }
    
    for channel, extractor in QUADRANT_EXTRACTORS.items():
        rgba_quadrant = extractor(img_array)
        quadrant_img = Image.fromarray(rgba_quadrant, mode='RGBA')
        atlas.paste(quadrant_img, positions[channel])
    
    return atlas


# ============================================================================
# PATTERN ATLAS BAKING
# ============================================================================

def extract_green_tile(img_array: np.ndarray) -> np.ndarray:
    """White image (1,1,1) with green channel as alpha"""
    if len(img_array.shape) == 3:
        green = img_array[:, :, 1].astype(np.float32)
    else:
        green = img_array.astype(np.float32)
    
    h, w = green.shape if len(green.shape) == 2 else (green.shape[0], green.shape[1])
    result = np.ones((h, w, 4), dtype=np.uint8) * 255
    result[:, :, 3] = green.astype(np.uint8)
    return result


def extract_blue_tile(img_array: np.ndarray) -> np.ndarray:
    """White image (1,1,1) with blue channel as alpha"""
    if len(img_array.shape) == 3:
        blue = img_array[:, :, 2].astype(np.float32)
    else:
        blue = img_array.astype(np.float32)
    
    h, w = blue.shape if len(blue.shape) == 2 else (blue.shape[0], blue.shape[1])
    result = np.ones((h, w, 4), dtype=np.uint8) * 255
    result[:, :, 3] = blue.astype(np.uint8)
    return result


def create_pattern_atlas(img_array: np.ndarray) -> Image.Image:
    """Create 512x256 pattern atlas with 2 tiles."""
    atlas = Image.new('RGBA', (512, 256), (0, 0, 0, 0))
    
    # Resize source to 256x256 if needed
    h, w = img_array.shape[:2]
    if h != 256 or w != 256:
        img = Image.fromarray(img_array)
        img = img.resize((256, 256), Image.Resampling.LANCZOS)
        img_array = np.array(img)
    
    # Tile positions: green (0,0), blue (256,0)
    green_tile = Image.fromarray(extract_green_tile(img_array), mode='RGBA')
    blue_tile = Image.fromarray(extract_blue_tile(img_array), mode='RGBA')
    
    atlas.paste(green_tile, (0, 0))
    atlas.paste(blue_tile, (256, 0))
    
    return atlas


# ============================================================================
# DDS LOADING
# ============================================================================

def load_dds_image(dds_path: Path) -> Optional[np.ndarray]:
    """Load DDS file and convert to RGBA numpy array."""
    if not HAS_IMAGEIO:
        raise ImportError("imageio and imageio-dds are required for DDS loading")
    
    try:
        # Load DDS using imageio
        img_data = iio.imread(dds_path)
        
        # Convert to RGBA if needed
        if len(img_data.shape) == 2:
            # Grayscale
            h, w = img_data.shape
            rgba = np.zeros((h, w, 4), dtype=np.uint8)
            rgba[:, :, 0] = img_data
            rgba[:, :, 1] = img_data
            rgba[:, :, 2] = img_data
            rgba[:, :, 3] = 255
            return rgba
        elif img_data.shape[2] == 3:
            # RGB
            h, w = img_data.shape[:2]
            rgba = np.zeros((h, w, 4), dtype=np.uint8)
            rgba[:, :, :3] = img_data
            rgba[:, :, 3] = 255
            return rgba
        elif img_data.shape[2] == 4:
            # Already RGBA
            return img_data
        else:
            return None
            
    except Exception as e:
        return None


# ============================================================================
# CONVERSION WORKER THREAD
# ============================================================================

class ConversionWorker(QThread):
    """Worker thread for asset conversion to keep GUI responsive."""
    
    progress = pyqtSignal(str, int, int)  # message, current, total
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, ck3_dir: Path, output_dir: Path):
        super().__init__()
        self.ck3_dir = Path(ck3_dir)
        self.output_dir = Path(output_dir)
        self.error_log = []
    
    def log_error(self, message: str):
        """Add error to log."""
        self.error_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def should_process(self, source_path: Path, dest_path: Path) -> bool:
        """Check if file needs processing based on timestamps."""
        if not dest_path.exists():
            return True
        
        source_time = source_path.stat().st_mtime
        dest_time = dest_path.stat().st_mtime
        return source_time > dest_time
    
    def run(self):
        """Main conversion process."""
        try:
            total_steps = 4
            current_step = 0
            
            # Step 1: Process emblems
            current_step += 1
            self.progress.emit("Processing emblems...", current_step, total_steps)
            if not self.process_emblems():
                self.finished.emit(False, "Emblem processing failed")
                return
            
            # Step 2: Process patterns
            current_step += 1
            self.progress.emit("Processing patterns...", current_step, total_steps)
            if not self.process_patterns():
                self.finished.emit(False, "Pattern processing failed")
                return
            
            # Step 3: Process frames
            current_step += 1
            self.progress.emit("Processing frames...", current_step, total_steps)
            if not self.process_frames():
                self.finished.emit(False, "Frame processing failed")
                return
            
            # Step 4: Convert metadata
            current_step += 1
            self.progress.emit("Converting metadata...", current_step, total_steps)
            if not self.convert_metadata():
                self.finished.emit(False, "Metadata conversion failed")
                return
            
            # Write error log if any errors occurred
            if self.error_log:
                error_log_path = self.output_dir / "conversion_errors.txt"
                with open(error_log_path, 'w') as f:
                    f.write('\n'.join(self.error_log))
                message = f"Conversion complete with {len(self.error_log)} errors. See conversion_errors.txt"
            else:
                message = "Conversion completed successfully!"
            
            self.finished.emit(True, message)
            
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")
    
    def process_emblems(self) -> bool:
        """Process emblem DDS files to source PNGs and atlases."""
        try:
            emblem_source_dir = self.ck3_dir / "game" / "gfx" / "coat_of_arms" / "colored_emblems"
            if not emblem_source_dir.exists():
                self.log_error(f"Emblem source directory not found: {emblem_source_dir}")
                return False
            
            # Create output directories
            source_out = self.output_dir / "coa_emblems" / "source"
            atlas_out = self.output_dir / "coa_emblems" / "atlases"
            source_out.mkdir(parents=True, exist_ok=True)
            atlas_out.mkdir(parents=True, exist_ok=True)
            
            # Find all emblem DDS files
            dds_files = list(emblem_source_dir.glob("ce_*.dds"))
            
            processed = 0
            skipped = 0
            errors = 0
            
            for i, dds_file in enumerate(dds_files):
                # Update progress every 50 files
                if i % 50 == 0:
                    self.progress.emit(f"Processing emblems... {i}/{len(dds_files)}", i, len(dds_files))
                
                base_name = dds_file.stem
                source_png = source_out / f"{base_name}.png"
                atlas_png = atlas_out / f"{base_name}_atlas.png"
                
                # Check if processing needed
                needs_source = self.should_process(dds_file, source_png)
                needs_atlas = self.should_process(dds_file, atlas_png)
                
                if not needs_source and not needs_atlas:
                    skipped += 1
                    continue
                
                # Load DDS
                img_array = load_dds_image(dds_file)
                if img_array is None:
                    self.log_error(f"Failed to load DDS: {dds_file.name}")
                    errors += 1
                    continue
                
                try:
                    # Save flat PNG for thumbnails
                    if needs_source:
                        img = Image.fromarray(img_array, mode='RGBA')
                        if img.size != (256, 256):
                            img = img.resize((256, 256), Image.Resampling.LANCZOS)
                        img.save(source_png, 'PNG')
                    
                    # Create and save atlas
                    if needs_atlas:
                        atlas = create_emblem_atlas(img_array)
                        atlas.save(atlas_png, 'PNG')
                    
                    processed += 1
                    
                except Exception as e:
                    self.log_error(f"Error processing {dds_file.name}: {str(e)}")
                    errors += 1
            
            self.progress.emit(f"Emblems: {processed} processed, {skipped} skipped, {errors} errors", len(dds_files), len(dds_files))
            return True
            
        except Exception as e:
            self.log_error(f"Emblem processing error: {str(e)}")
            return False
    
    def process_patterns(self) -> bool:
        """Process pattern DDS files to source PNGs and atlases."""
        try:
            pattern_source_dir = self.ck3_dir / "game" / "gfx" / "coat_of_arms" / "patterns"
            if not pattern_source_dir.exists():
                self.log_error(f"Pattern source directory not found: {pattern_source_dir}")
                return False
            
            # Create output directories
            source_out = self.output_dir / "coa_patterns" / "source"
            atlas_out = self.output_dir / "coa_patterns" / "atlases"
            source_out.mkdir(parents=True, exist_ok=True)
            atlas_out.mkdir(parents=True, exist_ok=True)
            
            # Find all pattern DDS files
            dds_files = list(pattern_source_dir.glob("pattern_*.dds"))
            
            processed = 0
            skipped = 0
            errors = 0
            
            for i, dds_file in enumerate(dds_files):
                self.progress.emit(f"Processing patterns... {i}/{len(dds_files)}", i, len(dds_files))
                
                base_name = dds_file.stem
                source_png = source_out / f"{base_name}.png"
                atlas_png = atlas_out / f"{base_name}_atlas.png"
                
                needs_source = self.should_process(dds_file, source_png)
                needs_atlas = self.should_process(dds_file, atlas_png)
                
                if not needs_source and not needs_atlas:
                    skipped += 1
                    continue
                
                img_array = load_dds_image(dds_file)
                if img_array is None:
                    self.log_error(f"Failed to load DDS: {dds_file.name}")
                    errors += 1
                    continue
                
                try:
                    if needs_source:
                        img = Image.fromarray(img_array, mode='RGBA')
                        if img.size != (256, 256):
                            img = img.resize((256, 256), Image.Resampling.LANCZOS)
                        img.save(source_png, 'PNG')
                    
                    if needs_atlas:
                        atlas = create_pattern_atlas(img_array)
                        atlas.save(atlas_png, 'PNG')
                    
                    processed += 1
                    
                except Exception as e:
                    self.log_error(f"Error processing {dds_file.name}: {str(e)}")
                    errors += 1
            
            self.progress.emit(f"Patterns: {processed} processed, {skipped} skipped, {errors} errors", len(dds_files), len(dds_files))
            return True
            
        except Exception as e:
            self.log_error(f"Pattern processing error: {str(e)}")
            return False
    
    def process_frames(self) -> bool:
        """Process frame DDS files to PNGs."""
        try:
            frame_source_dir = self.ck3_dir / "game" / "gfx" / "interface" / "coat_of_arms" / "frames"
            if not frame_source_dir.exists():
                self.log_error(f"Frame source directory not found: {frame_source_dir}")
                return False
            
            # Create output directory
            frame_out = self.output_dir / "coa_frames"
            frame_out.mkdir(parents=True, exist_ok=True)
            
            # Find all frame DDS files
            dds_files = list(frame_source_dir.glob("*.dds"))
            
            processed = 0
            skipped = 0
            errors = 0
            
            for i, dds_file in enumerate(dds_files):
                self.progress.emit(f"Processing frames... {i}/{len(dds_files)}", i, len(dds_files))
                
                png_file = frame_out / f"{dds_file.stem}.png"
                
                if not self.should_process(dds_file, png_file):
                    skipped += 1
                    continue
                
                img_array = load_dds_image(dds_file)
                if img_array is None:
                    self.log_error(f"Failed to load DDS: {dds_file.name}")
                    errors += 1
                    continue
                
                try:
                    img = Image.fromarray(img_array, mode='RGBA')
                    img.save(png_file, 'PNG')
                    processed += 1
                except Exception as e:
                    self.log_error(f"Error processing {dds_file.name}: {str(e)}")
                    errors += 1
            
            self.progress.emit(f"Frames: {processed} processed, {skipped} skipped, {errors} errors", len(dds_files), len(dds_files))
            return True
            
        except Exception as e:
            self.log_error(f"Frame processing error: {str(e)}")
            return False
    
    def convert_metadata(self) -> bool:
        """Convert CK3 .txt metadata files to JSON."""
        try:
            metadata_dir = self.ck3_dir / "game" / "common" / "coat_of_arms"
            
            # Convert emblems metadata
            emblems_txt = metadata_dir / "colored_emblems" / "50_coa_designer_emblems.txt"
            if emblems_txt.exists():
                data = parse_ck3_file(emblems_txt)
                output_path = self.output_dir / "coa_emblems" / "metadata" / "50_coa_designer_emblems.json"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
            
            # Convert patterns metadata
            patterns_txt = metadata_dir / "patterns" / "50_coa_designer_patterns.txt"
            if patterns_txt.exists():
                data = parse_ck3_file(patterns_txt)
                output_path = self.output_dir / "coa_patterns" / "metadata" / "50_coa_designer_patterns.json"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
            
            # Convert color palettes
            palettes_txt = metadata_dir / "color_palettes" / "50_coa_designer_palettes.txt"
            if palettes_txt.exists():
                data = parse_ck3_file(palettes_txt)
                output_path = self.output_dir / "coa_emblems" / "metadata" / "50_coa_designer_palettes.json"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
            
            # Convert emblem layouts
            layouts_txt = metadata_dir / "emblem_layouts" / "50_coa_designer_emblem_layouts.txt"
            if layouts_txt.exists():
                data = parse_ck3_file(layouts_txt)
                output_path = self.output_dir / "coa_emblems" / "metadata" / "50_coa_designer_emblem_layouts.json"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
            
            return True
            
        except Exception as e:
            self.log_error(f"Metadata conversion error: {str(e)}")
            return False


# ============================================================================
# MAIN GUI
# ============================================================================

class AssetConverterGUI(QMainWindow):
    """Main GUI window for asset converter."""
    
    def __init__(self):
        super().__init__()
        self.worker = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("CK3 Coat of Arms Asset Converter")
        self.setMinimumSize(700, 500)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("CK3 Coat of Arms Asset Converter")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # CK3 Directory selection
        ck3_group = QGroupBox("CK3 Installation Directory")
        ck3_layout = QHBoxLayout()
        self.ck3_path_edit = QLineEdit()
        self.ck3_path_edit.setPlaceholderText("Select CK3 installation directory...")
        self.ck3_browse_btn = QPushButton("Browse...")
        self.ck3_browse_btn.clicked.connect(self.browse_ck3_dir)
        ck3_layout.addWidget(self.ck3_path_edit)
        ck3_layout.addWidget(self.ck3_browse_btn)
        ck3_group.setLayout(ck3_layout)
        layout.addWidget(ck3_group)
        
        # Output Directory selection
        output_group = QGroupBox("Output Directory")
        output_layout = QHBoxLayout()
        self.output_path_edit = QLineEdit()
        
        # Default to ck3_assets in current directory
        if getattr(sys, 'frozen', False):
            default_output = Path(sys.executable).parent / "ck3_assets"
        else:
            default_output = Path(__file__).parent / "ck3_assets"
        self.output_path_edit.setText(str(default_output))
        
        self.output_browse_btn = QPushButton("Browse...")
        self.output_browse_btn.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(self.output_path_edit)
        output_layout.addWidget(self.output_browse_btn)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        self.progress_label = QLabel("Ready to convert assets")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Log output
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.convert_btn = QPushButton("Start Conversion")
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setMinimumHeight(40)
        button_layout.addWidget(self.convert_btn)
        layout.addLayout(button_layout)
        
        # Check for imageio
        if not HAS_IMAGEIO:
            self.log("WARNING: imageio and imageio-dds are required. Install with: pip install imageio imageio-dds")
            self.convert_btn.setEnabled(False)
    
    def browse_ck3_dir(self):
        """Open directory browser for CK3 installation."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select CK3 Installation Directory",
            "", QFileDialog.ShowDirsOnly
        )
        if dir_path:
            self.ck3_path_edit.setText(dir_path)
    
    def browse_output_dir(self):
        """Open directory browser for output location."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Output Directory",
            "", QFileDialog.ShowDirsOnly
        )
        if dir_path:
            self.output_path_edit.setText(dir_path)
    
    def log(self, message: str):
        """Add message to log."""
        self.log_text.append(message)
    
    def validate_paths(self) -> bool:
        """Validate CK3 directory structure."""
        ck3_dir = Path(self.ck3_path_edit.text())
        
        if not ck3_dir.exists():
            QMessageBox.critical(self, "Error", "CK3 directory does not exist")
            return False
        
        # Check for required subdirectories
        required_paths = [
            ck3_dir / "game" / "gfx" / "coat_of_arms" / "colored_emblems",
            ck3_dir / "game" / "gfx" / "coat_of_arms" / "patterns",
            ck3_dir / "game" / "gfx" / "interface" / "coat_of_arms" / "frames",
            ck3_dir / "game" / "common" / "coat_of_arms"
        ]
        
        missing = [str(p) for p in required_paths if not p.exists()]
        
        if missing:
            QMessageBox.critical(
                self, "Invalid CK3 Directory",
                "The selected directory does not appear to be a valid CK3 installation.\n\n"
                f"Missing paths:\n" + "\n".join(missing)
            )
            return False
        
        return True
    
    def start_conversion(self):
        """Start the conversion process."""
        if not self.validate_paths():
            return
        
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Busy", "Conversion already in progress")
            return
        
        ck3_dir = Path(self.ck3_path_edit.text())
        output_dir = Path(self.output_path_edit.text())
        
        # Disable UI during conversion
        self.convert_btn.setEnabled(False)
        self.ck3_browse_btn.setEnabled(False)
        self.output_browse_btn.setEnabled(False)
        
        self.log_text.clear()
        self.log(f"Starting conversion from: {ck3_dir}")
        self.log(f"Output to: {output_dir}")
        
        # Create and start worker thread
        self.worker = ConversionWorker(ck3_dir, output_dir)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
    
    def on_progress(self, message: str, current: int, total: int):
        """Handle progress updates."""
        self.progress_label.setText(message)
        if total > 0:
            self.progress_bar.setValue(int((current / total) * 100))
        self.log(message)
    
    def on_finished(self, success: bool, message: str):
        """Handle conversion completion."""
        self.log(message)
        
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)
        
        # Re-enable UI
        self.convert_btn.setEnabled(True)
        self.ck3_browse_btn.setEnabled(True)
        self.output_browse_btn.setEnabled(True)
        self.progress_bar.setValue(0 if not success else 100)


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    window = AssetConverterGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
