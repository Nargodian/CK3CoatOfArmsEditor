"""
CK3 Coat of Arms Editor - Data Models

This module contains the data model classes for CoA structure.
This is the MODEL in MVC architecture.

Public API: Import CoA, Layer, Layers, LayerTracker from models.coa
The models/_coa_internal/ subdirectory contains internal implementation only.
"""

# Import from coa.py file
from .coa import CoA, Layer, Layers
# LayerTracker is only in the internal package
from ._coa_internal.layer import LayerTracker

__all__ = ['CoA', 'Layer', 'Layers', 'LayerTracker']
