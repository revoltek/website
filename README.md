# degasperin.com

Personal website of Francesco de Gasperin, built with a small Python script and published on GitHub Pages.
The publication list refreshes itself from NASA ADS every Monday.

## Editing

| What | Where |
|---|---|
| Pages (About, Research, Talks, CV, …) | `content/*.md` |
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

The ADS API token is read from the `ADS_TOKEN` repository secret. Without it the site still
builds, using the list already in `data/publications.json`.
If ADS returns far fewer papers than last time (an outage), the script keeps the old list.

To restrict the list to papers you have claimed with ORCID, set `ads.orcid` in `site.yaml`.
