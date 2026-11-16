"""Reads the official card list from https://www.gundam-gcg.com/en/cards/.

`index.php?package=<id>` returns all cards of one product in a single HTML page (pagination runs
only in the browser); package ids are the `data-val="6xxxxx"` entries of the search filter. Each
printing has a detail page `detail.php?detailSearch=<official id>` and an image
`images/cards/card/<official id>.webp` (600x837).

All HTTP responses are cached on disk, so a second run only fetches what is missing.
"""

import html
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from .ids import parse_id

BASE_URL = "https://www.gundam-gcg.com/en/cards/"
USER_AGENT = "GCGDB/0.1 (private hobby project)"

_OFFICIAL_ID_RE = re.compile(r"^[A-Z]+\d*-\d{3}(?:_p\d+)?$")


@dataclass
class Variant:
    """One printing as scraped (details only after fetch_details)."""

    official_id: str
    name: str
    image_path: str
    package_ids: set = field(default_factory=set)
    details: dict = field(default_factory=dict)

    @property
    def card_no(self) -> str:
        return parse_id(self.official_id).card_no

    @property
    def alt_index(self) -> int:
        return parse_id(self.official_id).alt

    @property
    def exburst_id(self) -> str:
        return parse_id(self.official_id).exburst_id

    @property
    def image_url(self) -> str:
        return urllib.parse.urljoin(BASE_URL, self.image_path)

    @property
    def image_file(self) -> str:
        return Path(self.image_path).name


class Fetcher:
    """HTTP GET with an on-disk cache and a fixed delay between requests."""

    def __init__(self, cache_dir: Path, delay: float = 0.5, refresh_lists: bool = False):
        self.cache_dir = Path(cache_dir)
        self.delay = delay
        self.refresh_lists = refresh_lists
        self._last_request = 0.0

    def get(self, url: str, cache_name: str, binary: bool = False, cacheable: bool = True):
        path = self.cache_dir / cache_name
        if path.exists() and cacheable:
            data = path.read_bytes()
        else:
            wait = self._last_request + self.delay - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read()
            self._last_request = time.monotonic()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return data if binary else data.decode("utf-8")


def clean_text(fragment: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", fragment)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def parse_packages(index_html: str) -> dict:
    """{package_id: label} from the search filter, e.g. '616106' -> 'Stardust Trails [GD06]'."""
    packages = {}
    for match in re.finditer(r'data-val="(6\d{5})"\s*>([^<]+)</a>', index_html):
        packages[match.group(1)] = html.unescape(match.group(2)).strip()
    return packages


def split_package_label(label: str) -> tuple:
    """'Stardust Trails [GD06]' -> ('Stardust Trails', 'GD06'); 'Promotion card' -> ('Promotion card', None)."""
    match = re.match(r"^(.*?)\s*\[([A-Za-z0-9]+)\]$", label)
    return (match.group(1), match.group(2)) if match else (label, None)


def parse_card_list(list_html: str) -> list:
    """[(official_id, name, image_path)] for every card tile on a list page."""
    items = re.findall(
        r'detailSearch=([^"]+)"[^>]*>\s*<img[^>]*data-src="([^"?]+)[^"]*"\s+alt="([^"]*)"',
        list_html,
    )
    return [(official_id, html.unescape(name), image) for official_id, image, name in items]


def parse_detail(detail_html: str) -> dict:
    """Fields of a detail page. Keys: rarity, block, effect and the lower-cased data titles
    (lv., cost, color, type, zone, trait, link, ap, hp, source title, where to get it)."""
    details = {}
    rarity = re.search(r'<div class="rarity">(.*?)</div>', detail_html, re.S)
    if rarity:
        details["rarity"] = re.sub(r"\s+", "", clean_text(rarity.group(1)))
    block = re.search(r'<div class="blockIcon">(.*?)</div>', detail_html, re.S)
    if block:
        details["block"] = clean_text(block.group(1))
    effect = re.search(r'<div class="cardDataRow overview">\s*<div class="dataTxt[^"]*">(.*?)</div>',
                       detail_html, re.S)
    if effect:
        details["effect"] = clean_text(effect.group(1))
    for title, value in re.findall(
        r'<dt class="dataTit">(.*?)</dt>\s*<dd class="dataTxt[^"]*">(.*?)</dd>', detail_html, re.S
    ):
        details[clean_text(title).lower()] = clean_text(value)
    return details


def fetch_packages(fetcher: Fetcher) -> dict:
    return parse_packages(fetcher.get(BASE_URL, "index.html", cacheable=not fetcher.refresh_lists))


def fetch_variants(fetcher: Fetcher, packages: dict, log=print) -> dict:
    """{official_id: Variant} over all packages; a printing in several products lists them all."""
    variants = {}
    for package_id, label in packages.items():
        list_html = fetcher.get(
            f"{BASE_URL}index.php?package={package_id}",
            f"lists/{package_id}.html",
            cacheable=not fetcher.refresh_lists,
        )
        tiles = parse_card_list(list_html)
        log(f"  {label}: {len(tiles)} cards")
        for official_id, name, image_path in tiles:
            if not _OFFICIAL_ID_RE.match(official_id):
                print(f"    WARNING: unexpected card id {official_id!r}, skipped", file=sys.stderr)
                continue
            variant = variants.get(official_id)
            if variant is None:
                variant = variants[official_id] = Variant(official_id, name, image_path)
            variant.package_ids.add(package_id)
    return variants


def fetch_details(fetcher: Fetcher, variants: dict, details: bool = True, images: bool = False, log=print):
    """Fills Variant.details from the detail pages and/or downloads the images to <cache>/images/."""
    todo = sorted(variants.values(), key=lambda v: v.official_id)
    for i, variant in enumerate(todo, 1):
        if details:
            detail_html = fetcher.get(
                f"{BASE_URL}detail.php?detailSearch={urllib.parse.quote(variant.official_id)}",
                f"details/{variant.official_id}.html",
            )
            variant.details = parse_detail(detail_html)
        if images:
            fetcher.get(variant.image_url, f"images/{variant.image_file}", binary=True)
        if i % 100 == 0 or i == len(todo):
            log(f"  {i}/{len(todo)}")
