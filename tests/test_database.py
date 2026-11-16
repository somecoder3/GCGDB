import json
import tempfile
import unittest
from pathlib import Path

from gcgdb import database, export
from gcgdb.scraper import Variant


def sample():
    packages = {"616106": "Stardust Trails [GD06]", "616901": "Promotion card"}
    base = Variant("GD06-002", "Zaku", "../images/cards/card/GD06-002.webp", {"616106"},
                   {"rarity": "R", "block": "2", "type": "UNIT", "lv.": "4", "cost": "3", "ap": "-"})
    alt = Variant("GD06-002_p1", "Zaku", "../images/cards/card/GD06-002_p1.webp", {"616106", "616901"},
                  {"rarity": "R+", "block": "2"})
    token = Variant("T-025", "Gundam Exia", "../images/cards/card/T-025.webp", {"616901"},
                    {"type": "UNIT・TOKEN"})
    return packages, {v.official_id: v for v in (base, alt, token)}


class DatabaseTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "cards.db"
        self.assertEqual(database.write_database(self.path, *sample()), 2)
        self.db = database.connect(self.path)

    def tearDown(self):
        self.db.close()
        self.dir.cleanup()

    def test_tables(self):
        card = self.db.execute("SELECT * FROM card WHERE card_no = 'GD06-002'").fetchone()
        self.assertEqual((card["level"], card["cost"], card["ap"], card["set_code"]), (4, 3, None, "GD06"))
        self.assertEqual(self.db.execute("SELECT type FROM card WHERE card_no = 'T-025'").fetchone()[0], "UNIT TOKEN")
        alt = self.db.execute("SELECT * FROM variant WHERE exburst_id = 'GD06-002-ALT1'").fetchone()
        self.assertEqual((alt["official_id"], alt["alt_index"], alt["rarity"], alt["block"], alt["image_file"]),
                         ("GD06-002_p1", 1, "R+", "2", "GD06-002_p1.webp"))
        self.assertEqual(alt["image_url"], "https://www.gundam-gcg.com/en/images/cards/card/GD06-002_p1.webp")
        package = self.db.execute("SELECT * FROM package WHERE id = '616106'").fetchone()
        self.assertEqual((package["name"], package["code"]), ("Stardust Trails", "GD06"))
        self.assertEqual(database.read_meta(self.db)["schema_version"], "2")

    def test_read_only(self):
        with self.assertRaises(Exception):
            self.db.execute("DELETE FROM card")

    def test_cards_json(self):
        doc = json.loads(export.cards_json(self.db))
        self.assertEqual(doc["schema"], 2)
        self.assertEqual([v["id"] for v in doc["variants"]], ["GD06-002", "GD06-002-ALT1", "T-025"])
        self.assertEqual(doc["variants"][1]["packages"], ["616106", "616901"])
        self.assertEqual(doc["cards"][0]["set"], "GD06")
        self.assertEqual(export.cards_json(self.db), export.cards_json(self.db))

    def test_scanner_variants(self):
        self.assertEqual(
            export.scanner_variants_json(self.db).decode("utf-8"),
            '[{"id":"GD06-002","cardNo":"GD06-002","name":"Zaku","rarity":"R","file":"GD06-002.webp"},'
            '{"id":"GD06-002-ALT1","cardNo":"GD06-002","name":"Zaku","rarity":"R+","file":"GD06-002_p1.webp"},'
            '{"id":"T-025","cardNo":"T-025","name":"Gundam Exia","rarity":null,"file":"T-025.webp"}]',
        )


class CommittedDataTest(unittest.TestCase):
    """The committed data/cards.json must match data/cards.db."""

    def test_json_matches_db(self):
        json_path = database.REPO_ROOT / "data" / "cards.json"
        if not database.DEFAULT_DB.exists() or not json_path.exists():
            self.skipTest("no committed data")
        db = database.connect(database.DEFAULT_DB)
        try:
            self.assertEqual(export.cards_json(db), json_path.read_bytes(),
                             "data/cards.json is stale: python -m gcgdb export cards data/cards.json")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
