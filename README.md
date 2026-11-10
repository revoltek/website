# voo.it

Personal website of Francesco de Gasperin, built with a small Python script and published on GitHub Pages.
The publication list refreshes itself from NASA ADS every Monday.

## Editing

| What | Where |
|---|---|
| Pages (About, Research, CV, …) | `content/*.md` |
| Blog posts | `content/blog/YYYY-MM-DD-slug.md` |
| Menu, domain, ADS query | `site.yaml` |
| Press releases / data links shown under a paper | `data/publication_extras.yaml` (key = DOI or bibcode) |
| Images and downloads | `static/media/`, `static/files/` |
| Look | `static/css/style.css`, `templates/base.html` |

Every push to `main` rebuilds and publishes the site in about a minute.

Preview locally:

```
pip install -r requirements.txt
python build.py --serve        # http://localhost:8000
```

## Weekly publication update

`.github/workflows/deploy.yml` runs every Monday at 04:17 UTC. It calls
`scripts/update_publications.py`, which asks NASA ADS for every refereed paper by
`de Gasperin, F` (first-author and co-author), stores them in `data/publications.json`,
commits that file if anything changed, and republishes the site.

It needs an ADS API token saved as a repository secret:

1. Get a token at <https://ui.adsabs.harvard.edu/user/settings/token>.
2. In this repository: Settings → Secrets and variables → Actions → New repository secret,
   name `ADS_TOKEN`, value the token.
3. Actions → "Build and deploy" → Run workflow, to fill the list straight away.

Without the token the site still builds, using the list already in `data/publications.json`.
If ADS returns far fewer papers than last time (an outage), the script keeps the old list.

To restrict the list to papers you have claimed with ORCID, set `ads.orcid` in `site.yaml`.

## One-time setup

1. **Turn on Pages:** Settings → Pages → Build and deployment → Source: **GitHub Actions**.
2. **Copy the old images:** Actions → "Import media from old site" → Run workflow
   (while voo.it still serves WordPress). It downloads the files listed in `scripts/media.yaml`
   into `static/media/` and rebuilds the site.
3. **Custom domain:** Settings → Pages → Custom domain → `voo.it`, then at the DNS provider:
   - `voo.it` A records: 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153
   - `voo.it` AAAA records: 2606:50c0:8000::153, 2606:50c0:8001::153, 2606:50c0:8002::153, 2606:50c0:8003::153
   - `www.voo.it` CNAME `revoltek.github.io`
   - Once the certificate is issued, tick **Enforce HTTPS**.
4. **degasperin.com:** a Pages site has one custom domain, so redirect it at the DNS level
   (registrar URL forwarding or a Cloudflare redirect rule `degasperin.com/*` → `https://voo.it/`).

Before the custom domain is set, the site is at <https://revoltek.github.io/website/>;
the build adds that `/website` prefix to links automatically.
