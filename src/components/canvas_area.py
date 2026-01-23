from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSizePolicy)
from PyQt5.QtCore import Qt
from .canvas_widget import CoatOfArmsCanvas


class CanvasArea(QFrame):
	"""Center canvas area for coat of arms preview"""
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setStyleSheet("QFrame { background-color: #0d0d0d; }")
		self._setup_ui()
	
	def _setup_ui(self):
		"""Setup the canvas area UI"""
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(0)
		
		# Container to center the square canvas
		canvas_container = QFrame()
		canvas_container.setStyleSheet("QFrame { background-color: #0d0d0d; }")
		canvas_layout = QVBoxLayout(canvas_container)
		canvas_layout.setContentsMargins(10, 10, 10, 10)
		canvas_layout.setAlignment(Qt.AlignCenter)
		
		# OpenGL canvas widget (square aspect)
		self.canvas_widget = CoatOfArmsCanvas()
		self.canvas_widget.setMinimumSize(400, 400)
		self.canvas_widget.setMaximumSize(1000, 1000)
		
		canvas_layout.addWidget(self.canvas_widget)
		
		layout.addWidget(canvas_container, stretch=1)
		
		# Bottom bar
		bottom_bar = self._create_bottom_bar()
		layout.addWidget(bottom_bar)
	
	def _create_bottom_bar(self):
		"""Create the bottom bar with frame and prestige dropdowns"""
		bottom_bar = QFrame()
		bottom_bar.setStyleSheet("QFrame { background-color: #353535; border-top: 1px solid; }")
		bottom_bar.setFixedHeight(50)
		
		bottom_layout = QHBoxLayout(bottom_bar)
		bottom_layout.setContentsMargins(10, 5, 10, 5)
		bottom_layout.setSpacing(15)
		
		# Frame dropdown
		frame_label = QLabel("Frame:")
		frame_label.setStyleSheet("font-size: 11px; border: none;")
		bottom_layout.addWidget(frame_label)
		
		frame_options = ["None", "Dynasty", "House", "House China", "House Japan"] + \
		                [f"House Frame {i:02d}" for i in range(2, 31)]
		self.frame_combo = self._create_combo_box(frame_options)
		self.frame_combo.setCurrentIndex(1)  # Default to Dynasty
		self.frame_combo.currentTextChanged.connect(self._on_frame_changed)
		bottom_layout.addWidget(self.frame_combo)
		
		bottom_layout.addSpacing(20)
		
		# Prestige dropdown
		prestige_label = QLabel("Prestige:")
		prestige_label.setStyleSheet("font-size: 11px; border: none;")
		bottom_layout.addWidget(prestige_label)
		
		self.prestige_combo = self._create_combo_box(["Level 0", "Level 1", "Level 2", "Level 3", "Level 4", "Level 5"])
		self.prestige_combo.currentIndexChanged.connect(self._on_prestige_changed)
		bottom_layout.addWidget(self.prestige_combo)
		
		bottom_layout.addStretch()
		
		return bottom_bar
	
	def _create_combo_box(self, items):
		"""Create a styled combo box"""
		combo = QComboBox()
		combo.addItems(items)
		combo.setStyleSheet("""
			QComboBox {
				padding: 5px 10px;
				border-radius: 3px;
				min-width: 150px;
				border: none;
			}
			QComboBox::drop-down {
				border: none;
			}
			QComboBox::down-arrow {
				image: none;
				border-left: 4px solid transparent;
				border-right: 4px solid transparent;
				border-top: 6px solid;
				margin-right: 5px;
			}
		""")
		return combo
	
	def _on_frame_changed(self, frame_text):
		"""Handle frame selection change"""
		# Convert display text to frame name
		frame_map = {
			"None": "None",
			"Dynasty": "dynasty",
			"House": "house",
			"House China": "house_china",
			"House Japan": "house_japan"
		}
		
		# Handle House Frame XX format
		if frame_text.startswith("House Frame"):
			frame_num = frame_text.split()[-1]
			frame_name = f"house_frame_{frame_num}"
		else:
			frame_name = frame_map.get(frame_text, "None")
		
		self.canvas_widget.set_frame(frame_name)
	
	def _on_prestige_changed(self, index):
		"""Handle prestige level change"""
		self.canvas_widget.set_prestige(index)
