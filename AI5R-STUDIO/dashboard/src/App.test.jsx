import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App, { PUMP_WORKSPACE_ROUTE } from "./App";

// MWO-LTSA-AUTH-002 -- LTSAAuthGate's authClient now calls the real
// AUTH-001 backend (POST /api/auth/login); this suite mocks global fetch
// to return a real-shaped TAP_ADMIN identity for that one endpoint
// (Rule 2: production code has no demo identities, but a test fixture is
// fine), and falls through to a real fetch attempt for everything else,
// matching this suite's pre-existing behavior (LTSA data calls already
// hit real/absent endpoints in this test environment before this MWO;
// unchanged).
const TAP_ADMIN_LOGIN_RESPONSE = {
  access_token: "test.tap-admin.token",
  token_type: "bearer",
  user: { id: "u-tap-admin", email: "admin@tap.co.id" },
  organization: { id: "org-tap", code: "TAP" },
  role: "TAP_ADMIN",
  permissions: [
    "pump.read", "seal.read", "inventory.read", "maintenance.read", "maintenance.write",
    "condition.read", "drawing.read", "engineering_ai.ask", "import.read", "import.execute",
    "master.edit", "internal_inventory.read", "internal_component.read", "admin.users",
  ],
};

async function loginAsTapAdmin() {
  fireEvent.change(await screen.findByLabelText("Email"), { target: { value: "admin@tap.co.id" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "demo123" } });
  fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
  await screen.findByRole("heading", { name: "Pump Workspace" });
}

let realFetch;

beforeEach(() => {
  window.localStorage.clear();
  realFetch = global.fetch;
  global.fetch = vi.fn((url, options) => {
    if (String(url).includes("/api/auth/login")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => TAP_ADMIN_LOGIN_RESPONSE,
      });
    }
    return realFetch ? realFetch(url, options) : Promise.reject(new Error("no fetch"));
  });
});

afterEach(() => {
  window.history.replaceState({}, "", "/");
  window.localStorage.clear();
  global.fetch = realFetch;
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
