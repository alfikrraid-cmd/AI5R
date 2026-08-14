import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ExecutiveCard from "./ExecutiveCard";

const executive = {
  id: "raid",
  name: "Ra'id",
  role: "Chief Executive Officer",
  greeting: "Welcome, I'm Ra'id.",
};

describe("ExecutiveCard", () => {
  it("renders the executive's name, role, and Available status", () => {
    render(<ExecutiveCard executive={executive} />);

    expect(screen.getByRole("heading", { name: "Ra'id" })).toBeTruthy();
    expect(screen.getByText("Chief Executive Officer")).toBeTruthy();
    expect(screen.getByText("Available")).toBeTruthy();
  });

  it("does not show a greeting by default", () => {
    render(<ExecutiveCard executive={executive} />);

    expect(screen.queryByTestId("executive-greeting")).toBeNull();
  });

  it("shows the greeting when showGreeting is true", () => {
    render(<ExecutiveCard executive={executive} showGreeting />);

    expect(screen.getByTestId("executive-greeting").textContent).toBe("Welcome, I'm Ra'id.");
  });
});
