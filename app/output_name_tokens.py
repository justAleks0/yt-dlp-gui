"""Tap-to-build output filename: token catalog, yt-dlp template fragments, presets."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional

def _ensure_categories(config: dict):
    from utils import ensure_download_categories

    return ensure_download_categories(config)


@dataclass(frozen=True, slots=True)
class OutputNameToken:
    id: str
    label: str
    fragment: str
    tooltip: str
    section: str
    example: str


def token_chip_tooltip(t: OutputNameToken) -> str:
    """Chip hover text: description plus a concrete sample (illustrative, not live metadata)."""
    ex = (t.example or "").strip()
    if not ex:
        return t.tooltip
    return f"{t.tooltip}\n\nExample: {ex}"


# fmt: off
# yt-dlp output template fields — see https://github.com/yt-dlp/yt-dlp#output-template
TOKEN_CATALOG: tuple[OutputNameToken, ...] = (
    # --- Literals / separators ---
    OutputNameToken("lit_space", "Space", " ", "A single space.", "Separators", "Hello world"),
    OutputNameToken("lit_dash", " – ", " - ", "Space-dash-space between parts.", "Separators", "Song title - Artist name"),
    OutputNameToken("lit_underscore", "_", "_", "Underscore.", "Separators", "2024-01-15_dQw4w9WgXcQ_clip"),
    OutputNameToken("lit_comma_space", "Comma + space", ", ", "Comma and space.", "Separators", "Hello, world"),
    OutputNameToken("lit_dot", ".", ".", "Dot (not the extension dot; ext is added automatically).", "Separators", "part1.part2"),
    OutputNameToken("lit_paren_open", "(", "(", "Open parenthesis.", "Separators", "My Video (4K"),
    OutputNameToken("lit_paren_close", ")", ")", "Close parenthesis.", "Separators", "My Video (4K)"),
    OutputNameToken("lit_bracket_open", "[", "[", "Open bracket.", "Separators", "Title [dQw4w9WgXcQ"),
    OutputNameToken("lit_bracket_close", "]", "]", "Close bracket.", "Separators", "Title [dQw4w9WgXcQ]"),
    # --- Core ---
    OutputNameToken("video_title", "Video title", "%(title)s", "Video title (sanitized by yt-dlp).", "Core", "Never Gonna Give You Up"),
    OutputNameToken("fulltitle", "Full title", "%(fulltitle)s", "Full title if different from title.", "Core", "Never Gonna Give You Up (Official Video)"),
    OutputNameToken("video_id", "Video ID", "%(id)s", "Service-specific video identifier.", "Core", "dQw4w9WgXcQ"),
    OutputNameToken("display_id", "Display ID", "%(display_id)s", "Human-readable id when available.", "Core", "dQw4w9WgXcQ"),
    # --- Channel / uploader ---
    OutputNameToken("uploader", "Uploader", "%(uploader)s", "Channel or uploader name.", "Channel", "Rick Astley"),
    OutputNameToken("uploader_id", "Uploader ID", "%(uploader_id)s", "Uploader account id when available.", "Channel", "RickAstleyVEVO"),
    OutputNameToken("channel", "Channel", "%(channel)s", "Channel name (YouTube and others).", "Channel", "Rick Astley"),
    OutputNameToken("channel_id", "Channel ID", "%(channel_id)s", "Channel id string.", "Channel", "UCuAXFkgsw1L7xaCfnd5JJOw"),
    # --- Dates ---
    OutputNameToken("upload_date", "Upload date (YYYYMMDD)", "%(upload_date)s", "Raw upload date as YYYYMMDD.", "Dates", "20091025"),
    OutputNameToken("upload_date_iso", "Upload date (ISO)", "%(upload_date>%Y-%m-%d)s", "Upload date as YYYY-MM-DD.", "Dates", "2009-10-25"),
    OutputNameToken("release_year", "Release year", "%(release_year)s", "Release year when present.", "Dates", "2009"),
    OutputNameToken("phrase_uploaded_at", "Phrase: Uploaded at…", ", Uploaded at %(upload_date)s", "Comma, text, then raw upload date.", "Dates", ", Uploaded at 20091025"),
    OutputNameToken("phrase_by_channel", "Phrase: By…", " By %(uploader)s", "Space, “By”, space, then uploader.", "Dates", " By Rick Astley"),
    # --- Playlist ---
    OutputNameToken("playlist_title", "Playlist title", "%(playlist_title)s", "Playlist or series title.", "Playlist", "80s Hits"),
    OutputNameToken("playlist_id", "Playlist ID", "%(playlist_id)s", "Playlist identifier.", "Playlist", "PLrAXtmErZgOeiKm"),
    OutputNameToken("playlist_index", "Playlist index", "%(playlist_index)s", "Index of video in playlist (1-based).", "Playlist", "3"),
    OutputNameToken("playlist_autonumber", "Playlist autonumber", "%(playlist_autonumber)s", "Autonumber field from yt-dlp.", "Playlist", "003"),
    OutputNameToken("playlist_count", "Playlist count", "%(playlist_count)s", "Total entries when known.", "Playlist", "120"),
    # --- Series ---
    OutputNameToken("season_number", "Season #", "%(season_number)s", "Season number.", "Series", "2"),
    OutputNameToken("season", "Season", "%(season)s", "Season label.", "Series", "Season 2"),
    OutputNameToken("episode_number", "Episode #", "%(episode_number)s", "Episode number.", "Series", "05"),
    OutputNameToken("episode", "Episode", "%(episode)s", "Episode label.", "Series", "E05"),
    OutputNameToken("series", "Series", "%(series)s", "Series name.", "Series", "Breaking Bad"),
    # --- Music ---
    OutputNameToken("artist", "Artist", "%(artist)s", "May be empty for non-music.", "Music", "Daft Punk"),
    OutputNameToken("track", "Track", "%(track)s", "Track title.", "Music", "Get Lucky"),
    OutputNameToken("album", "Album", "%(album)s", "Album name.", "Music", "Random Access Memories"),
    OutputNameToken("track_number", "Track #", "%(track_number)s", "Track number.", "Music", "4"),
    OutputNameToken("album_type", "Album type", "%(album_type)s", "single, album, etc.", "Music", "album"),
    # --- Technical ---
    OutputNameToken("resolution", "Resolution", "%(resolution)s", "e.g. 1920x1080.", "Technical", "1920x1080"),
    OutputNameToken("width", "Width", "%(width)s", "Video width in pixels.", "Technical", "1920"),
    OutputNameToken("height", "Height", "%(height)s", "Video height in pixels.", "Technical", "1080"),
    OutputNameToken("fps", "FPS", "%(fps)s", "Frames per second.", "Technical", "30"),
    OutputNameToken("vcodec", "Video codec", "%(vcodec)s", "Video codec id.", "Technical", "avc1.640028"),
    OutputNameToken("acodec", "Audio codec", "%(acodec)s", "Audio codec id.", "Technical", "opus"),
    OutputNameToken("abr", "Audio bitrate", "%(abr)s", "Audio bitrate.", "Technical", "128"),
    OutputNameToken("vbr", "Video bitrate", "%(vbr)s", "Video bitrate.", "Technical", "5000"),
    OutputNameToken("tbr", "Total bitrate", "%(tbr)s", "Total bitrate.", "Technical", "2500"),
    OutputNameToken("format_id", "Format ID", "%(format_id)s", "yt-dlp format id string.", "Technical", "137+140"),
    OutputNameToken("format_note", "Format note", "%(format_note)s", "Can be long; may clutter filenames.", "Technical", "1080p60 HD"),
    # --- Meta / extractor ---
    OutputNameToken("extractor", "Extractor", "%(extractor)s", "Site plugin name.", "Meta", "youtube"),
    OutputNameToken("extractor_key", "Extractor key", "%(extractor_key)s", "Internal extractor key.", "Meta", "Youtube"),
    OutputNameToken("language", "Language", "%(language)s", "Language code when available.", "Meta", "en"),
    OutputNameToken("duration_string", "Duration", "%(duration_string)s", "Human-readable duration.", "Meta", "3:33"),
    OutputNameToken("duration", "Duration (sec)", "%(duration)s", "Duration in seconds.", "Meta", "213"),
    # --- Engagement (optional) ---
    OutputNameToken("view_count", "Views", "%(view_count)s", "View count.", "Engagement", "1_234_567_890"),
    OutputNameToken("like_count", "Likes", "%(like_count)s", "Like count.", "Engagement", "8_000_000"),
    OutputNameToken("comment_count", "Comments", "%(comment_count)s", "Comment count.", "Engagement", "450_000"),
)
# fmt: on

TOKEN_BY_ID: dict[str, OutputNameToken] = {t.id: t for t in TOKEN_CATALOG}

SECTION_ORDER: tuple[str, ...] = (
    "Separators",
    "Core",
    "Channel",
    "Dates",
    "Playlist",
    "Series",
    "Music",
    "Technical",
    "Meta",
    "Engagement",
)


def build_template_body(token_ids: list[str]) -> str:
    """Concatenate yt-dlp template fragments; unknown ids skipped."""
    parts: list[str] = []
    for tid in token_ids:
        t = TOKEN_BY_ID.get(str(tid).strip())
        if t:
            parts.append(t.fragment)
    return "".join(parts)


def human_preview(token_ids: list[str]) -> str:
    """Short preview from token labels."""
    labels: list[str] = []
    for tid in token_ids:
        t = TOKEN_BY_ID.get(str(tid).strip())
        if t:
            labels.append(t.label)
    return " · ".join(labels) if labels else ""


# Preset id -> ordered token ids (data-driven quick layouts)
PRESET_PATTERNS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "title_only": ("Title only", "Just the video title.", ("video_title",)),
    "title_dash_channel": (
        "Title — Channel",
        "Title, dash, uploader.",
        ("video_title", "lit_dash", "uploader"),
    ),
    "channel_dash_title": (
        "Channel — Title",
        "Uploader, dash, title.",
        ("uploader", "lit_dash", "video_title"),
    ),
    "date_iso_dash_title": (
        "Date — Title",
        "ISO date, dash, title.",
        ("upload_date_iso", "lit_dash", "video_title"),
    ),
    "title_paren_channel": (
        "Title (Channel)",
        "Title, space, channel in parentheses.",
        ("video_title", "lit_space", "lit_paren_open", "channel", "lit_paren_close"),
    ),
    "archive_dedupe": (
        "Archive (date_id_title)",
        "Sortable unique-ish name.",
        ("upload_date_iso", "lit_underscore", "video_id", "lit_underscore", "video_title"),
    ),
    "playlist_index_title": (
        "Playlist index — Title",
        "Index, dash, title.",
        ("playlist_index", "lit_dash", "video_title"),
    ),
    "music_artist_track": (
        "Music: Artist — Track",
        "Artist, dash, track.",
        ("artist", "lit_dash", "track"),
    ),
    "music_album_track": (
        "Music: Album — # — Track",
        "Album, dash, track number, dash, track.",
        ("album", "lit_dash", "track_number", "lit_dash", "track"),
    ),
    "technical": (
        "Title + resolution + format",
        "Title, dash, resolution, dash, format id.",
        ("video_title", "lit_dash", "resolution", "lit_dash", "format_id"),
    ),
    "title_bracket_id": (
        "Title [id]",
        "Title, space, id in brackets.",
        ("video_title", "lit_space", "lit_bracket_open", "video_id", "lit_bracket_close"),
    ),
    "verbose_youtube_style": (
        "Verbose (title, channel, date, id)",
        "Title, channel phrase, upload phrase, id.",
        (
            "video_title",
            "phrase_by_channel",
            "phrase_uploaded_at",
            "lit_space",
            "lit_bracket_open",
            "video_id",
            "lit_bracket_close",
        ),
    ),
}


def preset_ids_ordered() -> list[str]:
    return list(PRESET_PATTERNS.keys())


def resolve_output_name_tokens(
    config: dict, category_key: Optional[str]
) -> list[str]:
    """
    Pick token list: per-category custom filename if enabled and non-empty,
    else general.output_name_tokens, else [].
    """
    g = config.get("general") or {}
    general_tokens = _normalize_token_list(g.get("output_name_tokens"))

    if not category_key or not str(category_key).strip():
        return general_tokens

    name = str(category_key).strip()
    for row in _ensure_categories(config):
        if str(row.get("name", "")).strip() != name:
            continue
        if bool(row.get("use_custom_filename", False)):
            cat_tokens = _normalize_token_list(row.get("output_name_tokens"))
            if cat_tokens:
                return cat_tokens
        break

    return general_tokens


def _normalize_token_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    return []


def build_output_o_template(out_dir: str, body: str) -> str:
    """
    Full -o value: directory + / + body + .%(ext)s
    Uses forward slashes for yt-dlp on Windows.
    """
    od = str(out_dir).replace("\\", "/").rstrip("/")
    b = (body or "").strip()
    if not b:
        return ""
    return f"{od}/{b}.%(ext)s"


_YTDL_FIELD_PATTERN = re.compile(r"%\(([^)]+)\)s")


def guess_extension_for_preview(preset_key: str, info: Mapping[str, Any]) -> str:
    """Best guess for final container extension (preset beats pre-merge info['ext'])."""
    k = (preset_key or "").strip().lower()
    if k == "mp3":
        return "mp3"
    if k == "mp4":
        return "mp4"
    ext = info.get("ext")
    if isinstance(ext, str) and ext.isalnum() and 1 <= len(ext) <= 8:
        return ext.lower()
    if k == "best":
        return "mp4"
    return "mkv"


def _info_field_as_str(info: Mapping[str, Any], field: str) -> str:
    v = info.get(field)
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, (list, dict)):
        return ""
    return str(v).strip()


def _substitute_one_field_inner(inner: str, info: Mapping[str, Any], *, na: str) -> str:
    inner = inner.strip()

    if ">" in inner:
        field, strfmt = inner.split(">", 1)
        field = field.strip()
        strfmt = strfmt.strip()
        raw = _info_field_as_str(info, field)
        if field == "upload_date" and raw and raw[:8].isdigit():
            try:
                dt = datetime.strptime(raw[:8], "%Y%m%d")
                return dt.strftime(strfmt)
            except ValueError:
                return na
        if raw:
            try:
                dt = datetime.fromtimestamp(float(raw))
                return dt.strftime(strfmt)
            except (ValueError, TypeError, OSError):
                return raw if raw else na
        return na

    if "|" in inner:
        field, default = inner.split("|", 1)
        field = field.strip()
        v = _info_field_as_str(info, field)
        return v if v else default

    v = _info_field_as_str(info, inner)
    return v if v else na


def substitute_ytdlp_filename_template(
    template: str, info: Mapping[str, Any], *, ext: str, na: str
) -> str:
    """Replace %(…)s placeholders using extractor JSON (best-effort vs real yt-dlp)."""

    def repl(m: re.Match[str]) -> str:
        inner = m.group(1).strip()
        if inner == "ext":
            return ext
        return _substitute_one_field_inner(inner, info, na=na)

    return _YTDL_FIELD_PATTERN.sub(repl, template)


def _sanitize_basename_piece(name: str, *, windows: bool, ascii_only: bool, na: str) -> str:
    s = name.replace("/", " ").replace("\\", " ")
    if windows:
        for c in '<>:"|?*':
            s = s.replace(c, " ")
    s = " ".join(s.split())
    if ascii_only:
        s = "".join(c if ord(c) < 128 else "_" for c in s)
    s = s.strip(" .")
    return s if s else na


def preview_output_filepath(
    config: dict,
    *,
    save_folder: str,
    category_key: Optional[str],
    preset_key: str,
    info: Mapping[str, Any],
) -> str:
    """
    Human-readable path preview matching worker rules (folder, tokens, -P default).
    Uses current Settings (sort folders, filename pattern, category path override).
    """
    from utils import effective_download_path, resolve_download_base_path

    g = config.get("general") or {}
    sort_on = bool(g.get("download_sort_folders", True))
    na = str(g.get("output_na_placeholder") or "…").strip() or "…"
    restrict = bool(g.get("restrict_filenames", False))
    win_fn = g.get("windows_filenames")
    if win_fn is None:
        import sys

        win_fn = sys.platform == "win32"
    win_fn = bool(win_fn)

    base = resolve_download_base_path(config, (save_folder or "").strip(), category_key)
    out_dir = effective_download_path(base, preset_key, sort_on)
    tokens = resolve_output_name_tokens(config, category_key)
    body = build_template_body(list(tokens))
    ext = guess_extension_for_preview(preset_key, info)

    if body.strip():
        o_tmpl = build_output_o_template(out_dir, body)
        if not o_tmpl:
            joined = os.path.join(out_dir, f"{na}.{ext}")
        else:
            full = substitute_ytdlp_filename_template(o_tmpl, info, ext=ext, na=na)
            p = Path(full.replace("\\", "/"))
            if not p.is_absolute():
                p = Path(out_dir) / p
            name = _sanitize_basename_piece(
                p.name, windows=win_fn, ascii_only=restrict, na=f"{na}.{ext}"
            )
            joined = str(p.parent / name)
    else:
        default_tmpl = "%(title)s.%(ext)s"
        bn = substitute_ytdlp_filename_template(default_tmpl, info, ext=ext, na=na)
        bn = _sanitize_basename_piece(bn, windows=win_fn, ascii_only=restrict, na=f"{na}.{ext}")
        joined = os.path.join(out_dir, bn)

    return str(Path(joined))
