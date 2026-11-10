#!/usr/bin/env python3
"""Build the static site into _site/.

    python build.py              # build
    python build.py --serve      # build and preview at http://localhost:8000

The home page is made of the sections listed in site.yaml (content/*.md),
the blog of content/blog/YYYY-MM-DD-slug.md, images and files live in static/.
Publications come from data/publications.json (refreshed weekly by
scripts/update_publications.py) plus the notes in data/publication_extras.yaml.
"""
import datetime
import hashlib
import html
import json
import math
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

ICONS = {
    "ads": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5zM4 20.5A2.5 2.5 0 0 0 6.5 23H20v-5M8 7h8M8 11h6"/></svg>',
    "github": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 19c-4.5 1.4-4.5-2.5-6.5-3M15.5 22v-3.6a3.1 3.1 0 0 0-.9-2.4c3-.3 6.1-1.5 6.1-6.6a5.2 5.2 0 0 0-1.4-3.6 4.8 4.8 0 0 0-.1-3.6s-1.1-.3-3.7 1.4a12.7 12.7 0 0 0-6.6 0C6.3 1.9 5.2 2.2 5.2 2.2a4.8 4.8 0 0 0-.1 3.6 5.2 5.2 0 0 0-1.4 3.6c0 5.1 3.1 6.3 6.1 6.6a3.1 3.1 0 0 0-.9 2.4V22"/></svg>',
    "link": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/></svg>',
}


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
        code = (ROOT / m.group(1)).read_text().rstrip("\n")
        return f"```{m.group(2) or ''}\n{code}\n```"
    return re.sub(r"<!--\s*include:\s*(\S+)\s*(\w+)?\s*-->", repl, body)


def long_date(d):
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def esc(s):
    return html.escape(str(s), quote=True)


def clean_title(t):
    """ADS titles may carry entities and <sub>/<sup>; keep only those tags."""
    t = html.escape(html.unescape(t or ""), quote=False)
    return re.sub(r"&lt;(/?)(sub|sup|i)&gt;", lambda m: f"<{m.group(1)}{m.group(2).lower()}>", t, flags=re.I)


def h_index(counts):
    return sum(1 for i, c in enumerate(sorted(counts, reverse=True), 1) if c >= i)


# Page pieces ----------------------------------------------------------------

def ruler():
    """Log-frequency axis 10 MHz – 2 GHz with the ultra-low band (10–100 MHz) filled."""
    lo, hi = math.log10(10), math.log10(2000)
    pos = lambda f: 100 * (math.log10(f) - lo) / (hi - lo)
    parts = [f'<div class="band" style="left:0;width:{pos(100):.2f}%"></div>', '<div class="axis"></div>']
    for decade in (10, 100, 1000):
        for k in range(1, 10):
            f = decade * k
            if f > 2000:
                break
            parts.append(f'<span class="{"tick major" if k == 1 else "tick"}" style="left:{pos(f):.2f}%"></span>')
    for f, label in ((10, "10 MHz"), (100, "100 MHz"), (1000, "1 GHz")):
        parts.append(f'<span class="{"label start" if f == 10 else "label"}" style="left:{pos(f):.2f}%">{label}</span>')
    return ('<div class="ruler" role="img" aria-label="Radio frequency axis from 10 MHz to 2 GHz, '
            'highlighting the ultra-low frequencies below 100 MHz">' + "".join(parts) + "</div>")


def sidebar(active):
    p = SITE["profile"]
    menu = [f'<li><a href="{s["url"]}"{" aria-current=\"page\"" if s["id"] == active else ""}>{esc(s["title"])}</a></li>'
            for s in SITE["sections"]]
    for page in SITE.get("pages", []):
        cur = ' aria-current="page"' if page["key"] == active else ""
        menu.append(f'<li><a href="{page["url"]}"{cur}>{esc(page["title"])}</a></li>')
    links = [f'<li><a href="{esc(l["url"])}">{ICONS.get(l.get("icon"), ICONS["link"])}{esc(l["title"])}</a></li>'
             for l in p.get("links", [])]
    role = "<br>".join(md(r, inline=True) for r in p.get("role", []))
    return f"""<aside class="rail">
  <a class="portrait" href="/"><img src="{p['photo']}" width="168" height="168" alt="Portrait of {esc(p['name'])}"></a>
  <p class="name">{'<br>'.join(esc(x) for x in p.get('name_lines') or [p['name']])}</p>
  <p class="role">{role}</p>
  <a class="logo-chip" href="{esc(p['logo_url'])}"><img src="{p['logo']}" alt="{esc(p['logo_alt'])}"></a>
  <nav aria-label="Sections"><ul class="menu">
    {''.join(menu)}
  </ul></nav>
  <ul class="rail-links">{''.join(links)}</ul>
  <button class="theme-toggle" type="button" data-next="light" aria-label="Switch to a light background">
    <svg class="sun" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
    <svg class="moon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/></svg>
    <span>Light</span>
  </button>
</aside>"""


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
    return data, {str(k).lower(): v for k, v in (extras or {}).items()}


def is_me(author):
    sur, _, init = SITE["ads"]["author"].lower().partition(",")
    a_sur, _, a_first = author.lower().partition(",")
    return a_sur.strip() == sur.strip() and a_first.strip()[:1] == init.strip()[:1]


def authors_html(p, seed):
    names = p.get("authors") or []
    total = max(p.get("n_authors") or 0, len(names))
    limit = SITE["ads"].get("max_authors_shown", 10)
    fmt = lambda a: f"<strong>{esc(a)}</strong>" if is_me(a) else esc(a)
    shown_names = names[:limit]
    shown = "; ".join(fmt(a) for a in shown_names)
    if seed and total <= 1:
        return shown + " et al."
    if total > len(shown_names):
        if not any(is_me(a) for a in shown_names):
            shown += "; …; <strong>de Gasperin, F.</strong>"
        shown += f"; et al. ({total} authors)"
    return shown


def pub_html(p, role, extras, seed):
    doi = p.get("doi")
    ads = f"https://ui.adsabs.harvard.edu/abs/{p['bibcode']}/abstract"
    href = f"https://doi.org/{doi}" if doi else ads
    venue = ", ".join(str(x) for x in (p.get("pub"), p.get("volume"), p.get("page")) if x)
    chips = [f'<span class="chip {role}">{"first author" if role == "first" else "co-author"}</span>',
             f'<a href="{esc(ads)}">ADS</a>']
    if p.get("arxiv"):
        chips.append(f'<a href="https://arxiv.org/abs/{esc(p["arxiv"])}">arXiv:{esc(p["arxiv"])}</a>')
    if doi:
        chips.append(f'<a href="https://doi.org/{esc(doi)}">DOI</a>')
    n = p.get("citations", 0)
    if n:
        chips.append(f'<a href="https://ui.adsabs.harvard.edu/abs/{p["bibcode"]}/citations">'
                     f'{n} citation{"s" if n != 1 else ""}</a>')
    out = [f'<li class="pub" data-role="{role}"><span class="year">{esc(p.get("year", ""))}</span><div>',
           f'<a class="title" href="{esc(href)}">{clean_title(p["title"])}</a>',
           f'<span class="authors">{authors_html(p, seed)}</span>',
           f'<span class="venue">{esc(venue)}</span>',
           f'<span class="links">{"".join(chips)}</span>']
    for key in (str(doi or "").lower(), p["bibcode"].lower()):
        for line in (extras.get(key, []) if key else []):
            out.append(f'<span class="extra">{md(line, inline=True)}</span>')
    out.append("</div></li>")
    return "\n".join(out)


def metrics_table(data):
    first, co = data["first_author"], data.get("coauthor") or []
    m = data["metrics"]
    fc = [p.get("citations", 0) for p in first]
    if co:
        ac = fc + [p.get("citations", 0) for p in co]
        all_n, all_c, all_h = len(ac), sum(ac), h_index(ac)
    else:  # seed data: only first-author records, totals from ADS metrics
        all_n, all_c, all_h = m["refereed_papers"], m["citations"], m["h_index"]
    rows = [("Refereed papers", all_n, len(first)),
            ("Citations", all_c, sum(fc)),
            ("h-index", all_h, h_index(fc)),
            ("Citations per paper", round(all_c / max(all_n, 1)), round(sum(fc) / max(len(first), 1)))]
    body = "".join(f'<tr><th scope="row">{label}</th><td>{a:,}</td><td>{b:,}</td></tr>' for label, a, b in rows)
    upd = long_date(datetime.date.fromisoformat(data["updated"]))
    return (f'<table class="metrics"><caption>From NASA ADS, {upd}</caption>'
            f'<thead><tr><th scope="col"></th><th scope="col">All refereed</th><th scope="col">First author</th></tr></thead>'
            f"<tbody>{body}</tbody></table>")


def publications_html():
    data, extras = load_pubs()
    seed = data.get("seed", False)
    first, co = data["first_author"], data.get("coauthor") or []
    n_co = len(co) or data["metrics"].get("coauthor_papers", 0)
    items = [(p, "first") for p in first] + [(p, "co") for p in co]
    items.sort(key=lambda x: (str(x[0].get("year", "")), x[0]["bibcode"]), reverse=True)
    lis = [pub_html(p, role, extras, seed) for p, role in items]
    if not co and n_co:
        ads = SITE["ads"]["search_url"]
        lis.append(f'<li class="pub note" data-role="co"><span class="year"></span><div>The {n_co} co-authored '
                   f'papers are listed on <a href="{esc(ads)}">NASA ADS</a>.</div></li>')
    total = len(first) + n_co
    buttons = "".join(
        f'<button type="button" data-filter="{f}" aria-pressed="{"true" if f == "first" else "false"}">'
        f'{label} <span class="count">{count}</span></button>'
        for f, label, count in (("first", "First author", len(first)), ("co", "Co-author", n_co), ("all", "All", total)))
    return (metrics_table(data)
            + '<div class="pubhead"><h3>Refereed publications</h3>'
            + f'<div class="pubfilter" role="group" aria-label="Show publications">{buttons}</div></div>'
            + '<ol class="publist">\n' + "\n".join(lis) + "\n</ol>")


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
        posts.append({"meta": meta, "body": body, "date": date, "slug": m.group(2), "url": f"/blog/{m.group(2)}/"})
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

def render(page_title, content, active, permalink, description=None, home=False):
    head, body = gtm()
    css = hashlib.sha1((ROOT / "static" / "css" / "style.css").read_bytes()).hexdigest()[:8]
    values = {
        "lang": SITE.get("lang", "en"),
        "head_title": esc(SITE.get("home_title", SITE["title"]) if home else f"{page_title} | {SITE['title']}"),
        "og_type": "profile" if home else "article",
        "og_image": SITE["url"] + SITE["profile"]["photo"],
        "keywords": esc(SITE.get("keywords", "")),
        "jsonld": person_jsonld() if home else "",
        "page_title": esc(page_title),
        "site_name": esc(SITE["site_name"]),
        "description": esc(description or SITE["description"]),
        "canonical": SITE["url"] + permalink,
        "css_version": css,
        "gtm_head": head, "gtm_body": body,
        "sidebar": sidebar(active),
        "content": content,
        "body_class": "home" if home else "page",
        "year": datetime.date.today().year,
    }
    out = re.sub(r"\{\{ (\w+) \}\}", lambda m: str(values[m.group(1)]), TEMPLATE)
    if BASE:  # prefix root-relative links when served from a sub-path
        out = re.sub(r'((?:href|src)=")/(?!/)', rf"\1{BASE}/", out)
        out = out.replace("url(/media/", f"url({BASE}/media/")
    return out


def person_jsonld():
    """schema.org Person record: tells search engines who the site is about."""
    p = SITE["profile"]
    data = {
        "@context": "https://schema.org", "@type": "Person",
        "name": p["name"], "alternateName": ["Francesco de Gasperin", "Francesco De Gasperin", "de Gasperin", "F. de Gasperin"],
        "url": SITE["url"] + "/", "image": SITE["url"] + p["photo"],
        "jobTitle": "Astronomer", "description": " ".join(SITE["description"].split()),
        "affiliation": [
            {"@type": "Organization", "name": "INAF – Istituto di Radioastronomia", "url": "https://www.ira.inaf.it"},
            {"@type": "Organization", "name": "University of Hamburg", "url": "https://www.uni-hamburg.de"}],
        "memberOf": {"@type": "ResearchProject", "name": "ULU – Ultra Low Frequency Universe (ERC Consolidator Grant)",
                     "url": "https://www.ulu.radio"},
        "knowsAbout": ["Astronomy", "Radio astronomy", "Astrophysics", "LOFAR", "Galaxy clusters",
                       "Active galactic nuclei", "Ultra-low frequency radio observations"],
        "sameAs": [l["url"] for l in p.get("links", [])] + ["https://www.ulu.radio"],
    }
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + "</script>"


def write(permalink, html_):
    dest = OUT / permalink.lstrip("/") / "index.html" if permalink.endswith("/") else OUT / permalink.lstrip("/")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html_)


KIND_CLASS = {"invited talk": "invited", "talk": "talk", "lecture": "lecture", "poster": "poster"}


def talks_html(body):
    """Turn '- DD/MM/YYYY **Kind:** “Title”, venue' lines into a structured, styled list."""
    out, items = [], []
    def flush():
        if items:
            out.append('<ol class="talks">' + "".join(items) + "</ol>")
            items.clear()
    for line in body.splitlines():
        if line.startswith("### "):
            flush()
            out.append(f'<h3>{esc(line[4:].strip())}</h3>')
            continue
        m = re.match(r"^- (\d{2})/(\d{2})/(\d{4}) \*\*(.+?):\*\* (.*)$", line.strip())
        if not m:
            continue
        dd, mm, yyyy, kind, rest = m.groups()
        tm = re.match(r"^(\[)?“(.+?)”(?:\]\((.+?)\))?,?\s*(.*)$", rest)
        if tm:
            title, link, venue = tm.group(2), tm.group(3), tm.group(4)
        else:  # e.g. posters with several links: keep the text as Markdown
            title, link, venue = None, None, rest
        cls = KIND_CLASS.get(kind.lower(), "talk")
        t = (f'<a href="{esc(link)}">{esc(title)}</a>' if link else esc(title)) if title else md(venue, inline=True)
        v = esc(venue) if title else ""
        items.append(f'<li class="talk"><span class="date">{int(dd)} {MONTHS[int(mm) - 1][:3]}</span>'
                     f'<div><span class="kind {cls}">{esc(kind)}</span> <span class="ttitle">{t}</span>'
                     + (f'<span class="where">{v}</span>' if v else "") + "</div></li>")
    flush()
    return "\n".join(out)


def section_page(s):
    meta, body = read_page(ROOT / "content" / s["file"])
    if s["id"] == "talks":
        content = talks_html(body)
    else:
        content = md(includes(body)).replace("<!-- publications -->", publications_html())
    if s["id"] == "about":
        headline = meta.get("headline") or SITE["title"]
        return f'<h1 class="page-title hero-title">{esc(headline)}</h1>\n<section id="about" class="section hero">{ruler()}\n{content}</section>'
    # "<!-- card: Title -->" in a page starts a new card with its own heading
    parts = re.split(r"<!--\s*card:\s*(.+?)\s*-->", content)
    html_ = f'<h1 class="page-title">{esc(s["title"])}</h1>\n<section id="{s["id"]}" class="section">{parts[0]}</section>'
    for title, body in zip(parts[1::2], parts[2::2]):
        html_ += f'\n<h2 class="page-title">{esc(title)}</h2>\n<section class="section">{body}</section>'
    return html_


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "static", OUT)
    (OUT / ".nojekyll").write_text("")
    posts = load_posts()
    section_files = {s["file"] for s in SITE["sections"]}

    urls = []
    for sec in SITE["sections"]:
        home = sec["url"] == "/"
        write(sec["url"], render(sec["title"], section_page(sec), sec["id"], sec["url"], home=home))
        urls.append(sec["url"])

    for path in sorted((ROOT / "content").glob("*.md")):
        if path.name in section_files:
            continue
        meta, body = read_page(path)
        permalink = meta["permalink"]
        content = md(includes(body)).replace("<!-- blog-index -->", blog_index(posts))
        content = f'<h1 class="page-title">{esc(meta["title"])}</h1>\n<section class="section">{content}</section>'
        write(permalink, render(meta["title"], content, meta.get("nav"), permalink, meta.get("description")))
        urls.append(permalink)

    for i, p in enumerate(posts):
        newer = posts[i - 1] if i > 0 else None
        older = posts[i + 1] if i + 1 < len(posts) else None
        cats = ", ".join(p["meta"].get("categories", []))
        nav = ['<nav class="postnav" aria-label="More posts">']
        if older:
            nav.append(f'<a class="prev" href="{older["url"]}">Older: {esc(older["meta"]["title"])}</a>')
        if newer:
            nav.append(f'<a class="next" href="{newer["url"]}">Newer: {esc(newer["meta"]["title"])}</a>')
        nav.append("</nav>")
        content = (f'<p class="crumb"><a href="/blog/">Blog</a></p><h1 class="page-title">{esc(p["meta"]["title"])}</h1>'
                   f'<article class="section">'
                   f'<p class="postmeta">{long_date(p["date"])}{" in " + esc(cats) if cats else ""}</p>\n'
                   f"{md(includes(p['body']))}\n" + "\n".join(nav) + "</article>")
        write(p["url"], render(p["meta"]["title"], content, "blog", p["url"]))
        urls.append(p["url"])

    for old, new in (SITE.get("redirects") or {}).items():
        target = BASE + new
        write(old, f'<!doctype html><meta charset="utf-8"><title>Moved</title>'
                   f'<meta http-equiv="refresh" content="0; url={target}"><link rel="canonical" href="{SITE["url"]}{new}">'
                   f'<p>This page moved to <a href="{target}">{target}</a>.</p>\n')

    write("/404.html", render("Page not found",
                              '<h1 class="page-title">Page not found</h1><section class="section"><p>This address does not exist. '
                              'Try the <a href="/">home page</a> or the <a href="/blog/">blog</a>.</p></section>',
                              None, "/404.html"))

    today = datetime.date.today().isoformat()
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sitemap += [f"  <url><loc>{SITE['url']}{u}</loc><lastmod>{today}</lastmod></url>" for u in urls]
    sitemap.append("</urlset>")
    (OUT / "sitemap.xml").write_text("\n".join(sitemap) + "\n")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE['url']}/sitemap.xml\n")

    missing = set()
    for f in OUT.rglob("*.html"):
        for ref in re.findall(r'(?:href|src)="(/(?:media|files)/[^"#?]+)"', f.read_text()):
            if not (ROOT / "static" / ref.lstrip("/")).exists():
                missing.add(ref)
    print(f"Built {len(urls)} pages into {OUT.relative_to(ROOT)}/")
    if missing:
        print(f"Warning: {len(missing)} referenced file(s) not in static/: {', '.join(sorted(missing))}")


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        import functools, http.server
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT))
        print("Preview at http://localhost:8000  (Ctrl+C to stop)")
        http.server.ThreadingHTTPServer(("", 8000), handler).serve_forever()
