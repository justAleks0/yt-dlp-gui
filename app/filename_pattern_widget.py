"""Reusable tap-to-build filename pattern editor (chips + quick presets)."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from output_name_tokens import (
    PRESET_PATTERNS,
    SECTION_ORDER,
    TOKEN_BY_ID,
    TOKEN_CATALOG,
    human_preview,
    preset_ids_ordered,
    token_chip_tooltip,
)


class FilenamePatternEditor(QtWidgets.QWidget):
    """Read-only preview, tap chips, clear / remove last, quick preset combo."""

    patternChanged = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._tokens: list[str] = []

        root = QtWidgets.QVBoxLayout(self)
        root.setSpacing(8)

        prev_row = QtWidgets.QHBoxLayout()
        prev_row.addWidget(QtWidgets.QLabel("Current pattern:"))
        self._le_preview = QtWidgets.QLineEdit()
        self._le_preview.setReadOnly(True)
        self._le_preview.setPlaceholderText("Tap segments below, or apply a quick layout.")
        prev_row.addWidget(self._le_preview, stretch=1)
        root.addLayout(prev_row)

        quick = QtWidgets.QHBoxLayout()
        quick.addWidget(QtWidgets.QLabel("Quick layout:"))
        self._combo_preset = QtWidgets.QComboBox()
        for pid in preset_ids_ordered():
            label, desc, _toks = PRESET_PATTERNS[pid]
            self._combo_preset.addItem(label, pid)
            self._combo_preset.setItemData(
                self._combo_preset.count() - 1, desc, QtCore.Qt.ItemDataRole.ToolTipRole
            )
        self._combo_preset.setMinimumWidth(220)
        quick.addWidget(self._combo_preset, stretch=1)
        self._pb_apply_preset = QtWidgets.QPushButton("Apply layout")
        self._pb_apply_preset.setToolTip(
            "Replace the current pattern with the selected quick layout."
        )
        self._pb_apply_preset.clicked.connect(self._on_apply_preset)
        quick.addWidget(self._pb_apply_preset)
        root.addLayout(quick)

        row_btns = QtWidgets.QHBoxLayout()
        self._pb_clear = QtWidgets.QPushButton("Clear all")
        self._pb_clear.clicked.connect(self._on_clear)
        self._pb_undo_one = QtWidgets.QPushButton("Remove last")
        self._pb_undo_one.setToolTip("Remove the last segment from the pattern.")
        self._pb_undo_one.clicked.connect(self._on_remove_last)
        row_btns.addWidget(self._pb_clear)
        row_btns.addWidget(self._pb_undo_one)
        row_btns.addStretch()
        root.addLayout(row_btns)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setMinimumHeight(220)
        inner = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(inner)
        v.setSpacing(10)

        by_section: dict[str, list] = {}
        for t in TOKEN_CATALOG:
            by_section.setdefault(t.section, []).append(t)

        for sec in SECTION_ORDER:
            tokens = by_section.get(sec)
            if not tokens:
                continue
            sec_lbl = QtWidgets.QLabel(sec)
            _bf = sec_lbl.font()
            _bf.setBold(True)
            sec_lbl.setFont(_bf)
            v.addWidget(sec_lbl)
            grid = QtWidgets.QGridLayout()
            grid.setSpacing(4)
            cols = 3
            for i, tok in enumerate(tokens):
                btn = QtWidgets.QPushButton(tok.label)
                btn.setToolTip(token_chip_tooltip(tok))
                btn.clicked.connect(lambda checked=False, tid=tok.id: self._append(tid))
                grid.addWidget(btn, i // cols, i % cols)
            w = QtWidgets.QWidget()
            w.setLayout(grid)
            v.addWidget(w)

        v.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll, stretch=1)

        self._refresh_preview()

    def get_token_ids(self) -> list[str]:
        return list(self._tokens)

    def set_token_ids(self, ids: list[str] | None) -> None:
        self._tokens = [str(x).strip() for x in (ids or []) if str(x).strip()]
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        self._le_preview.setText(human_preview(self._tokens))

    def _append(self, tid: str) -> None:
        if tid in TOKEN_BY_ID:
            self._tokens.append(tid)
            self._refresh_preview()
            self.patternChanged.emit()

    def _on_clear(self) -> None:
        if not self._tokens:
            return
        self._tokens.clear()
        self._refresh_preview()
        self.patternChanged.emit()

    def _on_remove_last(self) -> None:
        if not self._tokens:
            return
        self._tokens.pop()
        self._refresh_preview()
        self.patternChanged.emit()

    def _on_apply_preset(self) -> None:
        pid = self._combo_preset.currentData()
        if pid is None:
            return
        entry = PRESET_PATTERNS.get(str(pid))
        if not entry:
            return
        _label, _desc, toks = entry
        new_list = list(toks)
        if self._tokens:
            r = QtWidgets.QMessageBox.question(
                self,
                "Replace pattern?",
                "Replace the current filename pattern with this quick layout?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No,
            )
            if r != QtWidgets.QMessageBox.StandardButton.Yes:
                return
        self._tokens = new_list
        self._refresh_preview()
        self.patternChanged.emit()


class CategoryFilenamePatternDialog(QtWidgets.QDialog):
    """Per-category filename override."""

    def __init__(
        self,
        parent: QtWidgets.QWidget,
        use_custom: bool,
        token_ids: list[str],
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Category filename pattern")
        self.setModal(True)
        self.resize(520, 520)

        lay = QtWidgets.QVBoxLayout(self)
        self._cb = QtWidgets.QCheckBox(
            "Use a custom filename pattern for this category (overrides the default on the Filenames tab)"
        )
        self._cb.setChecked(use_custom)
        lay.addWidget(self._cb)

        self._editor = FilenamePatternEditor()
        self._editor.set_token_ids(token_ids)
        lay.addWidget(self._editor)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _on_ok(self) -> None:
        use = self._cb.isChecked()
        toks = self._editor.get_token_ids()
        if use and not toks:
            QtWidgets.QMessageBox.warning(
                self,
                "Filename pattern",
                "Add at least one segment to the pattern, or turn off custom filename for this category.",
            )
            return
        self.accept()

    def values(self) -> tuple[bool, list[str]]:
        return self._cb.isChecked(), self._editor.get_token_ids()
