#!/usr/bin/env python3
"""Rebuild the Festival Calendar in index.html from events.json.

Run from anywhere:  python3 tools/build_calendar.py [--check]

Rewrites only these marked parts of index.html:
  <!-- MONTHPILLS:BEGIN --> ... <!-- MONTHPILLS:END -->   (month filter pills)
  <!-- CALENDAR:BEGIN -->   ... <!-- CALENDAR:END -->     (month groups + cards)
  <!-- MARKETS:BEGIN -->    ... <!-- MARKETS:END -->      (Christmas markets, trips, late markets from markets.json)
  <!-- EVENTCOUNT -->N<!-- /EVENTCOUNT -->                   (festival count)
  <!-- MARKETCOUNT -->N<!-- /MARKETCOUNT -->                 (Christmas market count)
Map pins are built in the browser from the cards, so there is no second list to keep in sync.

events.json fields per event:
  name, country (DE|FR|BE|NL|LU), location, lat, lng, start, end (YYYY-MM-DD),
  dates_display (prefix "~" when projected), status (verified|projected),
  link, desc, distance, optional: ongoing (bool), basis, source, note.
"""
import html, json, re, sys
from collections import OrderedDict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX, DATA, MARKETS = ROOT / "index.html", ROOT / "events.json", ROOT / "markets.json"
EARLIEST = "2026-11-01"           # nothing older than this goes on the page
LAST = "2027-12-31"               # calendar horizon
BBOX = (42.0, 54.5, -1.5, 14.5)   # lat_min, lat_max, lng_min, lng_max (~5h drive radius plus margin)
COUNTRIES = {"DE", "FR", "BE", "NL", "LU"}
COUNTRY_NAME = {"DE": "Germany", "FR": "France", "BE": "Belgium", "NL": "Netherlands", "LU": "Luxembourg"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]

# Notes shown at the top of a month group, keyed by YYYY-MM.
MONTH_NOTES = {
    "2027-02": "&#127917; <strong>Carnival week:</strong> Weiberfastnacht Thu 4 Feb, Rosenmontag Mon 8 Feb, Ash Wednesday 10 Feb.",
    "2027-11": "&#9888;&#65039; <strong>Totensonntag, Sunday 21 November 2027.</strong> A silent day in Germany: German Christmas markets stay shut, and most in RLP and BW only open in the days after. The 2027/28 markets will be added once cities publish their dates.",
}

e = html.escape


def fail(msg):
    sys.exit("build_calendar: " + msg)


def month_keys():
    y, m = 2026, 11
    while (y, m) <= (2027, 12):
        yield f"{y}-{m:02d}"
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def validate(events):
    seen = set()
    for i, ev in enumerate(events):
        where = f"event #{i} ({ev.get('name')!r})"
        for k in ("name", "country", "location", "lat", "lng", "start", "end", "dates_display", "status", "link", "desc", "distance"):
            if ev.get(k) in (None, ""):
                fail(f"{where}: missing {k}")
        if ev["country"] not in COUNTRIES:
            fail(f"{where}: bad country {ev['country']}")
        if not (BBOX[0] <= ev["lat"] <= BBOX[1] and BBOX[2] <= ev["lng"] <= BBOX[3]):
            fail(f"{where}: coordinates {ev['lat']},{ev['lng']} outside the region")
        for k in ("start", "end"):
            date.fromisoformat(ev[k])
        if ev["end"] < ev["start"]:
            fail(f"{where}: ends before it starts")
        if not ev.get("ongoing"):
            if ev["start"] < EARLIEST:
                fail(f"{where}: starts {ev['start']}, before {EARLIEST}")
            if ev["start"] > LAST:
                fail(f"{where}: starts after {LAST}")
        if ev["status"] not in ("verified", "projected"):
            fail(f"{where}: bad status {ev['status']}")
        if ev["status"] == "projected" and not ev["dates_display"].startswith("~"):
            fail(f"{where}: projected date must start with '~'")
        if ev["status"] == "verified" and ev["dates_display"].startswith("~"):
            fail(f"{where}: verified date must not start with '~'")
        key = (ev["name"].strip().lower(), ev["start"])
        if key in seen:
            fail(f"{where}: duplicate name+start")
        seen.add(key)


def date_bits(display):
    """Return (chip text, estimated?) - a leading ~ becomes the hand-written "est." tag."""
    d = display.strip()
    return (d[1:].strip(), True) if d.startswith("~") else (d, False)


def card(ev, month, market=False):
    c = ev["country"]
    chip, est = date_bits(ev["dates_display"])
    est_html = '<span class="est">est.</span>' if est else ""
    body = (f'<div class="known">Known for</div>\n                <p class="card-desc">{e(ev["known"])}</p>' if market
            else f'<p class="card-desc">{e(ev["desc"])}</p>')
    link = (f'<a class="link" href="{e(ev["link"])}" target="_blank" rel="noopener">Official site &rarr;</a>'
            if ev.get("link") else "")
    return f"""            <article class="card{' market' if market else ''}" style="--c:var(--c-{c.lower()})" data-lat="{ev['lat']:.4f}" data-lng="{ev['lng']:.4f}" data-month="{month}" data-country="{c}" data-dates="{ev['start']}">
              <div class="card-band"></div>
              <button class="star" type="button" aria-pressed="false" aria-label="Save {e(ev['name'])}">&#9733;</button>
              <div class="card-body">
                <div class="card-kicker"><span class="dot"></span>{COUNTRY_NAME[c]} &middot; {e(ev['location'])}</div>
                <h3 class="card-title">{e(ev['name'])}</h3>
                <div class="card-dates"><span class="date-chip">{e(chip)}</span>{est_html}</div>
                {body}
                <div class="card-foot"><span class="drive">{e(ev['distance'])}</span>{link}</div>
              </div>
            </article>"""


def build(events):
    groups = OrderedDict((k, []) for k in month_keys())
    groups["ongoing"] = []
    for ev in events:
        groups["ongoing" if ev.get("ongoing") else ev["start"][:7]].append(ev)
    for k, evs in groups.items():
        if not evs:
            fail(f"month group {k} is empty")
        evs.sort(key=lambda x: (x["start"], x["name"]))

    pills = ['        <button class="chip on" type="button" data-month="all" aria-pressed="true">All</button>']
    out = []
    shade = ["band-cream", "band-paper"]
    prev = "var(--paper)"
    for i, (k, evs) in enumerate(groups.items()):
        cls = shade[i % 2]
        if k == "ongoing":
            num, yr, label, pill = "&infin;", "Every year", "All year round", "All year"
        else:
            y, m = int(k[:4]), int(k[5:])
            num, yr, label, pill = f"{m:02d}", str(y), MONTHS[m-1], f"{MONTHS[m-1][:3]} &rsquo;{str(y)[2:]}"
        pills.append(f'        <button class="chip" type="button" data-month="{k}" aria-pressed="false">{pill}</button>')
        note = MONTH_NOTES.get(k)
        note_html = f'\n        <div class="note">{note}</div>' if note else ""
        n = len(evs)
        out.append(f"""<section class="band {cls} scallop month" style="--prev:{prev}" id="m-{k}" data-monthgroup="{k}">
      <div class="wrap reveal">
        <div class="month-head"><div class="month-num" aria-hidden="true">{num}</div>
          <div><div class="month-yr">{yr}</div><h2 class="month-name">{label}</h2><div class="month-count">{n} event{'s' if n != 1 else ''}</div></div></div>{note_html}
        <div class="grid">
{chr(10).join(card(ev, k) for ev in evs)}
        </div>
      </div>
    </section>
""")
        prev = "var(--paper-2)" if cls == "band-cream" else "var(--paper)"
    out.append(f"<style>#markets{{--prev:{prev}}}</style>")
    return "\n".join(pills) + "\n", "\n".join(out), groups


def build_markets(data):
    out, total = [], 0
    for cat in data["categories"]:
        ms = sorted(cat["markets"], key=lambda x: (x["start"], x["name"]))
        total += len(ms)
        for mk in ms:
            for k in ("name", "country", "lat", "lng", "start", "dates_display", "location", "known", "distance"):
                if mk.get(k) in (None, ""):
                    fail(f"market {mk.get('name')!r}: missing {k}")
        out.append(f"""      <div class="market-group" data-group>
        <h3 class="group-title">{e(cat['title'])} <span>{len(ms)}</span></h3>
        <div class="grid">
{chr(10).join(card(mk, mk['start'][:7], market=True) for mk in ms)}
        </div>
      </div>""")
    trips = []
    for t in data["trips"]:
        stops = "".join(f'<li><strong>{e(st["name"])}</strong><span>{e(st["detail"])}</span></li>' for st in t["stops"])
        pills = "".join(f'<span class="tpill">{e(p)}</span>' for p in t["pills"])
        trips.append(f'<div class="trip"><h4>{e(t["title"])}</h4><ol>{stops}</ol><div class="tpills">{pills}</div></div>')
    late = "".join(f'<li><strong>{e(a.rstrip(":"))}</strong> {e(b)}</li>' for a, b in data["open_past_24"])
    out.append(f"""      <div class="extras" data-extras>
        <div class="extra-block">
          <span class="eyebrow">road trips</span>
          <h3 class="h3">Weekend <em>routes</em></h3>
          <div class="trips">{''.join(trips)}</div>
        </div>
        <div class="extra-block">
          <span class="eyebrow">after Christmas</span>
          <h3 class="h3">Open past <em>24 December</em></h3>
          <ul class="late">{late}</ul>
        </div>
      </div>""")
    return "\n".join(out), total


def replace_block(src, tag, body):
    pat = re.compile(rf"(<!-- {tag}:BEGIN -->\n)(.*?)(\s*<!-- {tag}:END -->)", re.S)
    if len(pat.findall(src)) != 1:
        fail(f"expected exactly one {tag} block in index.html")
    return pat.sub(lambda m: m.group(1) + body.rstrip("\n") + m.group(3), src)


def main():
    events = json.loads(DATA.read_text(encoding="utf-8"))
    validate(events)
    pills, cal, groups = build(events)
    src = INDEX.read_text(encoding="utf-8")
    markets_html, n_markets = build_markets(json.loads(MARKETS.read_text(encoding="utf-8")))
    new = replace_block(replace_block(src, "MONTHPILLS", pills), "CALENDAR", cal)
    new = replace_block(new, "MARKETS", markets_html)
    new, n = re.subn(r"<!-- MARKETCOUNT -->.*?<!-- /MARKETCOUNT -->",
                     f"<!-- MARKETCOUNT -->{n_markets}<!-- /MARKETCOUNT -->", new)
    if n < 1:
        fail("expected a MARKETCOUNT marker in index.html")
    new, n = re.subn(r"<!-- EVENTCOUNT -->.*?<!-- /EVENTCOUNT -->",
                     f"<!-- EVENTCOUNT -->{len(events)}<!-- /EVENTCOUNT -->", new)
    if n < 1:
        fail("expected an EVENTCOUNT marker in index.html")
    for k, evs in groups.items():
        v = sum(ev["status"] == "verified" for ev in evs)
        print(f"  {k:8s} {len(evs):3d} events ({v} verified)")
    total = len(events)
    print(f"  total    {total:3d} events, {sum(ev['status']=='verified' for ev in events)} verified")
    if "--check" in sys.argv:
        print("check only: index.html not written")
        return
    INDEX.write_text(new, encoding="utf-8")
    print("index.html updated")


if __name__ == "__main__":
    main()
