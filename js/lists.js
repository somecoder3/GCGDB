// Card lists as text: export formats of other tools and a tolerant parser for pasted lists.
//
// An entry is { id, count, cardNo?, name? }: id is the ExBurst id (GD06-002-ALT1), cardNo and name
// are filled in from the id / a CardDB when missing (formats that need the name use them).

import { compareIds, ID_PATTERN, normalizeId, parseId } from "./ids.js";

// Formats in a sensible order for a selection list. Labels in a UI are the app's business.
export const LIST_FORMATS = [
  { id: "exburst", name: "ExBurst CSV", example: "Card No,Owned,Wanted,Trading,Tags\nGD06-004,2,0,0," },
  { id: "simple", name: "Simple", example: "2x GD06-004" },
  { id: "limitless", name: "Limitless", example: "2 Name GD06-004" },
  { id: "names", name: "Names only", example: "2x Name" },
  { id: "msa", name: "MSA Shuffle Fixer", example: "1 GD06-004 (one line per copy, shuffled)" },
  { id: "tts", name: "Tabletop Simulator", example: "// Main Deck\n2 x GD06-004 Name" },
];

// Fills cardNo and name; with a db (CardDB) the name comes from the database.
function complete(entries, db) {
  return entries.map((entry) => {
    const cardNo = entry.cardNo ?? parseId(entry.id)?.cardNo ?? entry.id;
    const name = entry.name ?? db?.card(cardNo)?.name ?? "";
    return { ...entry, cardNo, name };
  });
}

// Sums counts per key, keeping the first entry's fields; drops entries with count <= 0.
function sumBy(entries, key) {
  const result = new Map();
  for (const entry of entries) {
    const k = key(entry);
    const sum = result.get(k);
    if (sum) sum.count += entry.count;
    else result.set(k, { ...entry });
  }
  return [...result.values()].filter((entry) => entry.count > 0);
}

// The list as text, sorted by id. Options: db (CardDB, for names), random (for "msa", default Math.random).
export function formatList(entries, format, { db, random = Math.random } = {}) {
  const sorted = sumBy(complete(entries, db), (e) => e.id).sort((a, b) => compareIds(a.id, b.id));
  const lines = [];
  switch (format) {
    case "simple":
      for (const { id, count } of sorted) lines.push(`${count}x ${id}`);
      break;
    case "limitless":
      for (const { id, name, count } of sorted) lines.push(`${count} ${name} ${id}`);
      break;
    case "names":
      // Printings of one card (alt arts) share the name: one line per name.
      for (const { name, count } of sumBy(sorted, (e) => e.name)) lines.push(`${count}x ${name}`);
      break;
    case "msa": {
      // msafixer.com: one line per copy in random order; alt arts as their base card.
      const copies = [];
      for (const { cardNo, count } of sorted) for (let k = 0; k < count; k++) copies.push(`1 ${cardNo}`);
      for (let i = copies.length - 1; i > 0; i--) {
        const j = Math.floor(random() * (i + 1));
        [copies[i], copies[j]] = [copies[j], copies[i]];
      }
      lines.push(...copies);
      break;
    }
    case "tts":
      // Tabletop Simulator deck list; alt arts counted with their base card.
      lines.push("// Main Deck");
      for (const { cardNo, name, count } of sumBy(sorted, (e) => e.cardNo)) lines.push(`${count} x ${cardNo} ${name}`);
      break;
    case "exburst":
      lines.push("Card No,Owned,Wanted,Trading,Tags");
      for (const { id, count } of sorted) lines.push(`${id},${count},0,0,`);
      break;
    default:
      throw new Error(`unknown list format: ${format}`);
  }
  return lines.join("\n") + "\n";
}

// Parses a pasted list in any of LIST_FORMATS (and similar: "2 GD01-001", "GD01-001 x2", one id
// per line). Returns { entries: [{ id, count }], names: [{ name, count, line }], errors: [{ line, text }] }.
// entries are summed per id in order of first appearance. Lines with a count and a name but no id
// (the "names" format) land in names; resolve them with resolveNames(). Empty lines, "//" and "#"
// comments are skipped. ExBurst CSV: the Owned column counts.
export function parseList(text) {
  const entries = [], names = [], errors = [];
  const rows = String(text).replace(/^﻿/, "").split(/\r?\n/);
  let csv = null;
  rows.forEach((raw, i) => {
    const line = raw.trim();
    const number = i + 1;
    if (!line || line.startsWith("//") || line.startsWith("#")) return;
    if (/^card\s*no\s*,/i.test(line)) {
      csv = line.split(",").map((h) => h.trim().toLowerCase());
      return;
    }
    if (csv) {
      const cells = line.split(",").map((c) => c.trim());
      const id = normalizeId(cells[csv.indexOf("card no")] ?? "");
      const owned = csv.includes("owned") ? Number(cells[csv.indexOf("owned")]) : 1;
      if (id && Number.isInteger(owned) && owned >= 0) entries.push({ id, count: owned });
      else errors.push({ line: number, text: raw });
      return;
    }
    const ids = [...line.matchAll(ID_PATTERN)];
    // A trailing or leading count: "2x", "2 x", "x2", "2".
    const count = Number(/^(\d+)\s*x?\b/i.exec(line)?.[1] ?? /\bx\s*(\d+)$/i.exec(line)?.[1] ?? 1);
    if (ids.length === 1) {
      const id = normalizeId(ids[0][0]);
      if (id && count > 0) {
        entries.push({ id, count });
        return;
      }
    } else if (ids.length === 0) {
      const named = /^(\d+)\s*x?\s+(.+)$/i.exec(line);
      if (named) {
        names.push({ name: named[2].trim(), count: Number(named[1]), line: number });
        return;
      }
    }
    errors.push({ line: number, text: raw });
  });
  return { entries: sumBy(entries, (e) => e.id), names, errors };
}

// Maps names (from parseList) to base printings via a CardDB: exact name, case-insensitive.
// Returns { entries, unknown } where unknown keeps names that match no or several cards.
export function resolveNames(names, db) {
  const byName = new Map();
  for (const card of db.cards) {
    const key = card.name.toLowerCase();
    byName.set(key, byName.has(key) ? null : card);
  }
  const entries = [], unknown = [];
  for (const item of names) {
    const card = byName.get(item.name.toLowerCase());
    if (card) entries.push({ id: card.cardNo, count: item.count });
    else unknown.push(item);
  }
  return { entries: sumBy(entries, (e) => e.id), unknown };
}
