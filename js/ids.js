// Card numbers and printing ids of the Gundam Card Game (same rules as gcgdb/ids.py).
//
//   card number  GD06-002        one per card (all printings share it)
//   official id  GD06-002_p1     gundam-gcg.com, "_pN" for alt arts
//   ExBurst id   GD06-002-ALT1   exburst.dev, "-ALTN" for alt arts (the id used everywhere in GCGDB)

// Set codes whose cards are not part of one booster or starter deck (tokens, resources, EX cards).
export const GENERAL_SETS = new Set(["T", "R", "RP", "EXB", "EXBP", "EXR", "EXRP"]);

const ANY_ID = /^([A-Z]+\d*)-(\d{3})(?:(?:-ALT|_P)(\d+))?$/;

// Matches an id inside free text (lists, OCR output); use with normalizeId().
export const ID_PATTERN = /\b[A-Za-z]+\d*-\d{3}(?:-ALT\d+|_p\d+)?\b/g;

// { cardNo, set, number, alt, id, officialId } or null if the text is not a card id.
// Accepts card numbers, official and ExBurst ids, case-insensitive.
export function parseId(text) {
  const match = ANY_ID.exec(String(text).trim().toUpperCase());
  if (!match) return null;
  const [, set, digits, altText] = match;
  const cardNo = `${set}-${digits}`;
  const alt = altText ? Number(altText) : 0;
  return {
    cardNo,
    set,
    number: Number(digits),
    alt,
    id: alt ? `${cardNo}-ALT${alt}` : cardNo,
    officialId: alt ? `${cardNo}_p${alt}` : cardNo,
  };
}

export const isCardId = (text) => parseId(text) !== null;

// ExBurst id of any notation, or null.
export const normalizeId = (text) => parseId(text)?.id ?? null;

export const toOfficialId = (text) => parseId(text)?.officialId ?? null;

// GD06-002-ALT1 -> GD06, T-001 -> T.
export const setOf = (id) => String(id).toUpperCase().split(/[-_]/, 1)[0];

// Card number of a printing id: GD06-002-ALT1 -> GD06-002.
export const cardNoOf = (id) => parseId(id)?.cardNo ?? null;

// Sort order for ids: by card number, then alt index numerically (ALT2 before ALT10).
export function compareIds(a, b) {
  const pa = parseId(a), pb = parseId(b);
  if (!pa || !pb) return String(a).localeCompare(String(b));
  if (pa.cardNo !== pb.cardNo) return pa.cardNo < pb.cardNo ? -1 : 1;
  return pa.alt - pb.alt;
}
