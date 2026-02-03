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
# MOD SUPPORT - ASSET SOURCES
# ============================================================================

class ModAssetSource:
    """Represents a source of coat of arms assets (base game or mod)."""
    
    def __init__(self, name: str, path: Path, is_base_game: bool = False):
        self.name = name
        self.path = Path(path)
        self.is_base_game = is_base_game
        self.has_emblems = False
        self.has_patterns = False
        self.has_frames = False
        self.has_realm_frames = False
        self.has_title_frames = False
        self.has_culture_files = False
        self.has_emblem_metadata = False
        self.has_pattern_metadata = False
    
    def __repr__(self):
        return f"ModAssetSource(name={self.name}, has_emblems={self.has_emblems}, has_patterns={self.has_patterns}, has_frames={self.has_frames})"


def parse_mod_file(mod_file_path: Path) -> Optional[Tuple[str, str]]:
    """Parse a .mod file to extract name and path.
    
    Returns:
        Tuple of (mod_name, mod_path) or None if parsing fails
    """
    try:
        with open(mod_file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        
        # Extract name
        name_match = re.search(r'^name\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if not name_match:
            return None
        mod_name = name_match.group(1)
        
        # Extract path
        path_match = re.search(r'^path\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if not path_match:
            return None
        mod_path = path_match.group(1)
        
        return (mod_name, mod_path)
        
    except Exception:
        return None


def detect_coa_assets(mod_path: Path) -> Dict[str, bool]:
    """Detect which coat of arms asset types exist in a mod path.
    
    Returns:
        Dict with boolean flags for each asset type
    """
    # Check for emblems
    emblems_dir = mod_path / "gfx" / "coat_of_arms" / "colored_emblems"
    has_emblems = emblems_dir.exists() and any(emblems_dir.glob("*.dds"))
    
    # Check for patterns
    patterns_dir = mod_path / "gfx" / "coat_of_arms" / "patterns"
    has_patterns = patterns_dir.exists() and any(patterns_dir.glob("*.dds"))
    
    # Check for frames
    frames_dir = mod_path / "gfx" / "interface" / "coat_of_arms" / "frames"
    has_frames = frames_dir.exists() and any(frames_dir.glob("*.dds"))
    
    # Check for realm frames (government-specific)
    realm_frames_dir = mod_path / "gfx" / "interface" / "icons" / "realm_frames"
    has_realm_frames = realm_frames_dir.exists() and any(realm_frames_dir.glob("*_mask.dds"))
    
    # Check for title frames (crown_strip, title_mask, title_<size>, topframe_<size>)
    coa_dir = mod_path / "gfx" / "interface" / "coat_of_arms"
    has_title_frames = coa_dir.exists() and (
        (coa_dir / "title_mask.dds").exists() or
        any(coa_dir.glob("crown_strip_*.dds")) or
        any(coa_dir.glob("title_*.dds")) or
        any(coa_dir.glob("topframe_*.dds"))
    )
    
    # Check for culture files (frame transforms)
    culture_dir = mod_path / "common" / "culture" / "cultures"
    has_culture_files = culture_dir.exists() and any(culture_dir.glob("*.txt"))
    
    # Check for metadata files
    has_emblem_metadata = emblems_dir.exists() and any(emblems_dir.glob("*.txt"))
    has_pattern_metadata = patterns_dir.exists() and any(patterns_dir.glob("*.txt"))
    
    return {
        'has_emblems': has_emblems,
        'has_patterns': has_patterns,
        'has_frames': has_frames,
        'has_realm_frames': has_realm_frames,
        'has_title_frames': has_title_frames,
        'has_culture_files': has_culture_files,
        'has_emblem_metadata': has_emblem_metadata,
        'has_pattern_metadata': has_pattern_metadata
    }


def scan_mod_files(mod_dir: Path) -> List[Tuple[str, Path]]:
    """Scan mod directory for .mod files and extract mod info.
    
    Returns:
        List of (mod_name, mod_path) tuples
    """
    mod_files = list(mod_dir.glob("*.mod"))
    mods = []
    
    for mod_file in mod_files:
        result = parse_mod_file(mod_file)
        if result:
            mod_name, mod_path_str = result
            # Convert path to Path object and handle relative paths
            mod_path = Path(mod_path_str)
            if mod_path.exists():
                mods.append((mod_name, mod_path))
    
    return mods


def build_asset_sources(base_game_dir: Path, mod_dir: Optional[Path] = None) -> List[ModAssetSource]:
    """Build list of asset sources from base game and mods.
    
    Args:
        base_game_dir: Path to CK3 base game installation
        mod_dir: Optional path to mod directory
    
    Returns:
        List of ModAssetSource objects (base game first, then mods with CoA assets)
    """
    sources = []
    
    # Add base game source
    base_source = ModAssetSource("Base Game", base_game_dir, is_base_game=True)
    base_assets = detect_coa_assets(base_game_dir / "game")
    base_source.has_emblems = base_assets['has_emblems']
    base_source.has_patterns = base_assets['has_patterns']
    base_source.has_frames = base_assets['has_frames']
    base_source.has_realm_frames = base_assets['has_realm_frames']
    base_source.has_title_frames = base_assets['has_title_frames']
    base_source.has_culture_files = base_assets['has_culture_files']
    base_source.has_emblem_metadata = base_assets['has_emblem_metadata']
    base_source.has_pattern_metadata = base_assets['has_pattern_metadata']
    sources.append(base_source)
    
    # Add mod sources if mod directory provided
    if mod_dir and mod_dir.exists():
        mods = scan_mod_files(mod_dir)
        
        for mod_name, mod_path in mods:
            mod_assets = detect_coa_assets(mod_path)
            
            # Only add mod if it has at least one CoA asset type
            if any(mod_assets.values()):
                mod_source = ModAssetSource(mod_name, mod_path)
                mod_source.has_emblems = mod_assets['has_emblems']
                mod_source.has_patterns = mod_assets['has_patterns']
                mod_source.has_frames = mod_assets['has_frames']
                mod_source.has_realm_frames = mod_assets['has_realm_frames']
                mod_source.has_title_frames = mod_assets['has_title_frames']
                mod_source.has_culture_files = mod_assets['has_culture_files']
                mod_source.has_emblem_metadata = mod_assets['has_emblem_metadata']
                mod_source.has_pattern_metadata = mod_assets['has_pattern_metadata']
                sources.append(mod_source)
    
    return sources


def find_asset_files(source: ModAssetSource, asset_type: str) -> List[Path]:
    """Find asset files of a specific type in a source.
    
    Args:
        source: ModAssetSource to search
        asset_type: 'emblems', 'patterns', 'frames', or 'realm_frames'
    
    Returns:
        List of DDS file paths
    """
    if source.is_base_game:
        base_path = source.path / "game" / "gfx"
    else:
        base_path = source.path / "gfx"
    
    if asset_type == 'emblems':
        search_dir = base_path / "coat_of_arms" / "colored_emblems"
        pattern = "*.dds"  # Changed from ce_*.dds to catch all DDS files
    elif asset_type == 'patterns':
        search_dir = base_path / "coat_of_arms" / "patterns"
        pattern = "*.dds"  # Changed from pattern_*.dds to catch all DDS files
    elif asset_type == 'frames':
        if source.is_base_game:
            search_dir = source.path / "game" / "gfx" / "interface" / "coat_of_arms" / "frames"
        else:
            search_dir = source.path / "gfx" / "interface" / "coat_of_arms" / "frames"
        pattern = "*.dds"
    elif asset_type == 'realm_frames':
        if source.is_base_game:
            search_dir = source.path / "game" / "gfx" / "interface" / "icons" / "realm_frames"
        else:
            search_dir = source.path / "gfx" / "interface" / "icons" / "realm_frames"
        pattern = "*.dds"
    elif asset_type == 'title_frames':
        if source.is_base_game:
            search_dir = source.path / "game" / "gfx" / "interface" / "coat_of_arms"
        else:
            search_dir = source.path / "gfx" / "interface" / "coat_of_arms"
        # Get title_mask.dds, crown_strip_*.dds, title_*.dds (not title_mask.dds), topframe_*.dds
        if not search_dir.exists():
            return []
        files = []
        if (search_dir / "title_mask.dds").exists():
            files.append(search_dir / "title_mask.dds")
        files.extend(search_dir.glob("crown_strip_*.dds"))
        files.extend(search_dir.glob("title_[0-9]*.dds"))  # title_28.dds, etc., not title_mask.dds
        files.extend(search_dir.glob("topframe_*.dds"))
        return files
    else:
        return []
    
    if not search_dir.exists():
        return []
    
    return list(search_dir.glob(pattern))


def merge_metadata_simple(base_dict: Dict, new_dict: Dict, source_name: str) -> Dict:
    """Merge metadata with simple top-level override.
    
    Args:
        base_dict: Base metadata dictionary
        new_dict: New metadata to merge in
        source_name: Name of source for tracking
    
    Returns:
        Merged dictionary (modifies base_dict in place and returns it)
    """
    for key, value in new_dict.items():
        # Add source tracking if value is a dict
        if isinstance(value, dict):
            value['_source'] = source_name
            if key in base_dict:
                value['_overrides_base'] = True
        
        # Simple override: last one wins
        base_dict[key] = value
    
    return base_dict


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
        print(f"ERROR loading DDS {dds_path}: {type(e).__name__}: {str(e)}")
        return None


# ============================================================================
# CONVERSION WORKER THREAD
# ============================================================================

class ConversionWorker(QThread):
    """Worker thread for asset conversion to keep GUI responsive."""
    
    progress = pyqtSignal(str, int, int)  # message, current, total
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, ck3_dir: Path, output_dir: Path, mod_dir: Optional[Path] = None):
        super().__init__()
        self.ck3_dir = Path(ck3_dir)
        self.output_dir = Path(output_dir)
        self.mod_dir = Path(mod_dir) if mod_dir else None
        self.error_log = []
        
        # Build list of asset sources (base game + mods)
        self.asset_sources = build_asset_sources(self.ck3_dir, self.mod_dir)
        
        # Debug: Log asset source detection
        for src in self.asset_sources:
            print(f"DEBUG Source: {src.name}")
            print(f"  Path: {src.path}")
            print(f"  has_emblems={src.has_emblems}, has_patterns={src.has_patterns}, has_frames={src.has_frames}")
    
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
            # Log detected sources
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
            
            # Step 3.6: Process title frames (crown_strip, title_mask, title, topframe)
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
                # Count mods processed
                mod_count = len(self.asset_sources) - 1
                if mod_count > 0:
                    message = f"Conversion completed successfully! Processed base game + {mod_count} mod(s)"
                else:
                    message = "Conversion completed successfully!"
            
            self.finished.emit(True, message)
            
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")
    
    def process_emblems_from_sources(self) -> bool:
        """Process emblem DDS files from all sources to source PNGs and atlases."""
        try:
            # Create output directories
            source_out = self.output_dir / "coa_emblems" / "source"
            atlas_out = self.output_dir / "coa_emblems" / "atlases"
            source_out.mkdir(parents=True, exist_ok=True)
            atlas_out.mkdir(parents=True, exist_ok=True)
            
            total_processed = 0
            total_skipped = 0
            total_errors = 0
            
            # Process each source
            for source in self.asset_sources:
                self.progress.emit(f"Checking {source.name} for emblems... (has_emblems={source.has_emblems})", 0, 0)
                
                if not source.has_emblems:
                    self.progress.emit(f"  Skipping {source.name} - no emblems detected", 0, 0)
                    continue
                
                self.progress.emit(f"Processing emblems from {source.name}...", 0, 0)
                
                dds_files = find_asset_files(source, 'emblems')
                
                self.progress.emit(f"  Found {len(dds_files)} emblem DDS files in {source.name}", 0, 0)
                
                if not dds_files:
                    self.progress.emit(f"  No emblem files found in {source.name}", 0, 0)
                    continue
                
                processed = 0
                skipped = 0
                errors = 0
                
                for i, dds_file in enumerate(dds_files):
                    # Update progress every 50 files
                    if i % 50 == 0:
                        self.progress.emit(f"Processing emblems from {source.name}... {i}/{len(dds_files)}", i, len(dds_files))
                    
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
                        self.log_error(f"Failed to load DDS from {source.name}: {dds_file.name}")
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
                        self.log_error(f"Error processing {dds_file.name} from {source.name}: {str(e)}")
                        errors += 1
                
                total_processed += processed
                total_skipped += skipped
                total_errors += errors
                
                self.progress.emit(f"{source.name}: {processed} emblems processed, {skipped} skipped, {errors} errors", 0, 0)
            
            self.progress.emit(f"Total emblems: {total_processed} processed, {total_skipped} skipped, {total_errors} errors", 0, 0)
            return True
            
        except Exception as e:
            self.log_error(f"Emblem processing error: {str(e)}")
            return False
    
    def process_patterns_from_sources(self) -> bool:
        """Process pattern DDS files from all sources to source PNGs and atlases."""
        try:
            # Create output directories
            source_out = self.output_dir / "coa_patterns" / "source"
            atlas_out = self.output_dir / "coa_patterns" / "atlases"
            source_out.mkdir(parents=True, exist_ok=True)
            atlas_out.mkdir(parents=True, exist_ok=True)
            
            total_processed = 0
            total_skipped = 0
            total_errors = 0
            
            # Process each source
            for source in self.asset_sources:
                self.progress.emit(f"Checking {source.name} for patterns... (has_patterns={source.has_patterns})", 0, 0)
                
                if not source.has_patterns:
                    self.progress.emit(f"  Skipping {source.name} - no patterns detected", 0, 0)
                    continue
                
                self.progress.emit(f"Processing patterns from {source.name}...", 0, 0)
                
                dds_files = find_asset_files(source, 'patterns')
                
                self.progress.emit(f"  Found {len(dds_files)} pattern DDS files in {source.name}", 0, 0)
                
                if not dds_files:
                    self.progress.emit(f"  No pattern files found in {source.name}", 0, 0)
                    continue
                
                processed = 0
                skipped = 0
                errors = 0
                
                for i, dds_file in enumerate(dds_files):
                    self.progress.emit(f"Processing patterns from {source.name}... {i}/{len(dds_files)}", i, len(dds_files))
                    
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
                        self.log_error(f"Failed to load DDS from {source.name}: {dds_file.name}")
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
                        self.log_error(f"Error processing {dds_file.name} from {source.name}: {str(e)}")
                        errors += 1
                
                total_processed += processed
                total_skipped += skipped
                total_errors += errors
                
                self.progress.emit(f"{source.name}: {processed} patterns processed, {skipped} skipped, {errors} errors", 0, 0)
            
            self.progress.emit(f"Total patterns: {total_processed} processed, {total_skipped} skipped, {total_errors} errors", 0, 0)
            return True
            
        except Exception as e:
            self.log_error(f"Pattern processing error: {str(e)}")
            return False
    
    def process_frames_from_sources(self) -> bool:
        """Process frame DDS files from all sources to PNGs."""
        try:
            # Create output directory
            frame_out = self.output_dir / "coa_frames"
            frame_out.mkdir(parents=True, exist_ok=True)
            
            total_processed = 0
            total_skipped = 0
            total_errors = 0
            
            # Process each source
            for source in self.asset_sources:
                self.progress.emit(f"Checking {source.name} for frames... (has_frames={source.has_frames})", 0, 0)
                
                if not source.has_frames:
                    self.progress.emit(f"  Skipping {source.name} - no frames detected", 0, 0)
                    continue
                
                self.progress.emit(f"Processing frames from {source.name}...", 0, 0)
                
                dds_files = find_asset_files(source, 'frames')
                
                self.progress.emit(f"  Found {len(dds_files)} frame DDS files in {source.name}", 0, 0)
                
                if not dds_files:
                    self.progress.emit(f"  No frame files found in {source.name}", 0, 0)
                    continue
                
                processed = 0
                skipped = 0
                errors = 0
                
                for i, dds_file in enumerate(dds_files):
                    self.progress.emit(f"Processing frames from {source.name}... {i}/{len(dds_files)}", i, len(dds_files))
                    
                    png_file = frame_out / f"{dds_file.stem}.png"
                    
                    if not self.should_process(dds_file, png_file):
                        skipped += 1
                        continue
                    
                    img_array = load_dds_image(dds_file)
                    if img_array is None:
                        self.log_error(f"Failed to load DDS from {source.name}: {dds_file.name}")
                        errors += 1
                        continue
                    
                    try:
                        img = Image.fromarray(img_array, mode='RGBA')
                        img.save(png_file, 'PNG')
                        processed += 1
                    except Exception as e:
                        self.log_error(f"Error processing {dds_file.name} from {source.name}: {str(e)}")
                        errors += 1
                
                total_processed += processed
                total_skipped += skipped
                total_errors += errors
                
                self.progress.emit(f"{source.name}: {processed} frames processed, {skipped} skipped, {errors} errors", 0, 0)
            
            self.progress.emit(f"Total frames: {total_processed} processed, {total_skipped} skipped, {total_errors} errors", 0, 0)
            return True
            
        except Exception as e:
            self.log_error(f"Frame processing error: {str(e)}")
            return False
    
    def process_realm_frames_from_sources(self) -> bool:
        """Process realm frame (government) DDS files from all sources to PNGs."""
        try:
            # Create output directory
            realm_frames_out = self.output_dir / "realm_frames"
            realm_frames_out.mkdir(parents=True, exist_ok=True)
            
            total_processed = 0
            total_skipped = 0
            total_errors = 0
            
            # Process each source
            for source in self.asset_sources:
                if not source.has_realm_frames:
                    continue
                
                self.progress.emit(f"Processing realm frames from {source.name}...", 0, 0)
                
                dds_files = find_asset_files(source, 'realm_frames')
                
                if not dds_files:
                    self.progress.emit(f"No realm frame files found in {source.name}", 0, 0)
                    continue
                
                processed = 0
                skipped = 0
                errors = 0
                
                for i, dds_file in enumerate(dds_files):
                    self.progress.emit(f"Processing realm frames from {source.name}... {i}/{len(dds_files)}", i, len(dds_files))
                    
                    png_file = realm_frames_out / f"{dds_file.stem}.png"
                    
                    if not self.should_process(dds_file, png_file):
                        skipped += 1
                        continue
                    
                    img_array = load_dds_image(dds_file)
                    if img_array is None:
                        self.log_error(f"Failed to load DDS from {source.name}: {dds_file.name}")
                        errors += 1
                        continue
                    
                    try:
                        img = Image.fromarray(img_array, mode='RGBA')
                        img.save(png_file, 'PNG')
                        processed += 1
                    except Exception as e:
                        self.log_error(f"Error processing {dds_file.name} from {source.name}: {str(e)}")
                        errors += 1
                
                total_processed += processed
                total_skipped += skipped
                total_errors += errors
                
                self.progress.emit(f"{source.name}: {processed} realm frames processed, {skipped} skipped, {errors} errors", 0, 0)
            
            self.progress.emit(f"Total realm frames: {total_processed} processed, {total_skipped} skipped, {total_errors} errors", 0, 0)
            return True
            
        except Exception as e:
            self.log_error(f"Realm frame processing error: {str(e)}")
            return False
    
    def process_title_frames_from_sources(self) -> bool:
        """Process title frame assets (crown_strip, title_mask, title, topframe) to PNGs."""
        try:
            # Create output directory
            title_frames_out = self.output_dir / "title_frames"
            title_frames_out.mkdir(parents=True, exist_ok=True)
            
            total_processed = 0
            total_skipped = 0
            total_errors = 0
            
            # Process each source
            for source in self.asset_sources:
                if not source.has_title_frames:
                    continue
                
                self.progress.emit(f"Processing title frames from {source.name}...", 0, 0)
                
                dds_files = find_asset_files(source, 'title_frames')
                
                if not dds_files:
                    self.progress.emit(f"No title frame files found in {source.name}", 0, 0)
                    continue
                
                processed = 0
                skipped = 0
                errors = 0
                
                for i, dds_file in enumerate(dds_files):
                    self.progress.emit(f"Processing title frames from {source.name}... {i}/{len(dds_files)}", i, len(dds_files))
                    
                    png_file = title_frames_out / f"{dds_file.stem}.png"
                    
                    if not self.should_process(dds_file, png_file):
                        skipped += 1
                        continue
                    
                    img_array = load_dds_image(dds_file)
                    if img_array is None:
                        self.log_error(f"Failed to load DDS from {source.name}: {dds_file.name}")
                        errors += 1
                        continue
                    
                    try:
                        img = Image.fromarray(img_array, mode='RGBA')
                        img.save(png_file, 'PNG')
                        processed += 1
                    except Exception as e:
                        self.log_error(f"Error processing {dds_file.name} from {source.name}: {str(e)}")
                        errors += 1
                
                total_processed += processed
                total_skipped += skipped
                total_errors += errors
                
                self.progress.emit(f"{source.name}: {processed} title frames processed, {skipped} skipped, {errors} errors", 0, 0)
            
            self.progress.emit(f"Total title frames: {total_processed} processed, {total_skipped} skipped, {total_errors} errors", 0, 0)
            return True
            
        except Exception as e:
            self.log_error(f"Title frame processing error: {str(e)}")
            return False
    
    def extract_frame_transforms_from_sources(self) -> bool:
        """Extract frame scales and offsets from culture files in all sources."""
        try:
            from collections import defaultdict, Counter
            
            frame_scales = defaultdict(list)
            frame_offsets = defaultdict(list)
            culture_to_frame = {}
            
            # Process each source
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
                        # Detect culture definition start
                        culture_match = re.match(r'^(\w+)\s*=\s*\{', line)
                        if culture_match:
                            current_culture = culture_match.group(1)
                            current_frame = None
                            continue
                        
                        # Find house_coa_frame
                        frame_match = re.search(r'house_coa_frame\s*=\s*(house_frame_\d+)', line)
                        if frame_match and current_culture:
                            current_frame = frame_match.group(1)
                        
                        # Find house_coa_mask_scale
                        scale_match = re.search(r'house_coa_mask_scale\s*=\s*\{\s*([\d.]+)\s+([\d.]+)\s*\}', line)
                        if scale_match and current_culture and current_frame:
                            scale_x = float(scale_match.group(1))
                            scale_y = float(scale_match.group(2))
                            
                            frame_scales[current_frame].append((scale_x, scale_y))
                            culture_to_frame[current_culture] = {
                                'frame': current_frame,
                                'scale': [scale_x, scale_y]
                            }
                        
                        # Find house_coa_mask_offset
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
            
            # Save to output
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
    
    def extract_mask_texture(self) -> bool:
        """Extract the CoA mask texture from game files."""
        try:
            mask_source = self.ck3_dir / "game" / "gfx" / "coat_of_arms" / "coa_mask_texture.dds"
            if not mask_source.exists():
                self.log_error(f"Mask texture not found: {mask_source}")
                return False
            
            mask_dest = self.output_dir / "coa_mask_texture.png"
            
            # Check if processing needed
            if not self.should_process(mask_source, mask_dest):
                self.progress.emit("Mask texture already up to date", 0, 0)
                return True
            
            # Load and convert DDS to PNG
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
    
    def extract_emblem_layouts(self) -> bool:
        """Extract CK3 emblem layout templates from game files.
        
        Parses emblem_layouts/*.txt files and converts instance templates
        to flattened position arrays stored in JSON format.
        """
        try:
            # Find emblem layout files from all sources
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
                
                # Debug: Show first few files if any exist
                if layout_files:
                    for i, f in enumerate(layout_files[:3]):
                        self.progress.emit(f"    -> {f.name}", 0, 0)
                    if len(layout_files) > 3:
                        self.progress.emit(f"    -> ... and {len(layout_files) - 3} more", 0, 0)
                else:
                    # Show what IS in the directory
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
                        
                        # Parse layouts from this file
                        file_layouts = self.parse_emblem_layout_file(content)
                        
                        # Merge with existing (later sources override)
                        for layout_name, instances in file_layouts.items():
                            layouts_dict[layout_name] = instances
                            
                        self.progress.emit(f"  Loaded {len(file_layouts)} layouts from {layout_file.name}", 0, 0)
                        
                    except Exception as e:
                        self.log_error(f"Error parsing layout file {layout_file.name}: {e}")
            
            if not layouts_dict:
                self.log_error("No emblem layouts found")
                return False
            
            # Save to JSON
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
        
        # CK3 format: layout_name = { ... colored_emblem = { ... instance = { position = {...} scale = {...} } ... } }
        # Pattern to find layout blocks: layout_name = { ... }
        layout_pattern = r'(coa_designer_\w+)\s*=\s*\{(.*?)\n\}'
        
        for layout_match in re.finditer(layout_pattern, content, re.DOTALL):
            layout_name = layout_match.group(1)
            layout_block = layout_match.group(2)
            
            # Find all instance lines: instance = { position = { x y } scale = { sx sy } }
            # Note: rotation is optional and defaults to 0
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
    
    def convert_metadata_from_sources(self) -> bool:
        """Convert CK3 .txt metadata files to JSON from all sources."""
        try:
            emblems_metadata = {}
            patterns_metadata = {}
            
            # Process each source
            for source in self.asset_sources:
                if source.is_base_game:
                    metadata_dir = source.path / "game" / "gfx" / "coat_of_arms"
                else:
                    metadata_dir = source.path / "gfx" / "coat_of_arms"
                
                self.progress.emit(f"Converting metadata from {source.name}...", 0, 0)
                
                # Convert emblems metadata
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
                
                # Convert patterns metadata
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
            
            # Write merged metadata
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
        
        # Mod Directory selection (optional)
        mod_group = QGroupBox("Mod Directory (Optional)")
        mod_layout = QHBoxLayout()
        self.mod_path_edit = QLineEdit()
        self.mod_path_edit.setPlaceholderText("Optional: Select mod directory to include mod assets...")
        self.mod_browse_btn = QPushButton("Browse...")
        self.mod_browse_btn.clicked.connect(self.browse_mod_dir)
        mod_layout.addWidget(self.mod_path_edit)
        mod_layout.addWidget(self.mod_browse_btn)
        mod_group.setLayout(mod_layout)
        layout.addWidget(mod_group)
        
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
    
    def browse_mod_dir(self):
        """Open directory browser for mod directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Mod Directory",
            "", QFileDialog.ShowDirsOnly
        )
        if dir_path:
            self.mod_path_edit.setText(dir_path)
    
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
        mod_dir_text = self.mod_path_edit.text().strip()
        mod_dir = Path(mod_dir_text) if mod_dir_text else None
        
        # Disable UI during conversion
        self.convert_btn.setText("Converting...")
        self.convert_btn.setEnabled(False)
        self.ck3_browse_btn.setEnabled(False)
        self.mod_browse_btn.setEnabled(False)
        self.output_browse_btn.setEnabled(False)
        self.ck3_path_edit.setEnabled(False)
        self.mod_path_edit.setEnabled(False)
        self.output_path_edit.setEnabled(False)
        
        self.log_text.clear()
        self.log(f"Starting conversion from: {ck3_dir}")
        if mod_dir:
            self.log(f"Including mods from: {mod_dir}")
        self.log(f"Output to: {output_dir}")
        
        # Create and start worker thread
        self.worker = ConversionWorker(ck3_dir, output_dir, mod_dir)
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
            # Change button to close app
            self.convert_btn.setText("Conversion Done - Close")
            self.convert_btn.clicked.disconnect()
            self.convert_btn.clicked.connect(self.close)
            self.convert_btn.setEnabled(True)
            # Keep text fields disabled
        else:
            QMessageBox.critical(self, "Error", message)
            # Reset button for retry on error
            self.convert_btn.setText("Start Conversion")
            self.convert_btn.setEnabled(True)
            # Re-enable UI for retry
            self.ck3_browse_btn.setEnabled(True)
            self.mod_browse_btn.setEnabled(True)
            self.output_browse_btn.setEnabled(True)
            self.ck3_path_edit.setEnabled(True)
            self.mod_path_edit.setEnabled(True)
            self.output_path_edit.setEnabled(True)
        
        self.progress_bar.setValue(0 if not success else 100)


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    window = AssetConverterGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
