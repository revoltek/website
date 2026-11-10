#!/usr/bin/env python3
"""Build the static site into _site/.

    python build.py              # build
    python build.py --serve      # build and preview at http://localhost:8000

Pages live in content/*.md, blog posts in content/blog/YYYY-MM-DD-slug.md,
images and files in static/. Publications come from data/publications.json
(refreshed weekly by scripts/update_publications.py) plus the hand-written
notes in data/publication_extras.yaml.
"""
import datetime
import hashlib
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_site"
SITE = yaml.safe_load((ROOT / "site.yaml").read_text())
TEMPLATE = (ROOT / "templates" / "base.html").read_text()
# Path prefix when served from <user>.github.io/<repo>/ instead of a custom domain.
BASE = os.environ.get("BASE_PATH", "").rstrip("/")
MONTHS = "January February March April May June July August September October November December".split()


# Helpers ------------------------------------------------------------------

def md(text, inline=False):
    out = markdown.markdown(text, extensions=["extra", "sane_lists"], output_format="html")
    if inline and out.startswith("<p>") and out.endswith("</p>") and out.count("<p>") == 1:
        out = out[3:-4]
    return out


def read_page(path):
    raw = path.read_text()
    meta, body = {}, raw
    if raw.startswith("---"):
        _, fm, body = raw.split("---", 2)
        meta = yaml.safe_load(fm) or {}
    return meta, body.strip() + "\n"


def includes(body):
    """<!-- include: static/files/x.py python --> becomes a code block with that file."""
    def repl(m):
        rel, lang = m.group(1), m.group(2) or ""
        code = (ROOT / rel).read_text().rstrip("\n")
        return f"```{lang}\n{code}\n```"
    return re.sub(r"<!--\s*include:\s*(\S+)\s*(\w+)?\s*-->", repl, body)


def long_date(d):
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def esc(s):
    return html.escape(str(s), quote=True)


def clean_title(t):
    """ADS titles may carry entities and <sub>/<sup>; keep only those tags."""
    t = html.escape(html.unescape(t or ""), quote=False)
    return re.sub(r"&lt;(/?)(sub|sup|i)&gt;", lambda m: f"<{m.group(1)}{m.group(2).lower()}>", t, flags=re.I)


# Header pieces ------------------------------------------------------------

def ruler():
    """Log-frequency axis 10 MHz – 2 GHz with the ultra-low band (10–100 MHz) filled."""
    import math
    lo, hi = math.log10(10), math.log10(2000)
    pos = lambda f: 100 * (math.log10(f) - lo) / (hi - lo)
    parts = [f'<div class="band" style="left:0;width:{pos(100):.2f}%"></div>', '<div class="axis"></div>']
    for decade in (10, 100, 1000):
        for k in range(1, 10):
            f = decade * k
            if f > 2000:
                break
            cls = "tick major" if k == 1 else "tick"
            parts.append(f'<span class="{cls}" style="left:{pos(f):.2f}%"></span>')
    for f, label in ((10, "10 MHz"), (100, "100 MHz"), (1000, "1 GHz")):
        cls = "label start" if f == 10 else "label"
        parts.append(f'<span class="{cls}" style="left:{pos(f):.2f}%">{label}</span>')
    return ('<div class="ruler" role="img" aria-label="Radio frequency axis from 10 MHz to 2 GHz, '
            'highlighting the ultra-low frequencies below 100 MHz">' + "".join(parts) + "</div>")


def nav(active):
    items = []
    for item in SITE["nav"]:
        cur = ' aria-current="page"' if item["key"] == active else ""
        items.append(f'      <li><a href="{item["url"]}"{cur}>{esc(item["title"])}</a></li>')
    return "\n".join(items)


def gtm():
    gid = (SITE.get("gtm_id") or "").strip()
    if not gid:
        return "", ""
    head = ("<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':new Date().getTime(),event:'gtm.js'});"
            "var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;"
            "j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);"
            f"}})(window,document,'script','dataLayer','{gid}');</script>")
    body = (f'<noscript><iframe src="https://www.googletagmanager.com/ns.html?id={gid}" height="0" width="0" '
            'style="display:none;visibility:hidden"></iframe></noscript>')
    return head, body


# Publications --------------------------------------------------------------

def load_pubs():
    data = json.loads((ROOT / "data" / "publications.json").read_text())
    extras_file = ROOT / "data" / "publication_extras.yaml"
    extras = yaml.safe_load(extras_file.read_text()) if extras_file.exists() else {}
    extras = {str(k).lower(): v for k, v in (extras or {}).items()}
    return data, extras


def is_me(author):
    me = SITE["ads"]["author"].lower()
    sur, _, init = me.partition(",")
    a_sur, _, a_first = author.lower().partition(",")
    return a_sur.strip() == sur.strip() and a_first.strip()[:1] == init.strip()[:1]


def authors_html(p, seed):
    names = p.get("authors") or []
    limit = SITE["ads"].get("max_authors_shown", 10)
    fmt = lambda a: f"<strong>{esc(a)}</strong>" if is_me(a) else esc(a)
    shown = "; ".join(fmt(a) for a in names[:limit])
    if seed and len(names) <= 1:
        return shown + " et al."
    if len(names) > limit:
        shown += f"; et al. ({len(names)} authors)"
    return shown


def pub_html(p, extras, seed, compact=False):
    doi = p.get("doi")
    ads = f"https://ui.adsabs.harvard.edu/abs/{p['bibcode']}/abstract"
    href = f"https://doi.org/{doi}" if doi else ads
    venue = ", ".join(str(x) for x in (p.get("pub"), p.get("volume"), p.get("page")) if x)
    links = [f'<a href="{esc(ads)}">ADS</a>']
    if p.get("arxiv"):
        links.append(f'<a href="https://arxiv.org/abs/{esc(p["arxiv"])}">arXiv</a>')
    n = p.get("citations", 0)
    if n:
        cites = f"https://ui.adsabs.harvard.edu/abs/{p['bibcode']}/citations"
        links.append(f'<a href="{esc(cites)}">{n} citation{"s" if n != 1 else ""}</a>')
    out = [f'<li class="pub"><a class="title" href="{esc(href)}">{clean_title(p["title"])}</a>']
    if not compact:
        out.append(f'<span class="authors">{authors_html(p, seed)}</span>')
    out.append(f'<span class="venue">{esc(venue)}</span>')
    out.append(f'<span class="links">{"".join(links)}</span>')
    for key in (str(doi or "").lower(), p["bibcode"].lower()):
        for line in extras.get(key, []) if key else []:
            out.append(f'<span class="extra">{md(line, inline=True)}</span>')
    out.append("</li>")
    return "\n".join(out)


def by_year(pubs, extras, seed, compact=False):
    groups = {}
    for p in pubs:
        groups.setdefault(str(p.get("year", "")), []).append(p)
    html_ = []
    for year in sorted(groups, reverse=True):
        items = "\n".join(pub_html(p, extras, seed, compact) for p in groups[year])
        html_.append(f'<section class="yeargroup"><h3 class="year">{esc(year)}</h3>\n<ol>\n{items}\n</ol></section>')
    return "\n".join(html_)


def publications_html():
    data, extras = load_pubs()
    seed = data.get("seed", False)
    m = data["metrics"]
    upd = long_date(datetime.date.fromisoformat(data["updated"]))
    ads, scholar = SITE["ads"]["search_url"], SITE["ads"]["scholar_url"]
    parts = ['<div class="pubs">',
             f'<p class="summary">{m["citations"]:,} citations on {m["refereed_papers"]} refereed articles, '
             f'h-index {m["h_index"]}, as of {upd}. Full lists on <a href="{esc(ads)}">NASA ADS</a> and '
             f'<a href="{esc(scholar)}">Google Scholar</a>.</p>',
             "<h2>Refereed first-author papers</h2>",
             by_year(data["first_author"], extras, seed)]
    co = data.get("coauthor") or []
    if co:
        parts.append(f"<details><summary>All {len(co)} refereed papers as co-author</summary>\n"
                     f"{by_year(co, extras, seed)}\n</details>")
    elif m.get("coauthor_papers"):
        parts.append(f'<p class="summary">Co-author of {m["coauthor_papers"]} further refereed papers, '
                     f'listed on <a href="{esc(ads)}">NASA ADS</a>.</p>')
    parts.append("</div>")
    return "\n".join(parts)


# Blog ------------------------------------------------------------------------

def load_posts():
    posts = []
    for path in sorted((ROOT / "content" / "blog").glob("*.md")):
        meta, body = read_page(path)
        m = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)\.md$", path.name)
        if not m:
            sys.exit(f"Blog post name must be YYYY-MM-DD-slug.md: {path.name}")
        date = meta.get("date") or m.group(1)
        if isinstance(date, str):
            date = datetime.date.fromisoformat(date)
        posts.append({"meta": meta, "body": body, "date": date, "slug": m.group(2),
                      "url": f"/blog/{m.group(2)}/"})
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def blog_index(posts):
    groups = {}
    for p in posts:
        groups.setdefault(p["date"].year, []).append(p)
    out = ['<div class="postlist">']
    for year in sorted(groups, reverse=True):
        items = []
        for p in groups[year]:
            cats = ", ".join(p["meta"].get("categories", []))
            items.append(f'<li class="post"><a href="{p["url"]}">{esc(p["meta"]["title"])}</a>'
                         f'<span class="meta">{long_date(p["date"])}{" in " + esc(cats) if cats else ""}</span></li>')
        out.append(f'<section class="yeargroup"><h3 class="year">{year}</h3>\n<ul>\n' + "\n".join(items) + "\n</ul></section>")
    out.append("</div>")
    return "\n".join(out)


# Rendering ---------------------------------------------------------------------

def render(page_title, content, active, permalink, description=None):
    head, body = gtm()
    css = hashlib.sha1((ROOT / "static" / "css" / "style.css").read_bytes()).hexdigest()[:8]
    pubs_updated = long_date(datetime.date.fromisoformat(json.loads((ROOT / "data" / "publications.json").read_text())["updated"]))
    values = {
        "lang": SITE.get("lang", "en"),
        "head_title": esc(SITE["title"] if permalink == "/" else f"{page_title} | {SITE['title']}"),
        "page_title": esc(page_title),
        "title": esc(SITE["title"]),
        "site_name": esc(SITE["site_name"]),
        "description": esc(description or SITE["description"]),
        "canonical": SITE["url"] + permalink,
        "css_version": css,
        "gtm_head": head, "gtm_body": body,
        "ruler": ruler(),
        "nav": nav(active),
        "content": content,
        "year": datetime.date.today().year,
        "pubs_updated": pubs_updated,
    }
    out = re.sub(r"\{\{ (\w+) \}\}", lambda m: str(values[m.group(1)]), TEMPLATE)
    if BASE:  # prefix root-relative links when served from a sub-path
        out = re.sub(r'((?:href|src)=")/(?!/)', rf"\1{BASE}/", out)
    return out


def write(permalink, html_):
    dest = OUT / permalink.lstrip("/") / "index.html" if permalink.endswith("/") else OUT / permalink.lstrip("/")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html_)


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "static", OUT)
    (OUT / ".nojekyll").write_text("")
    posts = load_posts()
    urls = []

    for path in sorted((ROOT / "content").glob("*.md")):
        meta, body = read_page(path)
        permalink = meta["permalink"]
        content = md(includes(body))
        content = content.replace("<!-- publications -->", publications_html())
        content = content.replace("<!-- blog-index -->", blog_index(posts))
        content = f"<h1>{esc(meta['title'])}</h1>\n{content}"
        write(permalink, render(meta["title"], content, meta.get("nav"), permalink, meta.get("description")))
        urls.append(permalink)

    for i, p in enumerate(posts):
        newer = posts[i - 1] if i > 0 else None
        older = posts[i + 1] if i + 1 < len(posts) else None
        cats = ", ".join(p["meta"].get("categories", []))
        postnav = ['<nav class="postnav" aria-label="More posts">']
        if older:
            postnav.append(f'<a class="prev" href="{older["url"]}">Older: {esc(older["meta"]["title"])}</a>')
        if newer:
            postnav.append(f'<a class="next" href="{newer["url"]}">Newer: {esc(newer["meta"]["title"])}</a>')
        postnav.append("</nav>")
        content = (f"<h1>{esc(p['meta']['title'])}</h1>\n"
                   f'<p class="postmeta">{long_date(p["date"])}{" in " + esc(cats) if cats else ""}</p>\n'
                   f"{md(includes(p['body']))}\n" + "\n".join(postnav))
        write(p["url"], render(p["meta"]["title"], content, "blog", p["url"]))
        urls.append(p["url"])

    write("/404.html", render("Page not found",
                              '<h1>Page not found</h1>\n<p>This address does not exist on the new site. '
                              'Try the <a href="/">home page</a> or the <a href="/blog/">blog</a>.</p>', None, "/404.html"))

    today = datetime.date.today().isoformat()
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sitemap += [f"  <url><loc>{SITE['url']}{u}</loc><lastmod>{today}</lastmod></url>" for u in urls]
    sitemap.append("</urlset>")
    (OUT / "sitemap.xml").write_text("\n".join(sitemap) + "\n")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE['url']}/sitemap.xml\n")

    # Warn about files referenced from pages that are not in static/ yet (e.g. media not imported).
    missing = set()
    for f in OUT.rglob("*.html"):
        for ref in re.findall(r'(?:href|src)="(/(?:media|files)/[^"#?]+)"', f.read_text()):
            if not (ROOT / "static" / ref.lstrip("/")).exists():
                missing.add(ref)
    print(f"Built {len(urls)} pages into {OUT.relative_to(ROOT)}/")
    if missing:
        print(f"Warning: {len(missing)} referenced file(s) not in static/ yet "
              f"(run scripts/import_media.py): {', '.join(sorted(missing))}")


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        import functools, http.server
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT))
        print("Preview at http://localhost:8000  (Ctrl+C to stop)")
        http.server.ThreadingHTTPServer(("", 8000), handler).serve_forever()
