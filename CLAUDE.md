# GCGDB

Privates Projekt des Nutzers: gemeinsame Basis (Kartendatenbank + Werkzeuge) für mehrere Apps und
Tools rund ums **Gundam Card Game**. Erster Nutzer ist **GCGScanner** (`E:\programming\GCGScanner`,
PWA zum Kartenscannen, siehe dessen `CLAUDE.md`). Kommunikation auf Deutsch. Der Nutzer kommt aus der
Webentwicklung. Überblick und Befehle: `README.md`.

## Stand (16. Nov. 2026)

- Aufgebaut aus GCGScanner (`tools/carddb/build_carddb.py`, `export_variants()` im Dev-Server,
  Exportformate aus `pwa/js/collection.js`), dort aber **noch nicht eingebunden**. Der Nutzer will das
  als eigenen, späteren Schritt (z. B. als Abhängigkeit/Submodul).
- `data/cards.db` am 16. Nov. aus dem GCGScanner-Cache (`build/carddb-cache`, Stand 2. Nov.) neu gebaut,
  ohne Netzzugriff. Gegen die GCGScanner-DB geprüft: Karten, Varianten und Produktzuordnung gleich, bis
  auf `UNIT・TOKEN` → `UNIT TOKEN` (T-025, T-029; gewollt). `export scanner-variants` ist byte-gleich
  mit GCGScanners `pwa/data/variants.json` (Hash `bbc39be45807e480` wie in dessen `index.json`).
- Aufbau: `gcgdb/` (Python, nur Standardbibliothek: `ids`, `scraper`, `database`, `export`, `cli`),
  `js/` (ES-Module: `ids.js`, `carddb.js`, `lists.js`, `index.js`), `tests/` (unittest), `js/test/`
  (`node --test`), `data/` (committet).

## Entscheidungen

- **Schlüssel ist die ExBurst-Id** (`GD06-002-ALT1`), wie in GCGScanner. Alle Funktionen nehmen jede
  Schreibweise an (`parse_id`/`parseId`).
- **Schema nur erweitern**, Spalten nicht umbenennen oder entfernen; `meta.schema_version` hochzählen.
  `CardDB` (JS) lehnt neuere `cards.json`-Schemas ab. Schema 2 = Schema 1 + `package.name/code`,
  `card.set_code`, `variant.block`, `meta.schema_version`; `image_file` jetzt immer gesetzt
  (bisher nur, wenn das Bild im lokalen Cache lag; ein gemeinsamer Datensatz darf nicht vom Rechner abhängen).
- `data/cards.json` ist deterministisch (sortiert, kompakt) und muss zu `cards.db` passen; ein Test
  (`CommittedDataTest`) prüft das. `build` schreibt beides.
- `variant.block` (Block-Symbol, `1` GD01–GD04, `2` ab GD05, `β` Edition Beta, `-`) neu aufgenommen,
  weil GCGScanners Massenscan (Schritt 4: Variante bestimmen) das Jahr/Block-Symbol nutzen will.
- Listenformate (`LIST_FORMATS`/`formatList` in `js/lists.js`) mit denselben Ids und Ausgaben wie
  GCGScanners `EXPORT_FORMATS`; UI-Texte (deutsche Labels, Hinweise) bleiben in der App. Unterschied:
  Sortierung nach `compareIds` (ALT2 vor ALT10) statt `localeCompare`; bei heute max. ALT8 gleich.
- JS ohne Build und ohne npm-Abhängigkeiten (GCGScanner hat keinen Build-Schritt). Node (v26 auf dem
  Rechner) nur für Tests.

## Fakten (aus GCGScanner übernommen, dort geprüft)

- Kartenliste: `https://www.gundam-gcg.com/en/cards/index.php?package=<id>` liefert alle Karten eines
  Produkts auf einer Seite; Paket-IDs als `data-val="6xxxxx"`. Detailseite
  `detail.php?detailSearch=<official_id>`, Bild `images/cards/card/<official_id>.webp` (600×837).
- Bilder: gundam-gcg.com sendet `Cross-Origin-Resource-Policy: same-site`; die ExBurst-CDN hat
  Hotlink-Schutz (nicht umgehen). Bandai-Bilder nicht öffentlich weiterverbreiten (GCGScanner nutzt
  verschlüsselte Bildpakete). GCGDB speichert daher nur URL/Dateiname, keine Bilder.
- ExBurst-Importformat: `Card No,Owned,Wanted,Trading,Tags`, eine Zeile pro ExBurst-Id.
- Viele ALT-Nummern sind Nachdrucke derselben Illustration in anderen Produkten (z. B. `GD01-118` 9×).
- In der DB steht `LK` in der Rarität (`LKR+`), `SP` nicht (`GD05-123-ALT1` hat `U+`, Karte zeigt `SP`).

## Nächste Schritte (offen, mit dem Nutzer abstimmen)

- GCGScanner auf GCGDB umstellen: Submodul, `tools/carddb/` und `data/cards.db` dort entfernen,
  Dev-Server `export_variants()` → `gcgdb.export.scanner_variants_json`, `collection.js` → `formatList`,
  `GENERAL_SETS`/`setOf` aus `js/ids.js`; Pages-Workflow muss die GCGDB-Dateien mit veröffentlichen.
- Ggf. GitHub-Remote anlegen (bisher nur lokal) und CI für die Tests (Actions per Commit-SHA pinnen).

## Konventionen

- **Diese CLAUDE.md immer aktuell halten** (Wunsch des Nutzers, wie in GCGScanner): Änderungen,
  Erkenntnisse und Entscheidungen im selben Commit nachtragen, Veraltetes korrigieren.
- Abhängigkeiten exakt pinnen und gegen die Registry prüfen; keine Version unter 2 Wochen Alter
  (auch GitHub Actions, per Commit-SHA). Python möglichst nur Standardbibliothek.
- Neues Set: `python -m gcgdb build --details --refresh` (mit `--images`, wenn Bilder für einen
  Index gebraucht werden), Tests laufen lassen, `data/` committen. Danach in den abhängigen Projekten
  deren Folgeschritte (GCGScanner: Index, Bildpakete, Lesemodell neu bauen).
- Unter Windows mit Python-Pfaden `E:/...` statt `/e/...` (Git-Bash-Pfade versteht sqlite3 nicht).
