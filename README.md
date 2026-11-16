# GCGDB

Kartendatenbank und gemeinsame Werkzeuge für das **Gundam Card Game**, als Basis für eigene Apps
und Tools (zuerst [GCGScanner](https://github.com/somecoder3/GCGScanner)).

- **Daten**: `data/cards.db` (SQLite) und `data/cards.json` (dasselbe als JSON für Browser/PWA),
  erzeugt aus der offiziellen Kartenliste auf <https://www.gundam-gcg.com/en/cards/>.
  Stand 16. Nov. 2026: 1290 Karten, 2205 Druckvarianten, 26 Produkte.
- **Python-Paket `gcgdb`** (nur Standardbibliothek, Python 3.11+): Scraper, Datenbank, Exporte, CLI.
- **JavaScript-Module `js/`** (reine ES-Module ohne Build-Schritt, Browser und Node): Kartennummern,
  Datenbankzugriff auf `cards.json`, Listenformate (ExBurst-CSV, Limitless, TTS …) und Listen-Parser.

## Kartennummern

| Schreibweise | Beispiel | Verwendung |
|---|---|---|
| Kartennummer | `GD06-002` | eine pro Karte, alle Drucke teilen sie |
| offizielle Id | `GD06-002_p1` | gundam-gcg.com, `_pN` für Alt Arts |
| ExBurst-Id | `GD06-002-ALT1` | exburst.dev, `-ALTN`; **Schlüssel in GCGDB** |

Offiziell und ExBurst sind 1:1 (`_pN` ↔ `-ALTN`). Präfixe: `GD01`…, `ST01`…, `EB01`, `T` (Token),
`R`/`RP` (Ressourcen), `EXB`/`EXBP`, `EXR`/`EXRP`. Die letzten sieben sind „allgemeine Sets“
(`GENERAL_SETS`), die zu keinem Booster/Starter gehören.

## Datenbank bauen

```bash
python -m gcgdb build --details             # ~20 min beim ersten Lauf, danach aus dem Cache
python -m gcgdb build --details --refresh   # nach einem neuen Set: Kartenlisten neu laden
python -m gcgdb build --details --images    # zusätzlich alle Kartenbilder nach build/carddb-cache/images/
```

Alle Antworten liegen unter `build/carddb-cache/` (nicht im Repo); ein erneuter Lauf lädt nur, was fehlt.
Ein vorhandener Cache (z. B. aus GCGScanner) lässt sich mit `--cache <pfad>` nutzen. `build` schreibt
`data/cards.db` und `data/cards.json`; beide committen.

Weitere Befehle:

```bash
python -m gcgdb info                        # Stand und Karten pro Set
python -m gcgdb lookup GD01-118             # Karte mit allen Drucken und Produkten
python -m gcgdb export cards-pretty out.json
python -m gcgdb export scanner-variants out.json   # variants.json im Format von GCGScanner
```

## Tabellen (`data/cards.db`, Schema 2)

- `card`: eine Zeile pro Kartennummer (Name, Typ, Farbe, Level, Kosten, AP, HP, Zone, Trait, Link,
  Herkunftstitel, Effekt, `set_code`). Spieldaten vom Grunddruck.
- `variant`: eine Zeile pro Druck, Schlüssel `exburst_id`; `official_id`, `alt_index`, `rarity`
  (`LK` steht in der Rarität, z. B. `LKR+`; `SP` nicht), `block` (Block-Symbol: `1`, `2`, `β`, `-`),
  `image_url`/`image_file` (offizielles Bild).
- `package` (`id`, `label`, `name`, `code`) und `variant_package`: in welchen Produkten ein Druck steckt.
- `meta`: `schema_version`, Quelle, Erstellungszeit, Anzahlen.

Schema 2 ergänzt Schema 1 (GCGScanner) nur um Spalten; alte Leser funktionieren weiter.

Python:

```python
import gcgdb
db = gcgdb.connect()                      # data/cards.db, nur lesend, Zeilen per Spaltenname
db.execute("SELECT * FROM variant WHERE card_no = ?", (gcgdb.parse_id("GD01-118_p3").card_no,))
```

## JavaScript

```js
import { CardDB, formatList, parseList, parseId } from "./gcgdb/js/index.js";

const db = await CardDB.load(new URL("./gcgdb/data/cards.json", import.meta.url));
db.variant("GD06-002_p1");      // { id, officialId, cardNo, alt, rarity, block, image, packages, name, card }
db.card("GD06-002").variants;   // alle Drucke
db.sets();                      // [{ set: "GD01", cards: 130, general: false }, …]

formatList([{ id: "GD06-002-ALT1", count: 2 }], "exburst", { db });   // auch: simple, limitless, names, msa, tts
parseList(text);                // { entries: [{ id, count }], names, errors } – erkennt alle obigen Formate
```

## Tests

```bash
python -m unittest discover -s tests -t .
node --test js/test/
```

## In anderen Projekten verwenden

Empfohlen als **Git-Submodul** (z. B. `gcgdb/` im Projekt): Python-Werkzeuge importieren `gcgdb`
direkt, Web-Apps laden `js/*.js` und `data/cards.json` ohne Build-Schritt. Eine PWA, die nur einen
Ordner veröffentlicht, kopiert diese Dateien beim Deploy hinein. Alternativ:
`pip install git+https://github.com/<owner>/GCGDB` (nur Python, ohne `data/`).
