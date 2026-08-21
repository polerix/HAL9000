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
