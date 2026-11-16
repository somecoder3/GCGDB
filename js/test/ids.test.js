import assert from "node:assert/strict";
import { test } from "node:test";
import { cardNoOf, compareIds, isCardId, normalizeId, parseId, setOf, toOfficialId } from "../ids.js";

test("parses every notation", () => {
  for (const text of ["GD06-002_p1", "GD06-002-ALT1", " gd06-002-alt1 ", "gd06-002_P1"]) {
    assert.deepEqual(parseId(text), {
      cardNo: "GD06-002", set: "GD06", number: 2, alt: 1, id: "GD06-002-ALT1", officialId: "GD06-002_p1",
    });
  }
  assert.equal(normalizeId("T-001"), "T-001");
  assert.equal(toOfficialId("ST01-001-ALT8"), "ST01-001_p8");
  assert.equal(cardNoOf("EXBP-027-ALT1"), "EXBP-027");
});

test("set codes", () => {
  assert.equal(setOf("GD06-002-ALT1"), "GD06");
  assert.equal(setOf("rp-001_p1"), "RP");
  assert.equal(setOf("T-001"), "T");
});

test("rejects non-ids", () => {
  for (const text of ["", "GD06", "GD06-02", "GD06-0021", "GD06-002-ALT", "06-002", null]) {
    assert.equal(isCardId(text), false, String(text));
    assert.equal(normalizeId(text), null);
  }
});

test("sorts alt indexes numerically", () => {
  const ids = ["GD01-002", "GD01-001-ALT10", "GD01-001-ALT2", "GD01-001", "EB01-001"];
  assert.deepEqual(ids.sort(compareIds), ["EB01-001", "GD01-001", "GD01-001-ALT2", "GD01-001-ALT10", "GD01-002"]);
});
