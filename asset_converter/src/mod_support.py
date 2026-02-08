"""
Mod support and asset source management.

Handles detection of CK3 coat of arms assets across the base game and
Steam Workshop mods. Provides file discovery, mod parsing, and metadata merging.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ModAssetSource:
    """Represents a source of coat of arms assets (base game or mod)."""
    
    ASSET_FLAGS = (
        'has_emblems', 'has_patterns', 'has_frames', 'has_realm_frames',
        'has_title_frames', 'has_culture_files', 'has_emblem_metadata', 'has_pattern_metadata'
    )
    
    def __init__(self, name: str, path: Path, is_base_game: bool = False, assets: Optional[Dict[str, bool]] = None):
        self.name = name
        self.path = Path(path)
        self.is_base_game = is_base_game
        for flag in self.ASSET_FLAGS:
            setattr(self, flag, assets.get(flag, False) if assets else False)
    
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
        
        name_match = re.search(r'^name\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if not name_match:
            return None
        mod_name = name_match.group(1)
        
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
    
    # Check for title frames (crown_strip, title_mask, title_<size>, topframe, variants)
    coa_dir = mod_path / "gfx" / "interface" / "coat_of_arms"
    has_title_frames = coa_dir.exists() and (
        (coa_dir / "title_mask.dds").exists() or
        (coa_dir / "house_mask.dds").exists() or
        (coa_dir / "designer_mask.dds").exists() or
        (coa_dir / "coa_overlay.dds").exists() or
        (coa_dir / "lowborn.dds").exists() or
        any(coa_dir.glob("crown_strip_*.dds")) or
        any(coa_dir.glob("title_*.dds")) or
        any(coa_dir.glob("topframe_*.dds")) or
        any(coa_dir.glob("*_topframe_*.dds")) or  # holyorder_, mercenary_, landless_adventurer_
        any(coa_dir.glob("dynasty_*.dds")) or
        any(coa_dir.glob("*_mask.dds"))
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
    base_assets = detect_coa_assets(base_game_dir / "game")
    sources.append(ModAssetSource("Base Game", base_game_dir, is_base_game=True, assets=base_assets))
    
    # Add mod sources if mod directory provided
    if mod_dir and mod_dir.exists():
        for mod_name, mod_path in scan_mod_files(mod_dir):
            mod_assets = detect_coa_assets(mod_path)
            if any(mod_assets.values()):
                sources.append(ModAssetSource(mod_name, mod_path, assets=mod_assets))
    
    return sources


def find_asset_files(source: ModAssetSource, asset_type: str) -> List[Path]:
    """Find asset files of a specific type in a source.
    
    Args:
        source: ModAssetSource to search
        asset_type: 'emblems', 'patterns', 'frames', 'realm_frames', or 'title_frames'
    
    Returns:
        List of DDS file paths
    """
    if source.is_base_game:
        base_path = source.path / "game" / "gfx"
    else:
        base_path = source.path / "gfx"
    
    if asset_type == 'emblems':
        search_dir = base_path / "coat_of_arms" / "colored_emblems"
        pattern = "*.dds"
    elif asset_type == 'patterns':
        search_dir = base_path / "coat_of_arms" / "patterns"
        pattern = "*.dds"
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
        
        if not search_dir.exists():
            return []
        
        files = []
        
        # Mask textures
        for mask_name in ('title_mask.dds', 'house_mask.dds', 'designer_mask.dds',
                          'asia_house_mask.dds'):
            mask_path = search_dir / mask_name
            if mask_path.exists():
                files.append(mask_path)
        
        # Standalone special textures
        for special_name in ('coa_overlay.dds', 'lowborn.dds'):
            special_path = search_dir / special_name
            if special_path.exists():
                files.append(special_path)
        
        # Sized title/crown/dynasty textures
        files.extend(search_dir.glob("crown_strip_*.dds"))
        files.extend(search_dir.glob("title_[0-9]*.dds"))       # title_28.dds etc (not title_mask.dds)
        files.extend(search_dir.glob("title_no_holder_*.dds"))
        files.extend(search_dir.glob("dynasty_*.dds"))           # dynasty_115.dds etc
        
        # Topframe variants (base + holyorder/mercenary/landless_adventurer)
        files.extend(search_dir.glob("topframe_*.dds"))
        files.extend(search_dir.glob("holyorder_topframe_*.dds"))
        files.extend(search_dir.glob("mercenary_topframe_*.dds"))
        files.extend(search_dir.glob("landless_adventurer_topframe_*.dds"))
        
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
        if not isinstance(value, dict):
            continue
            
        value['_source'] = source_name
        if key in base_dict:
            value['_overrides_base'] = True
        
        base_dict[key] = value
    
    return base_dict
