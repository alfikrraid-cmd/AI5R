import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ReportGeneratedOn from "./ReportGeneratedOn";

describe("ReportGeneratedOn", () => {
  it("renders the given date in ISO format", () => {
    render(<ReportGeneratedOn date={new Date("2026-07-20T00:00:00Z")} />);

    expect(screen.getByText("Generated: 2026-07-20")).toBeTruthy();
  });

  it("defaults to today's date when none is given", () => {
    render(<ReportGeneratedOn />);

    const today = new Date().toISOString().slice(0, 10);
    expect(screen.getByText(`Generated: ${today}`)).toBeTruthy();
  });
});
