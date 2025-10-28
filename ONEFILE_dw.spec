# -*- mode: python ; coding: utf-8 -*-

import os, sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

project_root = os.getcwd()
is_macos = sys.platform == "darwin"

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
m5_ui       = os.path.join(project_root, "pages", "Modul5",  "UI5")
m7_ui       = os.path.join(project_root, "pages", "Modul7",  "UI")
m910_asset  = os.path.join(project_root, "pages", "Modul910","asset")
m910_ui     = os.path.join(project_root, "pages", "Modul910","ui_910")

add_tree(datas, home_ui,    os.path.join("pages", "Home",    "UI_home"))
add_tree(datas, home_nilai, os.path.join("pages", "Home",    "Nilai_home"))
add_tree(datas, m4_asset,   os.path.join("pages", "Modul4",  "Asset"))
add_tree(datas, m4_ui,      os.path.join("pages", "Modul4",  "ui"))
add_tree(datas, m5_ui,      os.path.join("pages", "Modul5",  "UI5"))
add_tree(datas, m7_ui,      os.path.join("pages", "Modul7",  "UI"))
add_tree(datas, m910_asset, os.path.join("pages", "Modul910","asset"))
add_tree(datas, m910_ui,    os.path.join("pages", "Modul910","ui_910"))
add_tree(datas, os.path.join(project_root, "public"), "public")


hidden = []
hidden += collect_submodules('pages')
hidden += ['pages.Home.resources_rc']
hidden += ['pages.Modul5.mplwidget']
hidden += ['pages.Home.Modul5New']
hidden += ['pages.Home.myQRC']

icon_file = "icon.icns" if is_macos else "icon.ico"
if not os.path.exists(icon_file):
    icon_file = None

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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    exclude_binaries=False,
    icon=icon_file,
    console=False,
)

app = BUNDLE(
    exe,
    name="ControlCenter-arm64.app",
    icon=icon_file,
    bundle_identifier="com.example.controlcenter",
    info_plist={
        "NSHighResolutionCapable": True,
        "CFBundleShortVersionString": os.environ.get("GITHUB_REF_NAME", "0.0.0"),
        "CFBundleVersion": os.environ.get("GITHUB_REF_NAME", "0.0.0"),
    },
)

coll = COLLECT(
    app,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="ControlCenter-arm64"
)