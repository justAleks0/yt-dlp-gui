"""Enumerate playlist entries with yt-dlp (flat playlist JSON lines)."""

from __future__ import annotations

import json
import logging
import subprocess as sp
import sys
from typing import Any, Optional

from PySide6.QtCore import QObject, QThread, Signal

from dep_dl import resolve_ytdlp_argv

logger = logging.getLogger(__name__)


def _entry_watch_url(obj: dict[str, Any]) -> Optional[str]:
    """Pick a per-video URL from a flat playlist entry."""
    for k in ("url", "original_url", "webpage_url"):
        u = obj.get(k)
        if isinstance(u, str) and u.startswith("http"):
            return u.strip()
    ie = obj.get("ie_key") or obj.get("extractor_key")
    vid = obj.get("id")
    if isinstance(vid, str) and vid.strip():
        ie_s = str(ie).lower() if ie else ""
        if "youtube" in ie_s:
            return f"https://www.youtube.com/watch?v={vid.strip()}"
    return None


class PlaylistExpandWorker(QThread):
    """Runs yt-dlp --flat-playlist --dump-json and emits one dict per playlist entry."""

    entries_ready = Signal(int, list)
    expand_failed = Signal(int, str)

    def __init__(self, playlist_url: str, generation: int, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._url = playlist_url
        self._gen = generation
        self._proc: Optional[sp.Popen[str]] = None

    def run(self) -> None:
        cmd = list(resolve_ytdlp_argv()) + [
            "--skip-download",
            "--flat-playlist",
            "--dump-json",
            "--no-warnings",
            "--",
            self._url,
        ]
        create = sp.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        entries: list[dict[str, Any]] = []
        err_tail = ""
        try:
            self._proc = sp.Popen(
                cmd,
                stdout=sp.PIPE,
                stderr=sp.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=create,
            )
        except OSError as e:
            self.expand_failed.emit(self._gen, f"Could not run yt-dlp: {e}")
            return

        proc = self._proc
        assert proc.stdout is not None
        interrupted = False
        for line in proc.stdout:
            if self.isInterruptionRequested():
                interrupted = True
                break
            line = line.strip()
            if not line:
                continue
            try:
                obj: Any = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            et = obj.get("_type")
            if et not in (None, "url"):
                continue
            if obj.get("live_status") == "is_live":
                continue
            watch = _entry_watch_url(obj)
            if not watch:
                continue
            entries.append(dict(obj))

        stderr_b = ""
        if interrupted:
            try:
                proc.terminate()
            except OSError:
                pass

        if proc.stderr:
            try:
                stderr_b = proc.stderr.read()
            except Exception:
                stderr_b = ""
        try:
            proc.wait(timeout=5)
        except sp.TimeoutExpired:
            proc.kill()
            proc.wait()
        if stderr_b:
            err_tail = stderr_b.strip()[-1200:]

        if interrupted or self.isInterruptionRequested():
            self.entries_ready.emit(self._gen, [])
            return

        if proc.returncode != 0:
            msg = err_tail or f"yt-dlp exited with code {proc.returncode}"
            logger.error("playlist expand failed: %s", msg)
            self.expand_failed.emit(self._gen, msg)
            return

        if len(entries) < 2:
            self.entries_ready.emit(self._gen, [])
            return

        self.entries_ready.emit(self._gen, entries)

    def request_stop(self) -> None:
        self.requestInterruption()
        proc = self._proc
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except OSError:
                pass
