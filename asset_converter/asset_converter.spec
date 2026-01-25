# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for CK3 Asset Converter

This builds the asset converter executable with DDS loading capabilities.
Run with: pyinstaller asset_converter.spec
"""

import os
base_dir = os.path.dirname(os.path.abspath(SPECPATH))

block_cipher = None

a = Analysis(
    ['asset_converter.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PyQt5.sip',
        'imageio',
        'imageio.plugins',
        'imageio.core',
        'imageio_dds',
        'PIL',
        'PIL.Image',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'OpenGL',  # Not needed for asset converter
        'PyQt5.QtOpenGL',  # Not needed for asset converter
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
    name='AssetConverter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI app - no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(base_dir, 'icon_assets.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AssetConverter',
)
