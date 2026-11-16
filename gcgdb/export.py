"""JSON exports of the card database, for apps that cannot read SQLite (browser, PWA).

cards.json (read by js/carddb.js):

    {
      "schema": 2,
      "meta":     {"source": ..., "built_at": ..., "card_count": ..., "variant_count": ...},
      "packages": [{"id": "616106", "code": "GD06", "name": "Stardust Trails", "label": "Stardust Trails [GD06]"}],
      "cards":    [{"cardNo": "GD06-002", "set": "GD06", "name": ..., "type": ..., "color": ..., "level": 4,
                    "cost": 3, "ap": 3, "hp": 3, "zone": ..., "trait": ..., "link": ..., "sourceTitle": ...,
                    "effect": ...}],
      "variants": [{"id": "GD06-002-ALT1", "officialId": "GD06-002_p1", "cardNo": "GD06-002", "alt": 1,
                    "rarity": "R+", "block": "2", "image": "GD06-002_p1.webp", "packages": ["616106"]}]
    }

Lists are sorted (packages by id, cards by number, variants by ExBurst id) and the output is
byte-for-byte deterministic for the same database, so it can be hashed and diffed.
"""

import json
import sqlite3
from pathlib import Path

from .database import connect, read_meta


def _dumps(value, pretty: bool) -> bytes:
    if pretty:
        text = json.dumps(value, ensure_ascii=False, indent=1) + "\n"
    else:
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return text.encode("utf-8")


def cards_document(db: sqlite3.Connection) -> dict:
    meta = read_meta(db)
    packages = [
        {"id": r["id"], "code": r["code"], "name": r["name"], "label": r["label"]}
        for r in db.execute("SELECT * FROM package ORDER BY id")
    ]
    cards = [
        {
            "cardNo": r["card_no"], "set": r["set_code"], "name": r["name"], "type": r["type"],
            "color": r["color"], "level": r["level"], "cost": r["cost"], "ap": r["ap"], "hp": r["hp"],
            "zone": r["zone"], "trait": r["trait"], "link": r["link"], "sourceTitle": r["source_title"],
            "effect": r["effect"],
        }
        for r in db.execute("SELECT * FROM card ORDER BY card_no")
    ]
    packages_of = {}
    for r in db.execute("SELECT exburst_id, package_id FROM variant_package ORDER BY exburst_id, package_id"):
        packages_of.setdefault(r[0], []).append(r[1])
    variants = [
        {
            "id": r["exburst_id"], "officialId": r["official_id"], "cardNo": r["card_no"],
            "alt": r["alt_index"], "rarity": r["rarity"], "block": r["block"], "image": r["image_file"],
            "packages": packages_of.get(r["exburst_id"], []),
        }
        for r in db.execute("SELECT * FROM variant ORDER BY exburst_id")
    ]
    return {
        "schema": int(meta.get("schema_version", 1)),
        "meta": {key: meta[key] for key in ("source", "built_at", "card_count", "variant_count") if key in meta},
        "packages": packages,
        "cards": cards,
        "variants": variants,
    }


def cards_json(db: sqlite3.Connection, pretty: bool = False) -> bytes:
    return _dumps(cards_document(db), pretty)


def scanner_variants_json(db: sqlite3.Connection) -> bytes:
    """The compact variant list of GCGScanner (pwa/data/variants.json, its index is built over it):
    [{"id", "cardNo", "name", "rarity", "file"}] by ExBurst id. Must stay byte-identical, because
    GCGScanner stores the hash of exactly these bytes next to its index."""
    rows = db.execute(
        """SELECT v.exburst_id, v.card_no, c.name, v.rarity, v.official_id || '.webp'
           FROM variant v JOIN card c ON c.card_no = v.card_no
           ORDER BY v.exburst_id"""
    ).fetchall()
    keys = ["id", "cardNo", "name", "rarity", "file"]
    return _dumps([dict(zip(keys, tuple(row))) for row in rows], pretty=False)


EXPORTS = {
    "cards": lambda db: cards_json(db),
    "cards-pretty": lambda db: cards_json(db, pretty=True),
    "scanner-variants": scanner_variants_json,
}


def write_export(db_path: Path, kind: str, out_path: Path) -> int:
    db = connect(db_path)
    try:
        data = EXPORTS[kind](db)
    finally:
        db.close()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    return len(data)
