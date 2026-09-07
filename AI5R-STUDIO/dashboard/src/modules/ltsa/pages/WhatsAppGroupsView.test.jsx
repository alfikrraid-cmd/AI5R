import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import WhatsAppGroupsView from "./WhatsAppGroupsView";
import { activateWhatsAppGroup, getAdminUsers, registerWhatsAppGroup } from "../../../api/ai5rClient";

// AI5R-WHATSAPP-GROUP-ADMIN-001 -- uses only synthetic group ids, never
// the real captured production JID. getAdminUsers/registerWhatsAppNumber/
// activateWhatsAppNumber are stubbed too (AI5R-WHATSAPP-SENDER-ADMIN-001)
// since this view now also renders WhatsAppSenderAccessView, which calls
// getAdminUsers() on mount -- WhatsAppSenderAccessView's own behavior is
// covered by its dedicated test file, not re-tested here.
vi.mock("../../../api/ai5rClient", () => ({
  registerWhatsAppGroup: vi.fn(),
  activateWhatsAppGroup: vi.fn(),
  getAdminUsers: vi.fn().mockResolvedValue([]),
  registerWhatsAppNumber: vi.fn(),
  activateWhatsAppNumber: vi.fn(),
  getWhatsAppSenderStatus: vi.fn(),
}));

const SYNTHETIC_JID = "111222333444555666@g.us";

function fillAndSubmit({ jid = SYNTHETIC_JID, label = "Synthetic Test Group" } = {}) {
  fireEvent.change(screen.getByLabelText("Group JID"), { target: { value: jid } });
  fireEvent.change(screen.getByLabelText("Display Label"), { target: { value: label } });
  fireEvent.click(screen.getByText("Register Group"));
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("WhatsAppGroupsView client-side validation", () => {
  it("rejects a JID that does not end in @g.us without calling the API", () => {
    render(<WhatsAppGroupsView />);
    fillAndSubmit({ jid: "not-a-valid-jid" });

    expect(screen.getByTestId("whatsapp-groups-validation-error").textContent).toMatch(/@g\.us/);
    expect(registerWhatsAppGroup).not.toHaveBeenCalled();
  });

  it("rejects an empty display label without calling the API", () => {
    render(<WhatsAppGroupsView />);
    fireEvent.change(screen.getByLabelText("Group JID"), { target: { value: SYNTHETIC_JID } });
    fireEvent.click(screen.getByText("Register Group"));

    expect(screen.getByTestId("whatsapp-groups-validation-error").textContent).toMatch(/Display Label/);
    expect(registerWhatsAppGroup).not.toHaveBeenCalled();
  });

  it("accepts a well-formed @g.us JID and a display label, and calls the API via the canonical client", async () => {
    registerWhatsAppGroup.mockResolvedValue({
      success: true,
      data: { group_hash: "hash-abcdef123456", display_label: "Synthetic Test Group", status: "PENDING" },
    });

    render(<WhatsAppGroupsView />);
    fillAndSubmit();

    await waitFor(() =>
      expect(registerWhatsAppGroup).toHaveBeenCalledWith({ groupId: SYNTHETIC_JID, displayLabel: "Synthetic Test Group" })
    );
  });
});

describe("WhatsAppGroupsView registration result and activation", () => {
  it("renders the returned group_hash (truncated) feeding activation, never the raw JID", async () => {
    registerWhatsAppGroup.mockResolvedValue({
      success: true,
      data: { group_hash: "hash-abcdef123456", display_label: "Synthetic Test Group", status: "PENDING" },
    });

    render(<WhatsAppGroupsView />);
    fillAndSubmit();

    await waitFor(() => expect(screen.getByTestId("whatsapp-groups-registered-summary")).toBeTruthy());
    expect(screen.getByTestId("whatsapp-groups-redacted-id").textContent).toBe("REDACTED");
    expect(screen.queryByText(SYNTHETIC_JID)).toBeNull();
    expect(document.body.innerHTML).not.toContain(SYNTHETIC_JID);
    expect(screen.getByText("Activate Group")).toBeTruthy();
  });

  it("does not persist the raw JID to localStorage or sessionStorage after registration", async () => {
    registerWhatsAppGroup.mockResolvedValue({
      success: true,
      data: { group_hash: "hash-abcdef123456", display_label: "Synthetic Test Group", status: "PENDING" },
    });

    render(<WhatsAppGroupsView />);
    fillAndSubmit();

    await waitFor(() => expect(screen.getByTestId("whatsapp-groups-registered-summary")).toBeTruthy());

    const localDump = JSON.stringify(window.localStorage);
    const sessionDump = JSON.stringify(window.sessionStorage);
    expect(localDump).not.toContain(SYNTHETIC_JID);
    expect(sessionDump).not.toContain(SYNTHETIC_JID);
    expect(screen.getByLabelText("Group JID").value).toBe("");
  });

  it("activating a PENDING group with the returned group_hash renders ACTIVE status", async () => {
    registerWhatsAppGroup.mockResolvedValue({
      success: true,
      data: { group_hash: "hash-abcdef123456", display_label: "Synthetic Test Group", status: "PENDING" },
    });
    activateWhatsAppGroup.mockResolvedValue({
      success: true,
      data: { group_hash: "hash-abcdef123456", display_label: "Synthetic Test Group", status: "ACTIVE" },
    });

    render(<WhatsAppGroupsView />);
    fillAndSubmit();
    await waitFor(() => expect(screen.getByText("Activate Group")).toBeTruthy());

    fireEvent.click(screen.getByText("Activate Group"));

    await waitFor(() => expect(activateWhatsAppGroup).toHaveBeenCalledWith({ groupHash: "hash-abcdef123456" }));
    await waitFor(() => expect(screen.getByText("ACTIVE")).toBeTruthy());
    expect(screen.queryByText("Activate Group")).toBeNull();
  });

  it("a register response that is already ACTIVE hides the Activate button immediately", async () => {
    registerWhatsAppGroup.mockResolvedValue({
      success: true,
      data: { group_hash: "hash-abcdef123456", display_label: "Synthetic Test Group", status: "ACTIVE" },
    });

    render(<WhatsAppGroupsView />);
    fillAndSubmit();

    await waitFor(() => expect(screen.getByText("ACTIVE")).toBeTruthy());
    expect(screen.queryByText("Activate Group")).toBeNull();
  });
});

describe("WhatsAppGroupsView error handling", () => {
  it("renders a friendly message on a 403 without leaking backend detail wording", async () => {
    const error = new Error("Missing permission: admin.users");
    error.status = 403;
    registerWhatsAppGroup.mockRejectedValue(error);

    render(<WhatsAppGroupsView />);
    fillAndSubmit();

    await waitFor(() =>
      expect(screen.getByTestId("whatsapp-groups-action-error").textContent).toBe(
        "You do not have permission to manage WhatsApp groups."
      )
    );
  });

  it("renders a generic server/network error message verbatim", async () => {
    registerWhatsAppGroup.mockRejectedValue(new Error("WhatsApp Group Admin API unavailable"));

    render(<WhatsAppGroupsView />);
    fillAndSubmit();

    await waitFor(() =>
      expect(screen.getByTestId("whatsapp-groups-action-error").textContent).toBe("WhatsApp Group Admin API unavailable")
    );
  });
});
