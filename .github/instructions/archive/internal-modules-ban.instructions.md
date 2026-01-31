---
applyTo: '**'
---

# Ban on Direct Access to Internal Modules

## 🚨 CRITICAL RULE: models/coa/ is INTERNAL ONLY 🚨

**The entire `models/coa/` package is PRIVATE implementation for the CoA model.**

### Public API (allowed):
```python
# ✅ CORRECT - Import from models
from models.coa import CoA, Layer, Layers, LayerTracker
```

### Internal Implementation (FORBIDDEN):
```python
# ❌ FORBIDDEN - Everything in models/coa/ is internal
from models.coa.coa_parser import *           # INTERNAL - parser implementation
from models.coa.coa_serializer import *       # INTERNAL - serializer implementation
from models.coa.layer import *                # INTERNAL - layer data structures
from models.coa.query_mixin import *          # INTERNAL - query implementation
from models.coa.coa import *                  # INTERNAL - main CoA implementation

# OLD paths that no longer exist:
from utils.coa_parser import *                # REMOVED
from services.coa_serializer import *         # REMOVED
from utils._internal_clausewitz_parser import *   # REMOVED
from services._internal_coa_serializer import *   # REMOVED
```

## Architecture

```
models/
├── coa.py              ← PUBLIC: Import from here
├── __init__.py         ← PUBLIC: Exports CoA, Layer, Layers, LayerTracker
└── coa/                ← INTERNAL: Never import from here
    ├── coa.py          ← INTERNAL: CoA implementation
    ├── layer.py        ← INTERNAL: Layer classes
    ├── query_mixin.py  ← INTERNAL: Query methods
    ├── coa_parser.py   ← INTERNAL: Parsing logic
    └── coa_serializer.py ← INTERNAL: Serialization logic
```

**Rule**: If it's inside `models/coa/`, it's for the CoA's internal use ONLY.

## Why This Matters

- **`models/coa/coa_parser.py`**: Produces intermediate dicts that are immediately converted to Layer objects. Never exposed externally.

- **`models/coa/coa_serializer.py`**: Works with Layer objects and dicts directly. Bypasses CoA encapsulation if accessed directly.

- **`models/coa/layer.py`**: Internal data structures. External code should query through CoA methods.

- **`models/coa/query_mixin.py`**: Implementation detail of how CoA provides query methods.

## Required Approach

All parsing, serialization, and layer manipulation MUST go through CoA API methods:

### Parsing
```python
# ✅ CORRECT
coa = CoA.from_string(text)
coa = CoA.from_layers_string(text)
```

### Serialization
```python
# ✅ CORRECT
text = coa.to_string()
text = coa.serialize_layers_to_string([uuid1, uuid2])
```

### Layer Operations
```python
# ✅ CORRECT
new_uuids = target_coa.copy_layers_from_coa(source_coa, at_front=True)
new_uuid = coa.duplicate_layer(uuid)
```

## Enforcement

Any code that imports these internal modules directly violates the refactoring rules and must be refactored to use CoA methods instead.

The underscore prefix (`_internal_*`) signals that these are private implementation details.
