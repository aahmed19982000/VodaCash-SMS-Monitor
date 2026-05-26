# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['desktop\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('desktop/assets', 'desktop/assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DaftarCash',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='C:\\Users\\ahmed\\AppData\\Local\\Temp\\5bd0b103-30cd-4be3-9b08-339f6c85dda8',
    icon=['desktop\\assets\\logo.ico'],
)
