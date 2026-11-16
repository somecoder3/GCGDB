import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import { CardDB } from "../carddb.js";

// The committed export of the real database.
const db = new CardDB(JSON.parse(await readFile(new URL("../../data/cards.json", import.meta.url), "utf8")));

test("counts match the meta data", () => {
  assert.equal(db.cards.length, Number(db.meta.card_count));
  assert.equal(db.variants.length, Number(db.meta.variant_count));
});

test("looks up printings in any notation", () => {
  const variant = db.variant("gd01-118_p8");
  assert.equal(variant.id, "GD01-118-ALT8");
  assert.equal(variant.card.cardNo, "GD01-118");
  assert.equal(variant.name, variant.card.name);
  assert.equal(db.variant("GD01-999"), undefined);
  assert.equal(db.variant("nonsense"), undefined);
});

test("cards list their printings in alt order", () => {
  const variants = db.variantsOf("GD01-118-ALT3");
  assert.equal(variants.length, 9);
  assert.deepEqual(variants.map((v) => v.alt), [0, 1, 2, 3, 4, 5, 6, 7, 8]);
  for (const card of db.cards) assert.ok(card.variants.length >= 1, card.cardNo);
});

test("every printing references known packages", () => {
  for (const variant of db.variants) {
    assert.ok(variant.packages.length >= 1, variant.id);
    assert.equal(db.packagesOf(variant.id).length, variant.packages.length);
  }
  assert.deepEqual(db.packagesOf("GD06-001").map((p) => p.code), ["GD06"]);
});

test("sets", () => {
  const sets = db.sets();
  assert.ok(sets.some((s) => s.set === "GD01" && s.cards === 130 && !s.general));
  assert.ok(sets.some((s) => s.set === "T" && s.general));
  assert.equal(sets.reduce((sum, s) => sum + s.cards, 0), db.cards.length);
});

test("name search", () => {
  const hits = db.searchByName("astray red");
  assert.ok(hits.length > 0);
  assert.ok(hits.every((card) => /astray/i.test(card.name) && /red/i.test(card.name)));
  assert.deepEqual(db.searchByName("  "), []);
});

test("rejects newer schema versions", () => {
  assert.throws(() => new CardDB({ schema: 99, packages: [], cards: [], variants: [] }));
});
