# CK3 Coat of Arms Editor

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub release](https://img.shields.io/github/v/release/Nargodian/CK3CoatOfArmsEditor)](https://github.com/Nargodian/CK3CoatOfArmsEditor/releases)

A desktop application for creating and editing coat of arms for Crusader Kings 3 (CK3). Built with Python, PyQt5, and OpenGL for real-time rendering of heraldic designs.

> **AI Disclosure:** This tool was developed with heavy AI assistance. I respect that people have valid concerns about AI, and I do not wish to claim ownership over the output. This tool is provided for its own sake as a useful utility, free for anyone to use or modify under the MIT License.

## Features

- **Visual Editor**: Real-time OpenGL rendering with CK3-authentic shaders
- **Asset Library**: Browse and select from 1000+ emblems and patterns
- **Transform Controls**: Intuitive handles for position, scale, rotation, and flip
- **Multi-Layer Support**: Manage multiple emblem layers with drag-and-drop reordering
- **Multi-Selection**: Select and transform multiple layers simultaneously
- **Color Customization**: Three-color system with CK3 color palette support
- **Import/Export**: Load and save CK3 .txt format coat of arms files
- **Copy/Paste**: Share designs via clipboard
- **Undo/Redo**: Full history management for all operations

## Download

**[Download the latest release](https://github.com/Nargodian/CK3CoatOfArmsEditor/releases)** - Windows 10/11 executable, no Python required.

## For Developers

### Requirements

- Python 3.8+
- PyQt5
- PyOpenGL
- NumPy
- Pillow (PIL)
- imageio, imageio-dds

### Development Setup

```bash
# Clone repository
git clone https://github.com/Nargodian/CK3CoatOfArmsEditor.git
cd CK3CoatOfArmsEditor

# Install dependencies
pip install -r requirements.txt

# Run the editor (development mode)
python editor/src/main.py

# Or run the asset converter
python asset_converter/asset_converter.py
```

### Building for Distribution

```bash
cd build
build.bat
# Creates versioned ZIP in build/dist/
```

See [PACKAGING.md](PACKAGING.md) and [ARCHITECTURE.md](docs/ARCHITECTURE.md) for complete details.

## Project Structure

The project follows a modular architecture with separate editor and asset converter projects:

```
CK3CoatOfArmsEditor/
├── editor/                          # Main editor project
│   ├── src/
│   │   ├── main.py                 # Main application (composition pattern)
│   │   ├── actions/                # Action handlers (file, clipboard, transform)
│   │   ├── components/             # UI components
│   │   │   ├── asset_sidebar.py   # Left panel - asset browser
│   │   │   ├── canvas_area.py     # Center panel - canvas container
│   │   │   ├── canvas_widget.py   # OpenGL rendering widget
│   │   │   ├── property_sidebar.py# Right panel - properties
│   │   │   ├── toolbar.py         # Top toolbar
│   │   │   ├── transform_widget.py# Transform handles overlay
│   │   │   └── canvas_widgets/    # Canvas sub-components
│   │   │       └── shader_manager.py # Shader compilation
│   │   ├── services/               # Business logic
│   │   │   ├── file_operations.py # File I/O
│   │   │   ├── layer_operations.py# Layer management
│   │   │   └── coa_serializer.py  # Serialization
│   │   ├── utils/                  # Utility modules
│   │   │   ├── path_resolver.py   # Dev/frozen path handling
│   │   │   ├── coa_parser.py      # CK3 format parser
│   │   │   ├── atlas_compositor.py# Atlas rendering
│   │   │   └── history_manager.py # Undo/redo state
│   │   └── shaders/                # GLSL shader files
│   │       ├── basic.vert         # Vertex shader
│   │       ├── basic.frag         # Basic texture shader
│   │       ├── base.frag          # Base layer shader
│   │       └── design.frag        # Emblem layer shader
│   └── editor.spec                 # PyInstaller build config
├── asset_converter/                # Asset extraction tool
│   ├── asset_converter.py         # GUI tool for CK3 asset extraction
│   └── asset_converter.spec       # PyInstaller build config
├── build/                          # Build tools
│   └── build.bat                  # Windows build script
├── docs/                           # Documentation
│   ├── ARCHITECTURE.md            # Technical architecture
│   ├── CoA_Parser_Documentation.md# Parser API reference
│   └── specifications/            # CK3 format specifications
├── examples/                       # Code examples and sample CoAs
│   ├── parser_example.py          # Parser usage example
│   └── game_samples/              # Sample CoA designs from game
├── tests/                          # Unit tests
│   ├── test_coa_parser.py        # Parser tests
│   ├── test_layer_copy_paste.py  # Layer operations tests
│   └── test_roundtrip.py         # Import/export tests
├── requirements.txt               # Python dependencies
├── PACKAGING.md                   # Build & distribution guide
└── README.md                      # This file
```

## Architecture Overview

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for complete technical details.

### Main Window (`main.py`)
- Application orchestration using composition pattern
- Delegates to action handler classes (FileActions, ClipboardActions, LayerTransformActions)
- Menu handling and keyboard shortcuts
- Undo/redo management with history snapshots
- Autosave and recent files tracking

### Components

#### Asset Sidebar (`asset_sidebar.py`)
- Tabbed interface for Patterns and Emblems
- Thumbnail grid with filtering
- Drag-and-drop to canvas

#### Canvas Area (`canvas_area.py`)
- Container for canvas widget and transform widget
- Manages layer selection and interaction modes
- Coordinates between canvas and transform handles

#### Canvas Widget (`canvas_widget.py`)
- OpenGL-based rendering using PyQt5's QOpenGLWidget
- Implements CK3's shader system (base.frag, design.frag)
- Texture atlas management for efficient rendering
- Real-time layer preview

#### Property Sidebar (`property_sidebar.py`)
- Three-tab interface: Base, Layers, Properties
- Base tab: Pattern selection and colors
- Layers tab: Layer list with multi-select and reordering
- Properties tab: Transform controls for selected layers

#### Transform Widget (`transform_widget.py`)
- Overlay widget for direct manipulation
- Interactive handles: center (move), corners (scale), edges (edge-scale), rotation
- Supports multi-selection transforms

### Utilities

#### CoA Parser (`utils/coa_parser.py`)
- Parses CK3's Clausewitz format text files
- Serializes editor data back to CK3 format
- Handles complex nested structures with proper escaping

#### History Manager (`utils/history_manager.py`)
- Implements undo/redo functionality
- JSON-based state snapshots
- Efficient memory management

#### Shader Manager (`components/canvas_widgets/shader_manager.py`)
- Loads and compiles GLSL shaders
- Creates shader programs
- Error handling and logging

## Shader System

The editor uses CK3's authentic shader system for accurate preview:

- **basic.vert**: Standard vertex shader for 2D quads
- **base.frag**: Renders base patterns with three-color mixing (secondary on green, tertiary on blue channels)
- **design.frag**: Renders emblems with overlay blending for shading (blue channel at 0.7 strength)
- **basic.frag**: Simple texture rendering for frames

All shaders support:
- CoA mask (shield shape)
- Material mask (dirt/wear effects)
- Noise texture (grain)
- Screen-space coordinate mapping

## CK3 Format Specification

The editor supports CK3's coat of arms format:

```
coat_of_arms = {
    pattern = "pattern_solid.dds"
    color1 = rgb { 113 32 22 }
    color2 = rgb { 150 57 0 }
    color3 = rgb { 187 130 46 }
    
    colored_emblem = {
        texture = "ce_eagle.dds"
        color1 = red
        color2 = yellow
        color3 = white
        instance = {
            position = { 0.500000 0.500000 }
            scale = { 0.600000 0.600000 }
            depth = 1.000000
            rotation = 0
        }
    }
}
```

## Development

### Running Tests

```bash
# Run parser tests
python tests/test_coa_parser.py

# Run layer operation tests  
python tests/test_layer_copy_paste.py

# Run round-trip tests
python tests/test_roundtrip.py
```

### Adding New Features

1. **New Asset Type**: Add JSON metadata to `json_output/`, PNGs to `source_coa_files/`
2. **New Shader Effect**: Modify `.frag` files in `src/shaders/`
3. **New Transform Mode**: Extend `transform_widget.py` handle system
4. **New Export Format**: Add serializer to `utils/coa_parser.py`

### Debugging

- Shader compilation errors appear in console
- OpenGL errors logged during rendering
- History manager logs state changes
- Parser errors include line/column information

## Known Limitations

- Large numbers of layers (100+) may impact performance
- Some CK3 features not yet supported (charges, pattern divisions)
- Undo history limited to last 50 operations
- Windows only (Linux/Mac would require platform-specific builds)

## Disclaimer

This is a fan-made tool for the Crusader Kings 3 community. 

Crusader Kings III and all game assets are property of Paradox Interactive. Users must own CK3 to use this tool. This project is not affiliated with or endorsed by Paradox Interactive.
