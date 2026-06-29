# Universal Video Muxer

> Automatically mux subtitles, fonts, chapters, and metadata into your videos using FFmpeg.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-required-green.svg)](https://ffmpeg.org/)
[![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-orange.svg)](https://github.com/TomSchimansky/CustomTkinter)

Universal Video Muxer is a universal FFmpeg-powered muxer designed for anime, donghua, TV series, and fansub releases. It automatically matches episodes with subtitles, embeds fonts, adds optional chapter markers, preserves audio tracks and metadata, and generates clean output filenames using customizable templates.

**Now includes a fully-featured CustomTkinter GUI** with batch processing, single-file mode, subtitle copying between videos, and real-time cancellation.

---

## Original Developer

Please support the original creator **Shridhuu**.

GitHub: [https://github.com/Shridhuu](https://github.com/Shridhuu)

---

## Features

### GUI Features

- **Modern Dark/Light Mode UI** — built with CustomTkinter
- **Three Operating Modes:**
  - **Batch Mode** — process entire folders automatically
  - **Single File Mode** — mux individual video + subtitle pairs
  - **Copy Subtitles Mode** — transfer subtitle tracks between matching videos with duration verification
- **Real-time Cancellation** — safely stop muxing mid-process without corrupting files
- **Visual Chapter Editor** — add jump points with HH:MM:SS time pickers instead of raw text
- **Template Variable Buttons** — one-click insertion of `{series}`, `{ep}`, `{ep2}`, `{video_stem}`
- **Scrollable Interface** — works on any screen size
- **Clearable Text Fields** — subtle ✕ buttons on all inputs
- **Embedded FFmpeg Support** — bundles ffmpeg/ffprobe in standalone Windows builds

### Core Muxing Features

- **Automatic episode-to-subtitle matching** from common naming schemes
- **Fallback positional matching** — if no episode numbers are detected, files are paired alphabetically 1-to-1
- **Already-muxed detection** — skips files that were previously processed
- **Multiple subtitle formats** — ASS, SSA, SRT, VTT, SUB (with ASS prioritized; all converted to ASS in output)
- **Font embedding** — all fonts in configured font directory are automatically attached
- **Chapter/jump point support** — optional chapter markers for media players
- **Lossless output** — video and audio are copied without re-encoding
- **Metadata & language preservation** — all track info carried over
- **Custom output naming** — flexible template system for filenames
- **Always outputs MKV** — regardless of source container format
- **Duration-matched subtitle copying** — verifies source/target durations match within 1.5s tolerance

---

## Requirements

### For GUI Usage

- Python 3.8+
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) (`pip install customtkinter`)
- FFmpeg & FFprobe (auto-detected from `tools/` folder or system PATH)

### For CLI Usage

- Python 3.8+
- [FFmpeg](https://ffmpeg.org/download.html)
- FFprobe (included with FFmpeg)

Verify your installation:

```bash
ffmpeg -version
ffprobe -version
```

---

## Installation

**Clone the repository:**

```bash
git clone https://github.com/FlamingWater35/universal-video-muxer.git
cd universal-video-muxer
```

**Install GUI dependencies:**

```bash
pip install customtkinter
```

Or simply download `gui.py` and place it in your release folder alongside the `tools/` directory.

---

## Project Structure

``` bash
universal-video-muxer/
├── assets/
│   └── icon.ico            ← App icon
├── tools/
│   ├── ffmpeg.exe          ← Bundled FFmpeg binary
│   └── ffprobe.exe         ← Bundled FFprobe binary
├── scripts/
│   └── build.ps1           ← PowerShell build script for Windows
├── gui.py            ← Main GUI application
└── README.md
```

### Default Media Folder Layout (Batch Mode)

When using Batch Mode, the default expected structure is:

``` bash
Series Folder/
├── 1.mkv
├── 2.mkv
├── 3.mkv
│
└── sub/
    ├── 1.ass
    ├── 2.ass
    ├── 3.ass
    │
    └── font/
        ├── font1.ttf
        ├── font2.otf
        └── font3.ttc
```

> **Note:** All directories (Video, Subtitle, Font) are fully configurable in the GUI. The above is only the default.

---

## Usage

### GUI Mode

```bash
python gui.py
```

The GUI provides three modes selectable via a segmented button at the top:

| Mode | Description |
|---|---|
| **Batch Mode** | Select video, subtitle, and font directories. Episodes are auto-matched by name/number. |
| **Single File Mode** | Pick one video file and one subtitle file for manual muxing. |
| **Copy Subtitles Mode** | Select a source directory (videos with subs) and target directory (videos without). Matches by filename and verifies duration before copying. |

#### Key GUI Controls

- **✕ Clear Buttons** — every text field has a subtle clear button
- **Template Variable Buttons** — click `{series}`, `{ep}`, `{ep2}`, or `{video_stem}` to insert into the output template
- **Chapter Editor** — toggle "Add Jump Points", then use the Title + HH:MM:SS fields to add chapters visually
- **Cancel Button** — appears during processing; safely terminates FFmpeg and cleans up temp files
- **Log Panel** — real-time scrollable console output at the bottom

### CLI Mode (Original)

Open a terminal in the same folder as your episodes and run:

```bash
python3 cli.py
```

---

## Output Template Variables

| Variable | Description |
|---|---|
| `{series}` | Series name |
| `{ep}` | Episode number |
| `{ep2}` | Episode number with leading zero |
| `{video_stem}` | Original filename without extension |

**Examples:**

```
{series} EP{ep2}
{series} S7-{ep2} [4K 8Bits E-AC-3 & AAC-LC]
{series} - {ep2}
{video_stem}
```

> In the GUI, click the variable buttons below the template field to insert them instantly.

---

## Supported Video Formats

| Format | Extension |
|---|---|
| Matroska | `.mkv` |
| MPEG-4 | `.mp4` |
| iTunes Video | `.m4v` |
| QuickTime | `.mov` |
| AVI | `.avi` |
| WebM | `.webm` |

> Regardless of input format, the output is always an `.mkv` file.

---

## Supported Episode Formats

Episode numbers are automatically detected from these filename patterns:

| Pattern | Example |
|---|---|
| `S##E##` | `Stellar Transformation S07E01.mkv` |
| `#x##` | `7x01.mkv` |
| `EP##` | `EP01.mkv` |
| `Episode ##` | `Episode 01.mkv` |
| `##` | `01.mkv` |
| `###` | `001.mkv` |

---

## Subtitle Priority

When multiple subtitle formats exist for the same episode, the best one is selected automatically:

1. ASS
2. SSA
3. SRT
4. VTT
5. SUB

Styled subtitles (ASS/SSA) are always preferred when available.

---

## Jump Points (Chapters)

### GUI

Toggle **"Add Jump Points (Chapters)"**, then use the visual editor:

- Enter a **Title**
- Set **HH**, **MM**, and **SS.ms** using dedicated fields
- Click **Add Chapter** to add it to the list
- Delete individual entries with the red **Delete** button

### CLI

When prompted `Add jump points? (y/n): y`, enter chapters in `Label|MM:SS` or `Label|HH:MM:SS` format:

``` bash
Opening|00:00
Episode Title & Number|02:32
Episode|02:35
```

---

## Font Attachments

All font files inside the configured font directory are automatically embedded into the output MKV.

**Supported formats:** `.ttf`, `.otf`, `.ttc`

---

## What Gets Preserved / Removed

| Preserved | Removed |
|---|---|
| Video streams | Existing cover art streams |
| Audio streams | Original subtitle tracks |
| Metadata | |
| Language information | |
| Attached fonts | |

---

## Notes

- Video and audio streams are copied directly — **no quality loss**.
- All subtitle formats are **converted to ASS** in the output and tagged as English (`language=eng`).
- Files already processed are **automatically skipped** on subsequent runs.
- If no episode numbers are found in filenames, files are **paired alphabetically** in order.
- Source files are removed only after **successful** muxing.
- **Copy Subtitles Mode** requires durations to match within **1.5 seconds**.
- FFmpeg and FFprobe are auto-detected from `tools/` first, then system PATH.
- Existing cover art is intentionally ignored during muxing.
- **Cancellation** safely terminates FFmpeg and removes incomplete temp files.

---

## Disclaimer

Universal Video Muxer is a **muxing utility only**. It does not encode video, encode audio, modify quality, or alter the original media streams in any way. All video and audio are copied directly using FFmpeg.

---

## License

This project is licensed under the [MIT License](LICENSE).
