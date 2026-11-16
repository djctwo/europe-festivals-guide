# Europe Festivals Guide

## Overview
Single-page public guide (`index.html`) to festivals, carnivals, wine fests and Christmas markets across Germany, France, Belgium, the Netherlands and Luxembourg. For expats and travellers. Season shown: **November 2026 – December 2027**.

## How content works (read before editing)
- **`events.json` is the canonical festival list.** Never hand-edit the calendar cards in `index.html`.
- **`markets.json`** holds the Christmas markets (by category), the weekend trip routes and the "open past 24 December" list.
- **`tools/build_calendar.py`** rewrites only the marked blocks in `index.html`: `MONTHPILLS`, `CALENDAR`, `MARKETS`, plus the `EVENTCOUNT` / `MARKETCOUNT` numbers. Run `python3 tools/build_calendar.py` (add `--check` to validate without writing).
- The script refuses to build if an event starts before 2026-11-01 or after 2027-12-31, lacks a field or coordinates, sits outside the region box, repeats a name+start, leaves a month empty, or breaks the date rule below.
- **Date rule:** `status: "verified"` = a 2027 (or 2026) date read from an official/reliable source page, shown plain. `status: "projected"` = estimated from the usual pattern; `dates_display` must start with `~`, which renders as the hand-written **est.** tag. Each projected event carries a one-line `basis`.
- Month notes (carnival week, Totensonntag 2027) live in `MONTH_NOTES` in the build script.
- Map pins are built in the browser from the cards (one pin per location, popup lists everything there), so there is no second list to keep in sync. Filters also filter the pins.
- Favourites are stored in localStorage under `kl-expat-favorites` (old key kept so saved stars survive), keyed by event name.

## Design ("Rhine Nights", shipped 2026-11-16)
- Night-sky hero with a line-drawn Rhine castle + vineyard + half-timbered houses (SVG, draws in), five-country colour band, sticky filter bar (month chips Nov '26 → Dec '27 + All year; country chips; Saved).
- Fonts: Fraunces (display), Bricolage Grotesque (body), Caveat (hand-written accents). Colours are oklch tokens on `:root`; country colours `--c-de/fr/be/nl/lu`.
- Bands alternate paper / cream with scalloped edges; giant month numerals; cards have a country-colour top band, ink date chip, hard offset shadow. Christmas markets are a night section with falling snow.
- Sister sites in the same family: SD × Baja guide (djctwo.github.io/sd-baja-guide).

## Tech
- Static HTML, embedded CSS/JS, no framework. Leaflet 1.9.4 from unpkg with SRI hashes.
- **Map tiles: OpenStreetMap** (`tile.openstreetmap.org`) darkened with a CSS filter. CARTO basemaps now need an API key, so don't go back to them. OSM blocks requests with no Referer: preview with `python3 -m http.server`, never `file://`.
- Public-content rules: no home pin, no "home-base" wording, no military or personal references. Drive times "from KL" are fine.

## Content stats (2026-11-16)
- **351 festivals** (203 verified dates, 148 estimated): DE 164 · FR 65 · NL 59 · BE 49 · LU 14.
- **41 Christmas markets** (2026/27 season) + 4 weekend routes.
- Research: 2026-11-16, eight research agents (carry-forward of the old list + five regional deep sweeps). The sweeps hit the session's shared 200-search limit, so France (Burgundy, Hauts-de-France), Saarland/Westerwald/Hunsrück and the BW/Hesse/Bavaria state tourism calendars are the thinnest. A follow-up pass is worthwhile.

## Yearly upkeep
- **Autumn 2027:** replace `markets.json` with verified 2027/28 market dates (most cities publish Sep–Oct), compute Totensonntag with Python, and re-check estimated 2027 events as dates are announced (flip to verified, drop the `~`).
- To roll the calendar forward: update `events.json`, change `EARLIEST`/`LAST` and `month_keys()` in the build script, rebuild.

## Repo
- Remote: `https://github.com/djctwo/europe-festivals-guide.git` (main) · GitHub Pages
- Live: https://djctwo.github.io/europe-festivals-guide/ (renamed from kl-expat-guide 2026-10-27; the old address is a 404 by design)
