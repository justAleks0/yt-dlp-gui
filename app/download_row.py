"""Single download entry: preview-style card (thumb + meta) with progress and status."""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from output_name_tokens import preview_output_filepath
from utils import (
    ItemRoles,
    TreeColumn,
    effective_download_path,
    resolve_download_base_path,
)

logger = logging.getLogger(__name__)


def _scale_thumb_pixmap(pm: QtGui.QPixmap, lb: QtWidgets.QLabel) -> QtGui.QPixmap:
    mx, my = lb.maximumSize().width(), lb.maximumSize().height()
    cw, ch = lb.width(), lb.height()
    tw = mx if cw <= 0 else min(mx, max(lb.minimumSize().width(), cw))
    th = my if ch <= 0 else min(my, max(lb.minimumSize().height(), ch))
    tw, th = max(tw, 1), max(th, 1)
    return pm.scaled(
        tw,
        th,
        QtCore.Qt.AspectRatioMode.KeepAspectRatio,
        QtCore.Qt.TransformationMode.SmoothTransformation,
    )


class DownloadRowFrame(QtWidgets.QFrame):
    """Queued/active download with the same visual cues as the URL preview panel."""

    def __init__(
        self,
        parent: QtWidgets.QWidget | None,
        download_id: int,
        link: str,
        category_display: str,
        preset_key: str,
        preset_display: str,
        *,
        preview_meta: Optional[Mapping[str, Any]] = None,
        preview_thumb_bytes: Optional[bytes] = None,
        yt_info: Optional[Mapping[str, Any]] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("downloadRow")
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Minimum,
        )

        self._id = download_id
        self._link = link
        self._path_role = ""
        self._category_key: str | None = None
        self._preset_key = preset_key

        self._cat_display = category_display
        self._preset_display = preset_display
        self._status_plain = "Queued"
        self._size_plain = "-"
        self._speed_plain = "-"
        self._eta_plain = "-"

        self._yt_info: dict[str, Any] | None = (
            dict(yt_info) if isinstance(yt_info, Mapping) else None
        )

        root = QtWidgets.QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(8, 6, 8, 6)

        row_preview = QtWidgets.QHBoxLayout()
        row_preview.setSpacing(10)

        self._lb_thumb = QtWidgets.QLabel(self)
        self._lb_thumb.setObjectName("downloadRowThumb")
        self._lb_thumb.setMinimumSize(QtCore.QSize(112, 63))
        self._lb_thumb.setMaximumSize(QtCore.QSize(176, 99))
        self._lb_thumb.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._lb_thumb.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._lb_thumb.setScaledContents(False)
        self._lb_thumb.setStyleSheet(
            "QLabel { background-color: palette(base); border: 1px solid palette(mid); border-radius: 3px; }"
        )

        text_col = QtWidgets.QVBoxLayout()
        text_col.setSpacing(6)
        text_col.setContentsMargins(0, 0, 0, 0)

        row_title_status = QtWidgets.QHBoxLayout()
        row_title_status.setSpacing(8)

        self._lb_video_title = QtWidgets.QLabel(self)
        self._lb_video_title.setWordWrap(True)
        self._lb_video_title.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        tf = self._lb_video_title.font()
        tf.setBold(True)
        self._lb_video_title.setFont(tf)

        self._lb_status = QtWidgets.QLabel(self._status_plain)
        self._lb_status.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTop
        )
        self._lb_status.setWordWrap(False)
        st_font = self._lb_status.font()
        st_font.setBold(True)
        self._lb_status.setFont(st_font)
        self._lb_status.setMinimumWidth(72)

        row_title_status.addWidget(self._lb_video_title, stretch=1)
        row_title_status.addWidget(self._lb_status, stretch=0)

        self._lb_secondary_meta = QtWidgets.QLabel(self)
        self._lb_secondary_meta.setWordWrap(True)
        self._lb_secondary_meta.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._lb_outfile = QtWidgets.QLabel(self)
        self._lb_outfile.setWordWrap(True)
        self._lb_outfile.setStyleSheet("color: palette(mid);")
        self._lb_outfile.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._lb_link = QtWidgets.QLabel(self)
        self._lb_link.setWordWrap(True)
        self._lb_link.setStyleSheet("color: palette(mid); font-size: 8pt;")
        self._lb_link.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )

        text_col.addLayout(row_title_status)
        text_col.addWidget(self._lb_secondary_meta)
        text_col.addWidget(self._lb_outfile)
        text_col.addWidget(self._lb_link)

        row_preview.addWidget(self._lb_thumb)
        row_preview.addLayout(text_col, stretch=1)

        root.addLayout(row_preview)

        self._lb_details = QtWidgets.QLabel()
        self._lb_details.setWordWrap(False)
        self._lb_details.setStyleSheet("color: palette(mid);")
        self._sync_details_label()
        root.addWidget(self._lb_details)

        self._lb_stats = QtWidgets.QLabel()
        self._lb_stats.setWordWrap(False)
        self._lb_stats.setStyleSheet("color: palette(mid);")
        self._sync_stats_label()
        root.addWidget(self._lb_stats)

        self._progress = QtWidgets.QProgressBar()
        self._progress.setMaximumHeight(14)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet("QProgressBar { margin-top: 2px; }")
        root.addWidget(self._progress)

        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)

        self._apply_preview_visuals(preview_meta, preview_thumb_bytes, link)

    def _apply_preview_visuals(
        self,
        preview_meta: Optional[Mapping[str, Any]],
        thumb_bytes: Optional[bytes],
        link: str,
    ) -> None:
        meta = preview_meta or {}
        t = (meta.get("title") or "").strip()
        self._lb_video_title.setText(t if t else link)
        lines: list[str] = []
        u = (meta.get("uploader") or "").strip()
        if u:
            lines.append(u)
        d = (meta.get("duration_string") or "").strip()
        if d:
            lines.append(d)
        vid = (meta.get("id") or "").strip()
        if vid:
            lines.append(f"ID: {vid}")
        sec = "\n".join(lines)
        self._lb_secondary_meta.setText(sec)
        self._lb_secondary_meta.setVisible(bool(sec))
        self._lb_link.setText(link)
        if thumb_bytes:
            pm = QtGui.QPixmap()
            if pm.loadFromData(bytes(thumb_bytes)):
                self._lb_thumb.setPixmap(_scale_thumb_pixmap(pm, self._lb_thumb))
            else:
                self._lb_thumb.clear()
        else:
            self._lb_thumb.clear()

    def refresh_outfile_preview(self, config: dict, save_folder: str) -> None:
        cat = self.data(0, ItemRoles.CategoryRole)
        cat_key = cat if isinstance(cat, str) and cat.strip() else None
        preset_key = self._preset_key
        sf = (save_folder or "").strip()
        if self._yt_info:
            try:
                path = preview_output_filepath(
                    config,
                    save_folder=sf,
                    category_key=cat_key,
                    preset_key=preset_key,
                    info=self._yt_info,
                )
            except OSError:
                logger.debug("Queue row outfile preview failed", exc_info=True)
                self._lb_outfile.setTextFormat(QtCore.Qt.TextFormat.PlainText)
                self._lb_outfile.setText(
                    "Output file (estimate): (could not resolve save folder)"
                )
                return
            self._lb_outfile.setTextFormat(QtCore.Qt.TextFormat.PlainText)
            self._lb_outfile.setText(
                "Output file (estimate):\n"
                f"{path}\n"
                "Final name may differ slightly after yt-dlp filename rules."
            )
            return
        if not sf:
            self._lb_outfile.clear()
            return
        resolved = resolve_download_base_path(config, sf, cat_key)
        sort_on = bool((config.get("general") or {}).get("download_sort_folders", True))
        folder = effective_download_path(resolved, preset_key, sort_on)
        self._lb_outfile.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self._lb_outfile.setText(f"Save folder:\n{folder}")

    def _sync_details_label(self) -> None:
        self._lb_details.setText(f"{self._cat_display} · {self._preset_display}")

    def _sync_stats_label(self) -> None:
        self._lb_stats.setText(
            f"Size {self._size_plain}   ·   Speed {self._speed_plain}   ·   ETA {self._eta_plain}"
        )

    @property
    def download_id(self) -> int:
        return self._id

    def data(self, _column: int, role: int):
        if role == ItemRoles.IdRole:
            return self._id
        if role == ItemRoles.LinkRole:
            return self._link
        if role == ItemRoles.PathRole:
            return self._path_role
        if role == ItemRoles.CategoryRole:
            return self._category_key
        return None

    def setData(self, _column: int, role: int, value) -> None:
        if role == ItemRoles.PathRole:
            self._path_role = str(value)
        elif role == ItemRoles.CategoryRole:
            self._category_key = value if isinstance(value, str) or value is None else None

    def title_for_log(self) -> str:
        t = self._lb_video_title.text().strip()
        return t if t else self._link

    def status_text(self) -> str:
        return self._status_plain

    def preset_text(self) -> str:
        """Config preset key (for paths and yt-dlp), not the human-readable label."""
        return self._preset_key

    def set_column_text(self, column: int, text: str) -> None:
        if column == TreeColumn.TITLE:
            self._lb_video_title.setText(text)
        elif column == TreeColumn.CATEGORY:
            self._cat_display = text
            self._sync_details_label()
        elif column == TreeColumn.PRESET:
            self._preset_display = text
            self._sync_details_label()
        elif column == TreeColumn.SIZE:
            self._size_plain = text
            self._sync_stats_label()
        elif column == TreeColumn.STATUS:
            self._status_plain = text
            self._lb_status.setText(text)
        elif column == TreeColumn.SPEED:
            self._speed_plain = text
            self._sync_stats_label()
        elif column == TreeColumn.ETA:
            self._eta_plain = text
            self._sync_stats_label()

    def set_progress_percent_str(self, percent: str) -> None:
        try:
            self._progress.setValue(round(float(percent.replace("%", ""))))
        except ValueError:
            pass
