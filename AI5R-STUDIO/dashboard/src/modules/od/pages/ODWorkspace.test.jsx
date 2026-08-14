import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ODWorkspace from "./ODWorkspace";

function fillAndContinue(labelText, value) {
  fireEvent.change(screen.getByLabelText(labelText), { target: { value } });
  fireEvent.click(screen.getByRole("button", { name: "Continue" }));
}

function completeOpenDesign() {
  fillAndContinue("Mission Input", "help me run my pump maintenance business");
  fillAndContinue("Who is this business, and what industry are you in?", "a pump maintenance company");
  fillAndContinue("What does success look like once this is working?", "no more missed service calls");
  fireEvent.click(screen.getByRole("button", { name: "Confirm & Seal Blueprint" }));
}

describe("ODWorkspace — MWO-OD-001 end-to-end prototype", () => {
  it("1. enters Reception first", () => {
    render(<ODWorkspace />);

    expect(screen.getByRole("heading", { name: "Welcome to your AI Company" })).toBeTruthy();
  });

  it("2-3. completes Open Design and generates a mock Business Blueprint", () => {
    render(<ODWorkspace />);

    fireEvent.click(screen.getByRole("button", { name: "Begin Open Design" }));
    expect(screen.getByLabelText("Mission Input")).toBeTruthy();

    completeOpenDesign();

    // 4. lands in Company Headquarters
    expect(screen.getByRole("heading", { name: "a pump maintenance company" })).toBeTruthy();
  });

  it("5. receives the Executive Briefing on first entry to Headquarters", () => {
    render(<ODWorkspace />);

    fireEvent.click(screen.getByRole("button", { name: "Begin Open Design" }));
    completeOpenDesign();

    expect(screen.getByRole("heading", { name: "Executive Briefing" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("heading", { name: "Executive Briefing" })).toBeNull();
  });

  it("6. navigates between Headquarters, Studio, Meeting and Presentation", () => {
    render(<ODWorkspace />);

    fireEvent.click(screen.getByRole("button", { name: "Begin Open Design" }));
    completeOpenDesign();
    fireEvent.click(screen.getByRole("button", { name: "Close" }));

    expect(screen.getByRole("tab", { name: "Headquarters" })).toBeTruthy();

    fireEvent.click(screen.getByRole("tab", { name: "Studio" }));
    expect(screen.getByRole("heading", { name: "Open Design" })).toBeTruthy();

    fireEvent.click(screen.getByRole("tab", { name: "Meeting" }));
    expect(screen.getByRole("heading", { name: "Meeting" })).toBeTruthy();

    fireEvent.click(screen.getByRole("tab", { name: "Presentation" }));
    expect(screen.getByRole("heading", { name: "Business Blueprint" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "a pump maintenance company" })).toBeTruthy();

    fireEvent.click(screen.getByRole("tab", { name: "Headquarters" }));
    expect(screen.getByRole("heading", { name: "a pump maintenance company" })).toBeTruthy();
  });
});
