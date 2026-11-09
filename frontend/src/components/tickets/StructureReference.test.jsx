// Protects stable persisted references and honest unsaved-item presentation.
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import StructureReference from "./StructureReference";

test("renders a copyable persisted nested-work reference", () => {
  render(
    <StructureReference
      prefix="ST"
      id={416}
      itemName="Subtask"
    />,
  );

  expect(
    screen.getByLabelText("Subtask reference ST-416"),
  ).toHaveTextContent("ST-416");
});

test("does not invent a permanent reference for an unsaved item", () => {
  render(
    <StructureReference
      prefix="AC"
      id={null}
      itemName="Acceptance criterion"
    />,
  );

  expect(
    screen.getByLabelText(
      "New Acceptance criterion; a permanent reference will be assigned after save",
    ),
  ).toHaveTextContent("NEW");
  expect(screen.queryByText(/AC-/)).not.toBeInTheDocument();
});
