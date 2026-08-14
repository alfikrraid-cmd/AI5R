import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import SuggestedActionsPanel from "./SuggestedActionsPanel";

describe("SuggestedActionsPanel", () => {
  it("renders exactly three suggested actions", () => {
    render(<SuggestedActionsPanel onNavigate={() => {}} />);

    expect(screen.getAllByRole("button")).toHaveLength(3);
  });

  it("navigates to studio, meeting, and presentation respectively", () => {
    const onNavigate = vi.fn();
    render(<SuggestedActionsPanel onNavigate={onNavigate} />);

    fireEvent.click(screen.getByRole("button", { name: "Bring your first ask to the company" }));
    expect(onNavigate).toHaveBeenCalledWith("studio");

    fireEvent.click(screen.getByRole("button", { name: "Meet your executives" }));
    expect(onNavigate).toHaveBeenCalledWith("meeting");

    fireEvent.click(screen.getByRole("button", { name: "Review your Business Blueprint" }));
    expect(onNavigate).toHaveBeenCalledWith("presentation");
  });
});
