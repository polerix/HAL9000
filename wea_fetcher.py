#!/usr/bin/env python3
"""Fetches weather from Open-Meteo and caches to cache/wea.json"""
import json, os, urllib.request, time
from config import WEATHER_LAT, WEATHER_LON, WEATHER_CITY, CACHE_DIR, CACHE_WEA_PATH

WMO_CODES = {
    0:"Clear",1:"Mainly Clear",2:"Partly Cloudy",3:"Overcast",
    45:"Fog",48:"Icy Fog",51:"Light Drizzle",53:"Drizzle",55:"Heavy Drizzle",
    61:"Light Rain",63:"Rain",65:"Heavy Rain",71:"Light Snow",73:"Snow",75:"Heavy Snow",
    77:"Snow Grains",80:"Light Showers",81:"Showers",82:"Heavy Showers",
    85:"Snow Showers",86:"Heavy Snow Showers",95:"Thunderstorm",96:"Thunderstorm+Hail",
    99:"Heavy Thunderstorm"
}

def fetch():
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={WEATHER_LAT}&longitude={WEATHER_LON}"
        f"&current=temperature_2m,apparent_temperature,weather_code,"
        f"wind_speed_10m,wind_direction_10m,precipitation,snowfall"
        f"&wind_speed_unit=kmh&temperature_unit=celsius&timezone=auto"
    )
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.load(r)
    c = data["current"]
    result = {
        "city": WEATHER_CITY,
        "temp": round(c["temperature_2m"]),
        "feels_like": round(c["apparent_temperature"]),
        "condition": WMO_CODES.get(c["weather_code"], "Unknown"),
        "wind_kmh": round(c["wind_speed_10m"]),
        "wind_dir": c["wind_direction_10m"],
        "rain_mm": round(c.get("precipitation", 0), 1),
        "snow_cm": round(c.get("snowfall", 0), 1),
        "fetched_at": time.strftime("%H:%M"),
        "fetched_ts": time.time()
    }
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_WEA_PATH, "w") as f:
        json.dump(result, f)
    return result

if __name__ == "__main__":
    print(fetch())
