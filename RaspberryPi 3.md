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

| Code | System | Subtitle | Panel Color |
|---|---|---|---|
| ATM | Spacecraft Atmosphere Monitoring | MRN: 80-EJ | Crimson Red (`#9D0032`) |
| CNT | Control | VER: 80-KJ | Sage Green (`#426F49`) |
| COM | Communications | PMT: 26-07 | Plum Magenta (`#733863`) |
| DMG | System Damage | GPM: 72-KC | Bright Crimson (`#C10341`) |
| FLX | Flight Dynamics | ATA: 48-12 | Royal Blue (`#294194`) |
| GDE | Guidance Data Extension | LIF: 13-AG | Cerulean Blue (`#2C4DA1`) |
| HIB | Hibernation | STA: 35-05 | Dark Teal (`#074941`) |
| LIF | Life Support | ATA: 61-08 | Rose Magenta (`#9E214B`) |
| MEM | Memory | PMT: 49-XB | Slate Steel Blue (`#17395A`) |
| NAV | Navigation | RTE: 09-EF | Deep Violet (`#52316B`) |
| NUC | Nuclear Reactor Status | AQS: 64-VN | Midnight Navy (`#0F1738`) |
| VEH | Vehicle Status | LIN: 86-QW | Cobalt Blue (`#2C4DA1`) |

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
