# yt-dlp-gui

<p align="center">
  <img src=".github/readme-dev-banner.svg" alt="This project is developed in bursts; it may look quiet but it is not abandoned." width="780" />
</p>

> [!IMPORTANT]
> This project is in constant development—though not always in a constant state of progress. I tend to work in bursts: when inspiration hits, I can be completely locked in for days, making rapid progress and refining every detail. As that initial momentum fades, development usually slows down or pauses unless bugs or major issues need fixing.
>
> Because of that, the project may seem inactive at times, but it's never truly abandoned. I often return to it unexpectedly—whether I've found a better solution, thought of a new feature, or simply felt motivated to keep building again.

Simplistic graphical interface for the command line tool [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Usage

There are two ways to get started, depending on your preference and system:

* [`Portable`](#portable) ~ *Windows*
* [`Manual`](#manual) ~ *Platform independent*

### Portable

Download the latest [stable](https://github.com/dsymbol/yt-dlp-gui/releases/latest) or [nightly](https://github.com/dsymbol/yt-dlp-gui/releases/tag/nightly) build. This is a ZIP file containing the program files and all necessary dependencies.

*All releases are built and released using GitHub Workflow*

### Manual

You **must** have [Python](https://www.python.org/downloads/) 3.9+ installed.

```bash
git clone https://github.com/dsymbol/yt-dlp-gui
cd yt-dlp-gui
pip install -r requirements.txt
cd app
python app.py
```

## Preset Customization (Advanced)

Want to create your own presets or modify existing ones? You're in the right section. customization options reside in the `config.toml` file. If a preset fails, check the `debug.log` file for details.

**Notes:** 
- All files mentioned are in the `yt-dlp-gui` root directory.
- The arguments specified will be added to the [base](https://github.com/dsymbol/yt-dlp-gui/blob/main/app/worker.py#L28) `yt-dlp` arguments.
- Prefer lists over strings for complex presets.

### Presets

Defined in the `[presets]` table. Each preset is a key‑value pair, the value can be provided as a string or list.

### Example

```toml
[general]
...

[presets]
...
mp4_thumbnail = ["-f", "bv*[vcodec^=avc]+ba[ext=m4a]/b", "--embed-thumbnail"]
```
