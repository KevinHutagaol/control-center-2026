# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

project_root = os.getcwd()

def add_tree(datas_list, src_dir, dest_prefix):
    """Append (src_file, dest_dir) for every file under src_dir."""
    src_dir = Path(src_dir)
    if not src_dir.is_dir():
        return
    for p in src_dir.rglob("*"):
        if p.is_file():
            rel_subdir = str(p.parent.relative_to(src_dir)).replace("\\", "/")
            dest_dir = os.path.join(dest_prefix, rel_subdir) if rel_subdir != "." else dest_prefix
            datas_list.append((str(p), dest_dir))

datas = []
datas.append((os.path.join(project_root, "firebaseAuth.json"), "."))
datas.append((os.path.join(project_root, "app-config.json"), "."))

home_ui     = os.path.join(project_root, "pages", "Home",    "UI_home")
home_nilai  = os.path.join(project_root, "pages", "Home",    "Nilai_home")
m4_asset    = os.path.join(project_root, "pages", "Modul4",  "Asset")
m4_ui       = os.path.join(project_root, "pages", "Modul4",  "ui")
m7_ui       = os.path.join(project_root, "pages", "Modul7",  "UI")
m910_asset  = os.path.join(project_root, "pages", "Modul910","asset")
m910_ui     = os.path.join(project_root, "pages", "Modul910","ui_910")

add_tree(datas, home_ui,    os.path.join("pages", "Home",    "UI_home"))
add_tree(datas, home_nilai, os.path.join("pages", "Home",    "Nilai_home"))
add_tree(datas, m4_asset,   os.path.join("pages", "Modul4",  "Asset"))
add_tree(datas, m4_ui,      os.path.join("pages", "Modul4",  "ui"))
add_tree(datas, m7_ui,      os.path.join("pages", "Modul7",  "UI"))
add_tree(datas, m910_asset, os.path.join("pages", "Modul910","asset"))
add_tree(datas, m910_ui,    os.path.join("pages", "Modul910","ui_910"))
add_tree(datas, os.path.join(project_root, "public"), "public")


hidden = []
hidden += collect_submodules('pages')
hidden += ['pages.Home.resources_rc']

a = Analysis(
    ['pages/Home/main.py'],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

# ONEFILE build: include binaries & datas here, and don't use COLLECT
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    getattr(a, "zipfiles", []),  # safe for all versions
    a.datas,
    [],
    name="ControlCenter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,          # ok even if UPX isn’t installed; it’ll just skip
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
)

# NOTE: no COLLECT() for onefile
