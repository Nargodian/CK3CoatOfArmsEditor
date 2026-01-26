# CK3 Coat of Arms Editor - Packaging Instructions

This document explains how to build and distribute the CK3 Coat of Arms Editor.

## Overview

The editor is distributed as two standalone executables:
1. **CoatOfArmsEditor.exe** - Main GUI application for creating/editing coat of arms
2. **AssetConverter.exe** - Tool to extract and convert CK3 game assets

Both executables share a common `_internal/` folder containing Python libraries and dependencies.

## Requirements

### For Building
- Python 3.8 or later
- All dependencies from `requirements.txt`

### For End Users
- Windows 10/11 (64-bit)
- Crusader Kings III installed (for asset extraction)
- No Python installation required

## Building the Executables

### Option 1: Using the Build Script (Windows)

```batch
# Install dependencies
pip install -r requirements.txt

# Run the build script
cd build
build.bat
```

This will:
1. Build both executables using PyInstaller
2. Merge them into `dist/merged/` with shared libraries
3. Create a version-numbered zip file (e.g., `COAEditor_1.0.23.zip`)

Version format: `Major.Minor.Patch`
- **Major.Minor**: Set manually in `VERSION` file at project root (e.g., `1.0`, `2.1`)
- **Patch**: Automatically counts commits since last git tag (or total commits if no tags)

To bump version:
1. Edit `VERSION` file (change `1.0` to `1.1`, `2.0`, etc.)
2. Run build - patch number auto-increments with each commit

Examples:
- `VERSION=1.0` with 23 commits since tag → `COAEditor_1.0.23.zip`
- `VERSION=2.1` with 0 commits (on tag) → `COAEditor_2.1.0.zip`

### Option 2: Manual Build

```batch
# Install dependencies
pip install -r requirements.txt

# Build editor
pyinstaller editor/editor.spec

# Build asset converter
pyinstaller asset_converter/asset_converter.spec

# Manually merge the distributions:
# 1. Create dist/merged/
# 2. Copy CoatOfArmsEditor.exe from dist/CoatOfArmsEditor/
# 3. Copy AssetConverter.exe from dist/AssetConverter/
# 4. Copy _internal/ from dist/CoatOfArmsEditor/ to dist/merged/
# 5. Merge any additional files from dist/AssetConverter/_internal/
```

## Distribution Structure

After building, the `dist/merged/` folder contains:

```
CK3CoatOfArmsEditor/
├── CoatOfArmsEditor.exe      # Main editor
├── AssetConverter.exe         # Asset extraction tool
└── _internal/                 # Shared libraries (managed by PyInstaller)
```

Users will create this structure after first use:

```
CK3CoatOfArmsEditor/
├── CoatOfArmsEditor.exe
├── AssetConverter.exe
├── _internal/
└── ck3_assets/               # Created by AssetConverter
    ├── coa_emblems/
    │   ├── metadata/         # JSON files
    │   ├── source/           # Flat PNGs (256x256)
    │   └── atlases/          # Baked atlases (512x512)
    ├── coa_patterns/
    │   ├── metadata/
    │   ├── source/           # Flat PNGs (256x256)
    │   └── atlases/          # Baked atlases (512x256)
    └── coa_frames/           # Frame PNGs and masks
```

## User Workflow

### First-Time Setup

1. Extract the distribution zip to any location
2. Run `AssetConverter.exe`
3. Select CK3 installation directory (e.g., `C:\Program Files (x86)\Steam\steamapps\common\Crusader Kings III`)
4. Click "Start Conversion" (takes 15-20 minutes for first run)
5. Wait for conversion to complete

### Using the Editor

1. Run `CoatOfArmsEditor.exe`
2. Create and edit coat of arms designs
3. Export to CK3 format

### Updating Assets

If CK3 is updated with new assets:
1. Run `AssetConverter.exe` again
2. Select the same CK3 directory
3. Incremental updates take only 2-3 minutes (only processes changed files)

## Asset Extraction Details

### What Gets Extracted

From CK3 installation (`game/` folder):

**Emblems** (1585+ files):
- Source: `gfx/coat_of_arms/colored_emblems/ce_*.dds`
- Output:
  - `ck3_assets/coa_emblems/source/ce_*.png` (flat PNG for thumbnails)
  - `ck3_assets/coa_emblems/atlases/ce_*_atlas.png` (4-quadrant atlas for rendering)

**Patterns** (43 files):
- Source: `gfx/coat_of_arms/patterns/pattern_*.dds`
- Output:
  - `ck3_assets/coa_patterns/source/pattern_*.png` (flat PNG)
  - `ck3_assets/coa_patterns/atlases/pattern_*_atlas.png` (2-tile atlas)

**Frames** (66 files):
- Source: `gfx/interface/coat_of_arms/coa_frames/*.dds`
- Output: `ck3_assets/coa_frames/*.png` (direct conversion)

**Metadata** (4 files):
- Source: `common/coat_of_arms/*.txt` (CK3 format)
- Output: `ck3_assets/coa_*/metadata/*.json` (JSON format)

### Atlas Formats

**Emblem Atlas** (512x512, 4 quadrants):
```
┌─────────┬─────────┐
│ R (TL)  │ G (TR)  │  Top-Left:  White RGB with red channel as alpha
│ 256x256 │ 256x256 │  Top-Right: White RGB with green channel as alpha
├─────────┼─────────┤
│ B (BL)  │ A (BR)  │  Bottom-Left:  RGB*2 with original alpha
│ 256x256 │ 256x256 │  Bottom-Right: White RGB with inverted alpha
└─────────┴─────────┘
```

**Pattern Atlas** (512x256, 2 tiles):
```
┌─────────┬─────────┐
│ G (L)   │ B (R)   │  Left:  White RGB with green channel as alpha
│ 256x256 │ 256x256 │  Right: White RGB with blue channel as alpha
└─────────┴─────────┘
```

## Creating a Distribution Package

1. Build the executables using `build.bat`
2. Copy `dist/merged/` to a clean folder
3. Create a `README.txt` with:
   - Installation instructions
   - System requirements
   - Link to CK3 (users must own the game)
   - License information
4. Create ZIP file for distribution

### Example README.txt

```
CK3 Coat of Arms Editor v1.0
=============================

REQUIREMENTS:
- Windows 10/11 (64-bit)
- Crusader Kings III (Steam or other official version)
- 2 GB free disk space for extracted assets

INSTALLATION:
1. Extract all files to a folder (e.g., C:\CK3CoatOfArmsEditor)
2. Run AssetConverter.exe
3. Select your CK3 installation folder
4. Wait for asset extraction (15-20 minutes)

USAGE:
1. Run CoatOfArmsEditor.exe
2. Create your coat of arms
3. Export to CK3 format

TROUBLESHOOTING:
- If assets don't load: Re-run AssetConverter.exe
- If CK3 path not found: Manually locate steamapps/common/Crusader Kings III
- For help: [Support URL]

LICENSE:
This editor is a fan-made tool. Crusader Kings III and all game assets are
property of Paradox Interactive. Users must own CK3 to use this tool.
```

## Important Notes

### Copyright and Distribution

- **DO NOT distribute CK3 game assets** (DDS files, textures, metadata)
- Only distribute the executables and code
- Users must extract assets from their own CK3 installation
- This ensures compliance with Paradox Interactive's terms

### Shaders

Shaders are bundled in `CoatOfArmsEditor.exe` (in `_MEIPASS/shaders/`):
- `basic.vert` - Vertex shader
- `basic.frag` - Basic fragment shader
- `base.frag` - Base layer shader
- `design.frag` - Emblem layer shader

These are editor code, not game assets, and can be distributed.

### Path Resolution

The `path_resolver.py` module handles differences between:
- **Development**: Paths relative to source code
- **Frozen**: Paths relative to executable location

When frozen (`sys.frozen == True`):
- Assets: `{exe_dir}/ck3_assets/`
- Shaders: `{sys._MEIPASS}/shaders/`

When developing:
- Assets: `{project_root}/ck3_assets/`
- Shaders: `{project_root}/src/shaders/`

## Troubleshooting Build Issues

### PyInstaller Warnings

Common warnings (can be ignored):
- "hidden import not found" - Usually false positives
- "numpy array C-extension" - Normal for OpenGL/numpy apps

### Missing Dependencies

If build fails with import errors:
```batch
pip install --upgrade -r requirements.txt
```

### Large Executable Size

Normal sizes:
- CoatOfArmsEditor.exe: ~50-100 MB
- AssetConverter.exe: ~40-80 MB
- _internal/: ~200-300 MB

This is normal for PyQt5 + OpenGL + image processing apps.

### Testing the Build

Test checklist:
1. ✓ Both executables run without errors
2. ✓ AssetConverter can select CK3 directory
3. ✓ AssetConverter extracts assets successfully
4. ✓ Editor loads without Python installed
5. ✓ Editor can load extracted assets
6. ✓ Shaders compile correctly
7. ✓ Can create and export coat of arms

## Development vs Production

### Development Mode
```batch
# Run editor from source
python src/main.py

# Run asset converter from source
python asset_converter.py
```

### Production Mode
```batch
# Run from dist/merged/
CoatOfArmsEditor.exe
AssetConverter.exe
```

Both modes use `path_resolver.py` to locate resources correctly.

## Version Control

Files to commit:
- All source code (`src/`, `*.py`)
- Spec files (`editor.spec`, `asset_converter.spec`)
- Build script (`build.bat`)
- Requirements (`requirements.txt`)
- Documentation

Files to ignore (`.gitignore`):
- `build/` - PyInstaller build artifacts
- `dist/` - Built executables
- `ck3_assets/` - Extracted game assets
- `__pycache__/` - Python cache
- `*.pyc` - Compiled Python

## Updates and Maintenance

When updating the editor:
1. Increment version number in code
2. Update CHANGELOG.md
3. Rebuild with `build.bat`
4. Test thoroughly
5. Create new distribution ZIP
6. Update documentation if needed

## Support

For build/packaging issues:
- Check this document
- Review PyInstaller documentation
- Verify all dependencies are installed
- Test in clean Python environment

---

**Note**: This packaging setup ensures the editor is truly portable - users can copy the folder anywhere and it will work, as long as they've extracted the CK3 assets once.
