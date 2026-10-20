# Karty piv Matuška pro obsluhu

Karty piv Pivovaru Matuška pro personál pivnice. Na líci je rychlý přehled (styl, °, %, hořkost, chutě, chmel), na rubu podrobnosti a „jak to říct hostovi“.

- `dist/karty.html` – webová verze (publikovaná jako sdílený odkaz na claude.ai)
- `dist/matuska-karty-tisk.pdf` – k tisku, všechna piva: A4, 4 karty A6 na list, oboustranně, převracet podle dlouhé strany
- `dist/matuska-karty-nas-cep.pdf` – totéž, jen piva z „Našeho čepu“

## Odkud jsou data

| Soubor | Co obsahuje | Kdo ho mění |
|---|---|---|
| `beers-web.json` | fakta z pivovarmatuska.cz (styl, °, %, IBU, slad, chmel, kvašení, dostupnost, popis) | `scrape.py`, automaticky |
| `texts.json` | texty pro obsluhu: prodejní věta, chutě, „komu nabídnout“, jídlo, vysvětlivky stylů a chmelů | ručně / Claude |
| `na-cepu.json` | „Náš čep“: `onTap` = stále na čepu, `sometimes` = občas (slugy z URL piva) | ručně / Claude |

Texty v `texts.json` vycházejí z popisů na webu pivovaru a z obecně známých vlastností chmelů a stylů. Žádná čísla si nevymýšlí: když pivovar hořkost neuvádí, karta ukáže „neuvedeno“.

## Aktualizace (při změně nabídky)

```sh
python3 scrape.py          # stáhne aktuální sortiment z webu pivovaru
python3 build.py --pdf     # sestaví web + PDF a vypíše piva bez textu
```

`build.py` upozorní na:
- **nová piva bez textu** → doplnit záznam do `texts.json` (případně nový chmel do `hops`),
- **texty pro piva, která z webu zmizela** → můžou zůstat, nebo je smažte,
- **neznámé slugy v `na-cepu.json`**.

Pak znovu publikovat `dist/karty.html` na stejný odkaz. Stačí napsat Claudovi „aktualizuj karty Matuška“ (případně i s tím, co je teď na čepu).

Úpravy „Našeho čepu“ v aplikaci (tlačítko na kartě: stále → občas → vůbec) si pamatuje každé zařízení zvlášť. Výchozí seznam pro všechna zařízení je v `na-cepu.json`; když se změní, zařízení přejdou na nový seznam.

Pivo, které na webu pivovaru není (např. Florida), zatím kartu nemá – doplní se, až budou podklady (etiketa, popis od pivovaru).
