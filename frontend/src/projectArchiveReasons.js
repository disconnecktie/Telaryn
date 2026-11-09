// Defines the shared archive classification vocabulary used by Project workflows.
export const ARCHIVE_REASONS = [
  { value: "completed", label: "Completed" },
  { value: "superseded", label: "Superseded" },
  { value: "cancelled", label: "Cancelled" },
  { value: "test_development", label: "Test / Development" },
  { value: "other", label: "Other" },
  { value: "unclassified", label: "Unclassified", legacy: true },
];

export function projectArchiveReasonValue(project) {
  return project.archive_reason || "unclassified";
}

export function projectArchiveReasonLabel(reason) {
  return ARCHIVE_REASONS.find((item) => item.value === (reason || "unclassified"))?.label
    || "Unclassified";
}
