# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect additional data files and plugins
_mpl_datas = collect_data_files('matplotlib')
# Comprehensive PySide6 hidden imports (widgets, multimedia, etc.)
_pyside6_modules = collect_submodules('PySide6')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    # Do NOT bundle external 'assets' and 'data' (keep them next to the exe for onefile)
    datas=_mpl_datas,
    hiddenimports=['PySide6', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'PySide6.QtMultimedia', 'matplotlib.backends.backend_qt5agg', 'PIL.Image', 'PIL.ImageFilter', 'PIL.ImageDraw'] + _pyside6_modules,
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
    name='SkiJumpingSimulator',
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
    icon=['assets\\SJS.ico'],
)
