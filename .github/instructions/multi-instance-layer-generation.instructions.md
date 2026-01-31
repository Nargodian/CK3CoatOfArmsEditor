---
applyTo: '**'
---

# Multi-Instance Layer Generation

For implementation of the multi-instance layer generation feature (Generate menu).

SAVE BUIDLING AND TESTING EXPORTS FOR LATER. FOCUS ON CORE LOGIC FIRST.
WE DON'T NEED IT TO EXPORT LAYERS UNLESS THE USER CAN ACTUALLY CREATE THEM FIRST. 

DON'T RUN MAIN UNTILL ITS ALL DONE.

## 🎯 Core Principles

1. **Separate Module Structure**: Keep generators in their own organized structure, each generator in its own file. Don't bloat main.py.
2. **Single Popup Architecture**: One `GeneratorPopup` dialog swaps between pattern generator objects
3. **Preview First**: 300x300px QPainter preview (left) with properties panel (right)
4. **Pattern Categories**: Path-Based, Grid-Based, Vanilla Layouts, Miscellaneous
5. **NumPy Transform Arrays**: 5xN format `[[x, y, scale_x, scale_y, rotation], ...]`
6. **Paste System Integration**: Use existing paste infrastructure for layer creation (undo/redo)
7. **Text Mode Exception**: Multi-instance incompatible with text mode (creates multiple layers instead)

## ❌ Critical Don'ts

- No scatter pattern with overlap detection (too complex)
- No manual array building for positions (use generator methods)
- No OpenGL preview (use QPainter)
- No separate undo system (paste infrastructure handles it)

## 📋 Full Specification

See [docs/multi_instance_layer_generation.txt](../../docs/multi_instance_layer_generation.txt) for complete technical details, all pattern types, parameters, workflows, and implementation phases.

note this is a living document so if you've got to deviate from the spec for any reason please make a note of it in "multi_instance_layer_generation.txt"
