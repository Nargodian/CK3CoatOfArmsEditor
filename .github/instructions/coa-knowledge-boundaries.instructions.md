---
applyTo: 'editor/src/models/**'
---

# CoA Model Knowledge Boundaries

## CoA SHOULD Know (Model Data)
- Layer UUIDs and ordering
- Layer positions, scales, rotations (instance data)
- Layer colors (RGB values and color names)
- Flip states (flip_x, flip_y)
- Mask data (pattern mask channels)
- Instance counts and selected instance index
- Layer visibility state
- Texture filename (as stored data only)
- Serialization/deserialization of layer data
- Layer operations (add, remove, duplicate, move, reorder)
- Transform history state for undo/redo

## CoA SHOULD NOT Know (External Dependencies)
- How many color pickers to display (query metadata cache based on filename)
- Texture metadata (dimensions, actual color count from file)
- Asset file paths or directory structure
- UI state (which layer is selected in UI)
- Rendering details (how to draw on canvas)
- Thumbnail generation or caching
- How textures are loaded or decoded
- Mouse/keyboard interaction
- Window or widget layout
- Color picker dialogs