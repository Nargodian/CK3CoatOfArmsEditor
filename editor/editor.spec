# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for CK3 Coat of Arms Editor

This builds the main editor executable with bundled shaders.
Run with: pyinstaller editor.spec
"""

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/shaders', 'shaders'),  # Bundle shaders into executable
    ],
    hiddenimports=[
        'PyQt5.sip',
        'PyQt5.QtOpenGL',
        'OpenGL',
        'OpenGL.GL',
        'OpenGL.GLU',
        'PIL',
        'PIL.Image',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'imageio',  # Not needed for editor
        'imageio_dds',  # Not needed for editor
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CoatOfArmsEditor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # TODO: Add icon file if available
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CoatOfArmsEditor',
)
