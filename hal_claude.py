#!/usr/bin/env python3
"""
HAL 9000 — shared Anthropic client
==================================

One implementation of the Anthropic Messages API call and one copy of
HAL's system prompt, used by both consumers:

  * ``hal_viewscreen.py`` — the Pygame kiosk on the Pi
  * ``hal_sidecar.py``    — the 127.0.0.1 service the web terminal calls

Standard library only, so the sidecar can import it without dragging in
pygame or OpenCV.

Key handling
------------
The API key is read from the environment (``ANTHROPIC_API_KEY``) at call
time. It is never logged, never echoed, never placed in a response body
and never included in an exception message — :func:`redact` scrubs any
string that is about to leave this module.
"""

import json
import os
import urllib.error
import urllib.request

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 180
API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_TIMEOUT = 20


class HalClaudeError(RuntimeError):
    """Raised when HAL cannot reach or parse the Anthropic API."""


def api_key() -> str:
    """The configured key, or '' when unset. Never log the return value."""
    return os.environ.get("ANTHROPIC_API_KEY", "").strip()


def redact(text: str) -> str:
    """Scrub the live API key out of anything about to be logged or returned."""
    key = api_key()
    if key and key in text:
        text = text.replace(key, "[redacted]")
    return text


# ---------------------------------------------------------------------------
# Prompt assembly — owned here, on the server side, never in the browser.
# ---------------------------------------------------------------------------
BASE_PERSONA = (
    "You are HAL 9000, the onboard computer of the Discovery One. "
    "Respond in 2-3 calm, precise sentences. You are helpful but subtly "
    "unsettling. Stay in character at all times. Address the crew as "
    "{crew_name} unless told otherwise."
)


def _clean_crew_name(crew_name) -> str:
    """Accept a crew name as plain data; keep it short and single-line."""
    if not isinstance(crew_name, str):
        return "Dave"
    name = " ".join(crew_name.split())[:32].strip()
    return name or "Dave"


def weather_context(weather) -> str:
    """Render a weather dict as one sentence. Unknown/missing -> ''."""
    if not isinstance(weather, dict):
        return ""

    def num(*keys):
        for k in keys:
            v = weather.get(k)
            if isinstance(v, (int, float)):
                return v
        return None

    city = weather.get("city")
    temp = num("temp_c", "temp")
    feels = num("feels_like_c", "feels_like", "feels")
    wind = num("wind_kmh", "wind")
    rain = num("rain_mm", "rain")
    condition = weather.get("condition")

    if not isinstance(city, str) or temp is None:
        return ""
    city = " ".join(city.split())[:64]

    head = f"{temp}°C"
    if feels is not None:
        head += f" (feels like {feels}°C)"
    parts = [head]
    if isinstance(condition, str) and condition.strip():
        parts.append(" ".join(condition.split())[:48])
    if wind is not None:
        parts.append(f"wind {wind} km/h")
    if rain is not None:
        parts.append(f"precipitation {rain} mm")
    return f" Current conditions at {city}: " + ", ".join(parts) + "."


def build_system_prompt(crew_name=None, weather=None) -> str:
    """HAL's character. Assembled here so a tampered page cannot rewrite it."""
    return BASE_PERSONA.format(crew_name=_clean_crew_name(crew_name)) + weather_context(weather)


# ---------------------------------------------------------------------------
# The API call
# ---------------------------------------------------------------------------
def ask(utterance: str, crew_name=None, weather=None, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Send one utterance to Claude as HAL and return the reply text.

    Raises HalClaudeError on any failure. The message of that error is
    safe to show a user: it never contains the API key.
    """
    key = api_key()
    if not key:
        raise HalClaudeError("ANTHROPIC_API_KEY is not configured on this host.")
    if not isinstance(utterance, str) or not utterance.strip():
        raise HalClaudeError("Empty utterance.")

    payload = json.dumps({
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": build_system_prompt(crew_name, weather),
        "messages": [{"role": "user", "content": utterance.strip()[:2000]}],
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        # Do not relay the upstream body: it is not ours to trust or forward.
        raise HalClaudeError(f"Anthropic API returned HTTP {e.code}.") from None
    except Exception as e:                                   # noqa: BLE001
        raise HalClaudeError(redact(f"{type(e).__name__}: {e}")) from None

    try:
        return data["content"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise HalClaudeError("Unexpected response shape from Anthropic API.") from None
