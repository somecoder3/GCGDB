// Read access to data/cards.json (written by `python -m gcgdb build` / `gcgdb export cards`).
//
//   const db = await CardDB.load(new URL("../gcgdb/data/cards.json", import.meta.url));
//   db.variant("GD06-002_p1")   // -> { id, officialId, cardNo, alt, rarity, block, image, packages, card }
//   db.card("GD06-002").variants

import { GENERAL_SETS, parseId } from "./ids.js";

export const SUPPORTED_SCHEMA = 2;

export class CardDB {
  constructor(doc) {
    if (!doc || doc.schema > SUPPORTED_SCHEMA) throw new Error(`unsupported cards.json schema ${doc?.schema}`);
    this.meta = doc.meta ?? {};
    this.packages = doc.packages;
    this.cards = doc.cards;
    this.variants = doc.variants;
    this.packageById = new Map(this.packages.map((p) => [p.id, p]));
    this.cardByNo = new Map();
    for (const card of this.cards) this.cardByNo.set(card.cardNo, { ...card, variants: [] });
    this.cards = [...this.cardByNo.values()];
    this.variantById = new Map();
    this.variants = this.variants.map((v) => {
      const card = this.cardByNo.get(v.cardNo);
      // name is repeated on the variant because most consumers only look at printings.
      const variant = { ...v, name: card?.name ?? "", card };
      card?.variants.push(variant);
      this.variantById.set(v.id, variant);
      return variant;
    });
    for (const card of this.cards) card.variants.sort((a, b) => a.alt - b.alt);
  }

  static async load(url, fetchOptions) {
    const response = await fetch(url, fetchOptions);
    if (!response.ok) throw new Error(`loading ${url}: HTTP ${response.status}`);
    return new CardDB(await response.json());
  }

  // Printing by any id notation (GD06-002, GD06-002_p1, gd06-002-alt1), or undefined.
  variant(id) {
    const parsed = parseId(id);
    return parsed ? this.variantById.get(parsed.id) : undefined;
  }

  // Card by card number or any printing id of it, or undefined.
  card(id) {
    const parsed = parseId(id);
    return parsed ? this.cardByNo.get(parsed.cardNo) : undefined;
  }

  // All printings (base card and alt arts) of the card an id belongs to, by alt index.
  variantsOf(id) {
    return this.card(id)?.variants ?? [];
  }

  // Set codes in sort order with counts, e.g. [{ set: "GD01", cards: 130, general: false }, ...].
  sets() {
    const counts = new Map();
    for (const card of this.cards) counts.set(card.set, (counts.get(card.set) ?? 0) + 1);
    return [...counts].sort(([a], [b]) => a.localeCompare(b))
      .map(([set, cards]) => ({ set, cards, general: GENERAL_SETS.has(set) }));
  }

  cardsOfSet(set) {
    return this.cards.filter((card) => card.set === set);
  }

  // Products a printing is in: [{ id, code, name, label }].
  packagesOf(id) {
    return (this.variant(id)?.packages ?? []).map((p) => this.packageById.get(p)).filter(Boolean);
  }

  // Simple case-insensitive search over card names (all words must occur).
  searchByName(query) {
    const words = String(query).toLowerCase().split(/\s+/).filter(Boolean);
    if (!words.length) return [];
    return this.cards.filter((card) => {
      const name = card.name.toLowerCase();
      return words.every((word) => name.includes(word));
    });
  }
}
