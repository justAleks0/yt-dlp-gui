import logging
import shlex
import subprocess as sp
import sys

from PySide6 import QtCore
from dep_dl import resolve_ytdlp_argv
from output_name_tokens import (
    build_output_o_template,
    build_template_body,
    resolve_output_name_tokens,
)
from utils import ItemRoles, TreeColumn, effective_download_path, general_ytdlp_cli_args

logger = logging.getLogger(__name__)


def _cli_args_from_config_value(raw) -> list[str]:
    """Preset / args from TOML: either a string (shell-style) or a list/tuple of argv tokens."""
    if isinstance(raw, (list, tuple)):
        return [str(x) for x in raw]
    return shlex.split(str(raw))


class DownloadWorker(QtCore.QThread):
    progress = QtCore.Signal(object, list)

    def __init__(self, row, config, link, base_path, preset):
        super().__init__()
        self.item = row  # DownloadRowFrame (or any object with .data(0, ItemRoles.IdRole))
        self.link = link
        self.base_path = base_path
        self.preset = preset
        self.id = self.item.data(0, ItemRoles.IdRole)
        self.config = config
        self._mutex = QtCore.QMutex()
        self._stop = False

    def build_command(self, config):
        args = list(resolve_ytdlp_argv())
        args += [
            "--newline",
            "--no-simulate",
            "--progress",
            "--progress-template",
            "%(progress.status)s__SEP__%(progress._total_bytes_estimate_str)s__SEP__%(progress._percent_str)s__SEP__%(progress._speed_str)s__SEP__%(progress._eta_str)s__SEP__%(info.title)s",
        ]
        p_args = config["presets"][self.preset]
        g_args = config["general"].get("global_args")

        sort_on = bool(config["general"].get("download_sort_folders", True))
        out_dir = effective_download_path(self.base_path, self.preset, sort_on)
        # Output location: custom template uses -o (path embedded); otherwise -P only. Preset args and
        # general_ytdlp_cli_args/global_args are appended after this block, unchanged.
        cat = self.item.data(0, ItemRoles.CategoryRole)
        cat_key = cat if isinstance(cat, str) and str(cat).strip() else None
        token_ids = resolve_output_name_tokens(config, cat_key)
        body = build_template_body(token_ids)
        if body.strip():
            args += ["-o", build_output_o_template(out_dir, body)]
        else:
            args += ["-P", out_dir]
        args += _cli_args_from_config_value(p_args)
        args += general_ytdlp_cli_args(config)
        args += g_args if isinstance(g_args, list) else shlex.split(g_args)
        args += ["--", self.link]
        return args

    def stop(self):
        with QtCore.QMutexLocker(self._mutex):
            self._stop = True

    def run(self):
        self.command = self.build_command(self.config)
        create_window = sp.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        output = ""
        logger.info(f"Download ({self.id}) starting with cmd: {self.command}")

        self.progress.emit(self.item, [(TreeColumn.STATUS, "Processing")])

        with sp.Popen(
            self.command,
            stdout=sp.PIPE,
            stderr=sp.STDOUT,
            text=True,
            universal_newlines=True,
            creationflags=create_window,
        ) as p:
            for line in p.stdout:
                output += line
                with QtCore.QMutexLocker(self._mutex):
                    if self._stop:
                        p.terminate()
                        p.wait()
                        logger.info(f"Download ({self.id}) stopped.")
                        break

                line = line.strip()
                if "__SEP__" in line:
                    status, total_bytes, percent, speed, eta, title = [
                        i.strip() for i in line.split("__SEP__")
                    ]
                    self.progress.emit(
                        self.item,
                        [
                            (TreeColumn.TITLE, title),
                            (TreeColumn.SIZE, total_bytes),
                            (TreeColumn.PROGRESS, percent),
                            (TreeColumn.SPEED, speed),
                            (TreeColumn.ETA, eta),
                            (TreeColumn.STATUS, "Downloading"),
                        ],
                    )
                elif line.startswith(("[Merger]", "[ExtractAudio]")):
                    self.progress.emit(self.item, [(TreeColumn.STATUS, "Converting")])
                elif line.startswith("WARNING:"):
                    logger.warning(f"Download ({self.id}) {line}")

        if p.returncode != 0:
            logger.error(f"Download ({self.id}) returncode: {p.returncode}\n{output}")
            self.progress.emit(self.item, [(TreeColumn.STATUS, "ERROR")])
        else:
            logger.info(f"Download ({self.id}) finished.")
            self.progress.emit(
                self.item,
                [
                    (TreeColumn.PROGRESS, "100%"),
                    (TreeColumn.STATUS, "Finished"),
                ],
            )
