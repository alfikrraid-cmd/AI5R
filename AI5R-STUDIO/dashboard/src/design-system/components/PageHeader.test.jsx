import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PageHeader from "./PageHeader";

describe("PageHeader", () => {
  it("renders the title", () => {
    render(<PageHeader title="Command Center" />);

    expect(screen.getByRole("heading", { name: "Command Center" })).toBeTruthy();
  });

  it("renders an optional subtitle", () => {
    render(<PageHeader title="Command Center" subtitle="Operational overview" />);

    expect(screen.getByText("Operational overview")).toBeTruthy();
  });

  it("renders optional actions", () => {
    render(
      <PageHeader title="Command Center" actions={<button>Refresh</button>} />
    );

    expect(screen.getByRole("button", { name: "Refresh" })).toBeTruthy();
  });
});
