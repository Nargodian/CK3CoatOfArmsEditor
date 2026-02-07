"""
CK3 Coat of Arms Editor - Color Picker Widget

Internal component that works exclusively with Color objects.
Converts to/from Qt primitives only at external API boundaries (QColorDialog, stylesheets).
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QPushButton, QLabel, QColorDialog
from PyQt5.QtGui import QColor
from constants import CK3_NAMED_COLORS, CK3_COLOR_NAMES_ORDERED
from models.color import Color


# Build CK3 preset palette as Color objects (constants boundary - convert once at module load)
CK3_PRESET_COLORS = []
for color_id in CK3_COLOR_NAMES_ORDERED:
    color = Color.from_name(color_id)
    display_name = ' '.join(word.capitalize() for word in color_id.split('_'))
    CK3_PRESET_COLORS.append((color, display_name))


class ColorPickerDialog(QDialog):
    """Dialog for selecting colors from CK3 palette or custom colors
    
    Works internally with Color objects, converting to Qt types only at API boundaries.
    """
    
    def __init__(self, parent=None, current_color=None):
        super().__init__(parent)
        self.setWindowTitle("Choose Color")
        self.setModal(True)
        self.selected_color = None
        self.current_color = current_color or Color.from_rgb255(0, 0, 0)
        self._setup_ui()
    
    def _setup_ui(self):
        """Build color picker UI with preset swatches and custom color option"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        label = QLabel("Select a color:")
        label.setStyleSheet("font-size: 12px; font-weight: bold;")
        layout.addWidget(label)
        
        # Create preset color grid
        grid_layout = QGridLayout()
        grid_layout.setSpacing(8)
        
        for i, (color, display_name) in enumerate(CK3_PRESET_COLORS):
            btn = self._create_preset_button(color, display_name)
            row, col = (0, i) if i < 7 else (1, i - 7)
            grid_layout.addWidget(btn, row, col)
        
        layout.addLayout(grid_layout)
        
        # Custom color option
        custom_btn = QPushButton("Custom Color...")
        custom_btn.setStyleSheet("padding: 8px; border-radius: 4px;")
        custom_btn.clicked.connect(self._open_custom_picker)
        layout.addWidget(custom_btn)
    
    def _create_preset_button(self, color, display_name):
        """Create a preset color swatch button"""
        btn = QPushButton()
        btn.setFixedSize(60, 60)
        btn.setToolTip(display_name)
        # Qt boundary: convert Color to hex for stylesheet
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color.to_hex()};
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 30);
            }}
        """)
        btn.clicked.connect(lambda: self._select_color(color))
        return btn
    
    def _select_color(self, color):
        """Accept the selected color"""
        self.selected_color = color
        self.accept()
    
    def _open_custom_picker(self):
        """Open Qt's color dialog and convert result back to Color object"""
        # Qt boundary: Color → QColor
        initial_qcolor = self.current_color.to_qcolor()
        picked_qcolor = QColorDialog.getColor(initial_qcolor, self, "Choose Custom Color")
        
        if picked_qcolor.isValid():
            # Qt boundary: QColor → Color (with empty name for custom colors)
            self.selected_color = Color.from_rgb255(
                picked_qcolor.red(), 
                picked_qcolor.green(), 
                picked_qcolor.blue()
            )
            self.selected_color.set_name('')
            self.accept()
    
    @staticmethod
    def get_color(parent=None, current_color=None):
        """Show color picker dialog and return selected Color object
        
        Args:
            parent: Parent widget
            current_color: Current Color object (optional)
            
        Returns:
            Selected Color object or None if cancelled
        """
        dialog = ColorPickerDialog(parent, current_color)
        return dialog.selected_color if dialog.exec_() else None


def create_color_button(color):
    """Create a color swatch button from Color object
    
    Args:
        color: Color object
        
    Returns:
        QPushButton configured as color swatch
    """
    btn = QPushButton()
    btn.setFixedSize(40, 40)
    # Qt boundary: convert Color to hex for stylesheet
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {color.to_hex()};
            border-radius: 4px;
        }}
    """)
    return btn
