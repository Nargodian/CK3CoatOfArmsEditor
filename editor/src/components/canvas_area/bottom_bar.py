"""Bottom bar component for canvas area - controls frame, splendor, rotation mode, and tools"""
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QComboBox
from components.ui_helpers import create_styled_combo_box


class BottomBar(QFrame):
	"""Bottom control bar with frame, splendor, rotation mode, and tool buttons"""
	
	def __init__(self, canvas_area):
		"""Initialize bottom bar
		
		Args:
			canvas_area: Parent CanvasArea instance
		"""
		super().__init__()
		self.canvas_area = canvas_area
		
		self.setStyleSheet("QFrame { background-color: #2d2d2d; border: none; }")
		self.setFixedHeight(50)
		
		self._setup_ui()
	
	def _setup_ui(self):
		"""Setup the bottom bar UI"""
		layout = QHBoxLayout(self)
		layout.setContentsMargins(10, 5, 10, 5)
		layout.setSpacing(15)
		
		# Frame dropdown
		frame_label = QLabel("Frame:")
		frame_label.setStyleSheet("font-size: 11px; border: none;")
		layout.addWidget(frame_label)
		
		frame_options = ["None", "Dynasty", "House", "House China", "House Japan"] + \
		                [f"House Frame {i:02d}" for i in range(2, 31)]
		self.frame_combo = create_styled_combo_box(frame_options)
		self.frame_combo.setFixedWidth(120)
		self.frame_combo.setCurrentIndex(2)  # Default to House
		self.frame_combo.currentTextChanged.connect(self._on_frame_changed)
		layout.addWidget(self.frame_combo)
		
		layout.addSpacing(20)
		
		# Splendor dropdown
		splendor_label = QLabel("Splendor:")
		splendor_label.setStyleSheet("font-size: 11px; border: none;")
		layout.addWidget(splendor_label)
		
		self.splendor_combo = create_styled_combo_box([
			"Base Origins / Obscure",
			"Insignificant / Noteworthy",
			"Reputable / Well-Known",
			"Significant / Famous",
			"Glorious / Fabled",
			"Legendary"
		])
		self.splendor_combo.setCurrentIndex(3)  # Default to Significant/Famous
		self.splendor_combo.currentIndexChanged.connect(self._on_splendor_changed)
		layout.addWidget(self.splendor_combo)
		
		layout.addSpacing(20)
		
		# Rotation mode dropdown
		rotation_label = QLabel("Rotation:")
		rotation_label.setStyleSheet("font-size: 11px; border: none;")
		layout.addWidget(rotation_label)
		
		self.rotation_mode_combo = create_styled_combo_box([
			"Rotate Only",
			"Orbit Only",
			"Normal",
			"Rotate (Deep)",
			"Orbit (Deep)"
		])
		self.rotation_mode_combo.setFixedWidth(120)
		self.rotation_mode_combo.setToolTip(
			"Rotation Mode:\n"
			"Rotate Only - Spin layers in place\n"
			"Orbit Only - Orbit layers around center\n"
			"Normal - Orbit + Rotate layers\n"
			"Rotate (Deep) - Spin all instances in place\n"
			"Orbit (Deep) - Orbit all instances around center"
		)
		self.rotation_mode_combo.setCurrentIndex(2)  # Default to Normal
		layout.addWidget(self.rotation_mode_combo)
		
		layout.addSpacing(20)
		
		# Transform mode dropdown
		self.transform_mode_combo = QComboBox()
		self.transform_mode_combo.addItems(["Normal", "Minimal", "Gimble"])
		self.transform_mode_combo.setCurrentIndex(0)  # Default to Normal
		self.transform_mode_combo.setToolTip("Transform Widget Mode (M)\nNormal: Scale + rotation handles\nMinimal: Corners only\nGimble: Position arrows + rotation ring")
		self.transform_mode_combo.setFixedHeight(20)
		self.transform_mode_combo.setStyleSheet("""
			QComboBox {
				font-size: 11px;
				padding: 2px 4px;
				border: 1px solid rgba(255, 255, 255, 40);
				background-color: rgba(40, 40, 40, 200);
				color: white;
			}
			QComboBox::drop-down {
				border: none;
			}
			QComboBox QAbstractItemView {
				background-color: rgba(40, 40, 40, 240);
				color: white;
				selection-background-color: rgba(100, 150, 255, 100);
			}
		""")
		self.transform_mode_combo.currentIndexChanged.connect(self._on_transform_mode_changed)
		layout.addWidget(self.transform_mode_combo)
		
		# Layer picker tool button
		self.picker_btn = QPushButton("🎯")
		self.picker_btn.setCheckable(True)
		self.picker_btn.setToolTip("Layer Picker Tool\nClick to select layer under mouse cursor")
		self.picker_btn.setFixedSize(24, 20)
		self.picker_btn.setStyleSheet("""
			QPushButton { 
				font-size: 14px; 
				padding: 0px; 
				border: 1px solid rgba(255, 255, 255, 40); 
			}
			QPushButton:checked {
				background-color: rgba(100, 150, 255, 100);
				border: 1px solid rgba(100, 150, 255, 180);
			}
		""")
		self.picker_btn.toggled.connect(self._on_picker_button_toggled)
		layout.addWidget(self.picker_btn)
		
		# Show selection toggle button
		self.show_selection_btn = QPushButton("👁")
		self.show_selection_btn.setCheckable(True)
		self.show_selection_btn.setChecked(False)
		self.show_selection_btn.setToolTip("Show Selection Tint\nHighlight selected layers in red")
		self.show_selection_btn.setFixedSize(24, 20)
		self.show_selection_btn.setStyleSheet("""
			QPushButton { 
				font-size: 14px; 
				padding: 0px; 
				border: 1px solid rgba(255, 255, 255, 40); 
			}
			QPushButton:checked {
				background-color: rgba(255, 100, 100, 100);
				border: 1px solid rgba(255, 100, 100, 180);
			}
		""")
		self.show_selection_btn.toggled.connect(self._on_show_selection_toggled)
		layout.addWidget(self.show_selection_btn)
		
		layout.addStretch()
	
	def get_rotation_mode(self):
		"""Get current rotation mode from dropdown
		
		Returns:
			String mode name for CoA.rotate_selection()
		"""
		mode_map = {
			"Rotate Only": "rotate_only",
			"Orbit Only": "orbit_only",
			"Normal": "both",
			"Rotate (Deep)": "rotate_only_deep",
			"Orbit (Deep)": "orbit_only_deep"
		}
		if not hasattr(self, 'rotation_mode_combo'):
			return "both"
		current_text = self.rotation_mode_combo.currentText()
		return mode_map.get(current_text, "both")
	
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
		
		self.canvas_area.canvas_widget.set_frame(frame_name)
	
	def _on_splendor_changed(self, index):
		"""Handle splendor level change"""
		self.canvas_area.canvas_widget.set_splendor(index)
	
	def _on_picker_button_toggled(self, checked):
		"""Handle layer picker button toggle"""
		if checked:
			self.canvas_area.canvas_widget.set_tool_mode('layer_picker')
		else:
			# Deactivate picker and re-enable transform widget (keeps selection)
			self.canvas_area.canvas_widget.set_tool_mode(None)
			self.canvas_area.update_transform_widget_for_layer()
	
	def _on_show_selection_toggled(self, checked):
		"""Handle show selection button toggle"""
		# Trigger canvas update to show/hide selection tint
		self.canvas_area.canvas_widget.update()
	
	def _on_transform_mode_changed(self, index):
		"""Handle transform mode dropdown change"""
		mode = ["normal", "minimal", "gimble"][index]
		self.canvas_area.transform_widget.set_transform_mode(mode)
