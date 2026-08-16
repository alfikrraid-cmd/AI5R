import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import App, { PUMP_WORKSPACE_ROUTE } from "./App";

// MWO-LTSA-AUTH-OPEN-DESIGN-001 -- the LTSA application is now behind
// LTSAAuthGate, so reaching any LTSA route (including a direct deep link)
// requires signing in first. This mirrors the demo credentials in
// modules/ltsa/auth/authClient.js.
async function loginAsTapAdmin() {
  fireEvent.change(await screen.findByLabelText("Email"), { target: { value: "admin@tap.co.id" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "demo123" } });
  fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
  await screen.findByRole("heading", { name: "Pump Workspace" });
}

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  window.history.replaceState({}, "", "/");
  window.localStorage.clear();
});

describe("App", () => {
  it("renders the AI5ROS Landing by default", () => {
    render(<App />);

    expect(screen.getByRole("heading", { level: 1, name: "AI5ROS" })).toBeTruthy();
    expect(screen.getByRole("heading", { level: 3, name: "LTSA" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "AI5ROS" }).getAttribute("aria-selected")).toBe("true");
  });

  it("renders a navigation tab for LTSA", () => {
    render(<App />);

    expect(screen.getByRole("tab", { name: "LTSA" })).toBeTruthy();
  });

  it("shows LTSA sign-in, not the workspace, for an unauthenticated visitor", async () => {
    window.history.replaceState({}, "", PUMP_WORKSPACE_ROUTE);

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Pump Workspace" })).toBeNull();
  });

  it("opens the Pump Workspace route when the LTSA tab is clicked, after signing in", async () => {
    render(<App />);

    fireEvent.click(screen.getByRole("tab", { name: "LTSA" }));
    await loginAsTapAdmin();

    expect(window.location.pathname).toBe(PUMP_WORKSPACE_ROUTE);
    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
    expect(screen.queryByRole("heading", { level: 1, name: "AI5ROS" })).toBeNull();
  });

  it("registers the Pump Workspace as a directly reachable route, after signing in", async () => {
    window.history.replaceState({}, "", PUMP_WORKSPACE_ROUTE);

    render(<App />);
    await loginAsTapAdmin();

    expect(screen.getByRole("tab", { name: "LTSA" }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
  });

  it("registers /ltsa as the LTSA application entry route, after signing in", async () => {
    window.history.replaceState({}, "", "/ltsa");

    render(<App />);
    await loginAsTapAdmin();

    expect(screen.getByRole("tab", { name: "LTSA" }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
  });

  it("registers /ltsa/{organization} as an LTSA organization route, after signing in", async () => {
    window.history.replaceState({}, "", "/ltsa/tap");

    render(<App />);
    await loginAsTapAdmin();

    expect(screen.getByRole("tab", { name: "LTSA" }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
    expect(screen.queryByRole("heading", { level: 1, name: "AI5ROS" })).toBeNull();
  });

  it("switches back to the AI5ROS Landing when its tab is clicked again", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("tab", { name: "LTSA" }));
    fireEvent.click(screen.getByRole("tab", { name: "AI5ROS" }));

    expect(screen.getByRole("heading", { level: 1, name: "AI5ROS" })).toBeTruthy();
    expect(window.location.pathname).toBe("/");
    expect(screen.queryByRole("heading", { name: "Pump Workspace" })).toBeNull();
  });
});
