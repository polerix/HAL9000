# HAL 9000 Viewscreen

Life-size HAL 9000 replica display system. A Pygame kiosk app drives a 7" 1024×600 HDMI display in portrait orientation (600×1024), cycling through 12 spacecraft systems every 30 seconds and showing two panels per system:

- **High Screen** – Red function label panel with the active system code (e.g. `ATM`, `NAV`, `DMG`)
- **Lower Screen** – Looping video animation matching the current function

Primary deployment target is a Raspberry Pi 3 driving the physical prop display — see [`RaspberryPi 3.md`](RaspberryPi%203.md) for hardware wiring, HDMI/portrait config, and the systemd service. This README covers running and developing the app, including on a desktop (macOS/Linux) for testing.

## Requirements

- Python 3.10+
- [`pygame-ce`](https://pyga.me/) (community fork of pygame — see note below)

Dependencies are pinned in [`requirements.txt`](requirements.txt).

> **Why pygame-ce, not pygame:** `pygame` 2.6.1 has a circular-import bug in `pygame.font` on newer Python releases (confirmed on 3.14), which crashes the app on startup with `NotImplementedError: font module not available`. `pygame-ce` is an actively maintained, drop-in-compatible fork without that bug. If you're on an older/stable Python and prefer upstream `pygame`, it should still work — just swap the pin in `requirements.txt`.

## Quick Start (Desktop / macOS testing)

Use a virtual environment so nothing touches your system Python:

```bash
cd HAL9000
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python3 hal_viewscreen.py --windowed   # windowed, for testing
python3 hal_viewscreen.py              # fullscreen
```

`.venv/` is self-ignored by git (venvs created with `python -m venv` write their own `.gitignore`), so it never needs to be committed.

## Quick Start (Raspberry Pi 3, production)

```bash
git clone <repo-url> ~/HAL9000
cd ~/HAL9000
chmod +x setup_pi.sh
sudo ./setup_pi.sh
sudo reboot
```

Full hardware setup, HDMI portrait config, and systemd service management: see [`RaspberryPi 3.md`](RaspberryPi%203.md).

## Keyboard Controls (Testing)

| Key | Action |
|---|---|
| `→` Right Arrow | Next function |
| `←` Left Arrow | Previous function |
| `Space` | Resume auto-cycling |
| `Esc` | Quit |

## System Functions

| Code | System | Subtitle |
|---|---|---|
| ATM | Spacecraft Atmosphere Monitoring | O2N: 14-RA |
| CNT | Control | SYS: 09-MX |
| COM | Communications | FRQ: 31-AE |
| DMG | System Damage | GPM: 72-KC |
| FLX | Flight Dynamics | DYN: 58-PL |
| GDE | Guidance Data Extension | NAV: 43-QR |
| HIB | Hibernation | CRY: 06-TB |
| LIF | Life Support | ENV: 21-SG |
| MEM | Memory | BNK: 88-FH |
| NAV | Navigation | TRJ: 55-WD |
| NUC | Nuclear Reactor Status | RCT: 37-JN |
| VEH | Vehicle Status | HUL: 64-BV |

## Architecture

```
hal_viewscreen.py      Main application (Pygame)
├── config.py          Constants, layout, function definitions
├── Video/             MP4 animations (7-8 per function)
├── Fonts/             Eurostile KFB font family
└── Artwork/SVG/       Screen layout + example panel
```

## Files

| File | Purpose |
|---|---|
| `hal_viewscreen.py` | Main display application |
| `config.py` | Configuration & constants |
| `requirements.txt` | Python dependencies |
| `setup_pi.sh` | Raspberry Pi setup script |
| `hal9000-viewscreen.service` | Systemd auto-start unit (Pi) |
| `RaspberryPi 3.md` | Hardware setup & Pi deployment reference |
| `7" ScreenSpecifications.md` | Display hardware spec sheet |

## Notes

- Video playback is fully in-window: frames are decoded with OpenCV and drawn directly onto the same pygame surface as the rest of the UI, rather than shelling out to an external player. There is no separate OS-level video window to position — the whole display is one window.
- This is software decoding. See [`RaspberryPi 3.md`](RaspberryPi%203.md) for a note on Pi 3 performance if you deploy there.
- The `set_function()` API in `FunctionController` is ready for external control (Arduino serial, network, etc.)
- Cycle interval is configurable in `config.py` (`CYCLE_INTERVAL_SEC`)
- Font rendering uses Eurostile KFB Bold Extended (matching the movie prop typography)

## Licensing

The source code in this repository is released under the [MIT License](LICENSE).

Third-party material bundled in this repository (fonts, audio, video, artwork, saved web pages and similar files) is **not** covered by that license. It remains the property of its respective owners and is included under their own terms. If you are a rights holder and want something removed, please open an issue.

## Deployment & Repository Status

- **Standardized Name**: `HAL9000`
- **Remote Origin**: `https://github.com/polerix/HAL9000`
- **License Level**: `MIT` ([`LICENSE`](LICENSE))
- **Security Policy**: [`SECURITY.md`](SECURITY.md)
- **GitHub Actions**: Static / Manual
- **Last Compliance Audit**: `2026-10-18`

### GitHub CleanUp Log
- **Unused / Archive / Cache Items Moved to `/Volumes/Clay/GitHubCleanUp/HAL9000/`**: 25 item(s) (4405 files, 461.01 MB)
  - `Video` — Legacy unsplit 4K videos superseded by Animations/ (86 files, 184 MB) (87 file(s), 183.59 MB)
  - `Function_Scenes` — Unused split title-card videos (High Screen renders dynamically via Pygame) (85 file(s), 2.78 MB)
  - `RaspberryPi 3` — 43-byte scratch file superseded by RaspberryPi 3.md (1 file(s), 0.0 KB)
  - `Artwork/HAL9000_Console_UX.ai` — Unreferenced Illustrator source file (1 file(s), 128.7 KB)
  - `Artwork/HAL 9000 Screens & Badge.pdf` — Unreferenced PDF file (1 file(s), 2.38 MB)
  - `PCB/hal9000-keypad/hal9000-keypad-backups` — KiCad PCB backup zip directory (1 file(s), 42.2 KB)
  - `Fonts/Futura-Font-main` — Unused commercial Futura font directory (173 file(s), 12.93 MB)
  - `Fonts/Helvetica-Font-main` — Unused commercial Helvetica font directory (164 file(s), 15.13 MB)
  - `Fonts/OnlineWebFonts_COM_87c39c0a0b710d515e8af4023784f55c` — Unused third-party webfont dump (10 file(s), 225.3 KB)
  - `Fonts/artisan12.otf` — Unused third-party OTF font (1 file(s), 37.5 KB)
  - `Fonts/Eurostile-Font-main/Alternate Version for Eurostile - Extended (Microgramma)` — Unused third-party font variant (2 file(s), 186.2 KB)
  - `Fonts/Eurostile-Font-main/Eurostile (Original Version)` — Unused third-party font variant (2 file(s), 85.9 KB)
  - `Fonts/Eurostile-Font-main/Eurostile (Pro Version)` — Unused commercial Pro font variant (19 file(s), 1.88 MB)
  - `Fonts/Eurostile-Font-main/Eurostile LT (Linotype)` — Unused commercial Linotype font variant (10 file(s), 624.0 KB)
  - `Fonts/Eurostile-Font-main/Eurostile LT (Pro Version, Unicode)` — Unused commercial Linotype Unicode font variant (6 file(s), 426.2 KB)
  - `Fonts/Eurostile-Font-main/New Version of Eurostile - Extended (Michroma)` — Unused font variant (2 file(s), 122.3 KB)
  - `Fonts/Eurostile-Font-main/Second Alternate Version for Eurostile - Extended (Gyrochrome)` — Unused font variant (6 file(s), 354.8 KB)
  - `Fonts/Eurostile-Font-main/Square 721 BT (Eurostile's Bitstream Version)` — Unused commercial Bitstream font variant (10 file(s), 413.0 KB)
  - `under-construction.html` — Unused placeholder HTML stub (1 file(s), 1.6 KB)
  - `__pycache__` — Local dependency/build cache (__pycache__) (2 file(s), 27.5 KB)
  - `.venv` — Local dependency/build cache (.venv) (3817 file(s), 239.68 MB)
  - `.DS_Store` — OS metadata file (1 file(s), 14.0 KB)
  - `Images/.DS_Store` — OS metadata file (1 file(s), 6.0 KB)
  - `Fonts/.DS_Store` — OS metadata file (1 file(s), 8.0 KB)
  - `Terminal_Parts/.DS_Store` — OS metadata file (1 file(s), 6.0 KB)
