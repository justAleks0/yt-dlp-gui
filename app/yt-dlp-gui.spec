# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — build from the app/ directory:
#   cd app && pyinstaller yt-dlp-gui.spec
#
# Output: dist/yt-dlp-gui/yt-dlp-gui.exe (onedir; config.toml + debug.log live beside the exe)

from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas = [
    ("config.toml", "."),
    ("assets", "assets"),
]

pys_datas, pys_binaries, pys_hiddenimports = collect_all("PySide6")
qa_datas, qa_binaries, qa_hiddenimports = collect_all("qtawesome")

hiddenimports = sorted(
    {
        *pys_hiddenimports,
        *qa_hiddenimports,
        "settings_dialog",
        "output_name_tokens",
        "filename_pattern_widget",
        "link_preview",
        "download_row",
        "dep_dl",
        "worker",
        "ui.main_window",
        "ui",
        "tomlkit",
        "requests",
        "certifi",
        "charset_normalizer",
        "idna",
        "urllib3",
    }
)

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=pys_binaries + qa_binaries,
    datas=datas + pys_datas + qa_datas,
    hiddenimports=list(hiddenimports),
    hookspath=[],
    hooksconfig={},
    runtime_tmpdir=None,
    excludes=[],
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
    name="yt-dlp-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/yt-dlp-gui.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="yt-dlp-gui",
)
