import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { activateWhatsAppNumber, registerWhatsAppNumber, storeSession } from "./ai5rClient";

// AI5R-WHATSAPP-SENDER-ADMIN-001 -- proves registerWhatsAppNumber/
// activateWhatsAppNumber go through the SAME canonical apiFetch()
// mechanism every other LTSA API function uses, hit the exact existing
// routers/admin_users.py routes with the correct user_id in the path,
// and surface backend errors verbatim (same discipline as every other
// Admin Users function). Uses only synthetic phone numbers/hashes --
// never a real number.
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

describe("registerWhatsAppNumber", () => {
  it("POSTs to /api/admin/users/{user_id}/whatsapp/register with the correct user_id and phone_number", async () => {
    global.fetch.mockResolvedValue(
      jsonResponse(200, { data: { sender_e164_sha256: "synthetic-hash-abc", user_id: "u-42", status: "PENDING", no_op: false } })
    );

    const result = await registerWhatsAppNumber("u-42", { phoneNumber: "+620000000000" });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/admin/users/u-42/whatsapp/register"),
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ Authorization: "Bearer test-admin-token" }),
        body: JSON.stringify({ phone_number: "+620000000000", provider: "whatsapp_cloud" }),
      })
    );
    expect(result.data.status).toBe("PENDING");
  });

  it("URL-encodes a user_id containing special characters", async () => {
    global.fetch.mockResolvedValue(jsonResponse(200, { data: {} }));

    await registerWhatsAppNumber("u/42 x", { phoneNumber: "+620000000000" });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining(encodeURIComponent("u/42 x")),
      expect.anything()
    );
  });

  it("surfaces a backend error verbatim (e.g. phone already bound)", async () => {
    global.fetch.mockResolvedValue(
      jsonResponse(409, { detail: "This WhatsApp number is already registered to a different user" })
    );

    await expect(registerWhatsAppNumber("u-42", { phoneNumber: "+620000000000" })).rejects.toMatchObject({
      message: "This WhatsApp number is already registered to a different user",
    });
  });
});

describe("activateWhatsAppNumber", () => {
  it("POSTs to /api/admin/users/{user_id}/whatsapp/activate with the correct user_id and sender_e164_sha256", async () => {
    global.fetch.mockResolvedValue(
      jsonResponse(200, { data: { sender_e164_sha256: "synthetic-hash-abc", user_id: "u-42", status: "ACTIVE", no_op: false } })
    );

    const result = await activateWhatsAppNumber("u-42", "synthetic-hash-abc");

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/admin/users/u-42/whatsapp/activate"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ sender_e164_sha256: "synthetic-hash-abc" }),
      })
    );
    expect(result.data.status).toBe("ACTIVE");
  });

  it("surfaces a backend error verbatim (e.g. not pending)", async () => {
    global.fetch.mockResolvedValue(jsonResponse(409, { detail: "identity status 'DISABLED' cannot be activated" }));

    await expect(activateWhatsAppNumber("u-42", "synthetic-hash-abc")).rejects.toMatchObject({
      message: "identity status 'DISABLED' cannot be activated",
    });
  });
});
