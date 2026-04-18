import re
import shutil
import sys
from pathlib import Path
from typing import Any, Optional

import tomlkit
from PySide6 import QtCore
from platformdirs import user_data_dir


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False)) and hasattr(sys, "_MEIPASS")


# Bundled resources (icons, default config template when frozen)
if _is_frozen():
    ROOT = Path(sys._MEIPASS)
    WRITABLE_ROOT = Path(sys.executable).resolve().parent
else:
    ROOT = Path(__file__).resolve().parent
    WRITABLE_ROOT = ROOT

CONFIG_PATH = WRITABLE_ROOT / "config.toml"
DEBUG_LOG_PATH = WRITABLE_ROOT / "debug.log"
BIN_DIR = Path(user_data_dir("yt-dlp-gui"))  # user data dir for persistence


def ensure_config_file() -> None:
    """When frozen, copy bundled ``config.toml`` next to the exe if none exists yet."""
    if not _is_frozen():
        return
    bundled = ROOT / "config.toml"
    if CONFIG_PATH.exists() or not bundled.is_file():
        return
    try:
        shutil.copy(bundled, CONFIG_PATH)
    except OSError:
        pass

_INVALID_FOLDER_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_preset_folder_name(preset: str) -> str:
    """Make a single path segment from a preset name (Windows-safe)."""
    s = (preset or "").strip()
    if not s:
        return "downloads"
    s = _INVALID_FOLDER_CHARS.sub("_", s)
    s = s.rstrip(". ")
    return s or "downloads"


# Shown in the preset dropdown and on download cards; config keys stay short (best, mp4, …).
_DEFAULT_PRESET_LABELS: dict[str, str] = {
    "best": "Highest quality (video + audio)",
    "mp4": "MP4 (H.264 video)",
    "mp3": "MP3 (audio, ID3 + cover)",
}


def preset_ui_label(config: dict, key: str) -> str:
    """Human-readable label for preset ``key``; falls back to title-cased key."""
    k = (key or "").strip()
    if not k:
        return ""
    raw = config.get("preset_labels")
    if raw is not None:
        try:
            v = raw.get(k) if hasattr(raw, "get") else None
            if v is not None and str(v).strip():
                return str(v).strip()
        except (TypeError, KeyError, AttributeError):
            pass
    return _DEFAULT_PRESET_LABELS.get(k, k.replace("_", " ").title())


DEFAULT_DOWNLOAD_CATEGORIES: list[dict[str, Any]] = [
    {
        "name": "Music",
        "use_custom_path": False,
        "path": "",
        "use_custom_filename": False,
        "output_name_tokens": [],
    },
    {
        "name": "Movies",
        "use_custom_path": False,
        "path": "",
        "use_custom_filename": False,
        "output_name_tokens": [],
    },
    {
        "name": "Gameplay",
        "use_custom_path": False,
        "path": "",
        "use_custom_filename": False,
        "output_name_tokens": [],
    },
    {
        "name": "Guides",
        "use_custom_path": False,
        "path": "",
        "use_custom_filename": False,
        "output_name_tokens": [],
    },
]


def ensure_download_categories(config: dict) -> list:
    """Ensure ``config['categories']`` exists and return it as a list of dict rows."""
    raw = config.get("categories")
    if not isinstance(raw, list) or not raw:
        config["categories"] = [dict(x) for x in DEFAULT_DOWNLOAD_CATEGORIES]
        return config["categories"]
    out: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "")).strip()
        if not name:
            continue
        _tokens = row.get("output_name_tokens")
        if isinstance(_tokens, list):
            tok_list = [str(x).strip() for x in _tokens if str(x).strip()]
        else:
            tok_list = []
        out.append(
            {
                "name": name,
                "use_custom_path": bool(row.get("use_custom_path", False)),
                "path": str(row.get("path") or ""),
                "use_custom_filename": bool(row.get("use_custom_filename", False)),
                "output_name_tokens": tok_list,
            }
        )
    if not out:
        config["categories"] = [dict(x) for x in DEFAULT_DOWNLOAD_CATEGORIES]
        return config["categories"]
    config["categories"] = out
    return out


def resolve_download_base_path(
    config: dict, default_base: str, category: Optional[str]
) -> str:
    """Directory used before optional preset subfolder: per-category path or default save folder."""
    base = (default_base or "").strip()
    if not category:
        return base
    for row in ensure_download_categories(config):
        if row.get("name") != category:
            continue
        if row.get("use_custom_path") and str(row.get("path", "")).strip():
            return str(Path(str(row["path"])).expanduser())
        break
    return base


def general_ytdlp_cli_args(config: dict) -> list[str]:
    """Extra yt-dlp flags from ``[general]`` (before user ``global_args``)."""
    g = config.get("general") or {}
    out: list[str] = []

    if not bool(g.get("continue_partial", True)):
        out.append("--no-continue")
    if bool(g.get("no_overwrites", True)):
        out.append("--no-overwrites")
    if bool(g.get("restrict_filenames", False)):
        out.append("--restrict-filenames")
    win_fn = g.get("windows_filenames")
    if win_fn is None:
        win_fn = sys.platform == "win32"
    if bool(win_fn):
        out.append("--windows-filenames")

    try:
        r = int(g.get("retries", 10))
        if r >= 0:
            out += ["--retries", str(min(r, 999))]
    except (TypeError, ValueError):
        out += ["--retries", "10"]
    try:
        fr = int(g.get("fragment_retries", 10))
        if fr >= 0:
            out += ["--fragment-retries", str(min(fr, 999))]
    except (TypeError, ValueError):
        out += ["--fragment-retries", "10"]
    try:
        cf = int(g.get("concurrent_fragments", 1))
        if cf >= 2:
            out += ["--concurrent-fragments", str(min(cf, 32))]
    except (TypeError, ValueError):
        pass

    arch = str(g.get("download_archive") or "").strip()
    if arch:
        p = Path(arch).expanduser()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        out += ["--download-archive", str(p)]

    return out


def effective_download_path(base_path: str, preset: str, sort_by_preset: bool) -> str:
    """Return the folder used for ``-P``; creates subfolder ``<preset>/`` when ``sort_by_preset``."""
    base = Path(base_path).expanduser()
    if sort_by_preset:
        dest = base / sanitize_preset_folder_name(preset)
    else:
        dest = base
    dest.mkdir(parents=True, exist_ok=True)
    return str(dest.resolve())


def load_toml(path):
    with open(path, "r", encoding="utf-8") as file:
        return tomlkit.parse(file.read())


def save_toml(path, data):
    with open(path, "w", encoding="utf-8") as file:
        file.write(tomlkit.dumps(data))


class ItemRoles:
    IdRole = QtCore.Qt.UserRole
    LinkRole = QtCore.Qt.UserRole + 1
    PathRole = QtCore.Qt.UserRole + 2
    CategoryRole = QtCore.Qt.UserRole + 3


class TreeColumn:
    TITLE = 0
    CATEGORY = 1
    PRESET = 2
    SIZE = 3
    PROGRESS = 4
    STATUS = 5
    SPEED = 6
    ETA = 7
