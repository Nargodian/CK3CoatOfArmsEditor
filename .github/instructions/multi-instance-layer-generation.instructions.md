---
applyTo: 'editor/src/actions/**, editor/src/components/**'
---

# Multi-Instance Layer Generation

For implementation of the multi-instance layer generation feature (Generate menu).

## 🎯 Core Principles

1. **Single Popup Architecture**: One `GeneratorPopup` dialog swaps between pattern generator objects
2. **Preview First**: 300x300px QPainter preview (left) with properties panel (right)
3. **Pattern Categories**: Path-Based, Grid-Based, Vanilla Layouts, Miscellaneous
4. **NumPy Transform Arrays**: 5xN format `[[x, y, scale_x, scale_y, rotation], ...]`
5. **Paste System Integration**: Use existing paste infrastructure for layer creation (undo/redo)
6. **Text Mode Exception**: Multi-instance incompatible with text mode (creates multiple layers instead)

## ❌ Critical Don'ts

- No scatter pattern with overlap detection (too complex)
- No manual array building for positions (use generator methods)
- No OpenGL preview (use QPainter)
- No separate undo system (paste infrastructure handles it)

## 📋 Full Specification

See [docs/multi_instance_layer_generation.txt](../../docs/multi_instance_layer_generation.txt) for complete technical details, all pattern types, parameters, workflows, and implementation phases.
