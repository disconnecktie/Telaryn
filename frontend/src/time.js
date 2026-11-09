// Timestamp values are UTC instants; the browser's configured zone controls display.
export function formatLocalDateTime(
  value,
  {
    locale,
    timeZone,
    dateStyle = "medium",
    timeStyle = "short",
  } = {},
) {
  if (!value) return "Unknown time";

  return new Intl.DateTimeFormat(locale, {
    dateStyle,
    timeStyle,
    ...(timeZone ? { timeZone } : {}),
  }).format(new Date(value));
}
