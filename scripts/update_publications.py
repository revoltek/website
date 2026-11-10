#!/usr/bin/env python3
"""Refresh data/publications.json from NASA ADS.

Needs an ADS API token in the ADS_TOKEN environment variable
(create one at https://ui.adsabs.harvard.edu/user/settings/token).
The query is configured in site.yaml under "ads".

Run locally:   ADS_TOKEN=xxxx python scripts/update_publications.py
On GitHub it runs every week from .github/workflows/deploy.yml.
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "publications.json"
API = "https://api.adsabs.harvard.edu/v1/search/query"
FIELDS = "bibcode,title,author,year,pub,volume,page,doi,identifier,citation_count,doctype,pubdate"
ROWS = 200


def ads_search(query, token):
    """Return every ADS document matching the query, newest first."""
    docs, start = [], 0
    while True:
        params = urllib.parse.urlencode({
            "q": query, "fl": FIELDS, "rows": ROWS, "start": start,
            "sort": "date desc, bibcode desc",
        })
        req = urllib.request.Request(f"{API}?{params}",
                                     headers={"Authorization": f"Bearer {token}"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    payload = json.load(r)
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                    time.sleep(10 * (attempt + 1))
                    continue
                raise
        resp = payload["response"]
        docs.extend(resp["docs"])
        start += ROWS
        if start >= resp["numFound"]:
            return docs


def record(d):
    arxiv = next((i.split(":", 1)[1] for i in d.get("identifier", [])
                  if i.lower().startswith("arxiv:")), None)
    return {
        "bibcode": d["bibcode"],
        "title": (d.get("title") or [""])[0],
        "authors": d.get("author", []),
        "year": d.get("year", ""),
        "pub": d.get("pub", ""),
        "volume": d.get("volume", ""),
        "page": (d.get("page") or [""])[0],
        "doi": (d.get("doi") or [None])[0],
        "arxiv": arxiv,
        "citations": d.get("citation_count", 0) or 0,
        "doctype": d.get("doctype", ""),
    }


def h_index(counts):
    counts = sorted(counts, reverse=True)
    return sum(1 for i, c in enumerate(counts, 1) if c >= i)


def main():
    token = os.environ.get("ADS_TOKEN", "").strip()
    if not token:
        sys.exit("ADS_TOKEN is not set: keeping the existing data/publications.json")

    cfg = yaml.safe_load((ROOT / "site.yaml").read_text())["ads"]
    name = cfg["author"]
    filters = ["property:refereed"]
    if cfg.get("orcid"):
        filters.append(f'orcid:"{cfg["orcid"]}"')
    if cfg.get("collection", "all") != "all":
        filters.append(f'collection:{cfg["collection"]}')
    filters += [f"-doctype:{t}" for t in cfg.get("exclude_doctypes", [])]
    extra = " ".join(filters)

    first = [record(d) for d in ads_search(f'author:"^{name}" {extra}', token)]
    other = [record(d) for d in ads_search(f'author:"{name}" -author:"^{name}" {extra}', token)]

    # Guard against an ADS hiccup wiping the page: refuse to write a much shorter list.
    if OUT.exists():
        old = json.loads(OUT.read_text())
        old_n = len(old.get("first_author", [])) + old.get("metrics", {}).get("coauthor_papers", 0)
        if len(first) + len(other) < 0.8 * old_n:
            sys.exit(f"ADS returned {len(first) + len(other)} papers, previously {old_n}: not overwriting")
    if not first:
        sys.exit("ADS returned no first-author papers: not overwriting")

    allp = first + other
    data = {
        "updated": datetime.date.today().isoformat(),
        "metrics": {
            "refereed_papers": len(allp),
            "first_author_papers": len(first),
            "coauthor_papers": len(other),
            "citations": sum(p["citations"] for p in allp),
            "h_index": h_index([p["citations"] for p in allp]),
        },
        "first_author": first,
        "coauthor": other,
    }
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    m = data["metrics"]
    print(f"Wrote {OUT.relative_to(ROOT)}: {m['first_author_papers']} first-author, "
          f"{m['coauthor_papers']} co-authored, {m['citations']} citations, h={m['h_index']}")


if __name__ == "__main__":
    main()
