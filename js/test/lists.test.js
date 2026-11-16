import assert from "node:assert/strict";
import { test } from "node:test";
import { formatList, LIST_FORMATS, parseList, resolveNames } from "../lists.js";

const entries = [
  { id: "GD06-004", name: "Zaku", count: 2 },
  { id: "GD05-123-ALT1", name: "Gundam", count: 1 },
  { id: "GD05-123", name: "Gundam", count: 1 },
];

test("ExBurst CSV", () => {
  assert.equal(formatList(entries, "exburst"),
    "Card No,Owned,Wanted,Trading,Tags\nGD05-123,1,0,0,\nGD05-123-ALT1,1,0,0,\nGD06-004,2,0,0,\n");
});

test("simple, limitless, names", () => {
  assert.equal(formatList(entries, "simple"), "1x GD05-123\n1x GD05-123-ALT1\n2x GD06-004\n");
  assert.equal(formatList(entries, "limitless"), "1 Gundam GD05-123\n1 Gundam GD05-123-ALT1\n2 Zaku GD06-004\n");
  assert.equal(formatList(entries, "names"), "2x Gundam\n2x Zaku\n");
});

test("tabletop simulator counts alt arts with their base card", () => {
  assert.equal(formatList(entries, "tts"), "// Main Deck\n2 x GD05-123 Gundam\n2 x GD06-004 Zaku\n");
});

test("msa: one line per copy, shuffled", () => {
  const text = formatList(entries, "msa", { random: () => 0 });
  assert.deepEqual(text.trim().split("\n").sort(), ["1 GD05-123", "1 GD05-123", "1 GD06-004", "1 GD06-004"]);
});

test("same id twice is summed, unknown format throws", () => {
  assert.equal(formatList([{ id: "T-001", count: 1 }, { id: "T-001", count: 2 }], "simple"), "3x T-001\n");
  assert.throws(() => formatList(entries, "nope"));
  assert.equal(new Set(LIST_FORMATS.map((f) => f.id)).size, LIST_FORMATS.length);
});

test("every format round-trips through parseList (except names)", () => {
  for (const { id } of LIST_FORMATS) {
    if (id === "names") continue;
    const parsed = parseList(formatList(entries, id));
    assert.deepEqual(parsed.errors, [], id);
    const total = parsed.entries.reduce((sum, e) => sum + e.count, 0);
    assert.equal(total, 4, id);
  }
  assert.deepEqual(parseList(formatList(entries, "simple")).entries,
    [{ id: "GD05-123", count: 1 }, { id: "GD05-123-ALT1", count: 1 }, { id: "GD06-004", count: 2 }]);
});

test("parses loose lists", () => {
  const { entries: parsed, names, errors } = parseList([
    "﻿# my deck",
    "2 gd01-001",
    "GD01-002_p1",
    "GD01-003 x3",
    "4 Zaku II",
    "",
    "// sideboard",
    "1x GD01-001",
    "what is this",
    "0 GD01-004",
  ].join("\r\n"));
  assert.deepEqual(parsed, [{ id: "GD01-001", count: 3 }, { id: "GD01-002-ALT1", count: 1 }, { id: "GD01-003", count: 3 }]);
  assert.deepEqual(names, [{ name: "Zaku II", count: 4, line: 5 }]);
  assert.deepEqual(errors.map((e) => e.line), [9, 10]);
});

test("ExBurst CSV uses the Owned column", () => {
  const { entries: parsed, errors } = parseList("Card No,Owned,Wanted,Trading,Tags\nGD05-123-ALT1,2,1,0,\nGD06-004,0,3,0,\nbroken,,\n");
  assert.deepEqual(parsed, [{ id: "GD05-123-ALT1", count: 2 }]);
  assert.equal(errors.length, 1);
});

test("resolveNames", () => {
  const db = { cards: [{ cardNo: "GD06-004", name: "Zaku" }, { cardNo: "GD01-001", name: "Twin" }, { cardNo: "GD02-001", name: "Twin" }] };
  const { entries: resolved, unknown } = resolveNames([{ name: "zaku", count: 2 }, { name: "Twin", count: 1 }, { name: "None", count: 1 }], db);
  assert.deepEqual(resolved, [{ id: "GD06-004", count: 2 }]);
  assert.deepEqual(unknown.map((u) => u.name), ["Twin", "None"]);
});
