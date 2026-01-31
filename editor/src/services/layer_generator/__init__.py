"""Layer generation service for creating multi-instance layers.

This service provides pattern-based generation of layers with multiple instances
arranged according to various procedural and preset patterns.
"""

from .base_generator import BaseGenerator
from .generator_popup import GeneratorPopup, PreviewWidget
from .path_sampler import PathSampler

__all__ = [
    'BaseGenerator',
    'GeneratorPopup',
    'PreviewWidget',
    'PathSampler',
]
