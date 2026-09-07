import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { activateWhatsAppGroup, registerWhatsAppGroup, storeSession } from "./ai5rClient";

// AI5R-WHATSAPP-GROUP-ADMIN-001 -- proves registerWhatsAppGroup/
// activateWhatsAppGroup go through the SAME canonical apiFetch()
// mechanism (Bearer-token attachment) every other LTSA API function
// uses, hit the exact existing backend routes, and surface backend
// errors (including a 403 with `.status` attached) the same way
// askCopilot()/_adminUsersRequest() already do. Uses only synthetic
// group ids -- never the real captured production JID.
function jsonResponse(status, body) {
  return { status, ok: status >= 200 && status < 300, json: async () => body };
}

beforeEach(() => {
  window.localStorage.clear();
  global.fetch = vi.fn();
  storeSession({ token: "test-admin-token" });
});

afterEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
});

describe("registerWhatsAppGroup", () => {
  it("POSTs to the admin/register endpoint with group_id and display_label", async () => {
    global.fetch.mockResolvedValue(
      jsonResponse(200, { success: true, data: { group_hash: "abc123hash", display_label: "Synthetic Group", status: "PENDING" } })
    );

    const result = await registerWhatsAppGroup({ groupId: "999999999@g.us", displayLabel: "Synthetic Group" });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/ltsa/whatsapp-group/admin/register"),
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ Authorization: "Bearer test-admin-token" }),
        body: JSON.stringify({ group_id: "999999999@g.us", display_label: "Synthetic Group" }),
      })
    );
    expect(result.data.status).toBe("PENDING");
  });

  it("throws with a readable message and .status on a non-ok response", async () => {
    global.fetch.mockResolvedValue(jsonResponse(403, { detail: "Missing permission: admin.users" }));

    await expect(registerWhatsAppGroup({ groupId: "999999999@g.us", displayLabel: "x" })).rejects.toMatchObject({
      message: "Missing permission: admin.users",
      status: 403,
    });
  });

  it("normalizes a Pydantic-style validation error array into a readable message", async () => {
    global.fetch.mockResolvedValue(
      jsonResponse(422, { detail: [{ loc: ["body", "display_label"], msg: "field required", type: "missing" }] })
    );

    await expect(registerWhatsAppGroup({ groupId: "999999999@g.us", displayLabel: "" })).rejects.toMatchObject({
      message: "field required",
    });
  });
});

describe("activateWhatsAppGroup", () => {
  it("POSTs to the admin/activate endpoint with group_hash", async () => {
    global.fetch.mockResolvedValue(
      jsonResponse(200, { success: true, data: { group_hash: "abc123hash", status: "ACTIVE" } })
    );

    const result = await activateWhatsAppGroup({ groupHash: "abc123hash" });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/ltsa/whatsapp-group/admin/activate"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ group_hash: "abc123hash", allowed_scope: null }),
      })
    );
    expect(result.data.status).toBe("ACTIVE");
  });

  it("surfaces a 404 (group not found) verbatim", async () => {
    global.fetch.mockResolvedValue(jsonResponse(404, { detail: "Group not found" }));

    await expect(activateWhatsAppGroup({ groupHash: "does-not-exist" })).rejects.toMatchObject({
      message: "Group not found",
      status: 404,
    });
  });
});
