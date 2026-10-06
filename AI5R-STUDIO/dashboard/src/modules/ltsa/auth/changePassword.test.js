import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { changePassword, getSession } from "./authClient";
import { getStoredSession, storeSession } from "../../../api/ai5rClient";
import { passwordPolicyError } from "./passwordPolicy";

// LTSA_CHANGE_PASSWORD_FIRST_LOGIN_R2A -- authClient.changePassword and the
// must_change_password session mapping.
function jsonResponse(status, body) {
  return { status, ok: status >= 200 && status < 300, json: async () => body };
}

const IDENTITY = {
  id: "u-1",
  name: "New User",
  username: "new.user",
  email: "new.user@tap.internal",
  user: { id: "u-1", username: "new.user", name: "New User", email: "new.user@tap.internal" },
  organization: { id: "org-tap", code: "TAP", name: "TAP" },
  role: "TAP_ENGINEER",
  permissions: ["pump.read"],
  data_scope_type: null,
  data_scope_value: null,
};

beforeEach(() => {
  window.localStorage.clear();
  global.fetch = vi.fn();
  storeSession({ token: "old.token", user: { id: "u-1" }, must_change_password: true });
});

afterEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
});

describe("authClient.changePassword", () => {
  it("posts the current/new password with the stored token and stores the fresh session", async () => {
    global.fetch.mockResolvedValue(
      jsonResponse(200, { access_token: "fresh.token", token_type: "bearer", ...IDENTITY, must_change_password: false })
    );

    const session = await changePassword("Temp-Passw0rd-2026", "Chosen-Passw0rd-2026");

    const [url, options] = global.fetch.mock.calls[0];
    expect(url).toMatch(/\/api\/auth\/change-password$/);
    expect(options.method).toBe("POST");
    expect(options.headers.Authorization).toBe("Bearer old.token");
    expect(JSON.parse(options.body)).toEqual({ current_password: "Temp-Passw0rd-2026", new_password: "Chosen-Passw0rd-2026" });
    expect(session.token).toBe("fresh.token");
    expect(session.must_change_password).toBe(false);
    expect(getStoredSession().token).toBe("fresh.token");
    expect(JSON.stringify(getStoredSession())).not.toContain("Chosen-Passw0rd-2026");
  });

  it("a wrong current password (400) keeps the stored session", async () => {
    global.fetch.mockResolvedValue(jsonResponse(400, { detail: "Current password is incorrect" }));
    await expect(changePassword("Wrong-Passw0rd-2026", "Chosen-Passw0rd-2026")).rejects.toMatchObject({
      code: "incorrect_current_password",
    });
    expect(getStoredSession().token).toBe("old.token");
  });

  it.each([
    [422, "password_policy", "Password must be at least 12 characters"],
    [429, "rate_limited", "Too many incorrect attempts. Please try again later."],
    [409, "password_changed_elsewhere", "Password was changed by another request. Please sign in again."],
  ])("maps HTTP %s to %s with the backend detail", async (status, code, detail) => {
    global.fetch.mockResolvedValue(jsonResponse(status, { detail }));
    await expect(changePassword("Temp-Passw0rd-2026", "Chosen-Passw0rd-2026")).rejects.toMatchObject({ code, detail });
    expect(getStoredSession().token).toBe("old.token");
  });

  it("an expired session (401) clears the stored session", async () => {
    global.fetch.mockResolvedValue(jsonResponse(401, { detail: "Invalid or expired token" }));
    await expect(changePassword("Temp-Passw0rd-2026", "Chosen-Passw0rd-2026")).rejects.toMatchObject({ code: "unauthorized" });
    expect(getStoredSession()).toBeNull();
  });
});

describe("must_change_password session mapping", () => {
  it("getSession keeps the flag from GET /api/auth/me so a reload stays forced", async () => {
    global.fetch.mockResolvedValue(jsonResponse(200, { ...IDENTITY, must_change_password: true }));
    const session = await getSession();
    expect(session.must_change_password).toBe(true);
  });

  it("a payload without the flag is not forced", async () => {
    global.fetch.mockResolvedValue(jsonResponse(200, { ...IDENTITY }));
    const session = await getSession();
    expect(session.must_change_password).toBe(false);
  });
});

describe("passwordPolicy (client mirror)", () => {
  it.each([
    ["", "Please enter a new password."],
    ["           ", "Please enter a new password."],
    ["a".repeat(11), "at least 12"],
    ["a".repeat(129), "at most 128"],
    ["New.User", "at least 12"],
    ["New.User.Account", null],
  ])("passwordPolicyError(%j)", (password, expected) => {
    const result = passwordPolicyError(password);
    if (expected === null) {
      expect(result).toBeNull();
    } else {
      expect(result).toContain(expected);
    }
  });

  it("rejects the username and email, case-insensitively", () => {
    expect(passwordPolicyError("NEW.USER.ACCT", { username: "new.user.acct" })).toMatch(/username/);
    expect(passwordPolicyError("New.User@Tap.Internal", { email: "new.user@tap.internal" })).toMatch(/email/);
  });
});
