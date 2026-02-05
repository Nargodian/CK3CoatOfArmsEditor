"""
CoA Internal Package - DO NOT IMPORT FROM HERE

This package contains INTERNAL implementation for the CoA model:
- layer.py: Layer and Layers data structures
- query_mixin.py: Query methods mixin
- coa_parser.py: Parsing implementation
- coa_serializer.py: Serialization implementation

⚠️ FORBIDDEN: Do not import from models._coa_internal.* directly
✅ CORRECT: Import from models.coa (the public API)

Example:
    from models.coa import CoA, Layer, Layers, LayerTracker
"""

# This package is internal - do not populate __all__
# External code must use models.coa

