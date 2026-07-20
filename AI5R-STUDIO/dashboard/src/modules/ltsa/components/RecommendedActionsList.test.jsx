import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import RecommendedActionsList from "./RecommendedActionsList";

const ACTIONS = [
  { id: "overdue-pm", severity: "danger", text: "Schedule 3 overdue preventive maintenance tasks." },
  { id: "wo-backlog", severity: "info", text: "Clear the work order backlog — 7 open versus 1 closed." },
];

describe("RecommendedActionsList", () => {
  it("renders every recommended action with its severity badge", () => {
    render(<RecommendedActionsList actions={ACTIONS} />);

    expect(screen.getByRole("heading", { name: "Recommended Actions" })).toBeTruthy();
    expect(screen.getByText("Schedule 3 overdue preventive maintenance tasks.")).toBeTruthy();
    expect(screen.getByText("Clear the work order backlog — 7 open versus 1 closed.")).toBeTruthy();
    expect(screen.getByText("DANGER")).toBeTruthy();
    expect(screen.getByText("INFO")).toBeTruthy();
  });

  it("renders a reassuring empty state when there are no recommended actions", () => {
    render(<RecommendedActionsList actions={[]} />);

    expect(screen.getByText(/no immediate actions required/i)).toBeTruthy();
  });
});
