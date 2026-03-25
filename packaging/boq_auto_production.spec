# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


repo_root = Path.cwd()
launch_script = repo_root / "launch_production.py"
datas = [
    (str(repo_root / "config"), "config"),
    (str(repo_root / "database"), "database"),
    (str(repo_root / "templates"), "templates"),
    (str(repo_root / "docs"), "docs"),
]

hiddenimports = [
    "streamlit",
    "streamlit.web",
    "streamlit.web.cli",
    "streamlit.runtime",
    "openpyxl",
    "rapidfuzz",
    "yaml",
    "fitz",
    "pytesseract",
]

a = Analysis(
    [str(launch_script)],
    pathex=[str(repo_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BOQ AUTO",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="BOQ AUTO Production",
)
