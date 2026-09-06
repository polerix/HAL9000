#!/usr/bin/env python3
"""
HAL 9000 Viewscreen – Main Application
========================================
Fullscreen kiosk display for Raspberry Pi 3 with a 600×1024 HDMI screen.

Renders two panels:
  • High Screen – Function label (3-letter code + subtitle) on a red panel
  • Lower Screen – Looping video playback from the Video/ directory

Usage:
    python3 hal_viewscreen.py              # Run fullscreen
    python3 hal_viewscreen.py --windowed   # Run in a window (for testing)
"""

import os
import sys
import glob
import json
import random
import signal
import time
import argparse

import cv2
import pygame
import pygame.gfxdraw

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    HIGH_SCREEN_X, HIGH_SCREEN_Y, PANEL_WIDTH, PANEL_HEIGHT, PANEL_CORNER_RADIUS,
    LOW_SCREEN_X, LOW_SCREEN_Y,
    COLOR_BLACK, COLOR_PANEL_RED, COLOR_TEXT_WHITE,
    FONT_BOLD_EXTENDED, FONT_EXTENDED, FONT_REGULAR,
    FONT_SIZE_CODE, FONT_SIZE_SUBTITLE,
    FUNCTIONS, FUNCTION_BY_CODE, VIDEO_DIR,
    CYCLE_INTERVAL_SEC, FPS,
    CACHE_WEA_PATH, CACHE_MED_PATH,
)


# ---------------------------------------------------------------------------
# Video Scanner
# ---------------------------------------------------------------------------

def scan_videos(video_dir: str) -> dict:
    """
    Scan the Video directory and map function codes to lists of video paths.

    Filenames follow the pattern:
        HAL 9000 Screensaver ... – ATM (Spacecraft ...) Animation N of M [...].mp4

    Returns:
        {"ATM": [path1, path2, ...], "CNT": [...], ...}
    """
    mapping = {}
    for func in FUNCTIONS:
        mapping[func["code"]] = []

    if not os.path.isdir(video_dir):
        print(f"[WARN] Video directory not found: {video_dir}")
        return mapping

    for filepath in sorted(glob.glob(os.path.join(video_dir, "*.mp4"))):
        basename = os.path.basename(filepath)
        # Extract function code from "– CODE (" pattern
        for func in FUNCTIONS:
            code = func["code"]
            # Match "– ATM " or "– ATM ("
            marker = f"– {code} ("
            if marker in basename:
                mapping[code].append(filepath)
                break

    for code, vids in mapping.items():
        print(f"[INFO] {code}: {len(vids)} video(s)")

    return mapping


# ---------------------------------------------------------------------------
# Rounded Rectangle Drawing
# ---------------------------------------------------------------------------

def draw_rounded_rect(surface, rect, color, radius=None):
    """
    Draw a filled rectangle with square corners.

    (Corners were previously rounded via pygame.gfxdraw circles, but the
    anti-aliased corner circles blended against the surface's existing
    pixels and left a faint dark outline. Square corners avoid that
    artifact entirely, so the rounding path was removed.)
    """
    pygame.draw.rect(surface, color, rect)


# ---------------------------------------------------------------------------
# High Screen Panel Renderer
# ---------------------------------------------------------------------------

class HighScreenPanel:
    """
    Renders the function label panel matching the example_panel.svg style:
    - Red (#c10341) rounded-rect background
    - Large white 3-letter function code (Eurostile KFB Bold Extended, 71px)
    - Smaller white subtitle (Eurostile KFB Extended, 17px)
    """

    def __init__(self):
        # Load fonts
        try:
            self.font_code = pygame.font.Font(FONT_BOLD_EXTENDED, FONT_SIZE_CODE)
            self.font_subtitle = pygame.font.Font(FONT_EXTENDED, FONT_SIZE_SUBTITLE)
            print(f"[INFO] Loaded Eurostile KFB fonts")
        except FileNotFoundError:
            print(f"[WARN] Eurostile KFB fonts not found, using system default")
            self.font_code = pygame.font.SysFont("monospace", FONT_SIZE_CODE, bold=True)
            self.font_subtitle = pygame.font.SysFont("monospace", FONT_SIZE_SUBTITLE)

        # Pre-render one colored background per function (color sourced from
        # Function.json via config.FUNCTION_BY_CODE), so each system gets
        # its own panel color instead of a single fixed red.
        self._bg_surfaces = {}
        for code, func in FUNCTION_BY_CODE.items():
            surface = pygame.Surface((PANEL_WIDTH, PANEL_HEIGHT), pygame.SRCALPHA)
            draw_rounded_rect(surface, (0, 0, PANEL_WIDTH, PANEL_HEIGHT),
                              func.get("color", COLOR_PANEL_RED), PANEL_CORNER_RADIUS)
            self._bg_surfaces[code] = surface

        self._default_bg = pygame.Surface((PANEL_WIDTH, PANEL_HEIGHT), pygame.SRCALPHA)
        draw_rounded_rect(self._default_bg, (0, 0, PANEL_WIDTH, PANEL_HEIGHT),
                          COLOR_PANEL_RED, PANEL_CORNER_RADIUS)

        self._current_code = None
        self._current_subtitle = None
        self._panel_surface = None

    def set_function(self, code: str, subtitle: str):
        """Update the displayed function."""
        if code == self._current_code and subtitle == self._current_subtitle:
            return  # No change

        self._current_code = code
        self._current_subtitle = subtitle

        func = FUNCTION_BY_CODE.get(code, {})
        text_color = func.get("text_color", COLOR_TEXT_WHITE)

        # Compose panel surface
        self._panel_surface = self._bg_surfaces.get(code, self._default_bg).copy()

        # Render the 3-letter code – centered, slightly below vertical center
        # (matching SVG: text at y=267.83 out of 472.5 → ~56.6% down)
        code_surface = self.font_code.render(code, True, text_color)
        code_x = (PANEL_WIDTH - code_surface.get_width()) // 2
        code_y = int(PANEL_HEIGHT * 0.45) - code_surface.get_height() // 2
        self._panel_surface.blit(code_surface, (code_x, code_y))

        # Render subtitle – centered, above the code
        # (matching SVG: text at y=189.92 out of 472.5 → ~40.2% down)
        sub_surface = self.font_subtitle.render(subtitle, True, text_color)
        sub_x = (PANEL_WIDTH - sub_surface.get_width()) // 2
        sub_y = int(PANEL_HEIGHT * 0.34) - sub_surface.get_height() // 2
        self._panel_surface.blit(sub_surface, (sub_x, sub_y))

    def draw(self, screen):
        """Blit the panel onto the main screen."""
        if self._panel_surface:
            screen.blit(self._panel_surface, (HIGH_SCREEN_X, HIGH_SCREEN_Y))


# ---------------------------------------------------------------------------
# Lower Screen Video Player
# ---------------------------------------------------------------------------

class VideoPlayer:
    """
    Decodes video frames (via OpenCV) and draws them directly onto the
    lower screen panel of the main pygame surface.

    This renders in-process rather than shelling out to an external
    player, so playback is always part of the same window as the rest
    of the UI — there is no separate OS-level player window to
    position, and no window chrome (title bar, rounded corners,
    dragging) to fight with.
    """

    def __init__(self):
        self._cap = None
        self._current_path = None
        self._frame_interval = 1.0 / 30.0
        self._next_frame_at = 0.0
        self._surface = None

    def play(self, video_path: str):
        """Start playing a video file. Stops any current playback first."""
        if video_path == self._current_path and self._cap is not None:
            return  # Already playing this video

        self.stop()

        if not os.path.isfile(video_path):
            print(f"[WARN] Video file not found: {video_path}")
            return

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"[WARN] Failed to open video: {video_path}")
            cap.release()
            return

        self._cap = cap
        self._current_path = video_path
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        self._frame_interval = 1.0 / fps
        self._next_frame_at = 0.0
        self._surface = None
        print(f"[INFO] Playing: {os.path.basename(video_path)}")

    def stop(self):
        """Release the current video."""
        if self._cap is not None:
            self._cap.release()
        self._cap = None
        self._current_path = None
        self._surface = None

    def update(self):
        """
        Advance playback if enough real time has passed for the next
        frame, looping back to the start on end-of-stream. Call once
        per app frame before draw().
        """
        if self._cap is None:
            return

        now = time.monotonic()
        if self._surface is not None and now < self._next_frame_at:
            return  # Not time for the next frame yet

        ok, frame = self._cap.read()
        if not ok:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self._cap.read()
            if not ok:
                return  # Corrupt/empty video; keep showing last good frame

        frame = cv2.resize(frame, (PANEL_WIDTH, PANEL_HEIGHT), interpolation=cv2.INTER_AREA)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self._surface = pygame.image.frombuffer(
            frame.tobytes(), (PANEL_WIDTH, PANEL_HEIGHT), "RGB"
        )
        self._next_frame_at = now + self._frame_interval

    def draw(self, screen):
        """Draw the current video frame, or a black placeholder if none."""
        if self._surface is not None:
            screen.blit(self._surface, (LOW_SCREEN_X, LOW_SCREEN_Y))
        else:
            draw_rounded_rect(
                screen,
                (LOW_SCREEN_X, LOW_SCREEN_Y, PANEL_WIDTH, PANEL_HEIGHT),
                COLOR_BLACK,
                PANEL_CORNER_RADIUS,
            )


# ---------------------------------------------------------------------------
# Live Data Panel (WEA / MED)
# ---------------------------------------------------------------------------

# Codes that render live instead of playing a video
LIVE_CODES = {"WEA", "MED"}


class LiveDataPanel:
    """Renders WEA or MED live data into the low screen rect."""

    def __init__(self):
        try:
            self.font_lg = pygame.font.Font(FONT_BOLD_EXTENDED, 36)
            self.font_md = pygame.font.Font(FONT_EXTENDED, 22)
            self.font_sm = pygame.font.Font(FONT_REGULAR, 16)
        except FileNotFoundError:
            self.font_lg = pygame.font.SysFont("monospace", 36, bold=True)
            self.font_md = pygame.font.SysFont("monospace", 22)
            self.font_sm = pygame.font.SysFont("monospace", 16)
        self._wea_cache = None
        self._med_cache = None
        self._last_load = 0

    def _load_cache(self):
        now = time.time()
        if now - self._last_load < 30:
            return
        self._last_load = now
        try:
            with open(CACHE_WEA_PATH) as f:
                self._wea_cache = json.load(f)
        except Exception:
            self._wea_cache = None
        try:
            with open(CACHE_MED_PATH) as f:
                self._med_cache = json.load(f)
        except Exception:
            self._med_cache = None

    def _text(self, surface, text, font, color, x, y, max_width=440):
        """Render text with word-wrap. Returns next y position."""
        words = text.split()
        line = ""
        cy = y
        for word in words:
            test = line + (" " if line else "") + word
            if font.size(test)[0] > max_width and line:
                surf = font.render(line, True, color)
                surface.blit(surf, (x, cy))
                cy += surf.get_height() + 2
                line = word
            else:
                line = test
        if line:
            surf = font.render(line, True, color)
            surface.blit(surf, (x, cy))
            cy += surf.get_height() + 2
        return cy

    def render_wea(self, surface, rect):
        self._load_cache()
        rx, ry, rw, rh = rect
        pad = 16
        cx = rx + pad
        cy = ry + pad
        WHITE = (241, 241, 241)
        AMBER = (212, 160, 23)
        GREY  = (160, 160, 160)

        pygame.draw.rect(surface, (10, 10, 10), rect)
        if not self._wea_cache:
            self._text(surface, "AWAITING TELEMETRY", self.font_md, AMBER, cx, ry + 200)
            return

        w = self._wea_cache
        cy = self._text(surface, w.get("city", "").upper(), self.font_lg, WHITE, cx, cy)
        cy += 8

        temp_str = f"{w['temp']}°C"
        surf = self.font_lg.render(temp_str, True, AMBER)
        surface.blit(surf, (cx, cy))
        cy += surf.get_height() + 4

        cy = self._text(surface, w.get("condition", ""), self.font_md, WHITE, cx, cy)
        cy += 6

        rows = [
            ("FEELS LIKE", f"{w.get('feels_like', '—')}°C"),
            ("WIND",       f"{w.get('wind_kmh', '—')} km/h"),
            ("RAIN",       f"{w.get('rain_mm', 0)} mm"),
            ("SNOW",       f"{w.get('snow_cm', 0)} cm"),
        ]
        for label, val in rows:
            lsurf = self.font_sm.render(label, True, GREY)
            vsurf = self.font_md.render(val, True, WHITE)
            surface.blit(lsurf, (cx, cy + 4))
            surface.blit(vsurf, (cx + 160, cy))
            cy += vsurf.get_height() + 8

        ts = self.font_sm.render(f"UPD {w.get('fetched_at', '')}", True, GREY)
        surface.blit(ts, (cx, ry + rh - 28))

    def render_med(self, surface, rect):
        self._load_cache()
        rx, ry, rw, rh = rect
        pad = 16
        cx = rx + pad
        cy = ry + pad
        WHITE = (241, 241, 241)
        AMBER = (212, 160, 23)
        GREY  = (160, 160, 160)

        pygame.draw.rect(surface, (10, 10, 10), rect)
        if not self._med_cache:
            self._text(surface, "AWAITING TELEMETRY", self.font_md, AMBER, cx, ry + 200)
            return

        m = self._med_cache
        cy = self._text(surface, "TRENDING", self.font_md, AMBER, cx, cy)
        cy += 4
        for item in (m.get("youtube") or [])[:2]:
            cy = self._text(surface, item.get("title", ""), self.font_sm, WHITE, cx, cy)
            cy += 4
        cy += 8

        div = self.font_sm.render("─" * 38, True, (60, 60, 60))
        surface.blit(div, (cx, cy)); cy += 18
        cy = self._text(surface, "WORLD NEWS", self.font_md, AMBER, cx, cy)
        cy += 4
        for item in (m.get("news") or [])[:4]:
            cy = self._text(surface, item.get("title", ""), self.font_sm, WHITE, cx, cy, max_width=440)
            cy += 3

        ts = self.font_sm.render(f"UPD {m.get('fetched_at', '')}", True, GREY)
        surface.blit(ts, (cx, ry + rh - 28))

    def render(self, surface, rect, code):
        if code == "WEA":
            self.render_wea(surface, rect)
        elif code == "MED":
            self.render_med(surface, rect)


# ---------------------------------------------------------------------------
# Function Controller
# ---------------------------------------------------------------------------

class FunctionController:
    """
    Manages which HAL function is currently active and handles cycling.
    Provides set_function() for external control (Arduino, network, etc).
    """

    def __init__(self, video_map: dict):
        self._video_map = video_map
        self._functions = FUNCTIONS
        self._current_index = 0
        self._last_change = 0.0
        self._manual_override = False

    @property
    def current(self) -> dict:
        return self._functions[self._current_index]

    def set_function(self, code: str):
        """
        Set a specific function by code. Used for external control.
        Disables auto-cycling until reset.
        """
        for i, func in enumerate(self._functions):
            if func["code"] == code:
                self._current_index = i
                self._last_change = time.time()
                self._manual_override = True
                return True
        return False

    def reset_auto_cycle(self):
        """Re-enable automatic cycling."""
        self._manual_override = False
        self._last_change = time.time()

    def update(self) -> bool:
        """
        Check if it's time to cycle to the next function.
        Returns True if the function changed.
        """
        if self._manual_override:
            return False

        now = time.time()
        if now - self._last_change >= CYCLE_INTERVAL_SEC:
            self._current_index = (self._current_index + 1) % len(self._functions)
            self._last_change = now
            return True
        return False

    def get_random_video(self) -> str:
        """Get a random video path for the current function, or None."""
        code = self.current["code"]
        videos = self._video_map.get(code, [])
        if videos:
            return random.choice(videos)
        return None


# ---------------------------------------------------------------------------
# Main Application
# ---------------------------------------------------------------------------

class HALViewscreen:
    """Main application orchestrating the HAL 9000 viewscreen display."""

    def __init__(self, windowed: bool = False):
        self._windowed = windowed
        self._running = False

        # Initialize Pygame
        pygame.init()
        pygame.mouse.set_visible(False)

        if windowed:
            self._screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            pygame.display.set_caption("HAL 9000 Viewscreen")
        else:
            self._screen = pygame.display.set_mode(
                (SCREEN_WIDTH, SCREEN_HEIGHT),
                pygame.FULLSCREEN | pygame.NOFRAME,
            )

        self._clock = pygame.time.Clock()

        # Scan videos
        self._video_map = scan_videos(VIDEO_DIR)

        # Create components
        self._high_panel = HighScreenPanel()
        self._video_player = VideoPlayer()
        self._live_panel = LiveDataPanel()
        self._controller = FunctionController(self._video_map)

        # Signal handlers for clean shutdown
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum, frame):
        print(f"\n[INFO] Received signal {signum}, shutting down...")
        self._running = False

    def _apply_function(self):
        """Apply the current function: update panel and start video (or live panel)."""
        func = self._controller.current
        code = func["code"]
        print(f"[INFO] Function: {code} – {func['name']}")

        # Update high screen panel
        self._high_panel.set_function(code, func["subtitle"])

        # WEA and MED render live — no video
        if code in LIVE_CODES:
            self._video_player.stop()
            return

        # Start video playback for all other functions
        video_path = self._controller.get_random_video()
        if video_path:
            self._video_player.play(video_path)
        else:
            print(f"[WARN] No videos available for {code}")
            self._video_player.stop()

    def run(self):
        """Main event loop."""
        self._running = True

        # Fill background black
        self._screen.fill(COLOR_BLACK)

        # Apply initial function
        self._apply_function()

        while self._running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self._running = False
                    elif event.key == pygame.K_RIGHT:
                        # Manual advance (for testing)
                        idx = (self._controller._current_index + 1) % len(FUNCTIONS)
                        self._controller.set_function(FUNCTIONS[idx]["code"])
                        self._apply_function()
                    elif event.key == pygame.K_LEFT:
                        idx = (self._controller._current_index - 1) % len(FUNCTIONS)
                        self._controller.set_function(FUNCTIONS[idx]["code"])
                        self._apply_function()
                    elif event.key == pygame.K_SPACE:
                        self._controller.reset_auto_cycle()

            # Check for function cycling
            if self._controller.update():
                self._apply_function()

            # Render frame
            self._screen.fill(COLOR_BLACK)
            self._high_panel.draw(self._screen)
            code = self._controller.current["code"]
            if code in LIVE_CODES:
                self._live_panel.render(
                    self._screen,
                    (LOW_SCREEN_X, LOW_SCREEN_Y, PANEL_WIDTH, PANEL_HEIGHT),
                    code,
                )
            else:
                self._video_player.update()
                self._video_player.draw(self._screen)

            pygame.display.flip()
            self._clock.tick(FPS)

        # Cleanup
        self._video_player.stop()
        pygame.quit()
        print("[INFO] HAL 9000 Viewscreen terminated.")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="HAL 9000 Viewscreen")
    parser.add_argument(
        "--windowed", "-w",
        action="store_true",
        help="Run in a window instead of fullscreen (for testing)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  HAL 9000 VIEWSCREEN")
    print("  Good afternoon. I am a HAL 9000 computer.")
    print("=" * 60)

    app = HALViewscreen(windowed=args.windowed)
    app.run()


if __name__ == "__main__":
    main()
