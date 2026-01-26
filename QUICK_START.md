# Quick Start Guide

## For End Users

1. **[Download the latest release](https://github.com/Nargodian/CK3CoatOfArmsEditor/releases)**
2. Extract the ZIP file
3. Run `AssetConverter.exe` and point it to your CK3 installation
4. Wait for asset extraction (15-20 minutes first time)
5. Run `CoatOfArmsEditor.exe` and start creating!

## For Developers

### Prerequisites

- Python 3.8 or later
- CK3 installed (for asset extraction)

## Step 1: Install Dependencies

```batch
pip install -r requirements.txt
```

This installs:
- PyQt5 (GUI framework)
- PyOpenGL (OpenGL for editor)
- Pillow, numpy (image processing)
- imageio, imageio-dds (DDS loading)
- PyInstaller (for building)

## Step 2: Test in Development Mode

### Test the Asset Converter

```batch
python asset_converter/asset_converter.py
```

1. Click "Browse..." next to CK3 Installation Directory
2. Select your CK3 folder (e.g., `C:\Program Files (x86)\Steam\steamapps\common\Crusader Kings III`)
3. Output directory should default to `ck3_assets` next to the script
4. Click "Start Conversion"
5. Wait 15-20 minutes for first run
6. Check that `ck3_assets/` folder was created with:
   - `coa_emblems/metadata/`, `source/`, `atlases/`
   - `coa_patterns/metadata/`, `source/`, `atlases/`
   - `coa_frames/`

### Test the Editor

```batch
python editor/src/main.py
```

1. Editor should load without errors
2. Check that assets appear in the sidebar
3. Try creating a coat of arms
4. Verify rendering works correctly
5. Try loading example CoAs from `examples/game_samples/`

## Step 3: Build Executables

```batch
cd build
build.bat
```

This will:
1. Clean previous builds
2. Build CoatOfArmsEditor.exe
3. Build AssetConverter.exe
4. Merge into `dist/merged/`

Build time: ~5-10 minutes (depends on system)

## Step 4: Test Built Executables

### Test AssetConverter.exe

```batch
cd dist\merged
AssetConverter.exe
```

1. Should launch without console window
2. UI should be identical to development version
3. Test converting assets again (should skip if already done)
4. Verify incremental updates work (modify a DDS, re-run)

### Test CoatOfArmsEditor.exe

```batch
cd dist\merged
CoatOfArmsEditor.exe
```

1. Should launch without console window
2. Should load assets from `ck3_assets/` folder
3. Shaders should compile correctly
4. All editor features should work

## Step 5: Test Portability

1. Copy `dist\merged\` to a different location (e.g., Desktop)
2. Copy `ck3_assets\` to the same location
3. Run both executables from the new location
4. Both should work correctly

## Common Issues

### "imageio-dds not found"

```batch
pip install imageio-dds
```

### "Assets not loading"

Check that `ck3_assets/` is in the same directory as the executable:
```
CoatOfArmsEditor/
├── CoatOfArmsEditor.exe
├── AssetConverter.exe
├── _internal/
└── ck3_assets/         <-- Must be here
```

### "Shader compilation failed"

Check that shaders are bundled correctly:
- In development: Should be in `src/shaders/`
- In frozen: Should be in `dist/merged/_internal/shaders/` or `sys._MEIPASS/shaders/`

### "Module not found" errors

Reinstall all dependencies:
```batch
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```

## Development Testing Checklist

### Asset Converter
- [ ] Launches in dev mode (`python asset_converter.py`)
- [ ] Launches in frozen mode (`AssetConverter.exe`)
- [ ] Can select CK3 directory
- [ ] Validates paths correctly
- [ ] Extracts emblems (1585+ files)
- [ ] Extracts patterns (43 files)
- [ ] Extracts frames (66 files)
- [ ] Converts metadata (4 JSON files)
- [ ] Shows progress correctly
- [ ] Logs errors to conversion_errors.txt
- [ ] Incremental updates work (only processes changed files)

### Editor
- [ ] Launches in dev mode (`python src/main.py`)
- [ ] Launches in frozen mode (`CoatOfArmsEditor.exe`)
- [ ] Loads emblem metadata
- [ ] Loads pattern metadata
- [ ] Displays emblem thumbnails
- [ ] Displays pattern thumbnails
- [ ] Shaders compile successfully
- [ ] Can create coat of arms
- [ ] Can edit layers
- [ ] Can export CK3 format
- [ ] Frames render correctly
- [ ] Atlas textures load correctly

### Packaging
- [ ] `build.bat` completes without errors
- [ ] Both executables created
- [ ] `_internal/` folder shared correctly
- [ ] Total size reasonable (~400-500 MB)
- [ ] No missing DLL errors

### Portability
- [ ] Can copy folder to any location
- [ ] Works from Desktop, USB drive, etc.
- [ ] No Python installation required
- [ ] Both exes share `_internal/` correctly

## Performance Benchmarks

Expected performance:

### Asset Conversion
- First run: 15-20 minutes (all 1700+ files)
- Incremental: 2-3 minutes (only changed files)
- Skip all: <5 seconds (if nothing changed)

### Editor Startup
- Development: 2-5 seconds
- Frozen: 3-7 seconds

### Rendering
- 60 FPS with 5-10 layers
- No lag when adding/removing layers
- Smooth layer transformations

## Publishing a Release

1. Update `VERSION` file if needed (e.g., `1.0` → `1.1`)
2. Run `build.bat` to create versioned ZIP
3. Create git tag: `git tag -a v1.0.X -m "Release v1.0.X"`
4. Push tag: `git push origin v1.0.X`
5. Create GitHub Release and upload ZIP
6. Add release notes with features/fixes

## Troubleshooting

### Build fails with "Module not found"

Check that all dependencies in editor.spec and asset_converter.spec are correct:
- Editor: PyQt5, PyOpenGL, Pillow, numpy
- Converter: PyQt5, imageio, imageio-dds, Pillow, numpy

### Executable crashes on startup

Run from command line to see error:
```batch
cd dist\merged
CoatOfArmsEditor.exe
```

Common issues:
- Missing DLLs (rebuild with PyInstaller)
- Shader files not bundled (check editor.spec datas)
- Path resolution issues (verify path_resolver.py)

### Assets don't load in frozen mode

Check path_resolver.py is using correct paths:
- Frozen: `Path(sys.executable).parent / "ck3_assets"`
- Should resolve to `dist/merged/ck3_assets/`

### Incremental updates don't work

Verify timestamp comparison in asset_converter.py:
- Should compare source DDS mtime vs dest PNG mtime
- Should only process if source is newer

## Development Workflow

For future development:

1. Always test in development mode first
2. Ensure path_resolver works for new paths
3. Build and test frozen mode
4. Update spec files if adding new dependencies
5. Update documentation

## Documentation

- [README.md](README.md) - Project overview and features
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Technical architecture details
- [PACKAGING.md](PACKAGING.md) - Build and distribution guide
- [docs/specifications/](docs/specifications/) - CK3 format specifications
