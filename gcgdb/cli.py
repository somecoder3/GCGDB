"""Command line: python -m gcgdb <command> (or `gcgdb <command>` after pip install).

    python -m gcgdb build --details           # scrape gundam-gcg.com -> data/cards.db + data/cards.json
    python -m gcgdb build --details --images  # + card images to <cache>/images/
    python -m gcgdb build --details --refresh # after a new set: re-download the card lists
    python -m gcgdb export cards-pretty out.json
    python -m gcgdb info
    python -m gcgdb lookup GD06-002_p1
"""

import argparse
import sys
from pathlib import Path

from . import database, export, scraper
from .ids import parse_id

DEFAULT_CACHE = database.REPO_ROOT / "build" / "carddb-cache"
DEFAULT_JSON = database.REPO_ROOT / "data" / "cards.json"


def cmd_build(args):
    fetcher = scraper.Fetcher(args.cache, args.delay, args.refresh)
    print("Fetching package list ...")
    packages = scraper.fetch_packages(fetcher)
    print(f"Found {len(packages)} packages. Fetching card lists ...")
    variants = scraper.fetch_variants(fetcher, packages)
    print(f"Found {len(variants)} printings.")
    if args.details or args.images:
        scraper.fetch_details(fetcher, variants, details=args.details, images=args.images)
    elif args.out.exists():
        print("WARNING: without --details the database has no rarity, type, stats or effects.", file=sys.stderr)
    card_count = database.write_database(args.out, packages, variants)
    print(f"Wrote {card_count} cards / {len(variants)} printings to {args.out}")
    if args.json:
        size = export.write_export(args.out, "cards", args.json)
        print(f"Wrote {args.json} ({size / 1024:.0f} KB)")


def cmd_export(args):
    size = export.write_export(args.db, args.kind, args.out)
    print(f"Wrote {args.out} ({size / 1024:.0f} KB)")


def cmd_info(args):
    db = database.connect(args.db)
    for key, value in database.read_meta(db).items():
        print(f"{key}: {value}")
    print("sets:")
    for row in db.execute(
        """SELECT c.set_code, COUNT(DISTINCT c.card_no), COUNT(v.exburst_id)
           FROM card c JOIN variant v ON v.card_no = c.card_no GROUP BY c.set_code ORDER BY c.set_code"""
    ):
        print(f"  {row[0]:<5} {row[1]:>4} cards {row[2]:>4} printings")


def cmd_lookup(args):
    db = database.connect(args.db)
    for text in args.ids:
        card_id = parse_id(text)
        card = db.execute("SELECT * FROM card WHERE card_no = ?", (card_id.card_no,)).fetchone()
        if card is None:
            print(f"{text}: unknown card")
            continue
        print(f"{card['card_no']}  {card['name']}  ({card['type']}, {card['color']})")
        for v in db.execute("SELECT * FROM variant WHERE card_no = ? ORDER BY alt_index", (card_id.card_no,)):
            mark = "*" if v["alt_index"] == card_id.alt else " "
            packs = [r[0] for r in db.execute(
                "SELECT p.label FROM variant_package vp JOIN package p ON p.id = vp.package_id WHERE vp.exburst_id = ?",
                (v["exburst_id"],))]
            print(f" {mark} {v['exburst_id']:<16} {v['rarity'] or '':<5} {', '.join(packs)}")


def main(argv=None):
    # Card names and effects contain non-ASCII characters; show progress immediately in log files.
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    parser = argparse.ArgumentParser(prog="gcgdb", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="scrape the official card list into the database")
    build.add_argument("--out", type=Path, default=database.DEFAULT_DB)
    build.add_argument("--json", type=Path, default=DEFAULT_JSON, help="also write this JSON export")
    build.add_argument("--no-json", dest="json", action="store_const", const=None)
    build.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    build.add_argument("--details", action="store_true", help="fetch the detail page of every printing")
    build.add_argument("--images", action="store_true", help="download every card image")
    build.add_argument("--refresh", action="store_true", help="re-download the card lists (e.g. after a new set)")
    build.add_argument("--delay", type=float, default=0.5, help="seconds between requests")
    build.set_defaults(func=cmd_build)

    exp = sub.add_parser("export", help="write a JSON export of the database")
    exp.add_argument("kind", choices=sorted(export.EXPORTS))
    exp.add_argument("out", type=Path)
    exp.add_argument("--db", type=Path, default=database.DEFAULT_DB)
    exp.set_defaults(func=cmd_export)

    info = sub.add_parser("info", help="show build info and card counts per set")
    info.add_argument("--db", type=Path, default=database.DEFAULT_DB)
    info.set_defaults(func=cmd_info)

    lookup = sub.add_parser("lookup", help="show a card and all its printings")
    lookup.add_argument("ids", nargs="+")
    lookup.add_argument("--db", type=Path, default=database.DEFAULT_DB)
    lookup.set_defaults(func=cmd_lookup)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
