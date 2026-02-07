"""Keyboard shortcuts help dialog."""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton


class ShortcutsDialog(QDialog):
    """Dialog displaying all keyboard shortcuts"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        layout = QVBoxLayout()
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml("""
        <h2>Keyboard Shortcuts</h2>
        
        <h3>File Operations</h3>
        <table width="100%">
        <tr><td width="30%"><b>Ctrl+N</b></td><td>Create new coat of arms</td></tr>
        <tr><td><b>Ctrl+O</b></td><td>Open existing file</td></tr>
        <tr><td><b>Ctrl+S</b></td><td>Save current file</td></tr>
        <tr><td><b>Ctrl+Shift+S</b></td><td>Save as new file</td></tr>
        <tr><td><b>Ctrl+E</b></td><td>Export as PNG image</td></tr>
        <tr><td><b>Ctrl+Shift+C</b></td><td>Copy entire coat of arms to clipboard</td></tr>
        <tr><td><b>Ctrl+Shift+V</b></td><td>Paste entire coat of arms from clipboard</td></tr>
        <tr><td><b>Alt+F4</b></td><td>Exit application</td></tr>
        </table>
        
        <h3>Edit Operations</h3>
        <table width="100%">
        <tr><td width="30%"><b>Ctrl+Z</b></td><td>Undo last action</td></tr>
        <tr><td><b>Ctrl+Y</b></td><td>Redo previously undone action</td></tr>
        <tr><td><b>F</b></td><td>Flip selected layer(s) horizontally</td></tr>
        <tr><td><b>Ctrl+F</b></td><td>Flip selected layer(s) vertically</td></tr>
        </table>
        
        <h3>View Operations</h3>
        <table width="100%">
        <tr><td width="30%"><b>Ctrl++</b></td><td>Zoom in (max 500%)</td></tr>
        <tr><td><b>Ctrl+-</b></td><td>Zoom out (min 25%)</td></tr>
        <tr><td><b>Ctrl+0</b></td><td>Reset zoom to 100%</td></tr>
        <tr><td><b>Ctrl+Wheel</b></td><td>Zoom in/out with mouse wheel</td></tr>
        <tr><td><b>Drag</b></td><td>Pan canvas when zoomed &gt;100%</td></tr>
        </table>
        
        <h3>Layer Operations</h3>
        <table width="100%">
        <tr><td width="30%"><b>Click</b></td><td>(on layer) Select single layer</td></tr>
        <tr><td><b>Shift+Click</b></td><td>(on layer) Select range of layers</td></tr>
        <tr><td><b>Ctrl+Click</b></td><td>(on layer) Add/remove layer from selection</td></tr>
        <tr><td><b>Ctrl+A</b></td><td>Select all layers</td></tr>
        <tr><td><b>Ctrl+C</b></td><td>Copy selected layer(s) — or full CoA if nothing selected</td></tr>
        <tr><td><b>Ctrl+X</b></td><td>Cut selected layer(s) to clipboard</td></tr>
        <tr><td><b>Ctrl+V</b></td><td>Paste layer(s) — auto-detects full CoA and imports it</td></tr>
        <tr><td><b>Ctrl+D</b></td><td>Duplicate selected layer(s)</td></tr>
        <tr><td><b>Delete</b></td><td>Delete selected layer(s)</td></tr>
        <tr><td><b>R</b></td><td>Rotate selected layer(s) −45 degrees</td></tr>
        <tr><td><b>Shift+R</b></td><td>Rotate selected layer(s) +45 degrees</td></tr>
        </table>
        
        <h3>Transform Widget</h3>
        <table width="100%">
        <tr><td width="30%"><b>M</b></td><td>Cycle transform modes (BBox/Minimal/Gimble)</td></tr>
        <tr><td><b>Shift</b></td><td>(while rotating) Snap rotation to 45° increments</td></tr>
        <tr><td><b>Ctrl+Drag</b></td><td>(on transform handles) Duplicate layer while moving</td></tr>
        <tr><td><b>Mouse Wheel</b></td><td>(while dragging) Adjust scale uniformly</td></tr>
        <tr><td><b>Alt+Wheel</b></td><td>(while dragging) Adjust rotation in 5° increments</td></tr>
        <tr><td><b>Ctrl+Wheel</b></td><td>(while dragging) Adjust scale X only</td></tr>
        <tr><td><b>Shift+Wheel</b></td><td>(while dragging) Adjust scale Y only</td></tr>
        </table>
        
        <h3>Grid &amp; Snapping</h3>
        <table width="100%">
        <tr><td width="30%"><b>View → Grid</b></td><td>Show grid overlay (2×2, 4×4, 8×8, 16×16, 32×32)</td></tr>
        <tr><td><b>View → Grid → Snap</b></td><td>Snap layer position to grid points while dragging</td></tr>
        </table>
        
        <h3>Picker Tool</h3>
        <table width="100%">
        <tr><td width="30%"><b>P</b></td><td>Toggle picker tool on/off</td></tr>
        <tr><td><b>Click</b></td><td>(while picking) Select layer under cursor</td></tr>
        <tr><td><b>Shift+Click</b></td><td>(while picking) Keep picker active for multi-select</td></tr>
        <tr><td><b>Ctrl+Hold</b></td><td>(while picking) Paint select/deselect layers</td></tr>
        </table>
        
        <h3>Help</h3>
        <table width="100%">
        <tr><td width="30%"><b>F1</b></td><td>Show this keyboard shortcuts help</td></tr>
        </table>
        
        <p><i>Tip: You can also access most commands through the menu bar.</i></p>
        """)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        
        layout.addWidget(text_edit)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
