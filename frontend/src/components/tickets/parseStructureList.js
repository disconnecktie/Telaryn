// Parse pasted lists without treating punctuation inside normal prose as a
// delimiter. Newlines and spreadsheet tabs are safe, predictable boundaries.
export function parseStructureList(value) {
  const seen = new Set();
  return String(value)
    .split(/\r?\n|\t/)
    .map((item) => item
      .trim()
      .replace(/^(?:[-*•]+|\d+[.)]|\[[ xX]\])\s*/, "")
      .trim())
    .filter((item) => {
      if (!item) return false;
      const key = item.toLocaleLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

export function appendUniqueStructureItems(existing, incoming, getText) {
  const keys = new Set(existing.map((item) => getText(item).toLocaleLowerCase()));
  return incoming.filter((item) => {
    const key = item.toLocaleLowerCase();
    if (keys.has(key)) return false;
    keys.add(key);
    return true;
  });
}
