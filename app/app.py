import html
import logging
import sys
from pathlib import Path
from typing import Optional, Tuple

import qtawesome as qta
from dep_dl import (
    BundleReinstallWorker,
    DependencyCheckWorker,
    DepWorker,
    YtdlpInstallWorker,
    failed_bundle_components_from_rows,
)
from PySide6 import QtCore, QtGui, QtWidgets
from download_row import DownloadRowFrame
from link_preview import LinkPreviewWorker, normalize_url_input
from output_name_tokens import preview_output_filepath
from settings_dialog import PreferencesDialog
from ui.main_window import Ui_MainWindow
from utils import (
    BIN_DIR,
    CONFIG_PATH,
    DEBUG_LOG_PATH,
    ROOT,
    WRITABLE_ROOT,
    ensure_config_file,
    ensure_download_categories,
    ItemRoles,
    TreeColumn,
    effective_download_path,
    load_toml,
    preset_ui_label,
    resolve_download_base_path,
    save_toml,
)
from worker import DownloadWorker

__version__ = ""
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s (%(module)s:%(lineno)d) %(message)s",
    handlers=[
        logging.FileHandler(DEBUG_LOG_PATH, encoding="utf-8", delay=True),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def _deps_rows_to_html(rows: list) -> str:
    """``rows`` is ``list[tuple[str, bool, str]]`` from :class:`DependencyCheckWorker`."""
    lines = []
    all_ok = all(r[1] for r in rows)
    if all_ok:
        head = '<p style="margin:0 0 6px 0;color:#66bb6a;"><b>All checked dependencies are OK.</b></p>'
    else:
        head = (
            '<p style="margin:0 0 6px 0;color:#ef5350;"><b>Some dependencies are missing or not working.</b></p>'
        )
    for name, ok, detail in rows:
        color = "#66bb6a" if ok else "#ef5350"
        sym = "&#10003;" if ok else "&#10007;"
        lines.append(
            f'<span style="color:{color}">{sym}</span> '
            f"<b>{html.escape(name)}</b> &mdash; {html.escape(detail)}"
        )
    return head + "<br/>".join(lines)


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowIcon(QtGui.QIcon(str(ROOT / "assets" / "yt-dlp-gui.ico")))
        self.pb_add.setIcon(qta.icon("mdi6.plus"))
        self.pb_add.setIconSize(QtCore.QSize(21, 21))
        self.pb_clear.setIcon(qta.icon("mdi6.trash-can-outline"))
        self.pb_clear.setIconSize(QtCore.QSize(22, 22))
        self.pb_download.setIcon(qta.icon("mdi6.download"))
        self.pb_download.setIconSize(QtCore.QSize(22, 22))
        self.pb_install_ytdlp.setIcon(qta.icon("mdi6.tray-arrow-down"))
        self.pb_refresh_deps.setIcon(qta.icon("mdi6.refresh"))
        self.pb_reinstall_all.setIcon(qta.icon("mdi6.package-variant"))
        self.pb_reinstall_failed.setIcon(qta.icon("mdi6.wrench"))
        self.action_preferences.setShortcut(QtGui.QKeySequence("Ctrl+,"))
        self.lb_deps_status.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.te_link.setPlaceholderText(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        self.lb_link_preview_thumb.setStyleSheet(
            "QLabel { background-color: palette(base); border: 1px solid palette(mid); border-radius: 3px; }"
        )

        self.w_downloads_list.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Minimum,
        )
        self.te_link.setFocus()
        ensure_config_file()
        self.load_config()

        self.connect_ui()
        self.pb_download.setEnabled(False)
        self.pb_install_ytdlp.setEnabled(False)
        self.pb_reinstall_all.setEnabled(False)
        self.pb_reinstall_failed.setEnabled(False)
        self._last_dep_rows: list = []
        self.ytdlp_install_worker = None
        self.bundle_reinstall_worker = None
        self._deps_worker = None
        self._deps_refresh_pending = False
        self._downloads_enabled = False
        self._reinstall_busy = False
        self.show()

        self.dep_worker = DepWorker(self.config["general"]["update_ytdlp"])
        self.dep_worker.finished.connect(self.on_dep_finished)
        self.dep_worker.progress.connect(self.on_dep_progress)
        self.dep_worker.start()

        self.to_dl = {}
        self.workers = {}
        self.index = 0

        self._link_preview_gen = 0
        self._link_preview_worker: Optional[LinkPreviewWorker] = None
        self._link_preview_timer = QtCore.QTimer(self)
        self._link_preview_timer.setSingleShot(True)
        self._link_preview_timer.timeout.connect(self._fetch_link_preview)
        self._preview_yt_info: Optional[dict] = None
        self._link_preview_last_url: Optional[str] = None
        self._link_preview_meta_dict: Optional[dict] = None
        self._link_preview_thumb_bytes: Optional[bytes] = None
        self.lb_link_preview_outfile.setStyleSheet("color: palette(mid);")

    def connect_ui(self):
        # buttons
        self.pb_path.clicked.connect(self.button_path)
        self.pb_add.clicked.connect(self.button_add)
        self.pb_clear.clicked.connect(self.button_clear)
        self.pb_download.clicked.connect(self.button_download)
        self.pb_install_ytdlp.clicked.connect(self.button_install_ytdlp)
        self.pb_refresh_deps.clicked.connect(self.refresh_dependency_status)
        self.pb_reinstall_all.clicked.connect(self.button_reinstall_all)
        self.pb_reinstall_failed.clicked.connect(self.button_reinstall_failed)
        self.action_preferences.triggered.connect(self.open_preferences)

        # menu bar
        self.action_open_bin_folder.triggered.connect(lambda: self.open_folder(BIN_DIR))
        self.action_open_log_folder.triggered.connect(
            lambda: self.open_folder(WRITABLE_ROOT)
        )
        self.action_exit.triggered.connect(self.close)
        self.action_about.triggered.connect(self.show_about)
        self.action_clear_url_list.triggered.connect(self._clear_url_field)
        self.te_link.textChanged.connect(self._schedule_link_preview)
        self.dd_category.currentIndexChanged.connect(
            lambda _i=None: self._update_link_preview_outfile_line()
        )
        self.dd_preset.currentIndexChanged.connect(
            lambda _i=None: self._update_link_preview_outfile_line()
        )
        self.le_path.textChanged.connect(self._on_save_path_text_changed)

    def on_dep_progress(self, status):
        self.statusBar.showMessage(status, 10000)

    def on_dep_finished(self):
        self.dep_worker.deleteLater()
        self._downloads_enabled = True
        self.pb_download.setEnabled(True)
        self.pb_install_ytdlp.setEnabled(True)
        self.pb_reinstall_all.setEnabled(True)
        self.refresh_dependency_status()
        self._schedule_link_preview()

    def _clear_url_field(self) -> None:
        self.te_link.clear()
        self._link_preview_timer.stop()
        self._link_preview_gen += 1
        self._reset_link_preview_ui()

    def _on_save_path_text_changed(self, _t: str = "") -> None:
        self._update_link_preview_outfile_line()
        self._refresh_queued_item_output_paths()

    def _reset_link_preview_ui(self) -> None:
        self._preview_yt_info = None
        self._link_preview_last_url = None
        self._link_preview_meta_dict = None
        self._link_preview_thumb_bytes = None
        self.lb_link_preview_thumb.clear()
        self.lb_link_preview_meta.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.lb_link_preview_meta.setText(
            "Paste a link above to see title, channel, and thumbnail before you add it to the queue."
        )
        self.lb_link_preview_outfile.clear()

    def _current_preset_key_for_preview(self) -> str:
        preset_key = self.dd_preset.currentData()
        if not isinstance(preset_key, str) or not preset_key.strip():
            preset_key = self.dd_preset.currentText().strip()
        return preset_key if preset_key else "best"

    def _current_category_key_for_preview(self) -> Optional[str]:
        cat_data = self.dd_category.currentData()
        if isinstance(cat_data, str) and cat_data.strip():
            return cat_data.strip()
        return None

    def _update_link_preview_outfile_line(self) -> None:
        info = self._preview_yt_info
        if not isinstance(info, dict) or not info:
            self.lb_link_preview_outfile.clear()
            return
        try:
            path = preview_output_filepath(
                self.config,
                save_folder=self.le_path.text(),
                category_key=self._current_category_key_for_preview(),
                preset_key=self._current_preset_key_for_preview(),
                info=info,
            )
        except OSError:
            logger.debug("Filename preview path error", exc_info=True)
            self.lb_link_preview_outfile.setText(
                "Output file (estimate): (could not resolve save folder)"
            )
            return
        self.lb_link_preview_outfile.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.lb_link_preview_outfile.setText(
            "Output file (estimate):\n"
            f"{path}\n"
            "Final name may differ slightly after yt-dlp filename rules."
        )

    def _schedule_link_preview(self) -> None:
        self._link_preview_timer.stop()
        url = normalize_url_input(self.te_link.text())
        if not url:
            self._link_preview_gen += 1
            self._reset_link_preview_ui()
            return
        self._link_preview_timer.start(550)

    def _fetch_link_preview(self) -> None:
        url = normalize_url_input(self.te_link.text())
        if not url:
            self._reset_link_preview_ui()
            return
        self._link_preview_gen += 1
        gen = self._link_preview_gen
        self.lb_link_preview_thumb.clear()
        self.lb_link_preview_meta.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.lb_link_preview_meta.setText("Loading preview…")
        self.lb_link_preview_outfile.clear()
        worker = LinkPreviewWorker(url, gen)
        worker.preview_ready.connect(self._on_link_preview_ready)
        worker.preview_failed.connect(self._on_link_preview_failed)
        worker.finished.connect(worker.deleteLater)
        self._link_preview_worker = worker
        worker.start()

    def _on_link_preview_ready(
        self, gen: int, url: str, meta: dict, thumb: object, yt_info: object
    ) -> None:
        if gen != self._link_preview_gen:
            return
        self._link_preview_last_url = normalize_url_input(url)
        self._link_preview_meta_dict = dict(meta) if isinstance(meta, dict) else None
        self._link_preview_thumb_bytes = (
            bytes(thumb) if isinstance(thumb, (bytes, bytearray)) else None
        )
        self._preview_yt_info = yt_info if isinstance(yt_info, dict) else None
        lines: list[str] = []
        t = (meta.get("title") or "").strip()
        if t:
            lines.append(t)
        u = (meta.get("uploader") or "").strip()
        if u:
            lines.append(u)
        d = (meta.get("duration_string") or "").strip()
        if d:
            lines.append(d)
        vid = (meta.get("id") or "").strip()
        if vid:
            lines.append(f"ID: {vid}")
        self.lb_link_preview_meta.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.lb_link_preview_meta.setText("\n".join(lines) if lines else "No details returned.")
        thumb_bytes = thumb if isinstance(thumb, (bytes, bytearray)) else None
        if thumb_bytes:
            pm = QtGui.QPixmap()
            if pm.loadFromData(bytes(thumb_bytes)):
                lb = self.lb_link_preview_thumb
                mx, my = lb.maximumSize().width(), lb.maximumSize().height()
                cw, ch = lb.width(), lb.height()
                tw = mx if cw <= 0 else min(mx, max(lb.minimumSize().width(), cw))
                th = my if ch <= 0 else min(my, max(lb.minimumSize().height(), ch))
                tw, th = max(tw, 1), max(th, 1)
                pm = pm.scaled(
                    tw,
                    th,
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation,
                )
                self.lb_link_preview_thumb.setPixmap(pm)
            else:
                self.lb_link_preview_thumb.clear()
        else:
            self.lb_link_preview_thumb.clear()
        self._update_link_preview_outfile_line()

    def _on_link_preview_failed(self, gen: int, message: str) -> None:
        if gen != self._link_preview_gen:
            return
        self._preview_yt_info = None
        self._link_preview_last_url = None
        self._link_preview_meta_dict = None
        self._link_preview_thumb_bytes = None
        self.lb_link_preview_thumb.clear()
        self.lb_link_preview_outfile.clear()
        self.lb_link_preview_meta.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        msg = (message or "Preview failed.").strip()
        if len(msg) > 600:
            msg = msg[:597] + "…"
        self.lb_link_preview_meta.setText(msg)

    def _set_reinstall_busy(self, busy: bool):
        self._reinstall_busy = busy
        self.pb_reinstall_all.setEnabled(not busy and self._downloads_enabled)
        self.pb_install_ytdlp.setEnabled(not busy and self._downloads_enabled)
        self.pb_refresh_deps.setEnabled(not busy)
        if self._downloads_enabled:
            self.pb_download.setEnabled(not busy)
        self._update_fix_failed_button()

    def _update_fix_failed_button(self):
        if not self._downloads_enabled or self._reinstall_busy:
            self.pb_reinstall_failed.setEnabled(False)
            return
        failed = failed_bundle_components_from_rows(self._last_dep_rows)
        self.pb_reinstall_failed.setEnabled(bool(failed))

    def refresh_dependency_status(self):
        if self._deps_worker and self._deps_worker.isRunning():
            self._deps_refresh_pending = True
            return

        self._deps_refresh_pending = False
        self.pb_refresh_deps.setEnabled(False)
        self.lb_deps_status.setText("<i>Checking dependencies…</i>")

        worker = DependencyCheckWorker()
        self._deps_worker = worker
        worker.result.connect(self._on_dependency_check_done)
        worker.finished.connect(self._on_dependency_check_worker_finished)
        worker.start()

    def _on_dependency_check_done(self, rows: list):
        self._last_dep_rows = list(rows)
        self.lb_deps_status.setText(_deps_rows_to_html(rows))
        self._update_fix_failed_button()
        all_ok = all(r[1] for r in rows)
        if all_ok:
            self.statusBar.showMessage("All dependencies OK.", 6000)
        else:
            self.statusBar.showMessage(
                "Some dependencies need attention — see the Dependencies section.",
                10000,
            )

    def _on_dependency_check_worker_finished(self):
        if not self._reinstall_busy:
            self.pb_refresh_deps.setEnabled(True)
        if self._deps_worker:
            self._deps_worker.deleteLater()
            self._deps_worker = None
        if self._deps_refresh_pending:
            self._deps_refresh_pending = False
            QtCore.QTimer.singleShot(0, self.refresh_dependency_status)

    def _bundle_reinstall_guards(self) -> bool:
        if self.bundle_reinstall_worker and self.bundle_reinstall_worker.isRunning():
            return False
        if self.ytdlp_install_worker and self.ytdlp_install_worker.isRunning():
            return False
        return True

    def _start_bundle_worker(self, only: Optional[Tuple[str, ...]]) -> None:
        self._set_reinstall_busy(True)
        worker = BundleReinstallWorker(only=only)
        self.bundle_reinstall_worker = worker
        worker.progress.connect(self.on_dep_progress)
        worker.finished_ok.connect(self._on_bundle_reinstall_ok)
        worker.finished_err.connect(self._on_bundle_reinstall_err)
        worker.finished.connect(self._on_bundle_reinstall_finished)
        worker.start()

    def button_reinstall_all(self):
        if not self._bundle_reinstall_guards():
            return

        confirm = QtWidgets.QMessageBox.question(
            self,
            "Re-install dependencies",
            "Remove existing copies and download fresh ffmpeg, ffprobe, deno, and yt-dlp "
            "into the app binaries folder?\n\n"
            "Old files and partial downloads are cleared first (no duplicates). "
            "This uses a lot of data and may take several minutes.",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if confirm != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        self._start_bundle_worker(None)

    def button_reinstall_failed(self):
        if not self._bundle_reinstall_guards():
            return

        failed = failed_bundle_components_from_rows(self._last_dep_rows)
        if not failed:
            QtWidgets.QMessageBox.information(
                self,
                "Fix failed only",
                "Nothing is marked failed yet. Click “Check again” to scan, then use this button "
                "if any tool shows a problem.",
            )
            return

        bullet = "\n".join(f"  • {name}" for name in failed)
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Fix failed only",
            "Remove existing copies and re-download only these tools?\n\n"
            f"{bullet}\n\n"
            "Each one is replaced in the app binaries folder (no duplicate files).",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if confirm != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        self._start_bundle_worker(failed)

    def _on_bundle_reinstall_ok(self, msg: str):
        self.statusBar.showMessage(msg, 20000)
        logger.info(msg)

    def _on_bundle_reinstall_err(self, msg: str):
        self.statusBar.showMessage("Re-install dependencies failed.", 12000)
        logger.error("bundle reinstall: %s", msg)
        QtWidgets.QMessageBox.critical(self, "Re-install dependencies", msg)

    def _on_bundle_reinstall_finished(self):
        self._set_reinstall_busy(False)
        if self.bundle_reinstall_worker:
            self.bundle_reinstall_worker.deleteLater()
            self.bundle_reinstall_worker = None
        self.refresh_dependency_status()

    def button_install_ytdlp(self):
        if self.ytdlp_install_worker and self.ytdlp_install_worker.isRunning():
            return
        if self.bundle_reinstall_worker and self.bundle_reinstall_worker.isRunning():
            return

        self.pb_install_ytdlp.setEnabled(False)
        worker = YtdlpInstallWorker()
        self.ytdlp_install_worker = worker
        worker.progress.connect(self.on_dep_progress)
        worker.finished_ok.connect(self._on_ytdlp_install_ok)
        worker.finished_err.connect(self._on_ytdlp_install_err)
        worker.finished.connect(self._on_ytdlp_install_worker_finished)
        worker.start()

    def _on_ytdlp_install_ok(self, msg: str):
        self.statusBar.showMessage(msg, 15000)
        logger.info(msg)

    def _on_ytdlp_install_err(self, msg: str):
        self.statusBar.showMessage("yt-dlp install failed.", 10000)
        logger.error("yt-dlp install failed: %s", msg)
        QtWidgets.QMessageBox.critical(self, "Install yt-dlp", msg)

    def _on_ytdlp_install_worker_finished(self):
        if not self._reinstall_busy:
            self.pb_install_ytdlp.setEnabled(True)
        if self.ytdlp_install_worker:
            self.ytdlp_install_worker.deleteLater()
            self.ytdlp_install_worker = None
        self.refresh_dependency_status()

    def open_folder(self, path):
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        QtGui.QDesktopServices.openUrl(
            QtCore.QUrl.fromLocalFile(str(p.resolve()))
        )

    def show_about(self):
        QtWidgets.QMessageBox.about(
            self,
            "About yt-dlp-gui",
            f'<a href="https://github.com/dsymbol/yt-dlp-gui">yt-dlp-gui</a> {__version__}<br><br>'
            "A GUI for yt-dlp written in PySide6.",
        )

    def open_menu_for_row(self, frame: DownloadRowFrame, position: QtCore.QPoint):
        menu = QtWidgets.QMenu()

        delete_action = menu.addAction(qta.icon("mdi6.trash-can"), "Delete")
        copy_url_action = menu.addAction(qta.icon("mdi6.content-copy"), "Copy URL")
        open_folder_action = menu.addAction(qta.icon("mdi6.folder-open"), "Open Folder")

        item_path = frame.data(0, ItemRoles.PathRole)
        item_link = frame.data(0, ItemRoles.LinkRole)
        action = menu.exec(frame.mapToGlobal(position))

        if action == delete_action:
            self.remove_item(frame)
        elif action == copy_url_action:
            QtWidgets.QApplication.clipboard().setText(item_link)
            logger.info(f"Copied URL to clipboard: {item_link}")
        elif action == open_folder_action:
            self.open_folder(item_path)
            logger.info(f"Opened folder: {item_path}")

    def remove_item(self, frame: DownloadRowFrame):
        item_id = frame.data(0, ItemRoles.IdRole)
        item_text = frame.title_for_log()

        logger.debug(f"Removing download ({item_id}): {item_text}")

        if worker := self.workers.get(item_id):
            worker.stop()

        self.to_dl.pop(item_id, None)
        self.vl_downloads.removeWidget(frame)
        frame.deleteLater()

    def button_path(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select a folder",
            self.le_path.text() or QtCore.QDir.homePath(),
            QtWidgets.QFileDialog.Option.ShowDirsOnly,
        )

        if path:
            self.le_path.setText(path)
            self.config["general"]["path"] = path
            self._refresh_queued_item_output_paths()

    def button_add(self):
        missing = []
        preset_key = self.dd_preset.currentData()
        if not isinstance(preset_key, str) or not preset_key.strip():
            preset_key = self.dd_preset.currentText().strip()
        preset_display = preset_ui_label(self.config, preset_key)
        link = normalize_url_input(self.te_link.text())
        path = self.le_path.text()
        cat_data = self.dd_category.currentData()
        cat_key = cat_data if isinstance(cat_data, str) and cat_data.strip() else None
        cat_display = self._category_label_for_data(cat_data)

        if not link:
            missing.append("Video URL")
        if not path:
            missing.append("Save to")

        if missing:
            missing_fields = ", ".join(missing)
            return QtWidgets.QMessageBox.information(
                self,
                "Application Message",
                f"Required field{'s' if len(missing) > 1 else ''} ({missing_fields}) missing.",
            )

        # Snapshot preview data before clearing the URL field (reset clears these buffers).
        snap_ok = self._link_preview_last_url == link
        meta_snap = (
            dict(self._link_preview_meta_dict)
            if snap_ok and isinstance(self._link_preview_meta_dict, dict)
            else None
        )
        thumb_snap = (
            bytes(self._link_preview_thumb_bytes)
            if snap_ok and self._link_preview_thumb_bytes
            else None
        )
        yt_snap = (
            dict(self._preview_yt_info)
            if snap_ok and isinstance(self._preview_yt_info, dict)
            else None
        )

        self.te_link.clear()
        self._link_preview_timer.stop()
        self._link_preview_gen += 1
        self._reset_link_preview_ui()

        sort_on = bool(self.config["general"].get("download_sort_folders", True))
        resolved_base = resolve_download_base_path(self.config, path, cat_key)

        frame = DownloadRowFrame(
            self.w_downloads_list,
            self.index,
            link,
            cat_display,
            preset_key,
            preset_display,
            preview_meta=meta_snap,
            preview_thumb_bytes=thumb_snap,
            yt_info=yt_snap,
        )
        frame.setData(0, ItemRoles.CategoryRole, cat_key)
        out_path = effective_download_path(resolved_base, preset_key, sort_on)
        frame.setData(0, ItemRoles.PathRole, out_path)
        frame.refresh_outfile_preview(self.config, path)
        self.vl_downloads.addWidget(frame)
        frame.customContextMenuRequested.connect(
            lambda pos, fr=frame: self.open_menu_for_row(fr, pos)
        )

        worker = DownloadWorker(frame, self.config, link, resolved_base, preset_key)
        self.to_dl[self.index] = worker
        logger.info(f"Queued download ({self.index}) added {link}")
        self.index += 1

    def button_clear(self):
        if self.workers:
            return QtWidgets.QMessageBox.critical(
                self,
                "Application Message",
                "Unable to clear list because there are active downloads in progress.\n"
                "Remove a download by right clicking on it and selecting delete.",
            )

        if self.vl_downloads.count() == 0:
            return

        if bool(self.config["general"].get("confirm_clear_queue", True)):
            confirm = QtWidgets.QMessageBox.question(
                self,
                "Clear queue",
                "Remove all queued downloads from the list?",
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No,
            )
            if confirm != QtWidgets.QMessageBox.StandardButton.Yes:
                return

        self.workers = {}
        self.to_dl = {}
        while self.vl_downloads.count():
            li = self.vl_downloads.takeAt(0)
            if w := li.widget():
                w.deleteLater()

    def button_download(self):
        if normalize_url_input(self.te_link.text()):
            self.button_add()

        if not self.to_dl:
            return QtWidgets.QMessageBox.information(
                self,
                "Application Message",
                "Unable to download because there are no links in the list.",
            )

        for idx, worker in self.to_dl.items():
            self.workers[idx] = worker
            worker.finished.connect(worker.deleteLater)
            worker.finished.connect(lambda x=idx: self.workers.pop(x))
            worker.progress.connect(self.on_dl_progress)
            worker.start()

        self.to_dl = {}

    def load_config(self):
        try:
            self.config = load_toml(CONFIG_PATH)
        except Exception:
            QtWidgets.QMessageBox.critical(
                self,
                "Application Message",
                "Config file error.",
            )
            logger.error("Config file error.", exc_info=True)
            QtWidgets.QApplication.exit()

        update_ytdlp = self.config["general"].get("update_ytdlp")
        self.config["general"]["update_ytdlp"] = update_ytdlp if update_ytdlp else True
        self.dd_preset.clear()
        for key in self.config["presets"].keys():
            k = str(key)
            self.dd_preset.addItem(preset_ui_label(self.config, k), k)
        idx = int(self.config["general"].get("current_preset", 0))
        if 0 <= idx < self.dd_preset.count():
            self.dd_preset.setCurrentIndex(idx)
        else:
            self.dd_preset.setCurrentIndex(0)
        self.le_path.setText(self.config["general"]["path"])
        if self.config["general"].get("download_sort_folders") is None:
            self.config["general"]["download_sort_folders"] = True
        ensure_download_categories(self.config)
        self._sanitize_current_category_in_config()
        self._populate_category_combo()

    def _category_names_in_config(self) -> set[str]:
        return {
            str(r.get("name", "")).strip()
            for r in ensure_download_categories(self.config)
            if str(r.get("name", "")).strip()
        }

    def _sanitize_current_category_in_config(self) -> None:
        names = self._category_names_in_config()
        cc = str(self.config["general"].get("current_category") or "").strip()
        self.config["general"]["current_category"] = cc if cc in names else ""

    def _category_label_for_data(self, data) -> str:
        return data if isinstance(data, str) and data else "—"

    def _populate_category_combo(self) -> None:
        self.dd_category.blockSignals(True)
        self.dd_category.clear()
        self.dd_category.addItem("(None)", None)
        for row in ensure_download_categories(self.config):
            name = str(row.get("name", "")).strip()
            if name:
                self.dd_category.addItem(name, name)
        self.dd_category.blockSignals(False)
        raw = self.config["general"].get("current_category")
        want = str(raw).strip() if isinstance(raw, str) and str(raw).strip() else None
        if want:
            for i in range(self.dd_category.count()):
                if self.dd_category.itemData(i) == want:
                    self.dd_category.setCurrentIndex(i)
                    return
        self.dd_category.setCurrentIndex(0)

    def open_preferences(self):
        dlg = PreferencesDialog(self, self.config)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.le_path.setText(self.config["general"].get("path", ""))
            self._sanitize_current_category_in_config()
            self._populate_category_combo()
            self._refresh_queued_item_output_paths()
            self._update_fix_failed_button()
            self._update_link_preview_outfile_line()

    def _refresh_queued_item_output_paths(self):
        default_base = self.le_path.text()
        sort_on = bool(self.config["general"].get("download_sort_folders", True))
        for i in range(self.vl_downloads.count()):
            li = self.vl_downloads.itemAt(i)
            w = li.widget()
            if not isinstance(w, DownloadRowFrame):
                continue
            if w.status_text() != "Queued":
                continue
            preset = w.preset_text()
            cat = w.data(0, ItemRoles.CategoryRole)
            cat_key = cat if isinstance(cat, str) and cat else None
            resolved = resolve_download_base_path(self.config, default_base, cat_key)
            w.setData(
                0,
                ItemRoles.PathRole,
                effective_download_path(resolved, preset, sort_on),
            )
            w.refresh_outfile_preview(self.config, default_base)

    def closeEvent(self, event):
        self.config["general"]["current_preset"] = self.dd_preset.currentIndex()
        self.config["general"]["path"] = self.le_path.text()
        cur_cat = self.dd_category.currentData()
        self.config["general"]["current_category"] = (
            cur_cat if isinstance(cur_cat, str) and cur_cat.strip() else ""
        )
        save_toml(CONFIG_PATH, self.config)
        event.accept()

    def on_dl_progress(self, row: DownloadRowFrame, emit_data):
        try:
            for data in emit_data:
                index, update = data
                if index != TreeColumn.PROGRESS:
                    row.set_column_text(index, update)
                else:
                    row.set_progress_percent_str(update)
        except AttributeError:
            logger.info(f"Download ({row.data(0, ItemRoles.IdRole)}) no longer exists")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())
