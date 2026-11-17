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

## Voice Mode (VOX) and the API key

**The web terminal holds no Anthropic API key, and never asks for one.** It
will not prompt you, there is no key field in the setup overlay, and nothing
key-shaped is written to `localStorage`. If a copy of this page ever asks you
to paste an `sk-ant-…` key, it is not this build — close it.

HAL answers from whichever of three tiers is available. The page picks one at
runtime by probing `http://127.0.0.1:3001/api/health` with a 400 ms timeout.

| Tier | When it is used | Where the key is | What HAL says |
|---|---|---|---|
| **Scripted** | default — no local service running | nowhere | a line from the nine film quotes, in order |
| **Sidecar** | `hal_sidecar.py` is running on this machine with a key | `ANTHROPIC_API_KEY` in the sidecar's environment | a live Claude response, in character |
| **Direct** (dev) | you added `?direct` to the URL | memory, this browser tab only | a live Claude response |

### The public demo is scripted

The GitHub Pages copy of `HAL9000-TERMINAL-WEB.html` has **no AI backend**. It
cannot have one: there is no key in the page and no service to reach. Press VOX
there and HAL recites film quotes. It is a prop, and it is honest about being a
prop. Everything else on the page — the eye, the screens, the VU meter, the
webcam feed, the weather — is real.

### Running the real thing locally

```bash
export ANTHROPIC_API_KEY=sk-ant-...        # your key, your machine
python3 hal_sidecar.py                     # listens on 127.0.0.1:3001 only
```

Then open `HAL9000-TERMINAL-WEB.html`. The page detects the sidecar and routes
VOX through it. Stop the sidecar and the page silently falls back to quotes.

The sidecar binds `127.0.0.1` and nothing else — not `0.0.0.0`, and there is no
flag that changes that. Nothing on your network can reach it. The key stays in
the sidecar process: it is never sent to the browser, never logged, and never
included in a response or an error.

**HAL's character is defined server-side**, in `hal_claude.py`. The browser
sends only `{utterance, crewName, weather}` as plain data. A page that has been
tampered with cannot rewrite who HAL is, because it never had the prompt.

### On the Pi

```bash
sudo ./install_sidecar.sh
sudo nano /etc/hal9000/env      # put the key here; the installer never touches it
sudo systemctl start hal9000-sidecar
```

`/etc/hal9000/env` is root-owned and mode 0600. The installer deliberately will
not take the key from you — not as an argument, not from a `read` prompt — so it
cannot end up in shell history or in `ps`.

### The `?direct` tier

`?direct` exists so the author can test against the live API without starting
the sidecar. It prompts once per tab and keeps the key in a closure: never in
`localStorage`, never in `sessionStorage`, never in the DOM, never in a cookie.
Nothing in the UI offers it and you cannot reach it by accident. It is not a
supported way to deploy this page. If you are not developing HAL, do not use it.

Full rationale: [`docs/ADR-001-ai-backend.md`](docs/ADR-001-ai-backend.md).

## Secret Scanning

```bash
python3 scripts/scan_secrets.py --self-test   # prove the scanner still works
python3 scripts/scan_secrets.py .             # scan the tree
```

Both run in CI on every push and pull request ([`.github/workflows/secret-scan.yml`](.github/workflows/secret-scan.yml)),
self-test first. The self-test plants each credential shape it claims to detect
and fails the build if any goes unnoticed — a scanner that cannot be shown to
fail is worse than no scanner, because it buys false confidence.

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
├── hal_claude.py      Shared Anthropic client + HAL's system prompt
├── Video/             MP4 animations (7-8 per function)
├── Fonts/             Eurostile KFB font family
└── Artwork/SVG/       Screen layout + example panel

hal_sidecar.py         127.0.0.1-only AI service for the web terminal
└── hal_claude.py      (same shared client — one implementation, two callers)

HAL9000-TERMINAL-WEB.html   Single-file web terminal; holds no API key
```

## Files

| File | Purpose |
|---|---|
| `hal_viewscreen.py` | Main display application |
| `config.py` | Configuration & constants |
| `requirements.txt` | Python dependencies |
| `hal_sidecar.py` | Loopback-only AI service for the web terminal |
| `hal_claude.py` | Shared Anthropic client and HAL's system prompt |
| `HAL9000-TERMINAL-WEB.html` | Single-file web terminal (no API key in it) |
| `setup_pi.sh` | Raspberry Pi setup script |
| `install_sidecar.sh` | Installs the sidecar service and `/etc/hal9000/env` |
| `scripts/scan_secrets.py` | Secret scanner with a self-test; runs in CI |
| `hal9000-viewscreen.service` | Systemd auto-start unit (Pi) |
| `hal9000-sidecar.service` | Systemd unit for the AI sidecar (Pi) |
| `docs/ADR-001-ai-backend.md` | Why the key lives where it does |
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
