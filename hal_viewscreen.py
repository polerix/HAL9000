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
import random
import signal
import subprocess
import time
import argparse

import pygame
import pygame.gfxdraw

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    HIGH_SCREEN_X, HIGH_SCREEN_Y, PANEL_WIDTH, PANEL_HEIGHT, PANEL_CORNER_RADIUS,
    LOW_SCREEN_X, LOW_SCREEN_Y,
    COLOR_BLACK, COLOR_PANEL_RED, COLOR_TEXT_WHITE,
    FONT_BOLD_EXTENDED, FONT_EXTENDED, FONT_REGULAR,
    FONT_SIZE_CODE, FONT_SIZE_SUBTITLE,
    FUNCTIONS, VIDEO_DIR,
    CYCLE_INTERVAL_SEC, FPS, VIDEO_PLAYER,
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

def draw_rounded_rect(surface, rect, color, radius):
    """
    Draw a filled rounded rectangle using pygame.gfxdraw for anti-aliased edges.
    """
    x, y, w, h = rect
    r = min(radius, w // 2, h // 2)

    # Central rectangles (no overlap with corners)
    pygame.draw.rect(surface, color, (x + r, y, w - 2 * r, h))
    pygame.draw.rect(surface, color, (x, y + r, w, h - 2 * r))

    # Four corner circles
    corners = [
        (x + r,     y + r),          # top-left
        (x + w - r - 1, y + r),      # top-right
        (x + r,     y + h - r - 1),  # bottom-left
        (x + w - r - 1, y + h - r - 1),  # bottom-right
    ]
    for cx, cy in corners:
        pygame.gfxdraw.aacircle(surface, cx, cy, r, color)
        pygame.gfxdraw.filled_circle(surface, cx, cy, r, color)


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

        # Pre-render panel background surface (reused across frames)
        self._bg_surface = pygame.Surface((PANEL_WIDTH, PANEL_HEIGHT), pygame.SRCALPHA)
        draw_rounded_rect(self._bg_surface, (0, 0, PANEL_WIDTH, PANEL_HEIGHT),
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

        # Compose panel surface
        self._panel_surface = self._bg_surface.copy()

        # Render the 3-letter code – centered, slightly below vertical center
        # (matching SVG: text at y=267.83 out of 472.5 → ~56.6% down)
        code_surface = self.font_code.render(code, True, COLOR_TEXT_WHITE)
        code_x = (PANEL_WIDTH - code_surface.get_width()) // 2
        code_y = int(PANEL_HEIGHT * 0.45) - code_surface.get_height() // 2
        self._panel_surface.blit(code_surface, (code_x, code_y))

        # Render subtitle – centered, above the code
        # (matching SVG: text at y=189.92 out of 472.5 → ~40.2% down)
        sub_surface = self.font_subtitle.render(subtitle, True, COLOR_TEXT_WHITE)
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
    Manages video playback in the lower screen area using mpv (subprocess).
    mpv is positioned/sized to match the low_screen panel bounds and
    uses hardware decoding on Raspberry Pi.
    """

    def __init__(self):
        self._process = None
        self._current_path = None

    def play(self, video_path: str):
        """Start playing a video file. Stops any current playback first."""
        if video_path == self._current_path and self._is_playing():
            return  # Already playing this video

        self.stop()
        self._current_path = video_path

        if not os.path.isfile(video_path):
            print(f"[WARN] Video file not found: {video_path}")
            return

        print(f"[INFO] Playing: {os.path.basename(video_path)}")

        if VIDEO_PLAYER == "mpv":
            self._play_mpv(video_path)
        else:
            self._play_omxplayer(video_path)

    def _play_mpv(self, video_path: str):
        """Launch mpv with geometry matching the lower screen panel."""
        # mpv geometry: WxH+X+Y
        geometry = f"{PANEL_WIDTH}x{PANEL_HEIGHT}+{LOW_SCREEN_X}+{LOW_SCREEN_Y}"

        cmd = [
            "mpv",
            "--no-terminal",
            "--no-osc",                    # No on-screen controls
            "--no-input-default-bindings",  # Disable keyboard shortcuts
            "--loop-file=inf",              # Loop indefinitely
            "--hwdec=auto",                 # Hardware decoding (RPi MMAL/V4L2)
            "--vo=gpu",                     # GPU video output
            f"--geometry={geometry}",
            "--no-border",                  # Borderless window
            "--ontop",                      # Keep on top
            "--no-keepaspect",              # Fill the panel exactly
            "--really-quiet",
            video_path,
        ]

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            print("[ERROR] mpv not found. Install with: sudo apt install mpv")
            self._process = None

    def _play_omxplayer(self, video_path: str):
        """Fallback: launch omxplayer with window bounds."""
        # omxplayer uses --win "x1 y1 x2 y2"
        x1, y1 = LOW_SCREEN_X, LOW_SCREEN_Y
        x2 = x1 + PANEL_WIDTH
        y2 = y1 + PANEL_HEIGHT

        cmd = [
            "omxplayer",
            "--loop",
            "--no-osd",
            "--aspect-mode", "stretch",
            "--win", f"{x1} {y1} {x2} {y2}",
            video_path,
        ]

        try:
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            print("[ERROR] omxplayer not found. Install with: sudo apt install omxplayer")
            self._process = None

    def _is_playing(self) -> bool:
        """Check if the video subprocess is still running."""
        return self._process is not None and self._process.poll() is None

    def stop(self):
        """Terminate the current video playback."""
        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
            except Exception:
                pass
            self._process = None
            self._current_path = None

    def draw_placeholder(self, screen):
        """
        Draw a black rounded rect in the lower screen area when no video plays.
        The video player window overlays on top of this.
        """
        draw_rounded_rect(
            screen,
            (LOW_SCREEN_X, LOW_SCREEN_Y, PANEL_WIDTH, PANEL_HEIGHT),
            COLOR_BLACK,
            PANEL_CORNER_RADIUS,
        )


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
        self._controller = FunctionController(self._video_map)

        # Signal handlers for clean shutdown
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum, frame):
        print(f"\n[INFO] Received signal {signum}, shutting down...")
        self._running = False

    def _apply_function(self):
        """Apply the current function: update panel and start video."""
        func = self._controller.current
        print(f"[INFO] Function: {func['code']} – {func['name']}")

        # Update high screen panel
        self._high_panel.set_function(func["code"], func["subtitle"])

        # Start video playback
        video_path = self._controller.get_random_video()
        if video_path:
            self._video_player.play(video_path)
        else:
            print(f"[WARN] No videos available for {func['code']}")
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
            self._video_player.draw_placeholder(self._screen)

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
