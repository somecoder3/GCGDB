"""Card numbers and printing ids of the Gundam Card Game.

Three notations exist for the same printing:

    card number   GD06-002           one per card (all printings share it)
    official id   GD06-002_p1        gundam-gcg.com, "_pN" for alt arts
    ExBurst id    GD06-002-ALT1      exburst.dev, "-ALTN" for alt arts (primary key in the database)

The mapping between official and ExBurst ids is 1:1. Card numbers look like GD01-001, ST01-001,
EB01-001, T-001 (token), R-001 / RP-001 (resource), EXB-001 / EXBP-001, EXR-001 / EXRP-001.
"""

import re
from dataclasses import dataclass

# Set codes whose cards are not part of one booster or starter deck (tokens, resources, EX cards).
GENERAL_SETS = frozenset({"T", "R", "RP", "EXB", "EXBP", "EXR", "EXRP"})

_CARD_NO = r"(?P<set>[A-Z]+\d*)-(?P<number>\d{3})"
CARD_NO_RE = re.compile(rf"^{_CARD_NO}$")
_ANY_ID_RE = re.compile(rf"^{_CARD_NO}(?:(?:-ALT|_P)(?P<alt>\d+))?$")


@dataclass(frozen=True, order=True)
class CardId:
    """One printing: card number plus alt-art index (0 = base printing)."""

    card_no: str
    alt: int = 0

    @property
    def set_code(self) -> str:
        return set_code(self.card_no)

    @property
    def number(self) -> int:
        return int(self.card_no.rsplit("-", 1)[1])

    @property
    def exburst_id(self) -> str:
        return self.card_no if self.alt == 0 else f"{self.card_no}-ALT{self.alt}"

    @property
    def official_id(self) -> str:
        return self.card_no if self.alt == 0 else f"{self.card_no}_p{self.alt}"

    def __str__(self) -> str:
        return self.exburst_id


def parse_id(text: str) -> CardId:
    """Parse a card number, official id or ExBurst id (case-insensitive, surrounding spaces ignored).

    >>> parse_id("gd06-002_p1").exburst_id
    'GD06-002-ALT1'
    """
    match = _ANY_ID_RE.match(text.strip().upper())
    if not match:
        raise ValueError(f"not a Gundam Card Game card id: {text!r}")
    return CardId(f"{match['set']}-{match['number']}", int(match["alt"] or 0))


def is_card_id(text: str) -> bool:
    return _ANY_ID_RE.match(text.strip().upper()) is not None


def set_code(card_no: str) -> str:
    """Set code of a card number or id: GD06-002-ALT1 -> GD06, T-001 -> T."""
    return card_no.split("-", 1)[0].split("_", 1)[0].upper()


def to_exburst_id(text: str) -> str:
    return parse_id(text).exburst_id


def to_official_id(text: str) -> str:
    return parse_id(text).official_id
