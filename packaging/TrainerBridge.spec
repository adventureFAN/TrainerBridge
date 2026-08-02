# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path


# PyInstaller provides SPECPATH as the directory that contains this
# specification file. The project root is therefore one directory above
# packaging/.
PROJECT_ROOT = Path(SPECPATH).parent

block_cipher = None

analysis = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        (
            str(PROJECT_ROOT / "assets"),
            "assets"
        )
    ],
    hiddenimports=["zstandard"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0
)

pyz = PYZ(
    analysis.pure,
    analysis.zipped_data,
    cipher=block_cipher
)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="TrainerBridge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None
)

collection = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="TrainerBridge"
)
