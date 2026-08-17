import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "./AuthContext";
import { onUnauthorized } from "../../../api/ai5rClient";

// MWO-LTSA-AUTH-002 Rule 4/6 -- AuthProvider's own `client` override
// (already present before this MWO) is the test seam here, so these use a
// fake client shaped exactly like the real authClient.js contract rather
// than mocking fetch a second time (already proven directly in
// authClient.test.js).
function Probe() {
  const { status, session } = useAuth();
  return <div data-testid="probe">{status}:{session?.role ?? "none"}</div>;
}

afterEach(() => {
  onUnauthorized(null);
  vi.restoreAllMocks();
});

describe("AuthProvider bootstrap", () => {
  it("reload with a valid token restores the session via the client's getSession (real /me path)", async () => {
    const client = {
      getSession: vi.fn().mockResolvedValue({ role: "TAP_ADMIN", permissions: ["admin.users"] }),
      login: vi.fn(),
      logout: vi.fn(),
    };

    render(
      <AuthProvider client={client}>
        <Probe />
      </AuthProvider>
    );

    await waitFor(() => expect(screen.getByTestId("probe")).toHaveTextContent("authenticated:TAP_ADMIN"));
    expect(client.getSession).toHaveBeenCalledTimes(1);
  });

  it("reload with an invalid/expired/disabled session (getSession resolves null) lands on unauthenticated", async () => {
    const client = {
      getSession: vi.fn().mockResolvedValue(null),
      login: vi.fn(),
      logout: vi.fn(),
    };

    render(
      <AuthProvider client={client}>
        <Probe />
      </AuthProvider>
    );

    await waitFor(() => expect(screen.getByTestId("probe")).toHaveTextContent("unauthenticated:none"));
  });

  it("a 401 from any protected request clears an authenticated session (Rule 6)", async () => {
    const client = {
      getSession: vi.fn().mockResolvedValue({ role: "TAP_ENGINEER", permissions: [] }),
      login: vi.fn(),
      logout: vi.fn(),
    };

    render(
      <AuthProvider client={client}>
        <Probe />
      </AuthProvider>
    );

    await waitFor(() => expect(screen.getByTestId("probe")).toHaveTextContent("authenticated:TAP_ENGINEER"));

    // Exercises the REAL apiFetch() 401 path (not a second mock of
    // AuthContext internals) -- proves the handler AuthProvider registered
    // on mount actually fires and updates React state, not just that
    // *a* handler was called (already proven directly in
    // ai5rClient.auth.test.js).
    global.fetch = vi.fn().mockResolvedValue({ status: 401, ok: false, json: async () => ({}) });
    const { getPumps } = await import("../../../api/ai5rClient");
    await expect(getPumps()).rejects.toThrow();

    await waitFor(() => expect(screen.getByTestId("probe")).toHaveTextContent("unauthenticated:none"));
  });
});
