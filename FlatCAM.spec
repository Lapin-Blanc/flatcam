# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for FlatCAM (onedir bundle).
#
# Build with:  pyinstaller FlatCAM.spec
# Output:      dist/FlatCAM/  (run dist/FlatCAM/flatcam)
#
# Notes:
# - onedir (not onefile): FlatCAMApp chdir()s to os.path.dirname(sys.executable)
#   and loads icons via relative "share/<file>" paths, so share/ must sit next
#   to the executable — which onedir provides and onefile (run from a temp
#   _MEIPASS dir) does not.
# - tclCommands are imported dynamically (importlib), so collect them explicitly.

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hiddenimports = collect_submodules('tclCommands')

datas = [
    ('share', 'share'),   # icons/cursors, loaded via relative paths at runtime
]

a = Analysis(
    ['flatcam_run.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter.test', 'sandbox', 'tests'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='flatcam',
    debug=False,
    strip=False,
    upx=False,
    console=True,   # keeps the log/TCL output visible; set False for a release
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='FlatCAM',
)
