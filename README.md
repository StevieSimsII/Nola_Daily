# Nola Daily

Nola Daily is a Python-powered daily digest for New Orleans. It gathers local news, restaurant coverage, entertainment headlines, live music listings, upcoming events, and the NOAA forecast, then publishes them to a cinematic static site on GitHub Pages.

The front-end (`docs/index.html` + `docs/assets/styles.css`) is a hand-crafted immersive page — "Night in the Quarter" — that fetches `docs/data/digest.json` client-side. The daily Python run only refreshes the JSON, so design changes never collide with data commits.

It is designed to run unattended from GitHub Actions and can optionally post a compact digest to Microsoft Teams or a Power Automate webhook.

## What It Publishes

- City news for New Orleans
- Restaurant and dining coverage
- Entertainment and culture headlines
- Live music and concert coverage
- Upcoming event listings from the WWOZ calendar
- Current forecast plus a 7 day forecast for New Orleans
- Clickable source links throughout the site

## Project Layout

- `src/noladaily/` Python package for collection, data output, and notifications
- `docs/` GitHub Pages site: static front-end plus generated `data/digest.json`
- `.github/workflows/` scheduled automation and Teams test workflows

## Local Setup

1. Create and activate a Python 3.11+ virtual environment.
2. Install the package:

```bash
python -m pip install --upgrade pip
python -m pip install .
```

3. Run a full refresh:

```bash
python -m noladaily --output-dir docs --data-path docs/data/digest.json
```

4. Serve `docs/` locally (the page fetches JSON, so `file://` won't work):

```bash
python -m http.server -d docs 8000
```

Then open `http://localhost:8000`.

## Teams Webhook Setup

The app supports two webhook styles:

- `power_automate`: best fit for a Power Automate manual trigger URL
- `teams`: best fit for a native Teams incoming webhook endpoint

For `power_automate`, the request body is the Adaptive Card itself, so the flow should pass the trigger body directly into the Teams card action.

Environment variables:

- `TEAMS_WEBHOOK_URL`: required only when you want notifications
- `TEAMS_WEBHOOK_MODE`: optional, defaults to `power_automate`
- `SITE_URL`: optional, used for the “Open site” button in notifications

Normal digest runs skip Teams delivery when `TEAMS_WEBHOOK_URL` is missing.

### Send a sample Teams notification

```bash
python -m noladaily --teams-sample --teams-required
```

### Send a notification from the latest generated digest

```bash
python -m noladaily --teams-from-file docs/data/digest.json --teams-required
```

## GitHub Actions

### Daily refresh

The scheduled workflow:

- installs Python
- refreshes the digest data (`docs/data/digest.json`)
- optionally sends a Teams notification
- commits the updated data file back to the repository (the static front-end is never regenerated)

### Teams test workflow

The manual Teams workflow supports:

- `sample`: sends a realistic test card without needing fresh data
- `latest`: sends a notification from the last generated digest file

## GitHub Pages Setup

After pushing this repo to GitHub:

1. Open repository Settings.
2. Go to Pages.
3. Set the source to `Deploy from a branch`.
4. Select the `main` branch and the `/docs` folder.

The daily workflow will keep `docs/` fresh, and GitHub Pages will publish the updated site.

## Recommended Repository Secrets And Variables

Secrets:

- `TEAMS_WEBHOOK_URL`

Variable