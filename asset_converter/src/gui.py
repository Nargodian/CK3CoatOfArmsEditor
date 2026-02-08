"""
Asset converter GUI.

PyQt5 main window providing directory selection, progress tracking,
and log output for the CK3 asset conversion pipeline.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QProgressBar,
    QTextEdit, QGroupBox, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from .dds_loading import HAS_IMAGEIO
from .converter_worker import ConversionWorker


# Settings file location
_SETTINGS_DIR = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'CK3CoatOfArmsEditor'
_SETTINGS_FILE = _SETTINGS_DIR / 'converter_settings.json'


class AssetConverterGUI(QMainWindow):
    """Main GUI window for asset converter."""
    
    def __init__(self):
        super().__init__()
        self.worker = None
        self._saved_settings = self._load_settings()
        self.init_ui()
    
    @staticmethod
    def _load_settings() -> dict:
        """Load saved directory paths from appdata."""
        try:
            if _SETTINGS_FILE.exists():
                with open(_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    @staticmethod
    def _save_settings(settings: dict):
        """Save directory paths to appdata."""
        try:
            _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            with open(_SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        except Exception:
            pass
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("CK3 Coat of Arms Asset Converter")
        self.setMinimumSize(700, 500)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("CK3 Coat of Arms Asset Converter")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # CK3 Directory selection
        ck3_group = QGroupBox("CK3 Installation Directory")
        ck3_layout = QHBoxLayout()
        self.ck3_path_edit = QLineEdit()
        self.ck3_path_edit.setPlaceholderText("Select CK3 installation directory...")
        if self._saved_settings.get('ck3_dir'):
            self.ck3_path_edit.setText(self._saved_settings['ck3_dir'])
        self.ck3_browse_btn = QPushButton("Browse...")
        self.ck3_browse_btn.clicked.connect(self.browse_ck3_dir)
        ck3_layout.addWidget(self.ck3_path_edit)
        ck3_layout.addWidget(self.ck3_browse_btn)
        ck3_group.setLayout(ck3_layout)
        layout.addWidget(ck3_group)
        
        # Mod Directory selection (optional)
        mod_group = QGroupBox("Mod Directory (Optional)")
        mod_layout = QHBoxLayout()
        self.mod_path_edit = QLineEdit()
        self.mod_path_edit.setPlaceholderText("Optional: Select mod directory to include mod assets...")
        if self._saved_settings.get('mod_dir'):
            self.mod_path_edit.setText(self._saved_settings['mod_dir'])
        self.mod_browse_btn = QPushButton("Browse...")
        self.mod_browse_btn.clicked.connect(self.browse_mod_dir)
        mod_layout.addWidget(self.mod_path_edit)
        mod_layout.addWidget(self.mod_browse_btn)
        mod_group.setLayout(mod_layout)
        layout.addWidget(mod_group)
        
        # Output Directory selection
        output_group = QGroupBox("Output Directory")
        output_layout = QHBoxLayout()
        self.output_path_edit = QLineEdit()
        
        # Default to ck3_assets relative to exe/script location
        if getattr(sys, 'frozen', False):
            default_output = Path(sys.executable).parent / "ck3_assets"
        else:
            default_output = Path(__file__).parent.parent / "ck3_assets"
        self.output_path_edit.setText(str(default_output))
        
        self.output_browse_btn = QPushButton("Browse...")
        self.output_browse_btn.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(self.output_path_edit)
        output_layout.addWidget(self.output_browse_btn)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        self.progress_label = QLabel("Ready to convert assets")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Log output
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.convert_btn = QPushButton("Start Conversion")
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setMinimumHeight(40)
        button_layout.addWidget(self.convert_btn)
        layout.addLayout(button_layout)
        
        # Check for imageio
        if not HAS_IMAGEIO:
            self.log("WARNING: imageio and imageio-dds are required. Install with: pip install imageio imageio-dds")
            self.convert_btn.setEnabled(False)
    
    def browse_ck3_dir(self):
        """Open directory browser for CK3 installation."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select CK3 Installation Directory",
            "", QFileDialog.ShowDirsOnly
        )
        if dir_path:
            self.ck3_path_edit.setText(dir_path)
    
    def browse_mod_dir(self):
        """Open directory browser for mod directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Mod Directory",
            "", QFileDialog.ShowDirsOnly
        )
        if dir_path:
            self.mod_path_edit.setText(dir_path)
    
    def browse_output_dir(self):
        """Open directory browser for output location."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Output Directory",
            "", QFileDialog.ShowDirsOnly
        )
        if dir_path:
            self.output_path_edit.setText(dir_path)
    
    def log(self, message: str):
        """Add message to log."""
        self.log_text.append(message)
    
    def validate_paths(self) -> bool:
        """Validate CK3 directory structure."""
        ck3_dir = Path(self.ck3_path_edit.text())
        
        if not ck3_dir.exists():
            QMessageBox.critical(self, "Error", "CK3 directory does not exist")
            return False
        
        required_paths = [
            ck3_dir / "game" / "gfx" / "coat_of_arms" / "colored_emblems",
            ck3_dir / "game" / "gfx" / "coat_of_arms" / "patterns",
            ck3_dir / "game" / "gfx" / "interface" / "coat_of_arms" / "frames",
            ck3_dir / "game" / "common" / "coat_of_arms"
        ]
        
        missing = [str(p) for p in required_paths if not p.exists()]
        
        if missing:
            QMessageBox.critical(
                self, "Invalid CK3 Directory",
                "The selected directory does not appear to be a valid CK3 installation.\n\n"
                f"Missing paths:\n" + "\n".join(missing)
            )
            return False
        
        return True
    
    def start_conversion(self):
        """Start the conversion process."""
        if not self.validate_paths():
            return
        
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Busy", "Conversion already in progress")
            return
        
        ck3_dir = Path(self.ck3_path_edit.text())
        output_dir = Path(self.output_path_edit.text())
        mod_dir_text = self.mod_path_edit.text().strip()
        mod_dir = Path(mod_dir_text) if mod_dir_text else None
        
        # Disable UI during conversion
        self.convert_btn.setText("Converting...")
        self.convert_btn.setEnabled(False)
        self.ck3_browse_btn.setEnabled(False)
        self.mod_browse_btn.setEnabled(False)
        self.output_browse_btn.setEnabled(False)
        self.ck3_path_edit.setEnabled(False)
        self.mod_path_edit.setEnabled(False)
        self.output_path_edit.setEnabled(False)
        
        self.log_text.clear()
        self.log(f"Starting conversion from: {ck3_dir}")
        if mod_dir:
            self.log(f"Including mods from: {mod_dir}")
        self.log(f"Output to: {output_dir}")
        
        self.worker = ConversionWorker(ck3_dir, output_dir, mod_dir)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
    
    def on_progress(self, message: str, current: int, total: int):
        """Handle progress updates."""
        self.progress_label.setText(message)
        if total > 0:
            self.progress_bar.setValue(int((current / total) * 100))
        self.log(message)
    
    def on_finished(self, success: bool, message: str):
        """Handle conversion completion."""
        self.log(message)
        
        if success:
            self._save_settings({
                'ck3_dir': self.ck3_path_edit.text(),
                'mod_dir': self.mod_path_edit.text(),
            })
            QMessageBox.information(self, "Success", message)
            self.convert_btn.setText("Conversion Done - Close")
            self.convert_btn.clicked.disconnect()
            self.convert_btn.clicked.connect(self.close)
            self.convert_btn.setEnabled(True)
        else:
            QMessageBox.critical(self, "Error", message)
            self.convert_btn.setText("Start Conversion")
            self.convert_btn.setEnabled(True)
            self.ck3_browse_btn.setEnabled(True)
            self.mod_browse_btn.setEnabled(True)
            self.output_browse_btn.setEnabled(True)
            self.ck3_path_edit.setEnabled(True)
            self.mod_path_edit.setEnabled(True)
            self.output_path_edit.setEnabled(True)
        
        self.progress_bar.setValue(0 if not success else 100)


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    window = AssetConverterGUI()
    window.show()
    sys.exit(app.exec_())
