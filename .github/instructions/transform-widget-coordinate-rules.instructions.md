---
applyTo: 'editor/src/components/transform_widget.py'
---

# Transform Widget Coordinate Rules

## Critical Balance Rule

**Any adjustment to the widget's input (display position) MUST be compensated in the output (transform values).**

The transform widget is sensitive to coordinate alterations. If you shift its display without correctly unshifting its output, you create divergence that will be interpreted as a transformation action, causing jumps and instability.

**CRITICAL:** Any adjustment made to the widget's **input** (display position, handle detection) must be compensated in the widget's **output** (transformed coordinates sent to model).

The system is sensitive to alterations. If you shift the widget's display without correctly unshifting its output, it creates a divergence that will be interpreted as a transform action, causing jumps and instability.


## Frame Offset System
- Frames have scale (0.85-1.0) and offset (X: 0, Y: -0.04 to 0.11)
- **Offset is applied in the composite shader** via `coaUV -= coaOffset`
- Positive offset.y **subtracts from UV**, moving content **UP** visually
- Widget must match this visual shift


The shader renders emblems at their true CoA positions, then shifts the **entire composite texture** using the frame offset. The widget must appear at this shifted position (input adjustment), but when the user drags, we must convert their mouse movement back to the unshifted CoA coordinate space (output compensation). This maintains the invariant that widget position values always represent true CoA coordinates (0-1 range), while the display position matches the visually shifted rendering.
