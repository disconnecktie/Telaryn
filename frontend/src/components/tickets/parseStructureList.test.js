// Keep bulk entry tolerant of common pasted list formats without changing text intent.
import { describe, expect, test } from "vitest";

import { appendUniqueStructureItems, parseStructureList } from "./parseStructureList";

describe("parseStructureList", () => {
  test("turns pasted lines into clean, unique items", () => {
    expect(parseStructureList(`
      - First criterion
      2. Second criterion, including a comma
      [x] Third criterion
      first criterion
    `)).toEqual([
      "First criterion",
      "Second criterion, including a comma",
      "Third criterion",
    ]);
  });

  test("accepts spreadsheet tabs as item boundaries", () => {
    expect(parseStructureList("First\tSecond\tThird")).toEqual([
      "First",
      "Second",
      "Third",
    ]);
  });
});

describe("appendUniqueStructureItems", () => {
  test("omits items already present in the draft", () => {
    const existing = [{ title: "Already there" }];
    expect(appendUniqueStructureItems(
      existing,
      ["already there", "New item"],
      (item) => item.title,
    )).toEqual(["New item"]);
  });
});
