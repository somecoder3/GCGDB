"""GCGDB: card database and tools for the Gundam Card Game (Python standard library only)."""

from .database import DEFAULT_DB, SCHEMA_VERSION, connect
from .ids import GENERAL_SETS, CardId, is_card_id, parse_id, set_code, to_exburst_id, to_official_id

__version__ = "0.1.0"
