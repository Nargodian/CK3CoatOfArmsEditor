"""
CK3 Coat of Arms Asset Converter - Package.

Modules:
    ck3_parser        - CK3/Paradox script file parser
    atlas_baking      - Emblem and pattern atlas creation
    dds_loading       - DDS texture loading via imageio
    mod_support       - Mod detection, asset sources, file discovery
    converter_worker  - QThread conversion pipeline
    gui               - PyQt5 GUI window
"""

from .ck3_parser import CK3Parser, parse_ck3_file
from .atlas_baking import create_emblem_atlas, create_pattern_atlas
from .dds_loading import load_dds_image, HAS_IMAGEIO
from .mod_support import (
    ModAssetSource,
    parse_mod_file,
    detect_coa_assets,
    scan_mod_files,
    build_asset_sources,
    find_asset_files,
    merge_metadata_simple,
)
from .converter_worker import ConversionWorker
from .gui import AssetConverterGUI, main

__all__ = [
    'CK3Parser', 'parse_ck3_file',
    'create_emblem_atlas', 'create_pattern_atlas',
    'load_dds_image', 'HAS_IMAGEIO',
    'ModAssetSource', 'parse_mod_file', 'detect_coa_assets',
    'scan_mod_files', 'build_asset_sources', 'find_asset_files',
    'merge_metadata_simple',
    'ConversionWorker',
    'AssetConverterGUI', 'main',
]
