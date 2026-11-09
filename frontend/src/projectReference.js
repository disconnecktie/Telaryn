// Formats the workspace-scoped Project number as an intentional human work key.
export function localProjectReference(project) {
  const number = project?.workspace_project_number;
  return Number.isInteger(number) && number > 0
    ? `PRJ-${String(number).padStart(3, "0")}`
    : "PRJ-???";
}
