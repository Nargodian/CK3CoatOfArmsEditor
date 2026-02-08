"""Shared UI helper functions for components"""

from PyQt5.QtWidgets import QComboBox, QLabel
from PyQt5.QtCore import Qt


def create_styled_combo_box(items):
    """Create a styled combo box with unicode down arrow
    
    Args:
        items: List of strings to populate the combo box
        
    Returns:
        QComboBox with custom styling and unicode arrow
    """
    combo = QComboBox()
    combo.addItems(items)
    combo.setStyleSheet("""
        QComboBox {
            padding: 5px 5px;
            padding-right: 20px;
            border-radius: 3px;
            border: none;
        }
        QComboBox::drop-down {
            border: none;
            width: 16px;
        }
        QComboBox::down-arrow {
            image: none;
        }
    """)
    
    # Create a label with unicode down arrow and position it
    arrow_label = QLabel("▼", combo)
    arrow_label.setStyleSheet("color: #aaa; font-size: 10px; background: transparent;")
    arrow_label.setAttribute(Qt.WA_TransparentForMouseEvents)
    arrow_label.setAlignment(Qt.AlignCenter)
    
    # Position the arrow on the right side
    def update_arrow_position():
        arrow_label.setGeometry(combo.width() - 20, 0, 20, combo.height())
    
    # Override resizeEvent properly
    original_resize = combo.resizeEvent
    def resize_with_arrow(event):
        original_resize(event)
        update_arrow_position()
    combo.resizeEvent = resize_with_arrow
    update_arrow_position()
    
    return combo
