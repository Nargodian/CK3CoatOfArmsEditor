# Flip Reset Bug Analysis

## Problem Statement
When a layer has "Flip X" or "Flip Y" checked, performing ANY transform operation (translate, rotate, scale) causes the flip checkbox to become unchecked and the layer to flip back to normal orientation.

## Data Flow Analysis

### 1. Initial State - User Checks "Flip X"
```
User clicks "Flip X" checkbox
  ↓
flip_x_check.stateChanged signal emitted
  ↓
ScaleEditor.valueChanged.emit()
  ↓
PropertySidebar._update_layer_scale_and_widget()
  ↓
scale_x, scale_y = self.scale_editor.get_scale_values()
  - get_scale_values() applies negative sign if flip checked
  - Returns e.g. scale_x = -0.5 (was 0.5)
  ↓
layer['scale_x'] = scale_x  # Store -0.5 in layer
  ↓
CanvasArea.update_transform_widget_for_layer()
  ↓
transform_widget.set_transform(pos_x, pos_y, -0.5, scale_y, rotation)
  - Transform widget now has self.scale_x = -0.5
```

**State after flip checked:**
- Layer data: `scale_x = -0.5`
- Transform widget: `self.scale_x = -0.5`
- Flip X checkbox: CHECKED

### 2. User Starts Transform (e.g., Translation)
```
User drags center handle (translation)
  ↓
TransformWidget.mousePressEvent()
  ↓
self.drag_start_transform = (pos_x, pos_y, self.scale_x, self.scale_y, rotation)
  - Captures current values: (0.5, 0.5, -0.5, 0.5, 0)
  - NOTE: scale_x is correctly -0.5 here
```

### 3. During Drag - The Bug Location
```
TransformWidget.mouseMoveEvent()
  ↓
_handle_drag(current_pos)
  ↓
start_x, start_y, start_sx, start_sy, start_rot = self.drag_start_transform
  - start_sx = -0.5 (correct!)
  ↓
if self.active_handle == self.HANDLE_CENTER:
    # Translation - only modifies position
    self.pos_x = start_x + delta_x
    self.pos_y = start_y + delta_y
    # DOES NOT TOUCH self.scale_x or self.scale_y!
  ↓
# Scale clamping (my attempted fix)
scale_handles = [TL, TR, BL, BR, L, R, T, B]
if not multi_selection and active_handle in scale_handles:
    # This code DOESN'T RUN during translation
    sign_x = 1 if self.scale_x >= 0 else -1
    self.scale_x = sign_x * max(0.01, min(1.0, abs(self.scale_x)))
  ↓
# CRITICAL: Emit signal with CURRENT self.scale_x value
self.transformChanged.emit(self.pos_x, self.pos_y, self.scale_x, self.scale_y, self.rotation)
```

**KEY ISSUE**: During CENTER handle drag:
- `self.scale_x` is NEVER MODIFIED in the if block
- `self.scale_x` retains whatever value it had BEFORE the drag
- BUT WHAT VALUE DID IT HAVE?

### 4. The Root Cause - Previous Transform Widget Update

Looking at `CanvasArea._on_transform_changed()` line 271:
```python
self.property_sidebar._load_layer_properties()
```

This is called AFTER every transform change. Let's trace it:

```
CanvasArea._on_transform_changed(pos_x, pos_y, scale_x, scale_y, rotation)
  - Receives: scale_x = -0.5 (first time, correct)
  ↓
layer['scale_x'] = scale_x  # Update layer with -0.5
  ↓
self.property_sidebar._load_layer_properties()  # ← THE PROBLEM
  ↓
PropertySidebar._load_layer_properties():
    scale_x_raw = self.get_property_value('scale_x')  # Returns -0.5
    scale_y_raw = self.get_property_value('scale_y')  # Returns 0.5
    ↓
    scale_x = scale_x_raw or 0.5  # scale_x = -0.5 (correct)
    scale_y = scale_y_raw or 0.5  # scale_y = 0.5 (correct)
    ↓
    self.scale_editor.set_scale_values(scale_x, scale_y)
    ↓
ScaleEditor.set_scale_values(-0.5, 0.5):
    if scale_x < 0:
        self.flip_x_check.setChecked(True)  # ✓ Sets checked
        scale_x = abs(scale_x)  # scale_x becomes 0.5
    
    self.scale_x_slider.setValue(0.5)  # ✓ Slider shows 0.5
    ↓
PropertySidebar._load_layer_properties() continues:
    if self.canvas_area:
        self.canvas_area.update_transform_widget_for_layer()
        ↓
CanvasArea.update_transform_widget_for_layer():
    layer = self.property_sidebar.layers[idx]
    scale_x = layer.get('scale_x', 0.5)  # Gets -0.5 from layer
    ↓
    self.transform_widget.set_transform(pos_x, pos_y, -0.5, 0.5, rotation)
    ↓
TransformWidget.set_transform():
    self.scale_x = -0.5  # ✓ CORRECTLY SET
```

**SO FAR SO GOOD!** After the first transform change, the transform widget has `self.scale_x = -0.5` correctly.

### 5. The Second Transform - Where It Breaks

**Hypothesis**: The bug happens on the SECOND transform change, not the first.

When user drags again:
```
TransformWidget.mousePressEvent()
  ↓
self.drag_start_transform = (pos_x, pos_y, self.scale_x, self.scale_y, rotation)
  - Should be: (new_pos, new_pos, -0.5, 0.5, rotation)
```

**WAIT!** Let me check if there's an issue with how `_load_layer_properties` updates the transform widget...

Actually, looking more carefully at the flow:

```
_on_transform_changed() called during drag
  ↓
Updates layer['scale_x'] = scale_x  # From transform widget emission
  ↓
Calls _load_layer_properties()
  ↓
Reads layer, calls set_scale_values(-0.5, 0.5)
  ↓
set_scale_values() sets flip checkbox checked, slider to 0.5
  ↓
Calls update_transform_widget_for_layer()
  ↓
Reads layer, calls set_transform(..., -0.5, 0.5, ...)
  ↓
Transform widget self.scale_x = -0.5
```

This creates a LOOP during the drag! Every mousemove calls `_on_transform_changed` which calls `_load_layer_properties` which calls `update_transform_widget_for_layer` which resets `self.scale_x`!

### 6. The REAL Bug

**During an active drag**, `_on_transform_changed` is being called repeatedly. Each call:
1. Updates the layer
2. Calls `_load_layer_properties()`
3. Which calls `update_transform_widget_for_layer()`
4. Which calls `transform_widget.set_transform()`
5. **Which OVERWRITES `self.scale_x` with the layer value**

BUT the transform widget is IN THE MIDDLE OF A DRAG! It has `drag_start_transform` saved with the values from `mousePressEvent`. When the drag continues, it uses values from `drag_start_transform`, not from `self.scale_x`!

NO WAIT. Let me re-read `_handle_drag`:

```python
start_x, start_y, start_sx, start_sy, start_rot = self.drag_start_transform

if self.active_handle == self.HANDLE_CENTER:
    self.pos_x = start_x + delta_x
    self.pos_y = start_y + delta_y
    # Does NOT touch self.scale_x
```

So during CENTER drag:
- `self.scale_x` is not modified
- `drag_start_transform[2]` (start_sx) is -0.5
- `self.scale_x` should still be -0.5 (not modified)

Then we emit:
```python
self.transformChanged.emit(self.pos_x, self.pos_y, self.scale_x, self.scale_y, self.rotation)
```

This should emit -0.5 because `self.scale_x` wasn't changed!

**UNLESS** `update_transform_widget_for_layer()` was called DURING the drag and changed `self.scale_x`!

Let me check if that's happening...

Actually, I think the issue is:
1. During drag, `_on_transform_changed` is called
2. It calls `_load_layer_properties()`  
3. Which reads the layer and sees scale_x = -0.5
4. Calls `set_scale_values(-0.5, 0.5)`
5. This sets the flip checkbox CHECKED (correct)
6. Then calls `update_transform_widget_for_layer()`
7. Which calls `set_transform(..., -0.5, ...)`

**But wait!** `set_transform` is being called DURING an active drag! This overwrites `self.scale_x`!

NO - actually `set_transform` should only set `self.scale_x`, it doesn't affect `drag_start_transform`. So the next mousemove should still use the correct `start_sx` from `drag_start_transform`.

Let me look at what happens to the checkbox visibility...

OH! I just realized - maybe the checkbox is being VISUALLY updated correctly (shows checked), but the actual LAYER value is being reset to positive?

Let me check `set_scale_values` more carefully:

```python
def set_scale_values(self, scale_x, scale_y):
    self.flip_x_check.blockSignals(True)
    
    if scale_x < 0:
        self.flip_x_check.setChecked(True)
        scale_x = abs(scale_x)  # ← Makes scale_x positive for slider
    else:
        self.flip_x_check.setChecked(False)  # ← UNCHECKS if positive!
    
    self.scale_x_slider.setValue(scale_x)  # Sets slider to positive value
    
    self.flip_x_check.blockSignals(False)
```

So if `set_scale_values` receives a POSITIVE value, it UNCHECKS the flip checkbox!

The question is: why would it receive a positive value during a drag when the layer has a negative value?

## Solution Approaches

### Option 1: Don't call _load_layer_properties during active drag
```python
def _on_transform_changed(self, pos_x, pos_y, scale_x, scale_y, rotation):
    # Update layer data
    layer['scale_x'] = scale_x
    layer['scale_y'] = scale_y
    # ...
    
    # Don't reload properties during drag - causes feedback loop
    # self.property_sidebar._load_layer_properties()
```

Call it only in `_on_transform_ended()` instead.

### Option 2: Block signals/updates during transform widget drag
Add a flag to prevent property reload during active drag.

### Option 3: Make set_scale_values preserve checkbox state
```python
def set_scale_values(self, scale_x, scale_y, preserve_flip=False):
    if preserve_flip:
        # Don't modify flip checkboxes, just update sliders
        self.scale_x_slider.setValue(abs(scale_x))
        self.scale_y_slider.setValue(abs(scale_y))
    else:
        # Normal behavior
        ...
```

## Layer Preview Icon Calculation

For dynamically colored layer preview thumbnails in the layer list:

### Requirements
- 64x64 or 128x128 thumbnail size
- Show the actual emblem/pattern texture
- Apply the layer's specific colors
- Update when colors change

### Implementation Approach

```python
def generate_layer_thumbnail(layer_data, size=64):
    """
    Generate a colored thumbnail for a layer.
    
    Args:
        layer_data: Dict with 'filename', 'color1', 'color2', 'color3'
        size: Thumbnail size (square)
    
    Returns:
        QPixmap thumbnail
    """
    filename = layer_data.get('filename', '')
    
    # Get colors from layer (already in 0-1 range)
    colors = {
        'color1': tuple(layer_data.get('color1', [0.75, 0.525, 0.188])),
        'color2': tuple(layer_data.get('color2', [0.45, 0.133, 0.090])),
        'color3': tuple(layer_data.get('color3', [0.45, 0.133, 0.090])),
        'background1': (0.5, 0.5, 0.5)  # Gray background for thumbnail
    }
    
    # Try atlas compositor first
    atlas_path = get_atlas_path(filename, 'emblem')
    if atlas_path.exists():
        return composite_emblem_atlas(str(atlas_path), colors, size=size)
    
    # Fallback to static preview
    from constants import ASSET_PREVIEW_PATH
    preview_path = ASSET_PREVIEW_PATH / filename.replace('.dds', '.png')
    if preview_path.exists():
        pixmap = QPixmap(str(preview_path))
        return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    
    # Ultimate fallback - placeholder
    placeholder = QPixmap(size, size)
    placeholder.fill(Qt.gray)
    return placeholder
```

### Integration Points

1. **LayerListWidget** - Update item creation:
```python
def _create_layer_item(self, layer_data, index):
    item = QListWidgetItem()
    
    # Generate thumbnail
    thumbnail = generate_layer_thumbnail(layer_data, size=48)
    item.setIcon(QIcon(thumbnail))
    
    # Layer name
    filename = layer_data.get('filename', 'Unknown')
    item.setText(f"{index}: {filename}")
    
    return item
```

2. **Color Change Handler** - Regenerate thumbnails:
```python
def _on_layer_color_changed(self, color_index, new_color):
    # ... existing code to update layer ...
    
    # Regenerate thumbnail for affected layers
    selected_indices = self.get_selected_indices()
    for idx in selected_indices:
        self._update_layer_thumbnail(idx)
```

3. **Thumbnail Update Method**:
```python
def _update_layer_thumbnail(self, layer_index):
    """Regenerate and update thumbnail for a specific layer"""
    if layer_index < 0 or layer_index >= len(self.layers):
        return
    
    layer = self.layers[layer_index]
    thumbnail = generate_layer_thumbnail(layer, size=48)
    
    # Find corresponding list item
    item = self.layer_list_widget.item(layer_index)
    if item:
        item.setIcon(QIcon(thumbnail))
```

### Performance Considerations

- **Caching**: Store generated thumbnails to avoid regeneration
```python
self.thumbnail_cache = {}  # layer_index -> QPixmap

def _get_layer_thumbnail(self, layer_index):
    if layer_index not in self.thumbnail_cache:
        self.thumbnail_cache[layer_index] = generate_layer_thumbnail(self.layers[layer_index])
    return self.thumbnail_cache[layer_index]

def _invalidate_thumbnail_cache(self, layer_index):
    self.thumbnail_cache.pop(layer_index, None)
```

- **Lazy Loading**: Only generate thumbnails for visible items
- **Background Threading**: Generate thumbnails in QThread for large layer counts

### Color Extraction Helper

```python
def extract_layer_colors(layer_data):
    """Extract color tuple dict from layer data"""
    return {
        'color1': tuple(layer_data.get('color1', [0.75, 0.525, 0.188])),
        'color2': tuple(layer_data.get('color2', [0.45, 0.133, 0.090])),
        'color3': tuple(layer_data.get('color3', [0.45, 0.133, 0.090])),
        'background1': (0.5, 0.5, 0.5)
    }
```

This creates a consistent interface between layer data storage and the compositor API.
