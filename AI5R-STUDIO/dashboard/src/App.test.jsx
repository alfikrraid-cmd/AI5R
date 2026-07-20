import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("App", () => {
  it("renders the OS Command Center by default, preserving existing behavior", () => {
    render(<App />);

    expect(screen.getByRole("heading", { level: 1, name: /AI5R OS COMMAND CENTER/i })).toBeTruthy();
    expect(screen.getByRole("heading", { level: 3, name: "System" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "OS Command Center" }).getAttribute("aria-selected")).toBe(
      "true"
    );
  });

  it("renders a navigation tab for LTSA", () => {
    render(<App />);

    expect(screen.getByRole("tab", { name: "LTSA" })).toBeTruthy();
  });

  it("switches to the LTSA workspace when its tab is clicked", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("tab", { name: "LTSA" }));

    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
    expect(screen.queryByRole("heading", { level: 3, name: "System" })).toBeNull();
  });

  it("switches back to the OS Command Center when its tab is clicked again", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("tab", { name: "LTSA" }));
    fireEvent.click(screen.getByRole("tab", { name: "OS Command Center" }));

    expect(screen.getByRole("heading", { level: 3, name: "System" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Pump Workspace" })).toBeNull();
  });
});
