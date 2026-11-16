import unittest

from gcgdb.scraper import parse_card_list, parse_detail, parse_packages, split_package_label

# Shortened copies of the markup on gundam-gcg.com (Nov. 2026).
INDEX_HTML = """
<li><a href="javascript:void(0);" data-val="616106">Stardust Trails [GD06]</a></li>
<li><a href="javascript:void(0);" data-val="616901">Promotion card</a></li>
<li><a href="javascript:void(0);" data-val="616003">Zeon&#039;s Rush [ST03]</a></li>
"""

LIST_HTML = """
<li class="cardItem"><a href="detail.php?detailSearch=GD06-002" class="cardStr">
  <img src="../images/common/loading.gif" data-src="../images/cards/card/GD06-002.webp?251111" alt="Zaku &amp; Co"></a></li>
<li class="cardItem"><a href="detail.php?detailSearch=GD06-002_p1" class="cardStr">
  <img src="../images/common/loading.gif" data-src="../images/cards/card/GD06-002_p1.webp?251111" alt="Zaku &amp; Co"></a></li>
"""

DETAIL_HTML = """
<div class="rarity">R
 +</div>
<div class="blockIcon">2</div>
<dl class="dataBox"><dt class="dataTit">Lv.</dt><dd class="dataTxt">4</dd></dl>
<dl class="dataBox"><dt class="dataTit">TYPE</dt><dd class="dataTxt">UNIT</dd></dl>
<dl class="dataBox"><dt class="dataTit">Source Title</dt><dd class="dataTxt isRegular">Mobile Suit Gundam</dd></dl>
<div class="cardDataRow overview">
  <div class="dataTxt isRegular">【Deploy】Draw 1.<br>(Line two)</div>
</div>
"""


class ScraperTest(unittest.TestCase):
    def test_packages(self):
        packages = parse_packages(INDEX_HTML)
        self.assertEqual(packages, {"616106": "Stardust Trails [GD06]", "616901": "Promotion card",
                                    "616003": "Zeon's Rush [ST03]"})
        self.assertEqual(split_package_label("Stardust Trails [GD06]"), ("Stardust Trails", "GD06"))
        self.assertEqual(split_package_label("Promotion card"), ("Promotion card", None))

    def test_card_list(self):
        self.assertEqual(parse_card_list(LIST_HTML), [
            ("GD06-002", "Zaku & Co", "../images/cards/card/GD06-002.webp"),
            ("GD06-002_p1", "Zaku & Co", "../images/cards/card/GD06-002_p1.webp"),
        ])

    def test_detail(self):
        d = parse_detail(DETAIL_HTML)
        self.assertEqual(d["rarity"], "R+")
        self.assertEqual(d["block"], "2")
        self.assertEqual(d["lv."], "4")
        self.assertEqual(d["type"], "UNIT")
        self.assertEqual(d["source title"], "Mobile Suit Gundam")
        self.assertEqual(d["effect"], "【Deploy】Draw 1.\n(Line two)")


if __name__ == "__main__":
    unittest.main()
