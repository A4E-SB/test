# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Himaya — single-folder exe (faster startup than onefile,
# and already satisfies "runs from a USB key"). For a single file use
# build_windows.bat --onefile.

import os

block_cipher = None
datas = [
    ("assets", "assets"),            # icon, fonts, optional tflite models
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=["customtkinter", "tkinterdnd2", "arabic_reshaper", "bidi"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # strip heavy unused packages to stay under ~100 MB
        "matplotlib", "tkinter.test", "unittest", "pydoc_data",
        "torch", "tensorflow", "IPython", "jupyter", "pytest",
        "setuptools", "pip", "lib2to3",
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
    name="Himaya",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                    # windowed app: no terminal on launch
    disable_windowed_traceback=False,
    icon=os.path.join("assets", "icon.ico") if os.path.exists(os.path.join("assets", "icon.ico")) else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Himaya",
)
