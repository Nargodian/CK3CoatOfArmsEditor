# Model Integration Plan

**Status:** IN PROGRESS - Step 1 Complete ✅  
**Goal:** Replace old layer_data dictionaries with new Layer/CoA model objects  
**Strategy:** Clean, document, integrate incrementally with verification at each step

---

## Progress Tracker

- ✅ **Step 1: MainWindow Initialization** - CoA instance created (Jan 29, 2026)
- ✅ **Step 2: File Operations** - Save/load using CoA.to_string()/from_string() (Jan 29, 2026)
- ✅ **Step 3: Layer List Widget** - CoA reference passed to widgets (Jan 29, 2026)
- ✅ **Step 4: Property Sidebar** - CoA reference passed (Jan 29, 2026)
- ✅ **Step 5: Canvas Area & Widget** - CoA references wired (Jan 29, 2026)
- 🔄 **Step 6: Menu Actions** - Next
- ⬜ Step 7: Undo/Redo System
- ⬜ Step 8: Test Basic Operations
- ⬜ Step 9: Cleanup - Remove Old System
- ⬜ Step 10: Integration Testing

**Integration Breadcrumbs:** Search for `#COA INTEGRATION ACTION:` comments in code to trace changes

**Note:** Steps 4-5 combined - all component references now wired to CoA model

---

## Integration Philosophy

**"Disinfect before treating"** - Your gut instinct is correct:
1. Identify old code to remove
2. Add clear TODO comments at integration points
3. Integrate new model systematically
4. Verify at each step before moving to next

---

## Phase 1: Mapping Old → New

### Old System (What Gets Removed)

**Data Storage:**
- `editor/src/services/layer_operations.py` - Dict manipulation functions
- All `layer_data` dict access patterns throughout codebase
- Manual UUID tracking in various places
- Scattered instance management logic

**Key Old Functions to Replace:**
```python
# layer_operations.py
def create_layer(emblem_path, pos_x, pos_y, ...)  # → CoA.add_layer()
def update_layer_property(layer_id, property, value)  # → layer.property = value
def get_layer_property(layer_id, property)  # → layer.property
def delete_layer(layer_id)  # → CoA.remove_layer()
def move_layer(from_idx, to_idx)  # → CoA.move_layer()
def duplicate_layer(layer_id)  # → CoA.duplicate_layer()
```

**Integration Points (Where UI Connects):**
- `editor/src/main.py` - MainWindow methods that manipulate layers
- `editor/src/components/property_sidebar.py` - Property editors read/write
- `editor/src/components/canvas_area.py` - Canvas transforms and rendering
- `editor/src/components/canvas_widget.py` - OpenGL rendering (reads layer data)
- `editor/src/services/file_operations.py` - Save/load (already partially done)

### New System (What We're Integrating)

**Model Layer:**
- `editor/src/models/layer.py` - Layer, Layers, LayerTracker classes
- `editor/src/models/coa.py` - CoA class (the MODEL in MVC)
- `editor/src/models/__init__.py` - Module exports

**Key New API:**
```python
# CoA instance becomes the single source of truth
self.coa = CoA()  # In MainWindow

# Layer operations
uuid = self.coa.add_layer(emblem_path="lion.dds", pos_x=0.5, pos_y=0.5)
self.coa.remove_layer(uuid)
self.coa.duplicate_layer(uuid)
self.coa.move_layer(uuid, 3)  # Move to position 3

# Transform operations
self.coa.translate_layer(uuid, delta_x=0.1, delta_y=0.2)
self.coa.rotate_layer(uuid, delta_degrees=15.0)
self.coa.scale_layer(uuid, factor_x=1.2, factor_y=1.2)
self.coa.flip_layer(uuid, flip_x=True, flip_y=False)

# Group operations (multi-selection)
self.coa.rotate_selection(uuids, angle=45.0, mode='both')
self.coa.merge_layers(uuids)
split_uuids = self.coa.split_layer(uuid)

# Property access
layer = self.coa._layers[index]  # Get Layer object
pos_x = layer.pos_x  # Read property
layer.pos_x = 0.5  # Write property

# Queries
count = self.coa.get_layer_count()
all_uuids = self.coa.get_all_layer_uuids()
top_uuid = self.coa.get_top_layer_uuid()
bounds = self.coa.get_layer_bounds(uuid)

# Serialization
ck3_text = self.coa.to_string()  # Export
new_coa = CoA.from_string(ck3_text)  # Import

# Undo/Redo
snapshot = self.coa.get_snapshot()  # Save state
self.coa.set_snapshot(snapshot)  # Restore state
```

---

## Phase 2: Integration Steps (Incremental)

### Step 1: MainWindow Initialization ✅ (Preparation)
**Goal:** Add CoA model instance to MainWindow, keep old system running

**Files:**
- `editor/src/main.py`

**Changes:**
```python
from models.coa import CoA

class MainWindow:
    def __init__(self):
        # OLD: self.layers = []
        self.coa = CoA()  # NEW MODEL
        # Keep old self.layers for now (parallel systems)
```

**Verification:** App starts, both systems exist

---

### Step 2: File Operations (Save/Load) 🔄 (In Progress)
**Goal:** Use CoA.from_string() and to_string() for all file I/O

**Files:**
- `editor/src/services/file_operations.py`

**Current State:**
- Already uses mature CoAParser/CoASerializer
- Need to switch to CoA model methods

**Changes:**
```python
def load_coa_file(filepath):
    # OLD: parsed = CoAParser.parse_string(text)
    #      return build layers from parsed dict
    
    # NEW:
    with open(filepath) as f:
        coa = CoA.from_string(f.read())
    return coa

def save_coa_file(coa, filepath):
    # OLD: serialized = CoASerializer.serialize(layer_dicts)
    
    # NEW:
    ck3_text = coa.to_string()
    with open(filepath, 'w') as f:
        f.write(ck3_text)
```

**Verification:** Load sample files, save, reload - verify identical

---

### Step 3: Layer List Widget 📋 (Next Up)
**Goal:** Layer list displays CoA layers, selection works

**Files:**
- `editor/src/components/property_sidebar_widgets/layer_list_widget.py`

**OLD Code Pattern:**
```python
# Builds list from self.layers dict list
for i, layer_data in enumerate(self.layers):
    item_text = layer_data.get('filename', 'Unknown')
```

**NEW Code Pattern:**
```python
# Builds list from CoA model
for i in range(self.coa.get_layer_count()):
    layer = self.coa._layers[i]
    item_text = layer.filename
    # Add instance badge if multi-instance
    if layer.instance_count > 1:
        item_text += f" ×{layer.instance_count}"
```

**TODOs to Add:**
- [ ] Replace layer_data loop with CoA iteration
- [ ] Add instance count badge display
- [ ] Update selection handling to use UUIDs
- [ ] Add hover tooltips for multi-instance layers

**Verification:** 
- Layer list displays correctly
- Selection syncs with canvas
- Instance badges show for multi-instance layers

---

### Step 4: Property Sidebar 🎛️
**Goal:** Property editors read/write Layer properties via CoA

**Files:**
- `editor/src/components/property_sidebar.py`

**OLD Code Pattern:**
```python
# Direct dict manipulation
self.layers[selected_index]['pos_x'] = new_value
value = self.layers[selected_index].get('pos_x', 0.5)
```

**NEW Code Pattern:**
```python
# Property access via Layer object
selected_uuid = self.get_selected_layer_uuid()
layer = self.coa._layers.get_layer_by_uuid(selected_uuid)
layer.pos_x = new_value  # Setter with validation
value = layer.pos_x  # Getter
```

**TODOs to Add:**
- [ ] Replace dict access with Layer properties
- [ ] Add instance selector (for multi-instance layers)
- [ ] Update mask checkboxes to use layer.mask
- [ ] Update color swatches to use layer.color1/2/3
- [ ] Add "Instance 1 of 3" label for multi-instance

**Verification:**
- Property changes update model
- UI reflects current layer state
- Multi-instance layers show instance info

---

### Step 5: Canvas Area (Transform Logic) 🖱️
**Goal:** Canvas transforms call CoA methods instead of direct dict manipulation

**Files:**
- `editor/src/components/canvas_area.py`

**OLD Code Pattern:**
```python
# Direct dict manipulation in mouse handlers
self.layers[layer_id]['pos_x'] += delta_x
self.layers[layer_id]['rotation'] += delta_angle
```

**NEW Code Pattern:**
```python
# Call CoA transform methods
if len(selected_uuids) == 1:
    self.coa.translate_layer(selected_uuids[0], delta_x, delta_y)
    self.coa.rotate_layer(selected_uuids[0], delta_angle)
else:
    # Multi-selection group transform
    self.coa.rotate_selection(selected_uuids, delta_angle, mode=self.rotation_mode)
```

**TODOs to Add:**
- [ ] Replace transform dict updates with CoA.translate_layer()
- [ ] Replace rotation dict updates with CoA.rotate_layer()
- [ ] Replace scale dict updates with CoA.scale_layer()
- [ ] Use CoA.rotate_selection() for group rotations
- [ ] Add rotation mode selector dropdown
- [ ] Update bounds calculation to use CoA.get_layer_bounds()

**Verification:**
- Dragging layers updates positions correctly
- Rotation handles work (single and multi-selection)
- Scale handles work
- Group rotation modes work correctly

---

### Step 6: Canvas Widget (OpenGL Rendering) 🎨
**Goal:** OpenGL rendering reads from Layer objects instead of dicts

**Files:**
- `editor/src/components/canvas_widget.py`

**OLD Code Pattern:**
```python
for layer_data in self.layers:
    pos_x = layer_data.get('pos_x', 0.5)
    pos_y = layer_data.get('pos_y', 0.5)
    # ... render with transform
```

**NEW Code Pattern:**
```python
for layer in self.coa._layers:
    for instance_idx in range(layer.instance_count):
        inst = layer.get_instance(instance_idx)
        pos_x = inst['pos_x']
        pos_y = inst['pos_y']
        # ... render instance with transform
        # Apply mask if layer.mask is not None
```

**TODOs to Add:**
- [ ] Replace layer_data loop with Layer iteration
- [ ] Add instance loop for multi-instance layers
- [ ] Use layer.get_instance() for transform data
- [ ] Use layer.mask for pattern mask uniform
- [ ] Use layer.color1/2/3 for emblem colors

**Verification:**
- All layers render correctly
- Multi-instance layers show all instances
- Pattern masks work
- Colors display correctly

---

### Step 7: Menu Actions (Layer Operations) 📋
**Goal:** Menu commands use CoA operations

**Files:**
- `editor/src/main.py` (menu action handlers)

**OLD Code Pattern:**
```python
def on_add_layer(self):
    new_layer = create_layer(...)  # layer_operations.py
    self.layers.append(new_layer)
```

**NEW Code Pattern:**
```python
def on_add_layer(self):
    uuid = self.coa.add_layer(emblem_path=selected_emblem)
    self.update_ui()
    
def on_delete_layer(self):
    selected_uuids = self.get_selected_layer_uuids()
    for uuid in selected_uuids:
        self.coa.remove_layer(uuid)
    self.update_ui()
    
def on_duplicate_layer(self):
    selected_uuid = self.get_selected_layer_uuid()
    new_uuid = self.coa.duplicate_layer(selected_uuid)
    self.select_layer(new_uuid)
    self.update_ui()

def on_merge_layers(self):
    selected_uuids = self.get_selected_layer_uuids()
    if len(selected_uuids) >= 2:
        merged_uuid = self.coa.merge_layers(selected_uuids)
        self.select_layer(merged_uuid)
        self.update_ui()

def on_split_layer(self):
    selected_uuid = self.get_selected_layer_uuid()
    split_uuids = self.coa.split_layer(selected_uuid)
    self.select_layers(split_uuids)
    self.update_ui()
```

**TODOs to Add:**
- [ ] Replace add layer logic with CoA.add_layer()
- [ ] Replace delete with CoA.remove_layer()
- [ ] Replace duplicate with CoA.duplicate_layer()
- [ ] Replace move up/down with CoA.move_layer()
- [ ] Add merge menu action (Layers → Merge as Instances)
- [ ] Add split menu action (Layers → Split Instances)
- [ ] Add rotation mode selector to UI

**Verification:**
- Add layer creates layer
- Delete removes layer
- Duplicate copies all instances
- Move up/down reorders
- Merge combines compatible layers
- Split separates instances

---

### Step 8: Undo/Redo System 🔄
**Goal:** Undo/redo uses CoA snapshots

**Files:**
- `editor/src/main.py` (undo stack management)

**OLD Code Pattern:**
```python
# Deep copy layer list for undo
self.undo_stack.append(copy.deepcopy(self.layers))
```

**NEW Code Pattern:**
```python
# Snapshot-based undo
def push_undo(self):
    snapshot = self.coa.get_snapshot()
    self.undo_stack.append(snapshot)

def undo(self):
    if self.undo_stack:
        # Save current state to redo
        self.redo_stack.append(self.coa.get_snapshot())
        # Restore previous state
        snapshot = self.undo_stack.pop()
        self.coa.set_snapshot(snapshot)
        self.update_ui()
```

**TODOs to Add:**
- [ ] Replace deepcopy with CoA.get_snapshot()
- [ ] Replace list restoration with CoA.set_snapshot()
- [ ] Call push_undo() before all operations
- [ ] Implement redo with snapshot stack

**Verification:**
- Undo restores previous state
- Redo works correctly
- Multi-step undo works
- Snapshots preserve all layer data

---

### Step 9: Cleanup - Remove Old System 🧹
**Goal:** Delete old layer_operations.py and dict-based code

**Files to Remove/Gut:**
- `editor/src/services/layer_operations.py` - Entire file
- Old dict manipulation scattered throughout

**Search Patterns to Find:**
```python
# Find and replace these patterns:
layer_data['pos_x']  # → layer.pos_x
layer_data.get('filename')  # → layer.filename
self.layers[index]  # → self.coa._layers[index]
create_layer(...)  # → self.coa.add_layer(...)
update_layer_property(...)  # → layer.property = value
```

**TODOs to Add:**
- [ ] Search for all "layer_data[" occurrences
- [ ] Search for all "layer_operations." imports
- [ ] Remove layer_operations.py
- [ ] Remove old migration code if present
- [ ] Clean up any parallel systems still running

**Verification:**
- No references to old layer_operations functions
- No dict-style layer access
- App runs with only model layer

---

### Step 10: Integration Testing 🧪
**Goal:** Verify complete system works end-to-end

**Test Scenarios:**
1. **File Round Trip:**
   - Load coa_sample_2.txt (6 layers, multi-instance)
   - Modify layers (move, rotate, recolor)
   - Save to new file
   - Reload and verify identical

2. **Multi-Instance Workflow:**
   - Create 3 single-instance cross layers
   - Merge into cross×3 layer
   - Transform group (rotate, scale)
   - Split back to 3 layers
   - Verify positions preserved

3. **Undo/Redo:**
   - Perform 10 operations
   - Undo all 10
   - Verify back to start state
   - Redo all 10
   - Verify end state matches

4. **Complex Operations:**
   - Load file with 5+ layers
   - Duplicate multi-instance layer
   - Delete some layers
   - Reorder remaining
   - Change colors and masks
   - Save and reload

**Verification Checklist:**
- [ ] All game samples load correctly
- [ ] Round-trip serialization preserves data
- [ ] Multi-instance layers display and transform
- [ ] Undo/redo works for all operations
- [ ] Performance acceptable (no lag)

---

## Phase 3: Reference Documents

### Files Touched (Complete List)

**Modified:**
- `editor/src/main.py` - MainWindow, menu actions, undo/redo
- `editor/src/components/property_sidebar.py` - Property editors
- `editor/src/components/property_sidebar_widgets/layer_list_widget.py` - Layer list
- `editor/src/components/canvas_area.py` - Transform logic
- `editor/src/components/canvas_widget.py` - OpenGL rendering
- `editor/src/services/file_operations.py` - Save/load (partially done)

**Removed:**
- `editor/src/services/layer_operations.py` - Delete entire file

**Added:**
- `editor/src/models/__init__.py` - Already exists ✅
- `editor/src/models/layer.py` - Already exists ✅
- `editor/src/models/coa.py` - Already exists ✅

### API Quick Reference

**Layer Properties (read/write):**
- `layer.pos_x`, `layer.pos_y` - Position (per-instance)
- `layer.scale_x`, `layer.scale_y` - Scale (per-instance)
- `layer.rotation` - Rotation in degrees (per-instance)
- `layer.depth` - Depth (per-instance)
- `layer.filename` - Texture filename (shared)
- `layer.color1`, `layer.color2`, `layer.color3` - RGB colors (shared)
- `layer.color1_name`, etc. - Named color strings (shared)
- `layer.mask` - Pattern mask [r, g, b] or None (shared)
- `layer.flip_x`, `layer.flip_y` - Flip flags (shared)
- `layer.uuid` - Unique identifier (read-only)
- `layer.instance_count` - Number of instances (read-only)

**CoA Methods:**
- `add_layer()`, `remove_layer()`, `duplicate_layer()`, `move_layer()`
- `translate_layer()`, `rotate_layer()`, `scale_layer()`, `flip_layer()`
- `add_instance()`, `remove_instance()`, `select_instance()`
- `merge_layers()`, `split_layer()`
- `rotate_selection()` - Group rotation with 6 modes
- `get_layer_count()`, `get_all_layer_uuids()`, `get_top_layer_uuid()`
- `get_layer_bounds()`, `get_layers_bounds()`
- `to_string()`, `from_string()` - Serialization
- `get_snapshot()`, `set_snapshot()` - Undo/redo

---

## Phase 4: Integration Workflow

### Recommended Order

1. **Step 1 (Initialization)** - Add CoA to MainWindow ← START HERE
2. **Step 2 (File I/O)** - Use CoA serialization
3. **Step 3 (Layer List)** - Display from CoA
4. **Step 4 (Properties)** - Read/write Layer properties
5. **Step 5 (Canvas Logic)** - Call CoA transforms
6. **Step 6 (Rendering)** - Read Layer data for OpenGL
7. **Step 7 (Menu Actions)** - Use CoA operations
8. **Step 8 (Undo/Redo)** - Snapshot-based
9. **Step 9 (Cleanup)** - Remove old code
10. **Step 10 (Testing)** - End-to-end verification

### Verification Strategy

After each step:
1. Run the app
2. Test the modified functionality
3. Verify old functionality still works
4. Run unit tests
5. Commit if stable

### Rollback Plan

- Each step committed separately
- If integration fails, revert last commit
- Fix issues before proceeding to next step

---

## Notes for Copilot

**When doing integration:**
- Always show full context (before/after code)
- Mark removed code clearly with comments
- Add TODO comments for future work
- Preserve existing functionality during transition
- Test incrementally, don't skip verification steps

**Communication pattern:**
- "Step 3: Integrating layer list widget"
- Show old code being removed
- Show new code being added
- Explain what changed and why
- List verification steps

**If problems arise:**
- Stop and document the issue
- Don't proceed to next step until resolved
- Ask user if unsure about approach
- Can always revert to previous commit

---

## Current Status

**Completed:**
- ✅ Model layer (Layer, CoA classes) - 2521 lines
- ✅ Unit tests (69 tests, all passing)
- ✅ Serialization (from_string, to_string)
- ✅ Documentation (this plan)

**Next Up:**
- 🔄 Step 1: Add CoA instance to MainWindow

**Blocked:**
- None currently

**Questions:**
- None currently

---

**Last Updated:** January 29, 2026  
**Maintained By:** Integration Team
