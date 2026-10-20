#!/usr/bin/env python3
"""Spojí beers-web.json (fakta z webu) + texts.json (texty pro obsluhu)
+ na-cepu.json a vyrobí karty.html (web) a tisk.html (+ PDF k tisku).

Použití:  python3 build.py [--pdf]
Vypíše piva, kterým chybí text (nová na webu) nebo která z webu zmizela.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(HERE, "dist")


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def num(s):
    m = re.search(r"\d+(?:[.,]\d+)?", s or "")
    return float(m.group(0).replace(",", ".")) if m else None


def hop_list(raw, gloss):
    out = []
    for name in [h.strip() for h in raw.split(",") if h.strip()]:
        base, extra = name, None
        if base.lower().startswith("čerstvý "):
            base, extra = base[8:].strip(), gloss["čerstvý"]
        if base.lower().startswith("cryo "):
            base, extra = base[5:].strip(), gloss["Cryo"]
        base = {"Fuggles": "Fuggle", "žatecký": "Žatecký"}.get(base, base)
        note = gloss.get(base)
        if note is None:
            print(f"  ! chmel bez popisu v texts.json: {base}", file=sys.stderr)
        out.append({"name": name[0].upper() + name[1:], "note": "; ".join(x for x in (note, extra) if x)})
    return out


def allergens(malt, extra):
    s = (malt + " " + extra).lower()
    out = ["ječmen (lepek)"]
    if "pšeni" in s:
        out.append("pšenice (lepek)")
    if "oves" in s or "ovesn" in s:
        out.append("oves")
    if "laktóz" in s:
        out.append("laktóza (mléko)")
    return out


def merge():
    web, texts, tap = load("beers-web.json"), load("texts.json"), load("na-cepu.json")
    styles, gloss, t_beers = texts["styles"], texts["hops"], texts["beers"]
    beers, missing = [], []
    web_slugs = {b["slug"] for b in web["beers"]}
    manual = load("beers-manual.json")["beers"] if os.path.exists(os.path.join(HERE, "beers-manual.json")) else []
    for m in manual:
        if m["slug"] in web_slugs:
            print(f"  ! {m['slug']} už je na webu pivovaru – smažte ho z beers-manual.json", file=sys.stderr)
    all_beers = web["beers"] + [m for m in manual if m["slug"] not in web_slugs]
    for b in all_beers:
        t = t_beers.get(b["slug"])
        if not t:
            missing.append(b["slug"])
            continue
        a = b["attrs"]
        extra = "; ".join(v for k, v in a.items() if k in ("další", "ostatní") and v)
        malt = a.get("slad", "")
        style = styles[t["styleKey"]]
        abv, ibu = num(a.get("alkohol")), num(a.get("hořkost"))
        beers.append({
            "slug": b["slug"], "name": b["name"], "category": b["category"], "url": b["url"],
            "image": b.get("image"),
            "siteStyle": a.get("styl", ""), "styleLabel": t.get("label") or style["name"],
            "styleName": style["name"], "styleText": style["text"],
            "deg": a.get("stupňovitost", "").replace(" ", ""), "abv": abv, "ibu": int(ibu) if ibu else None,
            "malt": malt, "hops": hop_list(a.get("chmel", ""), gloss),
            "fermentation": a.get("kvašení", ""), "availability": a.get("dostupnost", ""),
            "extra": extra, "allergens": allergens(malt, extra), "description": b["description"],
            "manual": "fetched" in b,
            **{k: t.get(k) for k in ("color", "group", "tagline", "flavors", "pitch", "who", "food", "caution", "tip")},
        })
    gone = sorted(set(t_beers) - {b["slug"] for b in all_beers})
    unknown_tap = sorted(set(tap["onTap"] + tap.get("sometimes", [])) - {b["slug"] for b in beers})
    return {"fetched": web["fetched"], "source": web["source"], "onTap": tap["onTap"],
            "sometimes": tap.get("sometimes", []),
            "onTapUpdated": tap.get("updated", ""), "beers": beers}, missing, gone, unknown_tap


def render(template, data, out):
    with open(os.path.join(HERE, template), encoding="utf-8") as f:
        html = f.read()
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    with open(os.path.join(DIST, out), "w", encoding="utf-8") as f:
        f.write(html.replace("__DATA__", payload))


def standalone():
    """dist/index.html – samostatná stránka pro hosting mimo claude.ai (např. GitHub Pages)."""
    with open(os.path.join(DIST, "karty.html"), encoding="utf-8") as f:
        page = f.read()
    links = ('<footer class="wrap" style="padding-block:0 40px"><b>K tisku (PDF):</b> '
             '<a href="matuska-karty-nas-cep.pdf">Náš čep</a> · '
             '<a href="matuska-karty-tisk.pdf">Celý sortiment</a> – A4, oboustranně, převracet podle dlouhé strany.</footer>')
    head = ('<!doctype html><html lang="cs"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            '<meta name="robots" content="noindex"><meta name="theme-color" content="#3f6b26">'
            '<style>:root{padding:env(safe-area-inset-top,0) 0 env(safe-area-inset-bottom,0)}body{margin:0}'
            'img{max-width:100%}[hidden]{display:none!important}</style></head><body>')
    title = re.search(r"<title>.*?</title>", page).group(0)
    head = head.replace("</head>", title + "</head>")
    page = page.replace(title, "", 1)
    page = page.replace('<footer class="wrap" id="foot"></footer>', '<footer class="wrap" id="foot"></footer>\n' + links)
    with open(os.path.join(DIST, "index.html"), "w", encoding="utf-8") as f:
        f.write(head + page + "</body></html>")


def main():
    data, missing, gone, unknown_tap = merge()
    os.makedirs(DIST, exist_ok=True)
    render("karty.template.html", data, "karty.html")
    render("tisk.template.html", data, "tisk.html")
    standalone()
    print(f"{len(data['beers'])} karet (web staženo {data['fetched']})", file=sys.stderr)
    for label, items in (("NOVÁ piva bez textu", missing), ("Texty pro piva, která už na webu nejsou", gone),
                         ("Na čepu, ale neznámý slug", unknown_tap)):
        if items:
            print(f"  ! {label}: {', '.join(items)}", file=sys.stderr)
    if "--pdf" in sys.argv:
        chrome = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        for pdf, query in (("matuska-karty-tisk.pdf", ""), ("matuska-karty-nas-cep.pdf", "?tap=1")):
            subprocess.run([chrome, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                            f"--print-to-pdf={os.path.join(DIST, pdf)}",
                            "file://" + os.path.join(DIST, "tisk.html") + query], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"  PDF: dist/{pdf}", file=sys.stderr)


if __name__ == "__main__":
    main()
