from PyQt5 import QtCore
from PyQt5.QtWidgets import QToolBar, QPushButton, QWidget, QSizePolicy, QApplication


def create_toolbar(parent):
	"""Create the main toolbar with New, Open, Save, Undo, Redo buttons"""
	toolbar = QToolBar("Main Toolbar")
	toolbar.setMovable(False)
	toolbar.setIconSize(QtCore.QSize(24, 24))
	parent.addToolBar(toolbar)
	
	# Add toolbar buttons
	new_btn = QPushButton("New")
	open_btn = QPushButton("Open")
	save_btn = QPushButton("Save")
	undo_btn = QPushButton("Undo")
	redo_btn = QPushButton("Redo")
	
	# Store references to undo/redo buttons for state management
	parent.undo_btn = undo_btn
	parent.redo_btn = redo_btn
	
	# Connect buttons to parent methods
	new_btn.clicked.connect(parent.new_coa)
	open_btn.clicked.connect(parent.load_coa)
	save_btn.clicked.connect(parent.save_coa)
	undo_btn.clicked.connect(parent.undo)
	redo_btn.clicked.connect(parent.redo)
	
	# Initially disable undo/redo
	undo_btn.setEnabled(False)
	redo_btn.setEnabled(False)
	
	toolbar.addWidget(new_btn)
	toolbar.addWidget(open_btn)
	toolbar.addWidget(save_btn)
	toolbar.addSeparator()
	toolbar.addWidget(undo_btn)
	toolbar.addWidget(redo_btn)
	
	# Add spacer to push copy/paste to the right
	spacer_widget = QWidget()
	spacer_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
	toolbar.addWidget(spacer_widget)
	
	# Add copy/paste buttons on the right
	toolbar.addSeparator()
	copy_btn = QPushButton("Copy to Clipboard")
	paste_btn = QPushButton("Paste from Clipboard")
	
	# Connect copy/paste to parent methods
	copy_btn.clicked.connect(parent.copy_coa)
	paste_btn.clicked.connect(parent.paste_coa)
	
	toolbar.addWidget(copy_btn)
	toolbar.addWidget(paste_btn)
	
	return toolbar
