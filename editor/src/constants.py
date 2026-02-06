"""
CK3 Coat of Arms Editor - Constants and Configuration

This module contains all constant values used throughout the application:
- CK3 named colors (official palette)
- Default emblem/layer settings
- Min/max values and constraints
- Rendering constants for shaders and canvas
- Coordinate system definitions

Based on: docs/specifications/coat_of_arms_format_specifics.txt
"""

# ======================================================================
# CK3 NAMED COLORS (OFFICIAL PALETTE)
# ======================================================================
# Colors are listed in the order they appear in CK3's color picker UI
# Source: game/common/named_colors/default_colors.txt (HSV → RGB conversion)

CK3_NAMED_COLORS = {
    'red':          {'rgb': [0.450, 0.133, 0.090], 'hex': '#732217'},
    'red_dark':     {'rgb': [0.300, 0.030, 0.030], 'hex': '#4D0808'},
    'orange':       {'rgb': [0.600, 0.230, 0.000], 'hex': '#993B00'},
    'yellow':       {'rgb': [0.750, 0.525, 0.188], 'hex': '#BF8630'},
    'yellow_light': {'rgb': [1.000, 0.680, 0.200], 'hex': '#FFAD33'},
    'white':        {'rgb': [0.800, 0.792, 0.784], 'hex': '#CCCAC8'},
    'grey':         {'rgb': [0.500, 0.500, 0.500], 'hex': '#808080'},
    'black':        {'rgb': [0.100, 0.090, 0.075], 'hex': '#19170E'},
    'brown':        {'rgb': [0.450, 0.234, 0.117], 'hex': '#733C1E'},
    'green':        {'rgb': [0.120, 0.300, 0.138], 'hex': '#1F4D23'},
    'green_light':  {'rgb': [0.200, 0.400, 0.220], 'hex': '#336638'},
    'blue_light':   {'rgb': [0.165, 0.365, 0.550], 'hex': '#2A5D8C'},
    'blue':         {'rgb': [0.080, 0.246, 0.400], 'hex': '#143E66'},
    'blue_dark':    {'rgb': [0.030, 0.170, 0.300], 'hex': '#082B4D'},
    'purple':       {'rgb': [0.350, 0.105, 0.252], 'hex': '#591B40'},
}

# Color names in UI order (for color picker display)
CK3_COLOR_NAMES_ORDERED = [
    'red', 'red_dark', 'orange', 'yellow', 'yellow_light',
    'white', 'grey', 'black', 'brown',
    'green', 'green_light',
    'blue_light', 'blue', 'blue_dark',
    'purple'
]

# ======================================================================
# LAYER MOVEMENT CONSTANTS
# ======================================================================
# Amount to move layers when using arrow keys
ARROW_KEY_MOVE_NORMAL = 0.01  # Normal arrow key movement
ARROW_KEY_MOVE_FINE = 0.002   # Fine movement with Shift modifier

# ======================================================================
# DEFAULT COLORS
# ======================================================================

# Default base pattern colors (if unspecified in CoA data)
DEFAULT_BASE_COLOR1 = 'purple'
DEFAULT_BASE_COLOR2 = 'yellow'
DEFAULT_BASE_COLOR3 = 'black'

# Default emblem colors (if unspecified in colored_emblem block)
DEFAULT_EMBLEM_COLOR1 = 'yellow'
DEFAULT_EMBLEM_COLOR2 = 'red'
DEFAULT_EMBLEM_COLOR3 = 'blue'

# Default pattern texture
DEFAULT_PATTERN_TEXTURE = 'pattern_solid.dds'  # CK3 default (single underscore)
DEFAULT_EMBLEM_TEXTURE = 'ce_fleur.dds'

# Default asset categories
DEFAULT_BASE_CATEGORY = '__Base_Patterns__'
DEFAULT_EMBLEM_CATEGORY = 'Nature'  # Where ce_fleur.dds is located

# Default frame
DEFAULT_FRAME = 'house'  # Options: 'house', 'dynasty', etc.

# ======================================================================
# HIGH CONTRAST FALLBACK COLORS
# ======================================================================

# For layer thumbnails and asset previews when emblem color is too similar to background
# Use CK3's defined black and white for authentic appearance
HIGH_CONTRAST_DARK = CK3_NAMED_COLORS['black']['rgb']   # [0.100, 0.090, 0.075]
HIGH_CONTRAST_LIGHT = CK3_NAMED_COLORS['white']['rgb']  # [0.800, 0.792, 0.784]

# Minimum color distance threshold (Euclidean distance in RGB space)
# Below this threshold, fallback to high contrast colors
MIN_COLOR_DISTANCE = 0.1

# ======================================================================
# COORDINATE SYSTEM
# ======================================================================

# Normalized coordinate space [0.0, 1.0]
# X-axis: 0.0 = left edge, 1.0 = right edge
# Y-axis: 0.0 = TOP edge, 1.0 = BOTTOM edge (INVERTED!)

COORD_MIN = 0.0
COORD_MAX = 1.0
COORD_CENTER = 0.5

# Default position (center of canvas)
DEFAULT_POSITION_X = 0.5
DEFAULT_POSITION_Y = 0.5

# ======================================================================
# SCALE CONSTRAINTS
# ======================================================================

# Single emblem scale limits [0.01, 1.0]
SCALE_MIN = 0.01  # Minimum scale (1% of canvas)
SCALE_MAX = 1.0   # Maximum scale (100% of canvas)

# Default scale for new layers
DEFAULT_SCALE_X = 0.7
DEFAULT_SCALE_Y = 0.7

# Unified scale (when scaling uniformly)
DEFAULT_UNIFIED_SCALE = True

# ======================================================================
# ROTATION
# ======================================================================

# Rotation in degrees [0, 359]
ROTATION_MIN = 0
ROTATION_MAX = 359
DEFAULT_ROTATION = 0

# ======================================================================
# DEPTH/LAYERING
# ======================================================================

# Depth controls z-order rendering (higher = in front)
DEPTH_MIN = 0.0
DEPTH_DEFAULT = 0.0
DEPTH_INCREMENT = 1.0  # Common increment between layers

# Typical depth range in CK3 CoAs
DEPTH_TYPICAL_MIN = 0.010000

# ======================================================================
# CANVAS RENDERING
# ======================================================================

# Canvas scale factor for rendering
# CK3 renders CoAs at 1.1x scale factor
CANVAS_SCALE_FACTOR = 1.1

# OpenGL texture filtering
TEXTURE_MIN_FILTER = 'GL_LINEAR_MIPMAP_LINEAR'
TEXTURE_MAG_FILTER = 'GL_LINEAR'

# Shader uniform names
SHADER_UNIFORM_TEXTURE = 'textureSampler'
SHADER_UNIFORM_COLOR1 = 'color1'
SHADER_UNIFORM_COLOR2 = 'color2'
SHADER_UNIFORM_COLOR3 = 'color3'
SHADER_UNIFORM_TRANSFORM = 'transform'

# ======================================================================
# EMBLEM SETTINGS
# ======================================================================

# Number of color channels per emblem (1, 2, or 3)
EMBLEM_COLORS_MIN = 1
EMBLEM_COLORS_MAX = 3
EMBLEM_COLORS_DEFAULT = 3

# Flip flags (negative scale values)
DEFAULT_FLIP_X = False
DEFAULT_FLIP_Y = False

# ======================================================================
# DECIMAL PRECISION
# ======================================================================

# Decimal places for position/scale values when saving
# CK3 commonly uses 6 decimal places (e.g., 0.970000)
DECIMAL_PRECISION_POSITION = 6
DECIMAL_PRECISION_SCALE = 6

# Rotation is always integer
ROTATION_DECIMAL_PLACES = 0

# ======================================================================
# HISTORY MANAGEMENT
# ======================================================================

# Maximum undo/redo history
MAX_HISTORY_ENTRIES = 100

# ======================================================================
# UI CONSTRAINTS
# ======================================================================

# Property slider ranges
SLIDER_POSITION_MIN = 0.0
SLIDER_POSITION_MAX = 1.0
SLIDER_SCALE_MIN = 0.01
SLIDER_SCALE_MAX = 1.0
SLIDER_ROTATION_MIN = 0
SLIDER_ROTATION_MAX = 359

# Layer list item height
LAYER_ITEM_HEIGHT = 60

# Color button sizes
COLOR_BUTTON_SIZE_LARGE = 40  # Base color buttons
COLOR_BUTTON_SIZE_SMALL = 16  # Inline layer color buttons

# ======================================================================
# FILE FORMATS
# ======================================================================

# Supported texture format
TEXTURE_FILE_EXTENSION = '.dds'

# CoA save file format
COA_FILE_EXTENSION = '.txt'

# ======================================================================
# PASTE OFFSET
# ======================================================================

# Small offset applied when pasting layers to make duplication visible
PASTE_OFFSET_X = 0.02
PASTE_OFFSET_Y = 0.02

# ======================================================================
# MULTI-SELECTION
# ======================================================================

# Group transforms don't clamp AABB scale (can exceed 1.0)
# Individual emblems still clamped to [0.01, 1.0]
GROUP_AABB_SCALE_UNLIMITED = True

# ======================================================================
# TRANSFORM WIDGET CONSTANTS
# ======================================================================

# Handle visual appearance
TRANSFORM_HANDLE_SIZE = 8  # Handle circle/square radius (pixels)
TRANSFORM_ROTATION_HANDLE_OFFSET = 30  # Distance above top edge (pixels)
TRANSFORM_HIT_TOLERANCE = 4  # Extra pixels for handle hit detection

# Gimble Mode Constants
TRANSFORM_GIMBLE_ARROW_START_OFFSET = 15  # Distance from center to arrow start (pixels)
TRANSFORM_GIMBLE_ARROW_LENGTH = 50  # Length of axis arrows (pixels)
TRANSFORM_GIMBLE_ARROW_HEAD_SIZE = 8  # Size of arrow head triangle (pixels)
TRANSFORM_GIMBLE_RING_RADIUS = 80  # Rotation ring radius - beyond arrow tips (pixels)
TRANSFORM_GIMBLE_RING_HIT_TOLERANCE = 8  # Hit tolerance for rotation ring (pixels)
TRANSFORM_GIMBLE_CENTER_DOT_RADIUS = 6  # Center dot radius in gimble mode (pixels)

# Interaction Constants
TRANSFORM_DUPLICATE_DRAG_THRESHOLD = 5  # Pixels to drag before Ctrl+drag duplicates layer
