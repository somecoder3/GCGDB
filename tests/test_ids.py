import unittest

from gcgdb.ids import CardId, is_card_id, parse_id, set_code, to_exburst_id, to_official_id


class IdTest(unittest.TestCase):
    def test_notations(self):
        for text in ("GD06-002_p1", "GD06-002-ALT1", " gd06-002-alt1 ", "gd06-002_P1"):
            self.assertEqual(parse_id(text), CardId("GD06-002", 1), text)
        self.assertEqual(to_exburst_id("ST01-001_p8"), "ST01-001-ALT8")
        self.assertEqual(to_official_id("ST01-001-ALT8"), "ST01-001_p8")
        self.assertEqual(to_exburst_id("GD06-002"), "GD06-002")

    def test_all_prefixes(self):
        for card_no, code in [("T-001", "T"), ("R-041", "R"), ("RP-001", "RP"), ("EXBP-027", "EXBP"),
                              ("EXR-011", "EXR"), ("EB01-090", "EB01"), ("ST14-016", "ST14")]:
            card = parse_id(card_no + "_p2")
            self.assertEqual(card.set_code, code)
            self.assertEqual(card.exburst_id, card_no + "-ALT2")
            self.assertEqual(set_code(card.exburst_id), code)

    def test_number(self):
        self.assertEqual(parse_id("GD01-118-ALT8").number, 118)

    def test_invalid(self):
        for text in ("", "GD06", "GD06-02", "GD06-0021", "GD06-002-ALT", "GD06-002_x1", "06-002"):
            self.assertFalse(is_card_id(text), text)
            with self.assertRaises(ValueError):
                parse_id(text)


if __name__ == "__main__":
    unittest.main()
