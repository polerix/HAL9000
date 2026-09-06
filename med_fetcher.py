#!/usr/bin/env python3
"""Fetches top YouTube trending video and BBC top news, caches to cache/med.json"""
import json, os, time, urllib.request
import xml.etree.ElementTree as ET
from config import CACHE_DIR, CACHE_MED_PATH

# YouTube trending RSS (top videos - US region, most viewed)
YT_RSS = "https://www.youtube.com/feeds/videos.xml?chart=trending&hl=en&gl=US"
# BBC World News RSS
BBC_RSS = "https://feeds.bbci.co.uk/news/world/rss.xml"

def fetch_rss(url, max_items=5):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        tree = ET.parse(r)
    root = tree.getroot()
    ns = {"atom": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/"}
    items = []
    # Try Atom feed (YouTube)
    for entry in root.findall("atom:entry", ns)[:max_items]:
        title_el = entry.find("atom:title", ns)
        link_el = entry.find("atom:link", ns)
        if title_el is not None:
            items.append({
                "title": title_el.text,
                "url": link_el.get("href", "") if link_el is not None else ""
            })
    # Try RSS feed (BBC)
    if not items:
        channel = root.find("channel")
        if channel:
            for item in channel.findall("item")[:max_items]:
                t = item.find("title")
                d = item.find("description")
                items.append({
                    "title": t.text if t is not None else "",
                    "description": (d.text or "")[:120] if d is not None else ""
                })
    return items

def fetch():
    result = {"fetched_at": time.strftime("%H:%M"), "fetched_ts": time.time()}
    try:
        result["youtube"] = fetch_rss(YT_RSS, 3)
    except Exception as e:
        result["youtube"] = [{"title": f"Unavailable ({e})", "url": ""}]
    try:
        result["news"] = fetch_rss(BBC_RSS, 5)
    except Exception as e:
        result["news"] = [{"title": f"Unavailable ({e})", "description": ""}]
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_MED_PATH, "w") as f:
        json.dump(result, f)
    return result

if __name__ == "__main__":
    import pprint; pprint.pprint(fetch())
