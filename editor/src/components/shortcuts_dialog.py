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
        
        <h3>Layer Operations</h3>
        <table width="100%">
        <tr><td width="30%"><b>Ctrl+A</b></td><td>Select all layers</td></tr>
        <tr><td><b>Ctrl+C</b></td><td>Copy selected layer(s)</td></tr>
        <tr><td><b>Ctrl+V</b></td><td>Paste layer(s) from clipboard</td></tr>
        <tr><td><b>Ctrl+D</b></td><td>Duplicate selected layer(s)</td></tr>
        <tr><td><b>Delete</b></td><td>Delete selected layer(s)</td></tr>
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
