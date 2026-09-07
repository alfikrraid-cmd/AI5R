import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import WhatsAppSenderAccessView from "./WhatsAppSenderAccessView";
import { activateWhatsAppNumber, getAdminUsers, registerWhatsAppNumber } from "../../../api/ai5rClient";

// AI5R-WHATSAPP-SENDER-ADMIN-001 -- uses only synthetic user/phone data,
// never a real captured identifier. Tab-level admin.users gating for
// this screen is proven separately in permissions.test.js
// ("whatsapp-groups" tab) since this component is rendered inside the
// SAME already-gated WhatsAppGroupsView tab, not a second route -- no
// user without admin.users can ever reach this component.
vi.mock("../../../api/ai5rClient", () => ({
  getAdminUsers: vi.fn(),
  registerWhatsAppNumber: vi.fn(),
  activateWhatsAppNumber: vi.fn(),
}));

const SYNTHETIC_USERS = [
  {
    id: "u-1", username: "tapeng", email: "tap-eng@tap.internal", status: "ACTIVE",
    organization_code: "TAP", organization_name: "TAP", role: "TAP_ENGINEER", membership_status: "ACTIVE",
  },
  {
    id: "u-2", username: "tapadmin", email: "tap-admin@tap.internal", status: "ACTIVE",
    organization_code: "TAP", organization_name: "TAP", role: "TAP_ADMIN", membership_status: "ACTIVE",
  },
];

const SYNTHETIC_PHONE = "+620000000000";

beforeEach(() => {
  vi.clearAllMocks();
  getAdminUsers.mockResolvedValue(SYNTHETIC_USERS);
});

afterEach(() => {
  vi.restoreAllMocks();
});

async function selectUser(label) {
  await waitFor(() => expect(screen.getByLabelText("User")).toBeTruthy());
  fireEvent.change(screen.getByLabelText("User"), { target: { value: "u-2" } });
}

describe("WhatsAppSenderAccessView user selection", () => {
  it("loads the existing user list via the canonical getAdminUsers client", async () => {
    render(<WhatsAppSenderAccessView />);
    await waitFor(() => expect(getAdminUsers).toHaveBeenCalledTimes(1));
    expect(screen.getByRole("option", { name: "tapadmin" })).toBeTruthy();
  });

  it("selecting a user displays their role read-only", async () => {
    render(<WhatsAppSenderAccessView />);
    await selectUser();

    expect(screen.getByTestId("whatsapp-sender-role").textContent).toBe("TAP_ADMIN");
    expect(screen.getAllByText(/read-only/).length).toBeGreaterThanOrEqual(1);
  });

  it("selecting a user displays scope read-only (honest 'not exposed' state, never fabricated)", async () => {
    render(<WhatsAppSenderAccessView />);
    await selectUser();

    expect(screen.getByTestId("whatsapp-sender-scope").textContent).toBe("Not exposed by the current Admin Users API");
  });

  it("provides no control anywhere that could change role or scope", async () => {
    render(<WhatsAppSenderAccessView />);
    await selectUser();

    expect(screen.queryByLabelText("Role")).toBeNull();
    expect(screen.queryByLabelText("Scope")).toBeNull();
    expect(document.querySelectorAll("select").length).toBe(1); // only the user picker
  });
});

describe("WhatsAppSenderAccessView registration", () => {
  it("register uses the correct selected user_id and canonical apiFetch-backed client", async () => {
    registerWhatsAppNumber.mockResolvedValue({
      data: { sender_e164_sha256: "synthetic-hash", user_id: "u-2", status: "PENDING", no_op: false },
    });

    render(<WhatsAppSenderAccessView />);
    await selectUser();
    fireEvent.change(screen.getByLabelText("WhatsApp Number"), { target: { value: SYNTHETIC_PHONE } });
    fireEvent.click(screen.getByText("Register Number"));

    await waitFor(() =>
      expect(registerWhatsAppNumber).toHaveBeenCalledWith("u-2", { phoneNumber: SYNTHETIC_PHONE })
    );
  });

  it("rejects submission with no user selected", async () => {
    render(<WhatsAppSenderAccessView />);
    await waitFor(() => expect(screen.getByLabelText("User")).toBeTruthy());
    fireEvent.change(screen.getByLabelText("WhatsApp Number"), { target: { value: SYNTHETIC_PHONE } });
    fireEvent.click(screen.getByText("Register Number"));

    expect(screen.getByTestId("whatsapp-sender-validation-error").textContent).toMatch(/Select a user/);
    expect(registerWhatsAppNumber).not.toHaveBeenCalled();
  });

  it("shows the identifier as REDACTED and never renders the raw phone after registration", async () => {
    registerWhatsAppNumber.mockResolvedValue({
      data: { sender_e164_sha256: "synthetic-hash", user_id: "u-2", status: "PENDING", no_op: false },
    });

    render(<WhatsAppSenderAccessView />);
    await selectUser();
    fireEvent.change(screen.getByLabelText("WhatsApp Number"), { target: { value: SYNTHETIC_PHONE } });
    fireEvent.click(screen.getByText("Register Number"));

    await waitFor(() => expect(screen.getByTestId("whatsapp-sender-registration-summary")).toBeTruthy());
    expect(screen.getByTestId("whatsapp-sender-redacted-id").textContent).toBe("REDACTED");
    expect(document.body.innerHTML).not.toContain(SYNTHETIC_PHONE);
    expect(document.body.innerHTML).not.toContain("synthetic-hash");
    expect(screen.getByLabelText("WhatsApp Number").value).toBe("");
  });

  it("does not persist the raw phone to localStorage or sessionStorage", async () => {
    registerWhatsAppNumber.mockResolvedValue({
      data: { sender_e164_sha256: "synthetic-hash", user_id: "u-2", status: "PENDING", no_op: false },
    });

    render(<WhatsAppSenderAccessView />);
    await selectUser();
    fireEvent.change(screen.getByLabelText("WhatsApp Number"), { target: { value: SYNTHETIC_PHONE } });
    fireEvent.click(screen.getByText("Register Number"));

    await waitFor(() => expect(screen.getByTestId("whatsapp-sender-registration-summary")).toBeTruthy());
    expect(JSON.stringify(window.localStorage)).not.toContain(SYNTHETIC_PHONE);
    expect(JSON.stringify(window.sessionStorage)).not.toContain(SYNTHETIC_PHONE);
  });

  it("register error is displayed verbatim", async () => {
    registerWhatsAppNumber.mockRejectedValue(new Error("This WhatsApp number is already registered to a different user"));

    render(<WhatsAppSenderAccessView />);
    await selectUser();
    fireEvent.change(screen.getByLabelText("WhatsApp Number"), { target: { value: SYNTHETIC_PHONE } });
    fireEvent.click(screen.getByText("Register Number"));

    await waitFor(() =>
      expect(screen.getByTestId("whatsapp-sender-action-error").textContent).toBe(
        "This WhatsApp number is already registered to a different user"
      )
    );
  });
});

describe("WhatsAppSenderAccessView activation", () => {
  it("activate uses the correct selected user_id and the hash returned by register", async () => {
    registerWhatsAppNumber.mockResolvedValue({
      data: { sender_e164_sha256: "synthetic-hash", user_id: "u-2", status: "PENDING", no_op: false },
    });
    activateWhatsAppNumber.mockResolvedValue({
      data: { sender_e164_sha256: "synthetic-hash", user_id: "u-2", status: "ACTIVE", no_op: false },
    });

    render(<WhatsAppSenderAccessView />);
    await selectUser();
    fireEvent.change(screen.getByLabelText("WhatsApp Number"), { target: { value: SYNTHETIC_PHONE } });
    fireEvent.click(screen.getByText("Register Number"));
    await waitFor(() => expect(screen.getByText("Activate Number")).toBeTruthy());

    fireEvent.click(screen.getByText("Activate Number"));

    await waitFor(() => expect(activateWhatsAppNumber).toHaveBeenCalledWith("u-2", "synthetic-hash"));
    await waitFor(() => expect(screen.getByText("ACTIVE")).toBeTruthy());
    expect(screen.queryByText("Activate Number")).toBeNull();
  });

  it("activate error is displayed verbatim", async () => {
    registerWhatsAppNumber.mockResolvedValue({
      data: { sender_e164_sha256: "synthetic-hash", user_id: "u-2", status: "PENDING", no_op: false },
    });
    activateWhatsAppNumber.mockRejectedValue(new Error("identity status 'DISABLED' cannot be activated"));

    render(<WhatsAppSenderAccessView />);
    await selectUser();
    fireEvent.change(screen.getByLabelText("WhatsApp Number"), { target: { value: SYNTHETIC_PHONE } });
    fireEvent.click(screen.getByText("Register Number"));
    await waitFor(() => expect(screen.getByText("Activate Number")).toBeTruthy());

    fireEvent.click(screen.getByText("Activate Number"));

    await waitFor(() =>
      expect(screen.getByTestId("whatsapp-sender-action-error").textContent).toBe(
        "identity status 'DISABLED' cannot be activated"
      )
    );
  });

  it("a register response that is already ACTIVE hides the Activate button immediately", async () => {
    registerWhatsAppNumber.mockResolvedValue({
      data: { sender_e164_sha256: "synthetic-hash", user_id: "u-2", status: "ACTIVE", no_op: true },
    });

    render(<WhatsAppSenderAccessView />);
    await selectUser();
    fireEvent.change(screen.getByLabelText("WhatsApp Number"), { target: { value: SYNTHETIC_PHONE } });
    fireEvent.click(screen.getByText("Register Number"));

    await waitFor(() => expect(screen.getByText("ACTIVE")).toBeTruthy());
    expect(screen.queryByText("Activate Number")).toBeNull();
  });
});
