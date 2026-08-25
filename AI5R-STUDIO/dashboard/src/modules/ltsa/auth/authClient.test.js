import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getSession, login, logout } from "./authClient";
import { getStoredSession } from "../../../api/ai5rClient";

// MWO-LTSA-AUTH-002 -- proves authClient.js against the REAL AUTH-001
// contract shape (routers/auth.py's own _identity_payload), with global
// fetch mocked (no live backend in this test run) -- production code
// itself contains no demo identities (Rule 2); only this test does.
function jsonResponse(status, body) {
  return { status, ok: status >= 200 && status < 300, json: async () => body };
}

beforeEach(() => {
  window.localStorage.clear();
  global.fetch = vi.fn();
});

afterEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
});

describe("authClient.login", () => {
  it("posts the exact AUTH-001 request shape and stores the real response shape", async () => {
    global.fetch.mockResolvedValue(
      jsonResponse(200, {
        access_token: "real.jwt.token",
        token_type: "bearer",
        user: { id: "u-1", email: "engineer@tap.internal" },
        organization: { id: "org-tap", code: "TAP" },
        role: "TAP_ENGINEER",
        permissions: ["pump.read", "seal.read"],
      })
    );

    const session = await login({ email: "engineer@tap.internal", password: "correct" });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/auth/login"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ identifier: "engineer@tap.internal", email: "engineer@tap.internal", password: "correct" }),
      })
    );
    expect(session.token).toBe("real.jwt.token");
    expect(session.role).toBe("TAP_ENGINEER");
    expect(session.permissions).toEqual(["pump.read", "seal.read"]);
    expect(session.organization.code).toBe("TAP");
    expect(getStoredSession()).toEqual(session);
  });


  it("posts username identifier while preserving the legacy email field contract", async () => {
    global.fetch.mockResolvedValue(
      jsonResponse(200, {
        access_token: "real.jwt.token",
        user: { id: "u-1", username: "ravi", email: null },
        organization: { id: "org-tap", code: "TAP" },
        role: "TAP_ENGINEER",
        permissions: ["pump.read"],
      })
    );

    const session = await login({ identifier: "ravi", password: "correct" });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/auth/login"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ identifier: "ravi", email: undefined, password: "correct" }),
      })
    );
    expect(session.user.name).toBe("ravi");
    expect(session.user.email).toBeNull();
  });
  it("maps a 401 (wrong password, unknown user, or disabled user) to invalid_credentials, never distinguishing them", async () => {
    global.fetch.mockResolvedValue(jsonResponse(401, { detail: "Invalid email or password" }));

    await expect(login({ email: "x@tap.internal", password: "wrong" })).rejects.toMatchObject({
      code: "invalid_credentials",
    });
  });

  it("maps a network failure to server_unavailable", async () => {
    global.fetch.mockRejectedValue(new TypeError("Failed to fetch"));

    await expect(login({ email: "x@tap.internal", password: "y" })).rejects.toMatchObject({
      code: "server_unavailable",
    });
  });

  it("never stores or exposes a password_hash or backend internals", async () => {
    global.fetch.mockResolvedValue(
      jsonResponse(200, {
        access_token: "t",
        user: { id: "u-1", email: "a@tap.internal" },
        organization: { id: "org-tap", code: "TAP" },
        role: "TAP_ADMIN",
        permissions: [],
      })
    );

    const session = await login({ email: "a@tap.internal", password: "x" });

    expect(JSON.stringify(session)).not.toMatch(/password_hash|scrypt\$/);
  });
});

describe("authClient.getSession", () => {
  it("returns null with no stored token, without ever calling the backend", async () => {
    const session = await getSession();
    expect(session).toBeNull();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("resolves identity from GET /api/auth/me with the stored Bearer token when a token exists", async () => {
    window.localStorage.setItem(
      "ai5r.ltsa.session",
      JSON.stringify({ token: "existing.token", user: {}, organization: {}, role: "TAP_ADMIN", permissions: [] })
    );
    global.fetch.mockResolvedValue(
      jsonResponse(200, {
        user: { id: "u-1", email: "a@tap.internal" },
        organization: { id: "org-tap", code: "TAP" },
        role: "TAP_ADMIN",
        permissions: ["admin.users"],
      })
    );

    const session = await getSession();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/auth/me"),
      expect.objectContaining({ headers: { Authorization: "Bearer existing.token" } })
    );
    expect(session.role).toBe("TAP_ADMIN");
    expect(session.permissions).toEqual(["admin.users"]);
  });

  it("clears the session and returns null on a 401 (expired/tampered token, or disabled membership)", async () => {
    window.localStorage.setItem(
      "ai5r.ltsa.session",
      JSON.stringify({ token: "stale.token", user: {}, organization: {}, role: "TAP_ADMIN", permissions: [] })
    );
    global.fetch.mockResolvedValue(jsonResponse(401, { detail: "Invalid or expired token" }));

    const session = await getSession();

    expect(session).toBeNull();
    expect(getStoredSession()).toBeNull();
  });
});

describe("authClient.logout", () => {
  it("clears the stored session", () => {
    window.localStorage.setItem("ai5r.ltsa.session", JSON.stringify({ token: "t" }));
    logout();
    expect(getStoredSession()).toBeNull();
  });
});
