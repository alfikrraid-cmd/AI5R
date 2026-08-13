import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import App, { PUMP_WORKSPACE_ROUTE } from "./App";

afterEach(() => {
  window.history.replaceState({}, "", "/");
});

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

  it("opens the Pump Workspace route when the LTSA tab is clicked", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("tab", { name: "LTSA" }));

    expect(window.location.pathname).toBe(PUMP_WORKSPACE_ROUTE);
    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
    expect(screen.queryByRole("heading", { level: 3, name: "System" })).toBeNull();
  });

  it("registers the Pump Workspace as a directly reachable route", () => {
    window.history.replaceState({}, "", PUMP_WORKSPACE_ROUTE);

    render(<App />);

    expect(screen.getByRole("tab", { name: "LTSA" }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
  });

  it("registers /ltsa as the LTSA application entry route", () => {
    window.history.replaceState({}, "", "/ltsa");

    render(<App />);

    expect(screen.getByRole("tab", { name: "LTSA" }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
  });

  it("switches back to the OS Command Center when its tab is clicked again", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("tab", { name: "LTSA" }));
    fireEvent.click(screen.getByRole("tab", { name: "OS Command Center" }));

    expect(screen.getByRole("heading", { level: 3, name: "System" })).toBeTruthy();
    expect(window.location.pathname).toBe("/");
    expect(screen.queryByRole("heading", { name: "Pump Workspace" })).toBeNull();
  });
});
