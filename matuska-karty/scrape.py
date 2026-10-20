#!/usr/bin/env python3
"""Stáhne aktuální sortiment z pivovarmatuska.cz do beers-web.json.

Použití:  python3 scrape.py [výstupní_soubor]
Bere jen fakta z webu pivovaru (styl, °, %, IBU, slad, chmel, kvašení,
dostupnost, popis, kategorie). Texty pro obsluhu jsou v beers-texts.json.
"""
import html
import json
import re
import sys
import urllib.request
from datetime import date

BASE = "https://www.pivovarmatuska.cz"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (matuska-karty)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def clean(s):
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"</p>\s*<p[^>]*>", "\n\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    return s.strip()


def categories():
    page = get(BASE + "/piva/")
    out, cat = [], None
    for m in re.finditer(r'<h2[^>]*>(.*?)</h2>|href="' + re.escape(BASE) + r'/pivo/([^"/]+)/?"', page, re.S):
        if m.group(1) is not None:
            cat = clean(m.group(1))
        elif cat and m.group(2) not in [s for s, _ in out]:
            out.append((m.group(2), cat))
    return out


def beer(slug):
    page = get(f"{BASE}/pivo/{slug}/")
    name = clean(re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S).group(1))
    desc = re.search(r'class="singlebeer__desc">(.*?)</div>', page, re.S)
    attrs = {clean(k).lower(): clean(v) for k, v in re.findall(
        r"<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*</tr>",
        re.search(r'singlebeer__attrs">(.*?)</table>', page, re.S).group(1), re.S)}
    nav = re.search(r"BottleCarousel__nav\">(.*?)</div>", page, re.S)
    sizes = [clean(x) for x in re.findall(r"<a[^>]*>(.*?)</a>", nav.group(1), re.S)] if nav else []
    imgs = re.findall(r'<img src="(https://snappycdn[^"]+)" alt="[^"]*- ([^"]+)"', page)
    return {
        "slug": slug,
        "url": f"{BASE}/pivo/{slug}/",
        "name": name,
        "description": clean(desc.group(1)) if desc else "",
        "attrs": attrs,
        "sizes": sizes,
        "image": imgs[0][0] if imgs else None,
    }


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "beers-web.json"
    beers = []
    for slug, cat in categories():
        b = beer(slug)
        b["category"] = cat
        beers.append(b)
        print(f"{cat:20} {b['name']}", file=sys.stderr)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"fetched": date.today().isoformat(), "source": BASE + "/piva/", "beers": beers},
                  f, ensure_ascii=False, indent=1)
    print(f"{len(beers)} piv -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
