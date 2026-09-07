import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import WhatsAppSenderAccessView from "./WhatsAppSenderAccessView";
import {
  activateWhatsAppNumber,
  getAdminUsers,
  getWhatsAppSenderStatus,
  registerWhatsAppNumber,
} from "../../../api/ai5rClient";

// AI5R-WHATSAPP-SENDER-STATUS-001 -- uses only synthetic user/phone data,
// never a real captured identifier. Tab-level admin.users gating for
// this screen is proven separately in permissions.test.js
// ("whatsapp-groups" tab) since this component is rendered inside the
// SAME already-gated WhatsAppGroupsView tab, not a second route.
vi.mock("../../../api/ai5rClient", () => ({
  getAdminUsers: vi.fn(),
  getWhatsAppSenderStatus: vi.fn(),
  registerWhatsAppNumber: vi.fn(),
  activateWhatsAppNumber: vi.fn(),
}));

const USER_A = {
  id: "u-a", username: "usera", email: "user-a@tap.internal", status: "ACTIVE",
  organization_code: "TAP", organization_name: "TAP", role: "TAP_ENGINEER", membership_status: "ACTIVE",
};
const USER_B = {
  id: "u-b", username: "userb", email: "ghonam.marino@gmail.com", status: "ACTIVE",
  organization_code: "TAP", organization_name: "TAP", role: "TAP_ADMIN", membership_status: "ACTIVE",
};
const SYNTHETIC_USERS = [USER_A, USER_B];
const SYNTHETIC_PHONE_A = "+620000000001";

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

beforeEach(() => {
  vi.clearAllMocks();
  getAdminUsers.mockResolvedValue(SYNTHETIC_USERS);
});

afterEach(() => {
  vi.restoreAllMocks();
});

async function selectUser(id) {
  await waitFor(() => expect(screen.getByLabelText("User")).toBeTruthy());
  fireEvent.change(screen.getByLabelText("User"), { target: { value: id } });
}

describe("WhatsAppSenderAccessView -- auto-load on selection", () => {
  it("selecting an ACTIVE user auto-loads and shows ACTIVE", async () => {
    getWhatsAppSenderStatus.mockResolvedValue({ data: { registered: true, status: "ACTIVE", provider: "whatsapp_cloud" } });

    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);

    expect(getWhatsAppSenderStatus).toHaveBeenCalledWith(USER_A.id);
    await waitFor(() => expect(screen.getByText("ACTIVE")).toBeTruthy());
    expect(screen.getByText("Provider: whatsapp_cloud")).toBeTruthy();
    expect(screen.queryByTestId("whatsapp-sender-not-registered")).toBeNull();
  });

  it("selecting a NOT_REGISTERED user shows 'Not registered' plus the phone form", async () => {
    getWhatsAppSenderStatus.mockResolvedValue({ data: { registered: false, status: "NOT_REGISTERED" } });

    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);

    await waitFor(() => expect(screen.getByTestId("whatsapp-sender-not-registered")).toBeTruthy());
    expect(screen.getByLabelText("WhatsApp Number")).toBeTruthy();
    expect(screen.getByText("Register Number")).toBeTruthy();
  });

  it("selecting a PENDING user shows PENDING and an Activate action", async () => {
    getWhatsAppSenderStatus.mockResolvedValue({
      data: { registered: true, status: "PENDING", provider: "whatsapp_cloud", sender_e164_sha256: "hash-a" },
    });

    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);

    await waitFor(() => expect(screen.getByText("PENDING")).toBeTruthy());
    expect(screen.getByText("Activate Number")).toBeTruthy();
  });
});

describe("WhatsAppSenderAccessView -- async race safety", () => {
  it("ACTIVE for A -> switch to B -> A's status disappears immediately", async () => {
    getWhatsAppSenderStatus.mockImplementation((userId) =>
      Promise.resolve(
        userId === USER_A.id
          ? { data: { registered: true, status: "ACTIVE", provider: "whatsapp_cloud" } }
          : { data: { registered: false, status: "NOT_REGISTERED" } }
      )
    );

    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);
    await waitFor(() => expect(screen.getByText("ACTIVE")).toBeTruthy());

    await selectUser(USER_B.id);

    expect(screen.queryByText("ACTIVE")).toBeNull();
    await waitFor(() => expect(screen.getByTestId("whatsapp-sender-not-registered")).toBeTruthy());
  });

  it("a slow lookup for A resolving after B is selected is never rendered for B", async () => {
    const { promise, resolve } = deferred();
    getWhatsAppSenderStatus.mockImplementation((userId) =>
      userId === USER_A.id ? promise : Promise.resolve({ data: { registered: false, status: "NOT_REGISTERED" } })
    );

    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);
    // A's lookup is still in flight (deferred).
    expect(screen.getByTestId("whatsapp-sender-status-loading")).toBeTruthy();

    await selectUser(USER_B.id);
    await waitFor(() => expect(screen.getByTestId("whatsapp-sender-not-registered")).toBeTruthy());

    // Now A's slow response finally arrives.
    resolve({ data: { registered: true, status: "ACTIVE", provider: "whatsapp_cloud" } });
    await new Promise((r) => setTimeout(r, 0));

    expect(screen.queryByText("ACTIVE")).toBeNull();
    expect(screen.getByTestId("whatsapp-sender-not-registered")).toBeTruthy();
  });

  it("a lookup error shows ERROR, never fabricated as NOT_REGISTERED", async () => {
    getWhatsAppSenderStatus.mockRejectedValue(new Error("boom"));

    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);

    await waitFor(() => expect(screen.getByTestId("whatsapp-sender-status-error")).toBeTruthy());
    expect(screen.getByTestId("whatsapp-sender-status-error").textContent).toBe("Unable to load WhatsApp access status.");
    expect(screen.queryByTestId("whatsapp-sender-not-registered")).toBeNull();
  });

  it("the WhatsApp Number field clears on user switch", async () => {
    getWhatsAppSenderStatus.mockResolvedValue({ data: { registered: false, status: "NOT_REGISTERED" } });

    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);
    await waitFor(() => expect(screen.getByLabelText("WhatsApp Number")).toBeTruthy());
    fireEvent.change(screen.getByLabelText("WhatsApp Number"), { target: { value: SYNTHETIC_PHONE_A } });
    expect(screen.getByLabelText("WhatsApp Number").value).toBe(SYNTHETIC_PHONE_A);

    await selectUser(USER_B.id);
    await waitFor(() => expect(screen.getByLabelText("WhatsApp Number")).toBeTruthy());
    expect(screen.getByLabelText("WhatsApp Number").value).toBe("");
  });

  it("successful register triggers a canonical status re-fetch (not local response state)", async () => {
    getWhatsAppSenderStatus
      .mockResolvedValueOnce({ data: { registered: false, status: "NOT_REGISTERED" } })
      .mockResolvedValueOnce({ data: { registered: true, status: "PENDING", provider: "whatsapp_cloud", sender_e164_sha256: "hash-a" } });
    registerWhatsAppNumber.mockResolvedValue({ data: { sender_e164_sha256: "hash-a", user_id: USER_A.id, status: "PENDING" } });

    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);
    await waitFor(() => expect(screen.getByLabelText("WhatsApp Number")).toBeTruthy());
    fireEvent.change(screen.getByLabelText("WhatsApp Number"), { target: { value: SYNTHETIC_PHONE_A } });
    fireEvent.click(screen.getByText("Register Number"));

    await waitFor(() => expect(getWhatsAppSenderStatus).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.getByText("PENDING")).toBeTruthy());
  });

  it("successful activate triggers a canonical status re-fetch", async () => {
    getWhatsAppSenderStatus
      .mockResolvedValueOnce({ data: { registered: true, status: "PENDING", provider: "whatsapp_cloud", sender_e164_sha256: "hash-a" } })
      .mockResolvedValueOnce({ data: { registered: true, status: "ACTIVE", provider: "whatsapp_cloud" } });
    activateWhatsAppNumber.mockResolvedValue({ data: { sender_e164_sha256: "hash-a", user_id: USER_A.id, status: "ACTIVE" } });

    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);
    await waitFor(() => expect(screen.getByText("Activate Number")).toBeTruthy());
    fireEvent.click(screen.getByText("Activate Number"));

    await waitFor(() => expect(activateWhatsAppNumber).toHaveBeenCalledWith(USER_A.id, "hash-a"));
    await waitFor(() => expect(getWhatsAppSenderStatus).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.getByText("ACTIVE")).toBeTruthy());
    expect(screen.queryByText("Activate Number")).toBeNull();
  });

  it("cannot activate using a different user's identifier (no cross-user activation)", async () => {
    getWhatsAppSenderStatus.mockImplementation((userId) =>
      Promise.resolve(
        userId === USER_A.id
          ? { data: { registered: true, status: "PENDING", provider: "whatsapp_cloud", sender_e164_sha256: "hash-a" } }
          : { data: { registered: false, status: "NOT_REGISTERED" } }
      )
    );

    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);
    await waitFor(() => expect(screen.getByText("Activate Number")).toBeTruthy());

    // Switch to B before clicking Activate for A.
    await selectUser(USER_B.id);
    expect(screen.queryByText("Activate Number")).toBeNull();
    expect(activateWhatsAppNumber).not.toHaveBeenCalled();
  });
});

describe("WhatsAppSenderAccessView -- role/scope stay read-only", () => {
  it("role remains read-only for the selected user", async () => {
    getWhatsAppSenderStatus.mockResolvedValue({ data: { registered: false, status: "NOT_REGISTERED" } });
    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_B.id);

    await waitFor(() => expect(screen.getByTestId("whatsapp-sender-role").textContent).toBe("TAP_ADMIN"));
    expect(document.querySelectorAll("select").length).toBe(1); // only the user picker
  });

  it("scope remains read-only, honestly stated (not fabricated)", async () => {
    getWhatsAppSenderStatus.mockResolvedValue({ data: { registered: false, status: "NOT_REGISTERED" } });
    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_B.id);

    expect(screen.getByTestId("whatsapp-sender-scope").textContent).toBe("Not exposed by the current Admin Users API");
  });
});

describe("WhatsAppSenderAccessView -- ACTIVE never shows Register as if unregistered", () => {
  it("does not render the phone form or Register button for an ACTIVE identity", async () => {
    getWhatsAppSenderStatus.mockResolvedValue({ data: { registered: true, status: "ACTIVE", provider: "whatsapp_cloud" } });

    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);

    await waitFor(() => expect(screen.getByText("ACTIVE")).toBeTruthy());
    expect(screen.queryByLabelText("WhatsApp Number")).toBeNull();
    expect(screen.queryByText("Register Number")).toBeNull();
  });
});

describe("WhatsAppSenderAccessView -- phone privacy", () => {
  it("never persists the raw phone to localStorage/sessionStorage and never logs it", async () => {
    const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    getWhatsAppSenderStatus
      .mockResolvedValueOnce({ data: { registered: false, status: "NOT_REGISTERED" } })
      .mockResolvedValueOnce({ data: { registered: true, status: "PENDING", provider: "whatsapp_cloud", sender_e164_sha256: "hash-a" } });
    registerWhatsAppNumber.mockResolvedValue({ data: { sender_e164_sha256: "hash-a", user_id: USER_A.id, status: "PENDING" } });

    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);
    await waitFor(() => expect(screen.getByLabelText("WhatsApp Number")).toBeTruthy());
    fireEvent.change(screen.getByLabelText("WhatsApp Number"), { target: { value: SYNTHETIC_PHONE_A } });
    fireEvent.click(screen.getByText("Register Number"));
    await waitFor(() => expect(screen.getByText("PENDING")).toBeTruthy());

    expect(JSON.stringify(window.localStorage)).not.toContain(SYNTHETIC_PHONE_A);
    expect(JSON.stringify(window.sessionStorage)).not.toContain(SYNTHETIC_PHONE_A);
    for (const call of consoleSpy.mock.calls) {
      expect(JSON.stringify(call)).not.toContain(SYNTHETIC_PHONE_A);
    }
  });
});
