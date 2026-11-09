// Keep the hosted-service permission distinct from public source inspection.
import { render, screen, within } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import PublicPolicyView from "./PublicPolicyView";

describe("Telaryn public Terms", () => {
  test("grants approved users hosted access without granting source reuse rights", () => {
    render(<PublicPolicyView policy="terms" onSignIn={vi.fn()} />);

    const serviceSection = screen.getByRole("heading", { name: "Permission to use the service" }).closest("section");
    expect(within(serviceSection).getByText(/permission to access and use the hosted Telaryn application/i)).toBeInTheDocument();
    expect(within(serviceSection).getByText(/does not grant a license to the underlying source code/i)).toBeInTheDocument();

    const ownershipSection = screen.getByRole("heading", { name: "Telaryn ownership and publicly visible code" }).closest("section");
    expect(within(ownershipSection).getByText(/may view and fork it through the permissions provided by GitHub/i)).toBeInTheDocument();
    expect(within(ownershipSection).getByText(/not an open-source license/i)).toBeInTheDocument();
    expect(within(ownershipSection).getByText(/does not claim exclusive copyright over general ideas or functionality/i)).toBeInTheDocument();
  });

  test("preserves the user's ownership of work submitted to Telaryn", () => {
    render(<PublicPolicyView policy="terms" onSignIn={vi.fn()} />);
    const section = screen.getByText("Your content").closest("section");
    expect(within(section).getByText(/You retain ownership of the content you submit/i)).toBeInTheDocument();
  });
});


describe("Telaryn public Privacy", () => {
  test("describes real retention triggers and closed-feedback periods", () => {
    render(<PublicPolicyView policy="privacy" onSignIn={vi.fn()} />);
    const section = screen.getByRole("heading", { name: "Retention" }).closest("section");
    expect(within(section).getByText(/access requests expire after 90 days/i)).toBeInTheDocument();
    expect(within(section).getByText(/a new access request triggers cleanup/i)).toBeInTheDocument();
    expect(within(section).getByText(/screenshots are eligible for removal 90 days after closure/i)).toBeInTheDocument();
    expect(within(section).getByText(/365 days after closure/i)).toBeInTheDocument();
    expect(within(section).getByText(/the administrative retention command performs this cleanup when run/i)).toBeInTheDocument();
    expect(within(section).getByText(/feedback that remains open is not covered/i)).toBeInTheDocument();
  });

  test("does not promise that screenshot pixels are redacted", () => {
    render(<PublicPolicyView policy="privacy" onSignIn={vi.fn()} />);
    expect(screen.getByText(/visible information in the image is not automatically redacted/i)).toBeInTheDocument();
  });
});
