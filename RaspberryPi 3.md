# HAL 9000 – Raspberry Pi 3 Viewscreen

## Overview

Life-size HAL 9000 replica display system running on Raspberry Pi 3. Drives a 7" 1024×600 HDMI display in portrait orientation (600×1024), showing two panels:

- **High Screen** – Red function label panel with the active system code (e.g. `ATM`, `NAV`, `DMG`)
- **Lower Screen** – Looping video animation matching the current function

The display cycles through 12 spacecraft systems every 30 seconds, randomly selecting one of 7-8 available animations per system.

## Hardware

| Component | Specification |
|---|---|
| Computer | Raspberry Pi 3 Model B |
| Display | Generic 7" 1024×600 HDMI (PCB80052, 7C GQ-852) |
| Connection | Mini-HDMI to HDMI |
| Orientation | Portrait (600×1024) |

## Quick Start

### 1. Clone to Raspberry Pi
```bash
git clone <repo-url> ~/HAL9000
cd ~/HAL9000
```

### 2. Run Setup
```bash
chmod +x setup_pi.sh
sudo ./setup_pi.sh
sudo reboot
```

### 3. Start Manually (for testing)
```bash
# Windowed mode (on desktop)
python3 hal_viewscreen.py --windowed

# Fullscreen
python3 hal_viewscreen.py
```

### 4. Service Commands
```bash
sudo systemctl start hal9000-viewscreen    # Start
sudo systemctl stop hal9000-viewscreen     # Stop
sudo systemctl status hal9000-viewscreen   # Status
journalctl -u hal9000-viewscreen -f        # Live logs
```

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

### Display Layout (600×1024)

```
┌──────────────────────────┐  0
│          (black)          │
│   ┌──────────────────┐   │  28px
│   │                  │   │
│   │   HIGH SCREEN    │   │
│   │   (red panel)    │   │
│   │   Function Label │   │
│   │                  │   │
│   └──────────────────┘   │  501px
│          (black)          │
│   ┌──────────────────┐   │  523px
│   │                  │   │
│   │   LOWER SCREEN   │   │
│   │   (video area)   │   │
│   │   video playback │   │
│   │                  │   │
│   └──────────────────┘   │  996px
│          (black)          │
└──────────────────────────┘  1024
    64px              537px
```

## Files

| File | Purpose |
|---|---|
| `hal_viewscreen.py` | Main display application |
| `config.py` | Configuration & constants |
| `setup_pi.sh` | Raspberry Pi setup script |
| `hal9000-viewscreen.service` | Systemd auto-start unit |
| `requirements.txt` | Python dependencies |

## Notes

- Videos are 4K source files decoded via OpenCV and drawn directly onto the pygame surface (in-process, same window as the rest of the UI — no separate player window). Frames are resized down to 473×473px each draw call.
- This is software decoding, not hardware-accelerated. On a Pi 3 this may not sustain smooth playback of full 4K source files — if you see dropped frames or high CPU, pre-transcode the videos in `Video/` down to roughly panel resolution (e.g. `ffmpeg -i in.mp4 -vf scale=473:473 out.mp4`) so decode cost matches what's actually displayed.
- The `set_function()` API in `FunctionController` is ready for external control (Arduino serial, network, etc.)
- Cycle interval is configurable in `config.py` (`CYCLE_INTERVAL_SEC`)
- Font rendering uses Eurostile KFB Bold Extended (matching the movie prop typography)
