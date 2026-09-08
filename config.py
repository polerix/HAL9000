"""
HAL 9000 Viewscreen – Configuration
=====================================
Layout constants extracted from 600x1024_VideoScreen_Layout_bleed.svg
and example_panel.svg. All coordinates are in pixels for 600x1024 portrait display.
"""

import json
import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ANIMATIONS_DIR = os.path.join(BASE_DIR, "Animations")
VIDEO_DIR = ANIMATIONS_DIR if os.path.isdir(ANIMATIONS_DIR) else os.path.join(BASE_DIR, "Video")
FONT_DIR = os.path.join(
    BASE_DIR, "Fonts", "Eurostile-Font-main",
    "Eurostile KFB (Self-created)"
)
FUNCTION_DATA_PATH = os.path.join(BASE_DIR, "Function.json")

# Eurostile KFB font files (matching the example_panel.svg styles)
FONT_BOLD_EXTENDED = os.path.join(FONT_DIR, "Eurostile KFB Bold Extended.ttf")
FONT_EXTENDED = os.path.join(FONT_DIR, "Eurostile KFB Extended.ttf")
FONT_REGULAR = os.path.join(FONT_DIR, "Eurostile KFB.ttf")

# ---------------------------------------------------------------------------
# Screen Dimensions
# ---------------------------------------------------------------------------
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 1024

# ---------------------------------------------------------------------------
# Panel Geometry (extracted from SVG path data)
# ---------------------------------------------------------------------------
# Both panels are 472.6 x 472.6 rounded rects with 43.83px corner radius,
# horizontally centered in the 600px canvas.

PANEL_WIDTH = 473
PANEL_HEIGHT = 473
PANEL_CORNER_RADIUS = 44

# High screen (function label panel)
HIGH_SCREEN_X = 64       # (600 - 473) / 2 ≈ 63.7
HIGH_SCREEN_Y = 28       # from SVG: y starts at 28.19
HIGH_SCREEN_RECT = (HIGH_SCREEN_X, HIGH_SCREEN_Y, PANEL_WIDTH, PANEL_HEIGHT)

# Low screen (video playback area)
LOW_SCREEN_X = 64
LOW_SCREEN_Y = 523       # from SVG: y starts at 523.22
LOW_SCREEN_RECT = (LOW_SCREEN_X, LOW_SCREEN_Y, PANEL_WIDTH, PANEL_HEIGHT)

# ---------------------------------------------------------------------------
# Colors (from example_panel.svg)
# ---------------------------------------------------------------------------
COLOR_BLACK = (0, 0, 0)
COLOR_PANEL_RED = (193, 3, 65)          # #c10341 – red panel background
COLOR_TEXT_WHITE = (241, 241, 241)      # #f1f1f1 – panel text
COLOR_PANEL_BLUE = (38, 60, 197)        # #263cc5 – SVG cutout reference

# ---------------------------------------------------------------------------
# Typography (sizes from example_panel.svg, scaled to panel)
# The example SVG is 472.5x472.5; our panel is 473x473 — near 1:1 mapping.
# ---------------------------------------------------------------------------
FONT_SIZE_CODE = 71           # Large 3-letter function code (71.07px in SVG)
FONT_SIZE_SUBTITLE = 17       # Subtitle text (16.72px in SVG)

# ---------------------------------------------------------------------------
# Function Definitions
# ---------------------------------------------------------------------------
# Each function has: code, full name, subtitle (HAL-authentic identifier),
# and its own high-screen panel color. Loaded from Function.json, which is
# the source of truth for this data (colors curated per-system: reds for
# damage/life-critical systems, blues for navigation/reactor, etc).
# Subtitles follow the example_panel.svg pattern: "GPM: 72-KC"

# Fallback used only if Function.json is missing/malformed, so the app can
# still start. Matches the original static design (every panel red).
_FALLBACK_FUNCTIONS = [
    {"code": "ATM", "name": "Spacecraft Atmosphere Monitoring", "subtitle": "MRN: 80-EJ"},
    {"code": "CNT", "name": "Control",                         "subtitle": "VER: 80-KJ"},
    {"code": "COM", "name": "Communications",                  "subtitle": "PMT: 26-07"},
    {"code": "DMG", "name": "System Damage",                   "subtitle": "GPM: 72-KC"},
    {"code": "FLX", "name": "Flight Dynamics",                 "subtitle": "ATA: 48-12"},
    {"code": "GDE", "name": "Guidance Data Extension",         "subtitle": "LIF: 13-AG"},
    {"code": "HIB", "name": "Hibernation",                     "subtitle": "STA: 35-05"},
    {"code": "LIF", "name": "Life Support",                    "subtitle": "ATA: 61-08"},
    {"code": "MEM", "name": "Memory",                          "subtitle": "PMT: 49-XB"},
    {"code": "NAV", "name": "Navigation",                      "subtitle": "RTE: 09-EF"},
    {"code": "NUC", "name": "Nuclear Reactor Status",          "subtitle": "AQS: 64-VN"},
    {"code": "VEH", "name": "Vehicle Status",                  "subtitle": "LIN: 86-QW"},
]
for _f in _FALLBACK_FUNCTIONS:
    _f["color"] = COLOR_PANEL_RED
    _f["text_color"] = COLOR_TEXT_WHITE


def _hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i:i + 2], 16) for i in (0, 2, 4))


def _load_functions():
    try:
        with open(FUNCTION_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        functions = []
        for entry in data:
            color = tuple(entry["rgb"]) if "rgb" in entry else _hex_to_rgb(entry["hex"])
            text_color = _hex_to_rgb(entry["text_color"]) if "text_color" in entry else COLOR_TEXT_WHITE
            functions.append({
                "code": entry["code"],
                "name": entry["name"],
                "subtitle": entry["subtitle"],
                "color": color,
                "text_color": text_color,
            })
        if not functions:
            raise ValueError("Function.json contained no entries")
        return functions
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"[WARN] Could not load {FUNCTION_DATA_PATH} ({e}); using default red panels")
        return _FALLBACK_FUNCTIONS


FUNCTIONS = _load_functions()
FUNCTION_BY_CODE = {f["code"]: f for f in FUNCTIONS}

# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------
CYCLE_INTERVAL_SEC = 30       # Seconds between function changes
FPS = 30                      # Pygame framerate cap

# ---------------------------------------------------------------------------
# Live Data Settings
# ---------------------------------------------------------------------------
WEATHER_LAT = 46.0878          # Moncton, NB
WEATHER_LON = -64.7782
WEATHER_CITY = "Moncton"
WEATHER_COUNTRY = "CA"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CACHE_DIR = os.path.join(BASE_DIR, "cache")
CACHE_WEA_PATH = os.path.join(CACHE_DIR, "wea.json")
CACHE_MED_PATH = os.path.join(CACHE_DIR, "med.json")
FETCH_INTERVAL_SEC = 600       # Refresh live data every 10 minutes
