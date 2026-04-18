"""Background fetch of video metadata + thumbnail for the URL field preview."""

from __future__ import annotations

import json
import logging
import subprocess as sp
import sys
import urllib.request
from typing import Any, Optional

from PySide6.QtCore import QObject, QThread, Signal

from dep_dl import resolve_ytdlp_argv

logger = logging.getLogger(__name__)


def normalize_url_input(raw: str) -> str:
    """Single URL: first non-empty line only (handles accidental newline paste)."""
    s = (raw or "").strip()
    if not s:
        return ""
    return s.splitlines()[0].strip()


def _pick_thumbnail_url(info: dict[str, Any]) -> Optional[str]:
    u = info.get("thumbnail")
    if isinstance(u, str) and u.startswith("http"):
        return u
    thumbs = info.get("thumbnails")
    if not isinstance(thumbs, list) or not thumbs:
        return None
    best: Optional[tuple[int, str]] = None
    for t in thumbs:
        if not isinstance(t, dict):
            continue
        url = t.get("url")
        if not isinstance(url, str) or not url.startswith("http"):
            continue
        w = t.get("width")
        try:
            wi = int(w) if w is not None else 0
        except (TypeError, ValueError):
            wi = 0
        if best is None or wi > best[0]:
            best = (wi, url)
    return best[1] if best else None


class LinkPreviewWorker(QThread):
    """Runs yt-dlp --dump-single-json and optionally downloads the thumbnail."""

    # generation, normalized URL, summary meta, thumb_bytes|None, full yt-dlp info (filename preview)
    preview_ready = Signal(int, str, dict, object, object)
    preview_failed = Signal(int, str)

    def __init__(self, url: str, generation: int, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._url = url
        self._gen = generation

    def run(self) -> None:
        cmd = list(resolve_ytdlp_argv()) + [
            "--skip-download",
            "--dump-single-json",
            "--no-playlist",
            "--no-warnings",
            "--",
            self._url,
        ]
        create = sp.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            proc = sp.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=35,
                creationflags=create,
            )
        except sp.TimeoutExpired:
            self.preview_failed.emit(self._gen, "Preview timed out (yt-dlp).")
            return
        except OSError as e:
            self.preview_failed.emit(self._gen, f"Could not run yt-dlp: {e}")
            return

        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()
            err = err[:800] if err else f"yt-dlp exited with code {proc.returncode}"
            self.preview_failed.emit(self._gen, err)
            return

        raw = (proc.stdout or "").strip()
        if not raw:
            self.preview_failed.emit(self._gen, "No data from yt-dlp.")
            return

        try:
            data: Any = json.loads(raw)
        except json.JSONDecodeError:
            self.preview_failed.emit(self._gen, "Could not read video information.")
            return

        if not isinstance(data, dict):
            self.preview_failed.emit(self._gen, "Unexpected response from yt-dlp.")
            return

        if data.get("_type") == "playlist" and data.get("entries"):
            ent = data["entries"][0]
            if isinstance(ent, dict):
                data = ent
            else:
                self.preview_failed.emit(
                    self._gen,
                    "That URL is a playlist. Paste a single video link to preview it.",
                )
                return

        thumb_url = _pick_thumbnail_url(data)
        thumb_bytes: Optional[bytes] = None
        if thumb_url:
            try:
                req = urllib.request.Request(
                    thumb_url,
                    headers={"User-Agent": "yt-dlp-gui/1.0 (preview)"},
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    thumb_bytes = resp.read(1_500_000)
            except Exception:
                logger.debug("Thumbnail fetch failed", exc_info=True)

        meta = {
            "title": str(data.get("title") or ""),
            "uploader": str(data.get("uploader") or data.get("channel") or ""),
            "duration_string": str(data.get("duration_string") or ""),
            "id": str(data.get("id") or ""),
        }
        self.preview_ready.emit(self._gen, self._url, meta, thumb_bytes, dict(data))
