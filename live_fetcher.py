#!/usr/bin/env python3
"""Background daemon: refreshes WEA and MED cache every FETCH_INTERVAL_SEC."""
import time, traceback
from config import FETCH_INTERVAL_SEC
import wea_fetcher, med_fetcher

def run():
    print("[live_fetcher] Starting")
    while True:
        for name, mod in [("WEA", wea_fetcher), ("MED", med_fetcher)]:
            try:
                mod.fetch()
                print(f"[live_fetcher] {name} updated")
            except Exception:
                print(f"[live_fetcher] {name} fetch failed:")
                traceback.print_exc()
        time.sleep(FETCH_INTERVAL_SEC)

if __name__ == "__main__":
    run()
