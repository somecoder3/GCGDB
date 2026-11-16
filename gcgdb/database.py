"""The SQLite card database (data/cards.db): schema, writing and opening.

Schema version 2. Compared with version 1 (GCGScanner until Nov. 2026) it only adds columns,
so readers of version 1 keep working: package.code / package.name, card.set_code, variant.block,
meta.schema_version. variant.image_file is always set now (file name of the official image).
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .ids import set_code
from .scraper import BASE_URL, split_package_label

SCHEMA_VERSION = 2
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / "data" / "cards.db"

SCHEMA = """
CREATE TABLE meta (
    key   TEXT PRIMARY KEY NOT NULL,
    value TEXT NOT NULL
);
-- A product (booster, starter deck, promotion ...). id is the official package id (6xxxxx).
CREATE TABLE package (
    id    TEXT PRIMARY KEY NOT NULL,
    label TEXT NOT NULL,          -- as on the website: 'Stardust Trails [GD06]'
    name  TEXT NOT NULL,          -- 'Stardust Trails'
    code  TEXT                    -- 'GD06'; NULL for 'Promotion card', 'Edition Beta' ...
);
-- One row per card number; game data comes from the base printing.
CREATE TABLE card (
    card_no      TEXT PRIMARY KEY NOT NULL,   -- GD06-002
    name         TEXT NOT NULL,
    type         TEXT,                        -- UNIT, PILOT, COMMAND, BASE, RESOURCE, UNIT TOKEN, EX BASE, EX RESOURCE
    color        TEXT,
    level        INTEGER,
    cost         INTEGER,
    ap           INTEGER,
    hp           INTEGER,
    zone         TEXT,
    trait        TEXT,
    link         TEXT,
    source_title TEXT,
    effect       TEXT,
    set_code     TEXT NOT NULL                -- GD06, ST01, T ...
);
-- One row per printing (base card and every alt art).
CREATE TABLE variant (
    exburst_id  TEXT PRIMARY KEY NOT NULL,          -- GD06-002-ALT1
    official_id TEXT NOT NULL UNIQUE,               -- GD06-002_p1
    card_no     TEXT NOT NULL REFERENCES card(card_no),
    alt_index   INTEGER NOT NULL,                   -- 0 = base printing
    rarity      TEXT,                               -- C, U, R, LR, P, with +/++; LK in the rarity (LKR+)
    image_url   TEXT NOT NULL,                      -- official image (not embeddable on other sites)
    image_file  TEXT NOT NULL,                      -- GD06-002_p1.webp
    block       TEXT                                -- block icon on the card: '1', '2', 'β', '-'
);
CREATE INDEX index_variant_card_no ON variant(card_no);
-- In which products a printing is included.
CREATE TABLE variant_package (
    exburst_id TEXT NOT NULL REFERENCES variant(exburst_id),
    package_id TEXT NOT NULL REFERENCES package(id),
    PRIMARY KEY (exburst_id, package_id)
);
"""


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _card_type(value):
    # The website writes the token type once as 'UNIT・TOKEN' and otherwise as 'UNIT TOKEN'.
    return value.replace("・", " ") if value else value


def write_database(out_path: Path, packages: dict, variants: dict, source: str = BASE_URL) -> int:
    """Writes packages {id: label} and variants {official_id: scraper.Variant}; returns the card count.
    Written to a temporary file first, so readers never see a half-written database."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(".tmp")
    tmp_path.unlink(missing_ok=True)
    db = sqlite3.connect(tmp_path)
    db.executescript(SCHEMA)
    db.executemany(
        "INSERT INTO package VALUES (?, ?, ?, ?)",
        [(package_id, label, *split_package_label(label)) for package_id, label in packages.items()],
    )

    by_card = {}
    for variant in variants.values():
        by_card.setdefault(variant.card_no, []).append(variant)

    for card_no, card_variants in sorted(by_card.items()):
        # The base printing carries the canonical data; fall back to any variant that has details.
        card_variants.sort(key=lambda v: v.alt_index)
        source_variant = next((v for v in card_variants if v.details), card_variants[0])
        d = source_variant.details
        db.execute(
            "INSERT INTO card VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                card_no, source_variant.name, _card_type(d.get("type")), d.get("color"),
                _to_int(d.get("lv.")), _to_int(d.get("cost")), _to_int(d.get("ap")), _to_int(d.get("hp")),
                d.get("zone"), d.get("trait"), d.get("link"), d.get("source title"), d.get("effect"),
                set_code(card_no),
            ),
        )
        for v in card_variants:
            db.execute(
                "INSERT INTO variant VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (v.exburst_id, v.official_id, card_no, v.alt_index, v.details.get("rarity"),
                 v.image_url, v.image_file, v.details.get("block")),
            )
            db.executemany(
                "INSERT INTO variant_package VALUES (?, ?)",
                [(v.exburst_id, package_id) for package_id in sorted(v.package_ids)],
            )

    db.executemany(
        "INSERT INTO meta VALUES (?, ?)",
        [
            ("schema_version", str(SCHEMA_VERSION)),
            ("source", source),
            ("built_at", datetime.now(timezone.utc).isoformat(timespec="seconds")),
            ("card_count", str(len(by_card))),
            ("variant_count", str(len(variants))),
        ],
    )
    db.commit()
    db.close()
    tmp_path.replace(out_path)
    return len(by_card)


def connect(path: Path = DEFAULT_DB) -> sqlite3.Connection:
    """Opens the database read-only; rows can be read by column name (row["card_no"])."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"card database not found: {path}")
    db = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def read_meta(db: sqlite3.Connection) -> dict:
    return {key: value for key, value in db.execute("SELECT key, value FROM meta")}
