// Defines explicit user-owned Project reporting contexts and display labels.
export const PROJECT_LIFE_CONTEXTS = [
  { value: "unclassified", label: "Unclassified" },
  { value: "work", label: "Work" },
  { value: "volunteer", label: "Volunteer" },
  { value: "personal", label: "Personal" },
];

export function projectLifeContextLabel(value) {
  return PROJECT_LIFE_CONTEXTS.find((context) => context.value === value)?.label
    || "Unclassified";
}
