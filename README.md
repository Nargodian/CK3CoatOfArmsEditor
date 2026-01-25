# CK3 Coat of Arms Editor

A desktop application for creating and editing coat of arms for Crusader Kings 3 (CK3). Built with Python, PyQt5, and OpenGL for real-time rendering of heraldic designs.

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

## Requirements

- Python 3.10+
- PyQt5
- PyOpenGL
- NumPy
- Pillow (PIL)

## Installation

```bash
# Clone repository
git clone <repository-url>
cd CK3CoatOfArmsEditor

# Install dependencies
pip install -r requirements.txt

# Run the editor (development mode)
python editor/src/main.py

# Or run the asset converter
python asset_converter/asset_converter.py
```

## Building for Distribution

```bash
# Build both executables
cd build
build.bat

# Find built executables in dist/merged/
```

See [PACKAGING.md](PACKAGING.md) for complete build and distribution instructions.

## Project Structure

The project follows a modular architecture with separate editor and asset converter projects:

```
CK3CoatOfArmsEditor/
├── editor/                          # Main editor project
│   ├── src/
│   │   ├── main.py                 # Main application window
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
│   └── specifications/            # Format specifications
├── examples/                       # Example CoA files
├── samples/                        # Sample designs
├── tests/                          # Unit tests
│   ├── test_coa_parser.py        # Parser tests
│   ├── test_layer_copy_paste.py  # Layer operations tests
│   └── test_roundtrip.py         # Import/export tests
├── requirements.txt               # Python dependencies
├── PACKAGING.md                   # Build & distribution guide
└── README.md                      # This file
```

## Architecture Overview

### Main Window (`main.py`)
- Application orchestration and menu handling
- File operations (open, save, import, export)
- Undo/redo management
- Connects UI components and manages state

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

## Refactoring History

This project underwent comprehensive refactoring in 2026:

- **Phase 1-2**: Extract utilities and services
- **Phase 3-4**: Modularize components and widgets
- **Phase 5**: Optimize rendering and texture systems
- **Phase 6**: Cleanup and documentation
- **Phase 7**: Utils cleanup and test organization

The refactoring reduced code duplication, improved maintainability, and established clear separation of concerns between UI, rendering, and business logic.

## Known Issues

- Large numbers of layers (100+) may impact performance
- Some CK3 coat of arms features not yet supported (charges, divisions)
- Undo history limited to last 100 operations

## Future Enhancements

- [ ] Support for CK3 charge system
- [ ] Pattern divisions (quartered, halved, etc.)
- [ ] Batch export for multiple designs
- [ ] Preset library for common designs
- [ ] Real-time collaboration features

## License

[Add your license here]

## Credits

Created for the Crusader Kings 3 modding community.

CK3 is a trademark of Paradox Interactive. This tool is not affiliated with or endorsed by Paradox Interactive.
