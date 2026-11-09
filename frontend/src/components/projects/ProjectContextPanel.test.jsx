// Verifies that authored Project context remains safe plain text with visible paragraphs.
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import ProjectContextPanel from "./ProjectContextPanel";

describe("ProjectContextPanel long-form text", () => {
  test("preserves line breaks in Project purpose, rationale, and description", () => {
    render(<ProjectContextPanel project={{
      id: 1,
      life_context: "work",
      ai_context_enabled: true,
      purpose: "First purpose paragraph.\n\nSecond purpose paragraph.",
      why_it_matters: "Immediate need.\nSupporting context.",
      description: "Project scope.\n\n<script>plain text only</script>",
    }} />);

    expect(screen.getByText(/First purpose paragraph/)).toHaveClass("preserve-line-breaks");
    expect(screen.getByText(/Immediate need/)).toHaveClass("preserve-line-breaks");

    const description = screen.getByText(/Project scope/);
    expect(description).toHaveClass("preserve-line-breaks");
    expect(description.querySelector("script")).toBeNull();
  });
});
