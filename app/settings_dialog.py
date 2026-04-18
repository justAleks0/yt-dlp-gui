"""Preferences / Settings dialog (extensible for future options)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from filename_pattern_widget import CategoryFilenamePatternDialog, FilenamePatternEditor
from utils import CONFIG_PATH, ensure_download_categories, save_toml

logger = logging.getLogger(__name__)


def _norm_output_token_list(raw) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    return []


def _page_intro(text: str) -> QtWidgets.QLabel:
    """Wrapped label for the top of a settings tab (uses normal text color for contrast)."""
    lb = QtWidgets.QLabel(text)
    lb.setWordWrap(True)
    lb.setOpenExternalLinks(False)
    # Avoid palette(mid) in stylesheets — on dark themes it is often nearly the same as the
    # window background and becomes unreadable. Inherit standard window foreground instead.
    lb.setStyleSheet("margin-bottom: 8px;")
    return lb


def _tip_label(text: str, tooltip: str) -> QtWidgets.QLabel:
    """Form row label with a hover tooltip (info bubble)."""
    lb = QtWidgets.QLabel(text)
    lb.setToolTip(tooltip)
    return lb


class PreferencesDialog(QtWidgets.QDialog):
    """Edit ``config`` ``[general]`` keys and save ``config.toml`` on OK."""

    def __init__(self, parent: QtWidgets.QWidget, config: dict):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(640, 620)

        root = QtWidgets.QVBoxLayout(self)

        self._cat_fn_state: list[tuple[bool, list[str]]] = []

        self._tabs = QtWidgets.QTabWidget()
        root.addWidget(self._tabs)

        self._tabs.addTab(self._build_general_tab(), "General")
        self._tabs.addTab(self._build_filename_tab(), "Filenames")
        self._tabs.addTab(self._build_categories_tab(), "Categories")
        self._tabs.addTab(self._build_advanced_tab(), "Advanced")

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._load_from_config()

    def _build_general_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)

        layout.addWidget(
            _page_intro(
                "Use this tab for the default save location, how files are sorted into folders, "
                "what happens when the app starts, confirmation before clearing the queue, "
                "and extra yt-dlp arguments that are appended to every download. "
                "Output file naming is on the Filenames tab."
            )
        )

        grp_dl = QtWidgets.QGroupBox("Downloads")
        grp_dl.setToolTip(
            "Where files go by default and whether each format preset gets its own subfolder."
        )
        form_dl = QtWidgets.QFormLayout(grp_dl)

        path_row = QtWidgets.QHBoxLayout()
        self._le_save_path = QtWidgets.QLineEdit()
        self._le_save_path.setReadOnly(True)
        self._le_save_path.setMinimumWidth(320)
        self._le_save_path.setToolTip(
            "Folder used when you pick “Save to” on the main window. "
            "You can still browse to another folder there without changing this default."
        )
        self._pb_browse_save = QtWidgets.QPushButton("Browse…")
        self._pb_browse_save.setToolTip("Choose the default download directory.")
        self._pb_browse_save.clicked.connect(self._browse_save_folder)
        path_row.addWidget(self._le_save_path, stretch=1)
        path_row.addWidget(self._pb_browse_save)
        form_dl.addRow(
            _tip_label(
                "Default save folder:",
                "The starting folder for downloads. Category-specific folders (if configured) "
                "or preset subfolders are created inside this path when those options are on.",
            ),
            path_row,
        )

        self._cb_sort_subfolders = QtWidgets.QCheckBox(
            "Save into a subfolder per preset (under the folder above)"
        )
        self._cb_sort_subfolders.setToolTip(
            "When enabled, each preset (e.g. mp3, mp4) saves under its own folder name "
            "below the default or category folder. Example: …/Downloads/mp3/video.webm.\n"
            "Turn off to put all files directly in the base folder."
        )
        form_dl.addRow(self._cb_sort_subfolders)

        layout.addWidget(grp_dl)

        grp_app = QtWidgets.QGroupBox("Startup")
        grp_app.setToolTip("Behavior when you launch the application.")
        form_app = QtWidgets.QFormLayout(grp_app)
        self._cb_update_ytdlp = QtWidgets.QCheckBox(
            "Check for yt-dlp updates when the application starts"
        )
        self._cb_update_ytdlp.setToolTip(
            "Runs an update check for the bundled yt-dlp on startup. "
            "If an update is available, it may be installed automatically depending on your setup. "
            "Takes effect the next time you start the app."
        )
        form_app.addRow(self._cb_update_ytdlp)
        layout.addWidget(grp_app)

        grp_ui = QtWidgets.QGroupBox("Interface")
        grp_ui.setToolTip("How the main window behaves when you use buttons.")
        form_ui = QtWidgets.QFormLayout(grp_ui)
        self._cb_confirm_clear = QtWidgets.QCheckBox(
            "Ask for confirmation before clearing the download queue"
        )
        self._cb_confirm_clear.setToolTip(
            "If enabled, clicking the trash (clear list) button shows a confirmation dialog "
            "before removing all queued items. Active downloads are never cleared this way."
        )
        form_ui.addRow(self._cb_confirm_clear)
        layout.addWidget(grp_ui)

        grp_args = QtWidgets.QGroupBox("Extra yt-dlp arguments")
        grp_args.setToolTip(
            "Raw command-line options appended after built-in options on every download. "
            "Use one option per line or space-separated, same as in a terminal."
        )
        v_args = QtWidgets.QVBoxLayout(grp_args)
        self._te_global_args = QtWidgets.QPlainTextEdit()
        self._te_global_args.setPlaceholderText(
            "Appended to every download, e.g.\n--cookies-from-browser firefox"
        )
        self._te_global_args.setToolTip(
            "Examples:\n"
            "• --cookies-from-browser firefox — use browser cookies\n"
            "• --proxy URL — route through a proxy\n"
            "• --write-thumbnail — save thumbnail images\n\n"
            "These are merged with options from the Advanced tab; later arguments can override earlier ones."
        )
        self._te_global_args.setMinimumHeight(100)
        v_args.addWidget(self._te_global_args)
        layout.addWidget(grp_args)

        layout.addStretch()
        return w

    def _build_filename_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.addWidget(
            _page_intro(
                "Build the default output filename pattern by tapping segments (title, channel, date, …). "
                "Leave it empty to use yt-dlp’s default naming for files in the chosen folder (-P only). "
                "On the Categories tab you can override this per category with “Set naming…”."
            )
        )
        grp = QtWidgets.QGroupBox("Default filename pattern")
        grp.setToolTip(
            "Optional. When non-empty, downloads use a custom -o template under your save folder. "
            "Categories can supply their own pattern when enabled there."
        )
        v = QtWidgets.QVBoxLayout(grp)
        self._filename_editor = FilenamePatternEditor()
        v.addWidget(self._filename_editor)
        layout.addWidget(grp)
        layout.addStretch()
        return w

    def _build_categories_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.addWidget(
            _page_intro(
                "Categories are labels you pick when adding URLs (Music, Movies, etc.). "
                "They help organize downloads. Optionally, each category can use its own base folder "
                "instead of the default “Save to” path; preset subfolders still apply underneath when enabled."
            )
        )
        hint2 = QtWidgets.QLabel(
            "Edit the table below: add or remove rows, set a name, turn on “Custom folder” to choose "
            "a dedicated directory, or use “Set naming…” for a category-specific filename pattern "
            "(overrides the Filenames tab). Changes apply after you click OK."
        )
        hint2.setWordWrap(True)
        hint2.setStyleSheet("margin-bottom: 4px;")
        layout.addWidget(hint2)

        self._tbl_categories = QtWidgets.QTableWidget(0, 5)
        self._tbl_categories.setHorizontalHeaderLabels(
            ["Name", "Custom folder", "Folder", "", "Naming"]
        )
        self._tbl_categories.setToolTip(
            "Each row is one category shown in the Category dropdown on the main window."
        )
        hdr = self._tbl_categories.horizontalHeader()
        hdr.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self._tbl_categories.setColumnWidth(3, 96)
        self._tbl_categories.setColumnWidth(4, 110)
        self._tbl_categories.verticalHeader().setVisible(False)
        self._tbl_categories.itemChanged.connect(self._on_category_table_item_changed)
        layout.addWidget(self._tbl_categories)

        for col, tip in enumerate(
            (
                "Shown in the Category dropdown. Names must be unique.",
                "When checked, downloads for this category use the folder in the next column "
                "as the base path (instead of the default save folder).",
                "Directory used for this category when “Custom folder” is enabled. Use Browse to pick it.",
                "Opens a folder picker for this row’s folder.",
                "Set a filename pattern for this category only (overrides the default on the Filenames tab).",
            )
        ):
            self._tbl_categories.model().setHeaderData(
                col,
                QtCore.Qt.Orientation.Horizontal,
                tip,
                QtCore.Qt.ItemDataRole.ToolTipRole,
            )

        row_btns = QtWidgets.QHBoxLayout()
        self._pb_cat_add = QtWidgets.QPushButton("Add category")
        self._pb_cat_add.setToolTip("Append a new empty category row at the bottom.")
        self._pb_cat_add.clicked.connect(self._add_category_row)
        self._pb_cat_remove = QtWidgets.QPushButton("Remove selected")
        self._pb_cat_remove.setToolTip(
            "Delete the highlighted row. You cannot recover it except by adding the category again."
        )
        self._pb_cat_remove.clicked.connect(self._remove_category_row)
        row_btns.addWidget(self._pb_cat_add)
        row_btns.addWidget(self._pb_cat_remove)
        row_btns.addStretch()
        layout.addLayout(row_btns)

        return w

    def _append_category_row(
        self,
        name: str,
        use: bool,
        path: str,
        use_fn: bool = False,
        fn_tokens: list[str] | None = None,
    ) -> None:
        r = self._tbl_categories.rowCount()
        self._tbl_categories.insertRow(r)
        it_name = QtWidgets.QTableWidgetItem(name)
        it_name.setToolTip(
            "Label for this category. It appears in the Category dropdown on the main window."
        )
        self._tbl_categories.setItem(r, 0, it_name)
        it_use = QtWidgets.QTableWidgetItem()
        it_use.setFlags(
            (it_use.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
            & ~QtCore.Qt.ItemFlag.ItemIsEditable
        )
        it_use.setCheckState(
            QtCore.Qt.CheckState.Checked if use else QtCore.Qt.CheckState.Unchecked
        )
        it_use.setToolTip(
            "Enable to use the folder in the next column as the base path for this category."
        )
        self._tbl_categories.setItem(r, 1, it_use)
        le = QtWidgets.QLineEdit(path)
        le.setReadOnly(True)
        le.setToolTip(
            "Destination folder when “Custom folder” is checked. Use Browse to change it."
        )
        self._tbl_categories.setCellWidget(r, 2, le)
        browse = QtWidgets.QPushButton("Browse…")
        browse.setToolTip("Choose the folder for this category.")
        browse.clicked.connect(self._browse_category_folder)
        self._tbl_categories.setCellWidget(r, 3, browse)
        le.setEnabled(use)

        tok_list = _norm_output_token_list(fn_tokens)
        self._cat_fn_state.append((bool(use_fn), list(tok_list)))
        name_btn = QtWidgets.QPushButton("Set naming…")
        name_btn.setToolTip(
            "Custom filename pattern for this category (overrides the default pattern on the Filenames tab)."
        )
        name_btn.clicked.connect(
            lambda _checked=False, row=r: self._edit_category_naming(row)
        )
        self._tbl_categories.setCellWidget(r, 4, name_btn)

    def _on_category_table_item_changed(self, item: QtWidgets.QTableWidgetItem) -> None:
        if item.column() != 1:
            return
        row = item.row()
        le = self._tbl_categories.cellWidget(row, 2)
        if isinstance(le, QtWidgets.QLineEdit):
            le.setEnabled(item.checkState() == QtCore.Qt.CheckState.Checked)

    def _browse_category_folder(self) -> None:
        btn = self.sender()
        if not isinstance(btn, QtWidgets.QWidget):
            return
        for r in range(self._tbl_categories.rowCount()):
            if self._tbl_categories.cellWidget(r, 3) is not btn:
                continue
            le = self._tbl_categories.cellWidget(r, 2)
            if not isinstance(le, QtWidgets.QLineEdit):
                return
            path = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                "Select folder for this category",
                le.text() or QtCore.QDir.homePath(),
                QtWidgets.QFileDialog.Option.ShowDirsOnly,
            )
            if path:
                le.setText(path)
            break

    def _edit_category_naming(self, row: int) -> None:
        if row < 0 or row >= len(self._cat_fn_state):
            return
        use, toks = self._cat_fn_state[row]
        dlg = CategoryFilenamePatternDialog(self, use, toks)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        use, toks = dlg.values()
        self._cat_fn_state[row] = (use, toks)

    def _add_category_row(self) -> None:
        self._append_category_row("New category", False, "", False, [])

    def _remove_category_row(self) -> None:
        r = self._tbl_categories.currentRow()
        if r >= 0:
            self._tbl_categories.removeRow(r)
            if 0 <= r < len(self._cat_fn_state):
                self._cat_fn_state.pop(r)

    def _load_categories_table(self) -> None:
        self._tbl_categories.blockSignals(True)
        self._tbl_categories.setRowCount(0)
        self._cat_fn_state.clear()
        for row in ensure_download_categories(self.config):
            self._append_category_row(
                str(row.get("name", "")),
                bool(row.get("use_custom_path", False)),
                str(row.get("path", "")),
                bool(row.get("use_custom_filename", False)),
                row.get("output_name_tokens"),
            )
        self._tbl_categories.blockSignals(False)

    def _categories_from_table(self) -> list[dict]:
        rows: list[dict] = []
        for r in range(self._tbl_categories.rowCount()):
            name_item = self._tbl_categories.item(r, 0)
            use_item = self._tbl_categories.item(r, 1)
            le = self._tbl_categories.cellWidget(r, 2)
            name = name_item.text().strip() if name_item else ""
            use = (
                use_item.checkState() == QtCore.Qt.CheckState.Checked if use_item else False
            )
            path = le.text().strip() if isinstance(le, QtWidgets.QLineEdit) else ""
            use_fn, fn_toks = (
                self._cat_fn_state[r]
                if r < len(self._cat_fn_state)
                else (False, [])
            )
            rows.append(
                {
                    "name": name,
                    "use_custom_path": use,
                    "path": path if use else "",
                    "use_custom_filename": use_fn,
                    "output_name_tokens": list(fn_toks) if use_fn else [],
                }
            )
        return rows

    def _validate_category_rows(self, cat_rows: list[dict]) -> bool:
        seen: set[str] = set()
        for row in cat_rows:
            n = row["name"].strip()
            if not n:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Categories",
                    "Every category needs a non-empty name.",
                )
                return False
            key = n.casefold()
            if key in seen:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Categories",
                    f"Duplicate category name: {n}",
                )
                return False
            seen.add(key)
            if row["use_custom_path"] and not str(row.get("path", "")).strip():
                QtWidgets.QMessageBox.warning(
                    self,
                    "Categories",
                    f'Category "{n}" has "Custom folder" enabled but no folder selected.',
                )
                return False
            if row.get("use_custom_filename") and not _norm_output_token_list(
                row.get("output_name_tokens")
            ):
                QtWidgets.QMessageBox.warning(
                    self,
                    "Categories",
                    f'Category "{n}" has a custom filename pattern enabled but no segments. '
                    "Open “Set naming…” and add segments, or turn off the custom pattern.",
                )
                return False
        return True

    def _build_advanced_tab(self) -> QtWidgets.QWidget:
        outer = QtWidgets.QWidget()
        outer_l = QtWidgets.QVBoxLayout(outer)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        inner = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(inner)

        lay.addWidget(
            _page_intro(
                "These options map to yt-dlp command-line flags for resuming, skipping duplicates, "
                "filename rules, retries, parallel fragments, and an optional download archive. "
                "They are applied in order before “Extra yt-dlp arguments” on the General tab, "
                "so you can override or extend behavior there."
            )
        )

        grp = QtWidgets.QGroupBox("Download behavior")
        grp.setToolTip(
            "Technical options passed to yt-dlp. Hover each control for details."
        )
        form = QtWidgets.QFormLayout(grp)

        self._cb_continue_partial = QtWidgets.QCheckBox(
            "Resume partial downloads (allow continuation)"
        )
        self._cb_continue_partial.setToolTip(
            "When on (default), yt-dlp can resume interrupted downloads.\n"
            "When off, adds --no-continue so partial files are not resumed—useful to force a full re-download."
        )
        form.addRow(self._cb_continue_partial)

        self._cb_no_overwrites = QtWidgets.QCheckBox(
            "Do not overwrite existing files (--no-overwrites)"
        )
        self._cb_no_overwrites.setToolTip(
            "When on (default), adds --no-overwrites: if the output file already exists, "
            "yt-dlp skips the download instead of replacing it."
        )
        form.addRow(self._cb_no_overwrites)

        self._cb_restrict_filenames = QtWidgets.QCheckBox(
            "Restrict filenames to ASCII (--restrict-filenames)"
        )
        self._cb_restrict_filenames.setToolTip(
            "Adds --restrict-filenames: only ASCII characters in filenames, "
            "reducing issues with some players or filesystems."
        )
        form.addRow(self._cb_restrict_filenames)

        self._cb_windows_filenames = QtWidgets.QCheckBox(
            "Windows-safe filenames (--windows-filenames)"
        )
        self._cb_windows_filenames.setToolTip(
            "Adds --windows-filenames: replaces characters that are invalid on Windows paths "
            "(recommended on Windows; optional elsewhere if you target Windows media paths)."
        )
        form.addRow(self._cb_windows_filenames)

        self._sb_retries = QtWidgets.QSpinBox()
        self._sb_retries.setRange(0, 999)
        self._sb_retries.setToolTip(
            "Passes --retries: how many times to retry failed HTTP requests for the whole file. "
            "Higher values help on unstable networks; 0 disables retries."
        )
        form.addRow(
            _tip_label(
                "HTTP retries:",
                "Number of times yt-dlp retries failed HTTP segment or file requests (0–999).",
            ),
            self._sb_retries,
        )

        self._sb_fragment_retries = QtWidgets.QSpinBox()
        self._sb_fragment_retries.setRange(0, 999)
        self._sb_fragment_retries.setToolTip(
            "Passes --fragment-retries: retries per fragment for DASH/HLS segmented streams."
        )
        form.addRow(
            _tip_label(
                "Fragment retries:",
                "Retries for each small piece of DASH/HLS video; increase if downloads stall mid-stream.",
            ),
            self._sb_fragment_retries,
        )

        self._sb_concurrent_fragments = QtWidgets.QSpinBox()
        self._sb_concurrent_fragments.setRange(1, 32)
        self._sb_concurrent_fragments.setToolTip(
            "Passes --concurrent-fragments when set to 2 or higher: download multiple fragments "
            "in parallel for DASH/HLS (can speed up fast connections; use 1 for default behavior)."
        )
        form.addRow(
            _tip_label(
                "Concurrent fragments:",
                "Parallel downloads for stream fragments. Leave at 1 unless you need more throughput.",
            ),
            self._sb_concurrent_fragments,
        )

        arch_row = QtWidgets.QHBoxLayout()
        self._le_download_archive = QtWidgets.QLineEdit()
        self._le_download_archive.setPlaceholderText(
            "Optional path to a text file listing finished video IDs"
        )
        self._le_download_archive.setToolTip(
            "Passes --download-archive FILE: yt-dlp appends each completed video ID to this file "
            "and skips downloading IDs already listed. Leave empty to disable. "
            "Useful to avoid re-downloading the same videos across sessions."
        )
        self._pb_browse_archive = QtWidgets.QPushButton("Browse…")
        self._pb_browse_archive.setToolTip("Choose where to store the archive text file.")
        self._pb_browse_archive.clicked.connect(self._browse_download_archive)
        arch_row.addWidget(self._le_download_archive, stretch=1)
        arch_row.addWidget(self._pb_browse_archive)
        form.addRow(
            _tip_label(
                "Download archive:",
                "Optional file listing finished video IDs (--download-archive). "
                "Parent folders are created automatically if needed.",
            ),
            arch_row,
        )

        lay.addWidget(grp)
        lay.addStretch()
        scroll.setWidget(inner)
        outer_l.addWidget(scroll)
        return outer

    def _browse_download_archive(self) -> None:
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Download archive file",
            self._le_download_archive.text().strip()
            or str(Path.home() / ".yt-dlp-gui-archive.txt"),
            "Text files (*.txt);;All files (*.*)",
        )
        if path:
            self._le_download_archive.setText(path)

    def _load_from_config(self) -> None:
        g = self.config["general"]
        self._le_save_path.setText(str(g.get("path", "")))

        sort_val = g.get("download_sort_folders")
        if sort_val is None:
            sort_val = True
        self._cb_sort_subfolders.setChecked(bool(sort_val))

        up = g.get("update_ytdlp")
        self._cb_update_ytdlp.setChecked(bool(up) if up is not None else True)

        cq = g.get("confirm_clear_queue")
        self._cb_confirm_clear.setChecked(bool(cq) if cq is not None else True)

        self._cb_continue_partial.setChecked(bool(g.get("continue_partial", True)))
        self._cb_no_overwrites.setChecked(bool(g.get("no_overwrites", True)))
        self._cb_restrict_filenames.setChecked(bool(g.get("restrict_filenames", False)))
        wf = g.get("windows_filenames")
        self._cb_windows_filenames.setChecked(
            bool(wf) if wf is not None else sys.platform == "win32"
        )
        try:
            self._sb_retries.setValue(int(g.get("retries", 10)))
        except (TypeError, ValueError):
            self._sb_retries.setValue(10)
        try:
            self._sb_fragment_retries.setValue(int(g.get("fragment_retries", 10)))
        except (TypeError, ValueError):
            self._sb_fragment_retries.setValue(10)
        try:
            self._sb_concurrent_fragments.setValue(max(1, int(g.get("concurrent_fragments", 1))))
        except (TypeError, ValueError):
            self._sb_concurrent_fragments.setValue(1)
        self._le_download_archive.setText(str(g.get("download_archive") or ""))

        ga = g.get("global_args")
        if ga is None:
            ga = ""
        elif not isinstance(ga, str):
            ga = str(ga)
        self._te_global_args.setPlainText(ga)

        self._filename_editor.set_token_ids(_norm_output_token_list(g.get("output_name_tokens")))

        self._load_categories_table()

    def _browse_save_folder(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select default download folder",
            self._le_save_path.text() or QtCore.QDir.homePath(),
            QtWidgets.QFileDialog.Option.ShowDirsOnly,
        )
        if path:
            self._le_save_path.setText(path)

    def _apply_widgets_to_config(self) -> None:
        g = self.config["general"]
        g["path"] = self._le_save_path.text().strip()
        g["download_sort_folders"] = self._cb_sort_subfolders.isChecked()
        g["update_ytdlp"] = self._cb_update_ytdlp.isChecked()
        g["confirm_clear_queue"] = self._cb_confirm_clear.isChecked()
        g["continue_partial"] = self._cb_continue_partial.isChecked()
        g["no_overwrites"] = self._cb_no_overwrites.isChecked()
        g["restrict_filenames"] = self._cb_restrict_filenames.isChecked()
        g["windows_filenames"] = self._cb_windows_filenames.isChecked()
        g["retries"] = self._sb_retries.value()
        g["fragment_retries"] = self._sb_fragment_retries.value()
        g["concurrent_fragments"] = self._sb_concurrent_fragments.value()
        g["download_archive"] = self._le_download_archive.text().strip()
        g["global_args"] = self._te_global_args.toPlainText().strip()
        g["output_name_tokens"] = self._filename_editor.get_token_ids()

        cat_rows = self._categories_from_table()
        self.config["categories"] = [
            {
                "name": row["name"].strip(),
                "use_custom_path": row["use_custom_path"],
                "path": str(row.get("path", "")).strip() if row["use_custom_path"] else "",
                "use_custom_filename": bool(row.get("use_custom_filename", False)),
                "output_name_tokens": _norm_output_token_list(row.get("output_name_tokens"))
                if row.get("use_custom_filename")
                else [],
            }
            for row in cat_rows
        ]

    def _on_ok(self) -> None:
        if not self._validate_category_rows(self._categories_from_table()):
            return
        self._apply_widgets_to_config()
        try:
            save_toml(CONFIG_PATH, self.config)
        except OSError as e:
            logger.exception("Failed to save config")
            QtWidgets.QMessageBox.critical(
                self,
                "Settings",
                f"Could not save settings:\n{e}",
            )
            return
        self.accept()
