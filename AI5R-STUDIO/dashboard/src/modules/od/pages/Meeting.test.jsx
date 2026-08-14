import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Meeting from "./Meeting";

describe("Meeting page", () => {
  it("renders every executive with their greeting", () => {
    render(<Meeting />);

    expect(screen.getByRole("heading", { name: "Meeting" })).toBeTruthy();
    ["Ra'id", "Graham", "Aurora", "Atlas", "Sophia"].forEach((name) => {
      expect(screen.getByRole("heading", { name })).toBeTruthy();
    });
    expect(screen.getAllByTestId("executive-greeting")).toHaveLength(5);
  });
});
