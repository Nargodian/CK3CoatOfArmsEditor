"""Path resolver for handling differences between development and frozen executable environments.

This module provides utility functions to locate application resources like assets and shaders
in both development (running from source) and production (PyInstaller frozen executable) environments.
"""

import sys
import os
from pathlib import Path


def get_base_dir() -> Path:
    """Get the base directory for the application.
    
    In frozen mode (PyInstaller executable), returns the directory containing the .exe file.
    In development mode, returns the project root directory (parent of src/).
    
    Returns:
        Path: Base directory path
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller executable
        # sys.executable is the path to the .exe file
        return Path(os.path.dirname(sys.executable))
    else:
        # Running as script - this file is in editor/src/utils/
        # Go up three levels to get to project root
        return Path(__file__).resolve().parent.parent.parent.parent


def get_assets_dir() -> Path:
    """Get the ck3_assets directory path.
    
    This directory contains all game assets extracted from CK3 installation:
    - coa_emblems/ (metadata, source PNGs, atlases)
    - coa_patterns/ (metadata, source PNGs, atlases)
    - coa_frames/ (frame PNGs and masks)
    
    Returns:
        Path: Path to ck3_assets folder next to executable or in project root
    """
    return get_base_dir() / "ck3_assets"


def get_shader_dir() -> Path:
    """Get the shader directory path.
    
    Shaders are bundled with the application code (not user-generated assets).
    In frozen mode, they're extracted to a temporary location by PyInstaller.
    In development mode, they're in the source tree.
    
    Returns:
        Path: Path to shader files
    """
    if getattr(sys, 'frozen', False):
        # Shaders are bundled in PyInstaller's temporary extraction folder
        return Path(sys._MEIPASS) / "shaders"
    else:
        # Development mode - shaders are in src/shaders/
        return Path(__file__).resolve().parent.parent / "shaders"


def get_emblem_metadata_path() -> Path:
    """Get path to emblem metadata JSON file.
    
    Returns:
        Path: Full path to 50_coa_designer_emblems.json
    """
    return get_assets_dir() / "coa_emblems" / "metadata" / "50_coa_designer_emblems.json"


def get_pattern_metadata_path() -> Path:
    """Get path to pattern metadata JSON file.
    
    Returns:
        Path: Full path to 50_coa_designer_patterns.json
    """
    return get_assets_dir() / "coa_patterns" / "metadata" / "50_coa_designer_patterns.json"


def get_emblem_atlas_dir() -> Path:
    """Get directory containing emblem atlas PNGs.
    
    Returns:
        Path: Path to emblem atlases directory
    """
    return get_assets_dir() / "coa_emblems" / "atlases"


def get_pattern_atlas_dir() -> Path:
    """Get directory containing pattern atlas PNGs.
    
    Returns:
        Path: Path to pattern atlases directory
    """
    return get_assets_dir() / "coa_patterns" / "atlases"


def get_emblem_source_dir() -> Path:
    """Get directory containing flat emblem PNGs for thumbnails.
    
    Returns:
        Path: Path to emblem source images directory
    """
    return get_assets_dir() / "coa_emblems" / "source"


def get_pattern_source_dir() -> Path:
    """Get directory containing flat pattern PNGs for thumbnails.
    
    Returns:
        Path: Path to pattern source images directory
    """
    return get_assets_dir() / "coa_patterns" / "source"


def get_frames_dir() -> Path:
    """Get directory containing coat of arms frame PNGs.
    
    Returns:
        Path: Path to coa_frames directory
    """
    return get_assets_dir() / "coa_frames"


def check_assets_exist() -> tuple[bool, list[str]]:
    """Check if required asset directories exist.
    
    Returns:
        tuple: (all_exist: bool, missing_paths: list[str])
    """
    required_paths = [
        get_emblem_metadata_path(),
        get_pattern_metadata_path(),
        get_emblem_atlas_dir(),
        get_pattern_atlas_dir(),
        get_frames_dir(),
    ]
    
    missing = []
    for path in required_paths:
        if not path.exists():
            missing.append(str(path))
    
    return (len(missing) == 0, missing)
