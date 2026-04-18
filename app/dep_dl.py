import importlib.util
import os
import platform
import shutil
import stat
import sys
import zipfile
from dataclasses import dataclass
from typing import List, Optional, Tuple
import logging


import requests
from PySide6.QtCore import QThread, Signal

from utils import ROOT, BIN_DIR
import subprocess as sp

logger = logging.getLogger(__name__)

os.environ["PATH"] += os.pathsep + str(BIN_DIR)
os.environ["PATH"] += os.pathsep + str(ROOT / "bin")  # old version compatibility

BINARIES = {
    "Linux": {
        "ffmpeg": "ffmpeg-linux64-v4.1",
        "ffprobe": "ffprobe-linux64-v4.1",
        "yt-dlp": "yt-dlp_linux",
        "deno": "deno-x86_64-unknown-linux-gnu.zip",
    },
    "Darwin": {
        "ffmpeg": "ffmpeg-osx64-v4.1",
        "ffprobe": "ffprobe-osx64-v4.1",
        "yt-dlp": "yt-dlp_macos",
        "deno": "deno-x86_64-apple-darwin.zip",
    },
    "Windows": {
        "ffmpeg": "ffmpeg-win64-v4.1.exe",
        "ffprobe": "ffprobe-win64-v4.1.exe",
        "yt-dlp": "yt-dlp.exe",
        "deno": "deno-x86_64-pc-windows-msvc.zip",
    },
}

YT_DLP_BASE_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/"
FFMPEG_BASE_URL = "https://github.com/imageio/imageio-binaries/raw/183aef992339cc5a463528c75dd298db15fd346f/ffmpeg/"
DENO_BASE_URL = "https://github.com/denoland/deno/releases/latest/download/"

# Order used for full bundle reinstall (ffmpeg/ffprobe before yt-dlp).
BUNDLE_EXES = ("ffmpeg", "ffprobe", "deno", "yt-dlp")
_BUNDLE_SET = frozenset(BUNDLE_EXES)


def failed_bundle_components_from_rows(
    rows: List[Tuple[str, bool, str]],
) -> Tuple[str, ...]:
    """Names from the last dependency scan that are missing or broken (subset of ``BUNDLE_EXES``)."""
    failed = {name for name, ok, _ in rows if not ok and name in _BUNDLE_SET}
    return tuple(e for e in BUNDLE_EXES if e in failed)


def bundle_binary_job(system_os: str, exe: str) -> Tuple[str, str]:
    """Return ``(download_url, dest_path)`` for a bundled tool under ``BIN_DIR``."""
    binary_name = BINARIES[system_os][exe]
    if exe == "yt-dlp":
        url = YT_DLP_BASE_URL + binary_name
    elif exe == "deno":
        url = DENO_BASE_URL + binary_name
    else:
        url = FFMPEG_BASE_URL + binary_name
    target_name = f"{exe}.exe" if system_os == "Windows" else exe
    return url, str(BIN_DIR / target_name)

DOWNLOAD_HEADERS = {
    "User-Agent": "yt-dlp-gui/1.0 (+https://github.com/dsymbol/yt-dlp-gui)",
    "Accept": "*/*",
}
# Official Windows build is a large PyInstaller binary; tiny files are usually HTML errors.
_MIN_YTDLP_WINDOWS_EXE_BYTES = 8 * 1024 * 1024
_REQUEST_TIMEOUT = (30, 600)


def _make_executable(path: str) -> None:
    try:
        st = os.stat(path)
        os.chmod(path, st.st_mode | stat.S_IEXEC)
    except OSError:
        pass


def download_file(url: str, filename: str, progress_emit) -> None:
    """Stream a URL to ``filename``. ``progress_emit`` is ``callable(str)``."""
    prepare_tool_reinstall(filename)
    response = requests.get(
        url,
        stream=True,
        headers=DOWNLOAD_HEADERS,
        timeout=_REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    block_size = 8192
    downloaded = 0

    display_name = os.path.basename(filename)
    temp_filename = filename + ".part"

    try:
        with open(temp_filename, "wb") as f:
            for chunk in response.iter_content(chunk_size=block_size):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)

                if total_size > 0:
                    percentage = int((downloaded / total_size) * 100)
                    dl_mb = downloaded / (1024 * 1024)
                    tot_mb = total_size / (1024 * 1024)
                    status = (
                        f"Downloading dependency: ({display_name}) "
                        f"{dl_mb:.2f} / {tot_mb:.2f} MB {percentage}%"
                    )
                else:
                    dl_mb = downloaded / (1024 * 1024)
                    status = f"{display_name}: {dl_mb:.2f} MB"

                progress_emit(status)
    except Exception:
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except OSError:
                pass
        raise

    if total_size > 0 and downloaded != total_size:
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except OSError:
                pass
        raise OSError(
            f"Incomplete download ({downloaded} of {total_size} bytes). "
            "Check your network and try Install yt-dlp again."
        )

    if url.endswith(".zip"):
        try:
            zip_filename = temp_filename + ".zip"
            shutil.move(temp_filename, zip_filename)

            with zipfile.ZipFile(zip_filename, "r") as zf:
                target_filename = zf.namelist()[0]
                with zf.open(target_filename) as source, open(
                    filename, "wb"
                ) as target:
                    shutil.copyfileobj(source, target)

            if os.path.exists(zip_filename):
                os.remove(zip_filename)
            return
        except Exception as e:
            if os.path.exists(zip_filename):
                os.remove(zip_filename)
            raise e

    if os.path.exists(filename):
        os.remove(filename)
    os.rename(temp_filename, filename)


def _remove_file_quiet(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def prepare_tool_reinstall(dest_path: str) -> None:
    """Remove an existing install and stale ``.part`` / ``.part.zip`` files so reinstall is a single clean file."""
    _remove_file_quiet(dest_path)
    _remove_file_quiet(dest_path + ".part")
    _remove_file_quiet(dest_path + ".part.zip")


def _verify_windows_ytdlp_exe(path: str) -> None:
    size = os.path.getsize(path)
    if size < _MIN_YTDLP_WINDOWS_EXE_BYTES:
        raise OSError(
            f"File is only {size} bytes (expected a large executable). "
            "The download may have failed or returned an error page. Try Install yt-dlp again."
        )
    with open(path, "rb") as f:
        if f.read(2) != b"MZ":
            raise OSError(
                "Downloaded file is not a valid Windows executable (.exe). Try Install yt-dlp again."
            )


def _verify_ytdlp_runs(exe_path: str) -> None:
    create_window = sp.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        p = sp.run(
            [exe_path, "--version"],
            capture_output=True,
            text=True,
            timeout=60,
            creationflags=create_window,
        )
    except sp.TimeoutExpired:
        raise OSError(
            "yt-dlp did not respond in time. The file may be damaged or blocked by security software."
        )
    combined = (p.stdout or "") + (p.stderr or "")
    if p.returncode != 0 or "PyInstaller" in combined and "ERROR" in combined:
        raise OSError(
            "The downloaded yt-dlp.exe fails to start. This is usually an incomplete download, "
            "or antivirus quarantining part of the file.\n\n"
            "Try: run “Install yt-dlp” again; add an exclusion for the binaries folder "
            f"(File → Open Binaries Folder); or install globally with: pip install yt-dlp\n\n"
            f"Details: {combined.strip()[:500]}"
        )


@dataclass(frozen=True)
class DependencyRow:
    name: str
    ok: bool
    detail: str


def _tool_filename(base: str) -> str:
    return f"{base}.exe" if platform.system() == "Windows" else base


def _probe_ytdlp_argv(argv: List[str]) -> bool:
    """True if ``argv`` + ``--version`` runs without PyInstaller failure."""
    create_window = sp.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        p = sp.run(
            argv + ["--version"],
            capture_output=True,
            text=True,
            timeout=45,
            creationflags=create_window,
        )
    except (sp.TimeoutExpired, OSError):
        return False
    combined = (p.stdout or "") + (p.stderr or "")
    if p.returncode != 0 or ("PyInstaller" in combined and "ERROR" in combined):
        return False
    return True


def resolve_ytdlp_argv() -> List[str]:
    """Argv prefix to run yt-dlp: first working exe, else ``python -m yt_dlp``, else ``[\"yt-dlp\"]``.

    ``PATH`` may point at a broken PyInstaller copy in the app folder; this skips it when
    ``pip install yt-dlp`` (importable ``yt_dlp``) works.
    """
    seen: set[str] = set()
    path_candidates: List[str] = []

    which_path = shutil.which("yt-dlp")
    if which_path:
        path_candidates.append(which_path)

    for folder in (BIN_DIR, ROOT / "bin"):
        p = folder / _tool_filename("yt-dlp")
        if p.is_file():
            s = str(p)
            if s not in path_candidates:
                path_candidates.append(s)

    for exe_path in path_candidates:
        if exe_path in seen:
            continue
        seen.add(exe_path)
        if _probe_ytdlp_argv([exe_path]):
            return [exe_path]

    if importlib.util.find_spec("yt_dlp") is not None:
        mod_argv = [sys.executable, "-m", "yt_dlp"]
        if _probe_ytdlp_argv(mod_argv):
            return mod_argv

    return ["yt-dlp"]


def _resolve_tool_executable(cmd: str) -> str | None:
    """Resolve ``cmd`` on ``PATH`` (after env setup) or in ``BIN_DIR`` / ``ROOT/bin``."""
    w = shutil.which(cmd)
    if w:
        return w
    for folder in (BIN_DIR, ROOT / "bin"):
        p = folder / _tool_filename(cmd)
        if p.is_file():
            return str(p)
    return None


def _run_tool_probe(argv: List[str], timeout: float) -> Tuple[int, str]:
    create_window = sp.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        p = sp.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=create_window,
        )
    except sp.TimeoutExpired:
        return -1, "timed out"
    except OSError as e:
        return -1, str(e)
    out = ((p.stdout or "") + (p.stderr or "")).strip()
    return p.returncode, out


def _verify_ffmpeg_or_ffprobe(path: str, label: str) -> None:
    code, out = _run_tool_probe([path, "-version"], 25)
    if code != 0:
        raise OSError(
            f"{label} self-test failed (exit {code}): {(out or '')[:280]}"
        )


def _verify_deno_binary(path: str) -> None:
    code, out = _run_tool_probe([path, "--version"], 30)
    if code != 0:
        raise OSError(
            f"deno self-test failed (exit {code}): {(out or '')[:280]}"
        )


def scan_dependencies() -> List[DependencyRow]:
    """Probe yt-dlp, ffmpeg, ffprobe, and deno (PATH + app binary folders)."""
    rows: List[DependencyRow] = []

    argv = resolve_ytdlp_argv()
    code, out = _run_tool_probe(argv + ["--version"], 45)
    snippet = out.replace("\r\n", "\n").strip()
    bad = "PyInstaller" in snippet and "ERROR" in snippet
    if code != 0 or bad:
        short = snippet[:220] + ("…" if len(snippet) > 220 else "")
        if argv == ["yt-dlp"]:
            rows.append(
                DependencyRow(
                    "yt-dlp",
                    False,
                    "No working yt-dlp — run: pip install -U yt-dlp (then restart the app), "
                    "or fix the bundled exe (antivirus / exclusion).",
                )
            )
        else:
            rows.append(
                DependencyRow(
                    "yt-dlp",
                    False,
                    f"Not working (exit {code}). {short}".strip(),
                )
            )
    else:
        ver = snippet.split("\n")[0][:100]
        if len(argv) >= 3 and argv[1] == "-m" and argv[2] == "yt_dlp":
            rows.append(
                DependencyRow(
                    "yt-dlp",
                    True,
                    f"{ver} — Python module: {' '.join(argv)}",
                )
            )
        else:
            rows.append(
                DependencyRow("yt-dlp", True, f"{ver} — {' '.join(argv)}"),
            )

    for label, extra_args, tmo in (
        ("ffmpeg", ["-version"], 25),
        ("ffprobe", ["-version"], 25),
        ("deno", ["--version"], 25),
    ):
        path = _resolve_tool_executable(label)
        if not path:
            rows.append(
                DependencyRow(
                    label,
                    False,
                    "Not found — wait for first-run download or install to PATH.",
                )
            )
            continue
        code, out = _run_tool_probe([path] + extra_args, tmo)
        snippet = out.replace("\r\n", "\n").strip()
        if code != 0:
            short = snippet[:200] + ("…" if len(snippet) > 200 else "")
            rows.append(
                DependencyRow(
                    label,
                    False,
                    f"Not working (exit {code}). {short}".strip(),
                )
            )
        else:
            line = snippet.split("\n")[0][:120]
            rows.append(DependencyRow(label, True, f"{line} — {path}"))

    return rows


class DependencyCheckWorker(QThread):
    """Runs :func:`scan_dependencies` off the UI thread."""

    result = Signal(object)

    def run(self):
        try:
            rows = scan_dependencies()
            self.result.emit([(r.name, r.ok, r.detail) for r in rows])
        except Exception as e:
            logger.exception("dependency scan failed")
            self.result.emit(
                [("dependency check", False, f"Scan failed: {e}")]
            )


class BundleReinstallWorker(QThread):
    """Re-download bundled tools into ``BIN_DIR``, replacing any previous files (no duplicates)."""

    progress = Signal(str)
    finished_ok = Signal(str)
    finished_err = Signal(str)

    def __init__(self, only: Optional[Tuple[str, ...]] = None):
        super().__init__()
        self.only = only

    def run(self):
        system_os = platform.system()
        if system_os not in BINARIES:
            self.finished_err.emit("Unsupported operating system.")
            return

        if self.only:
            wanted = frozenset(self.only)
            unknown = wanted - _BUNDLE_SET
            if unknown:
                self.finished_err.emit(f"Unknown component(s): {', '.join(sorted(unknown))}")
                return
            exes = tuple(e for e in BUNDLE_EXES if e in wanted)
            if not exes:
                self.finished_err.emit("Nothing to reinstall.")
                return
        else:
            exes = BUNDLE_EXES

        BIN_DIR.mkdir(parents=True, exist_ok=True)

        try:
            for exe in exes:
                url, dest = bundle_binary_job(system_os, exe)
                self.progress.emit(f"Reinstalling {exe} (downloading)…")
                download_file(url, dest, self.progress.emit)
                _make_executable(dest)

                if exe == "yt-dlp":
                    if system_os == "Windows":
                        _verify_windows_ytdlp_exe(dest)
                    try:
                        _verify_ytdlp_runs(dest)
                    except OSError:
                        _remove_file_quiet(dest)
                        raise
                elif exe == "ffmpeg":
                    _verify_ffmpeg_or_ffprobe(dest, "ffmpeg")
                elif exe == "ffprobe":
                    _verify_ffmpeg_or_ffprobe(dest, "ffprobe")
                elif exe == "deno":
                    _verify_deno_binary(dest)
        except Exception as e:
            logger.exception("bundle reinstall failed")
            self.finished_err.emit(str(e))
            return

        label = ", ".join(exes)
        self.finished_ok.emit(
            f"Replaced in app binaries folder: {label}."
        )


class YtdlpInstallWorker(QThread):
    """Download latest yt-dlp release binary into ``BIN_DIR`` (always overwrites)."""

    progress = Signal(str)
    finished_ok = Signal(str)
    finished_err = Signal(str)

    def run(self):
        system_os = platform.system()
        if system_os not in BINARIES:
            self.finished_err.emit("Unsupported operating system.")
            return

        BIN_DIR.mkdir(parents=True, exist_ok=True)
        url, dest = bundle_binary_job(system_os, "yt-dlp")

        try:
            download_file(url, dest, self.progress.emit)
            if system_os == "Windows":
                _verify_windows_ytdlp_exe(dest)
            _make_executable(dest)
            _verify_ytdlp_runs(dest)
        except Exception as e:
            logger.exception("yt-dlp install download failed")
            _remove_file_quiet(dest)
            self.finished_err.emit(str(e))
            return

        self.finished_ok.emit(f"yt-dlp saved to {dest}")


class DepWorker(QThread):
    progress = Signal(str)

    def __init__(self, update_ytdlp: bool):
        super().__init__()
        self.missing: List[Tuple[str, str]] = []
        self.update_ytdlp = update_ytdlp

    def _check_missing_dependencies(self):
        system_os = platform.system()
        if system_os not in BINARIES:
            return

        required_binaries = ["ffmpeg", "ffprobe", "yt-dlp", "deno"]
        missing_exes = [
            exe
            for exe in required_binaries
            if not shutil.which(exe)
            and not (
                BIN_DIR / (exe + (".exe" if system_os == "Windows" else ""))
            ).exists()
        ]

        if not missing_exes:
            return

        BIN_DIR.mkdir(parents=True, exist_ok=True)

        for exe in missing_exes:
            self.missing.append(bundle_binary_job(system_os, exe))

    def chmod(self):
        _make_executable(self.filename)

    def run(self):
        self._check_missing_dependencies()

        if self.missing:
            for missingexe in self.missing:
                self.url, self.filename = missingexe
                self._download()
                self.chmod()
                base = os.path.basename(self.filename).lower()
                if base in ("yt-dlp.exe", "yt-dlp"):
                    try:
                        if platform.system() == "Windows":
                            _verify_windows_ytdlp_exe(self.filename)
                        _verify_ytdlp_runs(self.filename)
                    except OSError as e:
                        logger.error("Bundled yt-dlp failed verification: %s", e)
                        _remove_file_quiet(self.filename)
                        self.progress.emit(
                            "yt-dlp download was invalid — use “Install yt-dlp” or: pip install yt-dlp"
                        )

        if self.update_ytdlp:
            self.update()

        self.finished.emit()

    def update(self):
        create_window = sp.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        output = ""
        updated = False

        with sp.Popen(
            resolve_ytdlp_argv() + ["-U"],
            stdout=sp.PIPE,
            stderr=sp.STDOUT,
            text=True,
            universal_newlines=True,
            creationflags=create_window,
        ) as p:
            for line in p.stdout:
                output += line
                if line.startswith("Updating to"):
                    updated = True
                    self.progress.emit("Updating yt-dlp...")

        if p.returncode != 0:
            logger.error(f"yt-dlp update failed returncode: {p.returncode}\n{output}")
        elif updated:
            self.progress.emit("yt-dlp updated")
            logger.info(f"yt-dlp updated\n{output}")

    def _download(self):
        download_file(self.url, self.filename, self.progress.emit)
