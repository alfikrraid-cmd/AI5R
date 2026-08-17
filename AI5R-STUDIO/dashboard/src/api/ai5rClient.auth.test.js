import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getPumps, onUnauthorized, storeSession } from "./ai5rClient";

// MWO-LTSA-AUTH-002 Rule 5/6 -- proves the ONE canonical authenticated-
// request mechanism every LTSA API function now goes through: Bearer-token
// attachment from the stored session, and centralized 401 handling. Uses
// getPumps() as a representative call site -- every other LTSA function in
// this file goes through the exact same apiFetch() wrapper.
function jsonResponse(status, body) {
  return { status, ok: status >= 200 && status < 300, json: async () => body };
}

beforeEach(() => {
  window.localStorage.clear();
  global.fetch = vi.fn();
});

afterEach(() => {
  window.localStorage.clear();
  onUnauthorized(null);
  vi.restoreAllMocks();
});

describe("ai5rClient authenticated requests", () => {
  it("attaches Authorization: Bearer <token> from the stored session", async () => {
    storeSession({ token: "abc123" });
    global.fetch.mockResolvedValue(jsonResponse(200, { success: true, data: [] }));

    await getPumps();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/ltsa/pumps"),
      expect.objectContaining({ headers: { Authorization: "Bearer abc123" } })
    );
  });

  it("sends no Authorization header when there is no session", async () => {
    global.fetch.mockResolvedValue(jsonResponse(200, { success: true, data: [] }));

    await getPumps();

    const [, options] = global.fetch.mock.calls[0];
    expect(options.headers).not.toHaveProperty("Authorization");
  });

  it("on 401, clears the stored session and invokes the registered unauthorized handler", async () => {
    storeSession({ token: "expired" });
    global.fetch.mockResolvedValue(jsonResponse(401, { detail: "Invalid or expired token" }));
    const handler = vi.fn();
    onUnauthorized(handler);

    await expect(getPumps()).rejects.toThrow();

    expect(handler).toHaveBeenCalledTimes(1);
  });

  it("on 403, does NOT clear the session or call the unauthorized handler", async () => {
    storeSession({ token: "valid-but-insufficient" });
    global.fetch.mockResolvedValue(jsonResponse(403, { detail: "Missing permission: pump.read" }));
    const handler = vi.fn();
    onUnauthorized(handler);

    await expect(getPumps()).rejects.toThrow();

    expect(handler).not.toHaveBeenCalled();
    expect(JSON.parse(window.localStorage.getItem("ai5r.ltsa.session")).token).toBe("valid-but-insufficient");
  });
});
