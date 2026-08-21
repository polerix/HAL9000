"""
HAL 9000 Viewscreen – Configuration
=====================================
Layout constants extracted from 600x1024_VideoScreen_Layout_bleed.svg
and example_panel.svg. All coordinates are in pixels for 600x1024 portrait display.
"""

import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(BASE_DIR, "Video")
FONT_DIR = os.path.join(
    BASE_DIR, "Fonts", "Eurostile-Font-main",
    "Eurostile KFB (Self-created)"
)

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
# Each function has: code, full name, subtitle (HAL-authentic identifier)
# Subtitles follow the example_panel.svg pattern: "GPM: 72-KC"

FUNCTIONS = [
    {"code": "ATM", "name": "Spacecraft Atmosphere Monitoring", "subtitle": "O2N: 14-RA"},
    {"code": "CNT", "name": "Control",                         "subtitle": "SYS: 09-MX"},
    {"code": "COM", "name": "Communications",                  "subtitle": "FRQ: 31-AE"},
    {"code": "DMG", "name": "System Damage",                   "subtitle": "GPM: 72-KC"},
    {"code": "FLX", "name": "Flight Dynamics",                 "subtitle": "DYN: 58-PL"},
    {"code": "GDE", "name": "Guidance Data Extension",         "subtitle": "NAV: 43-QR"},
    {"code": "HIB", "name": "Hibernation",                     "subtitle": "CRY: 06-TB"},
    {"code": "LIF", "name": "Life Support",                    "subtitle": "ENV: 21-SG"},
    {"code": "MEM", "name": "Memory",                          "subtitle": "BNK: 88-FH"},
    {"code": "NAV", "name": "Navigation",                      "subtitle": "TRJ: 55-WD"},
    {"code": "NUC", "name": "Nuclear Reactor Status",          "subtitle": "RCT: 37-JN"},
    {"code": "VEH", "name": "Vehicle Status",                  "subtitle": "HUL: 64-BV"},
]

# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------
CYCLE_INTERVAL_SEC = 30       # Seconds between function changes
FPS = 30                      # Pygame framerate cap
