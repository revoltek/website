#!/usr/bin/env python3
"""One-time copy of images and files from the old WordPress site into static/media/.

Run it while the old site is still online, either from GitHub
(Actions -> "Import media from old site" -> Run workflow) or locally:
    python scripts/import_media.py
Files already present in static/media/ are skipped.
"""
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "static" / "media"
HOSTS = ["https://voo.it", "http://voo.it", "http://w.voo.it", "http://www.voo.it"]
PREFIXES = ["/wp-content/uploads/sites/6/", "/wp-content/uploads/"]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (site migration)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        if r.status != 200 or "text/html" in r.headers.get("Content-Type", ""):
            return None   # WordPress answers missing files with an HTML page
        return r.read()


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    manifest = yaml.safe_load((ROOT / "scripts" / "media.yaml").read_text())
    missing = []
    for name, paths in manifest.items():
        target = DEST / name
        if target.exists():
            print(f"skip   {name}")
            continue
        data, got = None, None
        for path in paths:
            for host in HOSTS:
                for prefix in PREFIXES:
                    url = host + prefix + path
                    try:
                        data = fetch(url)
                    except (urllib.error.URLError, TimeoutError, ValueError):
                        data = None
                    if data:
                        got = url
                        break
                if data:
                    break
            if data:
                break
        if data:
            target.write_bytes(data)
            print(f"saved  {name}  <- {got}")
        else:
            missing.append(name)
            print(f"MISSING {name}")
    if missing:
        print(f"\n{len(missing)} file(s) not found: {', '.join(missing)}")
        sys.exit(1 if len(missing) == len(manifest) else 0)


if __name__ == "__main__":
    main()
