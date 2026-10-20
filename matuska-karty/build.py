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
    for b in web["beers"]:
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
            **{k: t.get(k) for k in ("color", "group", "tagline", "flavors", "pitch", "who", "food", "caution", "tip")},
        })
    gone = sorted(set(t_beers) - {b["slug"] for b in web["beers"]})
    unknown_tap = sorted(set(tap["onTap"]) - {b["slug"] for b in beers})
    return {"fetched": web["fetched"], "source": web["source"], "onTap": tap["onTap"],
            "onTapUpdated": tap.get("updated", ""), "beers": beers}, missing, gone, unknown_tap


def render(template, data, out):
    with open(os.path.join(HERE, template), encoding="utf-8") as f:
        html = f.read()
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    with open(os.path.join(DIST, out), "w", encoding="utf-8") as f:
        f.write(html.replace("__DATA__", payload))


def main():
    data, missing, gone, unknown_tap = merge()
    os.makedirs(DIST, exist_ok=True)
    render("karty.template.html", data, "karty.html")
    render("tisk.template.html", data, "tisk.html")
    print(f"{len(data['beers'])} karet (web staženo {data['fetched']})", file=sys.stderr)
    for label, items in (("NOVÁ piva bez textu", missing), ("Texty pro piva, která už na webu nejsou", gone),
                         ("Na čepu, ale neznámý slug", unknown_tap)):
        if items:
            print(f"  ! {label}: {', '.join(items)}", file=sys.stderr)
    if "--pdf" in sys.argv:
        chrome = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        subprocess.run([chrome, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={os.path.join(DIST, 'matuska-karty-tisk.pdf')}",
                        "file://" + os.path.join(DIST, "tisk.html")], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("  PDF: dist/matuska-karty-tisk.pdf", file=sys.stderr)


if __name__ == "__main__":
    main()
