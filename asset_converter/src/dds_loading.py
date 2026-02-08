"""
DDS image loading utilities.

Loads DDS texture files using imageio and converts them to RGBA numpy arrays
for further processing by the atlas baking and conversion pipeline.
"""

from pathlib import Path
from typing import Optional

import numpy as np

try:
    import imageio
    import imageio.v3 as iio
    HAS_IMAGEIO = True
except ImportError:
    HAS_IMAGEIO = False


def load_dds_image(dds_path: Path) -> Optional[np.ndarray]:
    """Load DDS file and convert to RGBA numpy array.
    
    Args:
        dds_path: Path to the DDS file
        
    Returns:
        RGBA numpy array (h, w, 4) or None on failure
        
    Raises:
        ImportError: If imageio/imageio-dds are not installed
    """
    if not HAS_IMAGEIO:
        raise ImportError("imageio and imageio-dds are required for DDS loading")
    
    try:
        img_data = iio.imread(dds_path)
        
        if len(img_data.shape) == 2:
            # Grayscale
            h, w = img_data.shape
            rgba = np.zeros((h, w, 4), dtype=np.uint8)
            rgba[:, :, 0] = img_data
            rgba[:, :, 1] = img_data
            rgba[:, :, 2] = img_data
            rgba[:, :, 3] = 255
            return rgba
        elif img_data.shape[2] == 3:
            # RGB
            h, w = img_data.shape[:2]
            rgba = np.zeros((h, w, 4), dtype=np.uint8)
            rgba[:, :, :3] = img_data
            rgba[:, :, 3] = 255
            return rgba
        elif img_data.shape[2] == 4:
            # Already RGBA
            return img_data
        else:
            return None
            
    except Exception as e:
        print(f"ERROR loading DDS {dds_path}: {type(e).__name__}: {str(e)}")
        return None
