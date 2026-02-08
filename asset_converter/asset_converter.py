#!/usr/bin/env python3
"""
CK3 Coat of Arms Asset Converter - Entry Point

Launches the asset converter GUI. All implementation lives in the src/ package.
"""

import sys
import os

# Add parent directory to path so 'src' package is importable when run directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.gui import main


if __name__ == '__main__':
    main()
