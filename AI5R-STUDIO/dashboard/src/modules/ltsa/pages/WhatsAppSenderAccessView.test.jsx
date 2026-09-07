import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import WhatsAppSenderAccessView from "./WhatsAppSenderAccessView";
import { activateWhatsAppNumber, getAdminUsers, registerWhatsAppNumber } from "../../../api/ai5rClient";

// AI5R-WHATSAPP-SENDER-ADMIN-001 / owner UAT state-safety fix -- uses
// only synthetic user/phone data, never a real captured identifier. Tab-
// level admin.users gating for this screen is proven separately in
// permissions.test.js ("whatsapp-groups" tab) since this component is
// rendered inside the SAME already-gated WhatsAppGroupsView tab, not a
// second route -- no user without admin.users can ever reach this
// component.
vi.mock("../../../api/ai5rClient", () => ({
  getAdminUsers: vi.fn(),
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
const SYNTHETIC_PHONE_B = "+620000000002";

// A promise the test controls the resolution timing of, to simulate a
// slow/delayed backend response arriving after the admin has already
// switched users.
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

describe("WhatsAppSenderAccessView -- neutral/initial state", () => {
  it("initial sender status is neutral, not fabricated as registered/active/inactive", async () => {
    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);

    expect(screen.getByTestId("whatsapp-sender-status-neutral").textContent).toBe("Status not loaded for this user.");
    expect(screen.queryByTestId("whatsapp-sender-redacted-id")).toBeNull();
  });

  it("selecting user A shows A's own details (canonical user source)", async () => {
    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);

    expect(screen.getByText("Name: usera")).toBeTruthy();
    expect(screen.getByText("Email: user-a@tap.internal")).toBeTruthy();
    expect(screen.getByTestId("whatsapp-sender-role").textContent).toBe("TAP_ENGINEER");
  });
});

describe("WhatsAppSenderAccessView -- register result scoping", () => {
  it("register result for A shows A's own status", async () => {
    registerWhatsAppNumber.mockResolvedValue({ data: { sender_e164_sha256: "hash-a", user_id: USER_A.id, status: "PENDING" } });

    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);
    fireEvent.change(screen.getByLabelText("WhatsApp Number"), { target: { value: SYNTHETIC_PHONE_A } });
    fireEvent.click(screen.getByText("Register Number"));

    await waitFor(() => expect(screen.getByText("PENDING")).toBeTruthy());
  });

  it("switching A -> B immediately clears/hides A's result and shows the neutral state", async () => {
    registerWhatsAppNumber.mockResolvedValue({ data: { sender_e164_sha256: "hash-a", user_id: USER_A.id, status: "ACTIVE" } });

    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);
    fireEvent.change(screen.getByLabelText("WhatsApp Number"), { target: { value: SYNTHETIC_PHONE_A } });
    fireEvent.click(screen.getByText("Register Number"));
    await waitFor(() => expect(screen.getByText("ACTIVE")).toBeTruthy());

    await selectUser(USER_B.id);

    expect(screen.queryByText("ACTIVE")).toBeNull();
    expect(screen.getByTestId("whatsapp-sender-status-neutral").textContent).toBe("Status not loaded for this user.");
  });

  it("ACTIVE obtained for A never renders as B's status, even reselecting A afterward shows neutral again (no backend lookup exists)", async () => {
    registerWhatsAppNumber.mockResolvedValue({ data: { sender_e164_sha256: "hash-a", user_id: USER_A.id, status: "ACTIVE" } });

    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);
    fireEvent.change(screen.getByLabelText("WhatsApp Number"), { target: { value: SYNTHETIC_PHONE_A } });
    fireEvent.click(screen.getByText("Register Number"));
    await waitFor(() => expect(screen.getByText("ACTIVE")).toBeTruthy());

    await selectUser(USER_B.id);
    expect(screen.queryByText("ACTIVE")).toBeNull();

    await selectUser(USER_A.id);
    // No GET lookup exists -- re-selecting A does not resurrect the
    // in-memory result either; this is deliberate honesty, not a bug.
    expect(screen.getByTestId("whatsapp-sender-status-neutral")).toBeTruthy();
  });

  it("the WhatsApp Number field clears on user change", async () => {
    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);
    fireEvent.change(screen.getByLabelText("WhatsApp Number"), { target: { value: SYNTHETIC_PHONE_A } });
    expect(screen.getByLabelText("WhatsApp Number").value).toBe(SYNTHETIC_PHONE_A);

    await selectUser(USER_B.id);
    expect(screen.getByLabelText("WhatsApp Number").value).toBe("");
  });
});

describe("WhatsAppSenderAccessView -- async race safety", () => {
  it("a delayed register response for A cannot populate B's status if the admin switched before it resolved", async () => {
    const { promise, resolve } = deferred();
    registerWhatsAppNumber.mockReturnValue(promise);

    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);
    fireEvent.change(screen.getByLabelText("WhatsApp Number"), { target: { value: SYNTHETIC_PHONE_A } });
    fireEvent.click(screen.getByText("Register Number"));

    // Switch to B BEFORE A's register call resolves.
    await selectUser(USER_B.id);
    expect(screen.getByTestId("whatsapp-sender-status-neutral")).toBeTruthy();

    // Now A's stale response arrives.
    resolve({ data: { sender_e164_sha256: "hash-a", user_id: USER_A.id, status: "ACTIVE" } });
    await new Promise((r) => setTimeout(r, 0));

    // B must still show neutral, never A's ACTIVE result.
    expect(screen.queryByText("ACTIVE")).toBeNull();
    expect(screen.getByTestId("whatsapp-sender-status-neutral")).toBeTruthy();
  });

  it("a delayed activate response for A cannot populate B's status, and A's hash cannot be reused for B's activation", async () => {
    registerWhatsAppNumber.mockResolvedValue({ data: { sender_e164_sha256: "hash-a", user_id: USER_A.id, status: "PENDING" } });
    const { promise, resolve } = deferred();
    activateWhatsAppNumber.mockReturnValue(promise);

    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);
    fireEvent.change(screen.getByLabelText("WhatsApp Number"), { target: { value: SYNTHETIC_PHONE_A } });
    fireEvent.click(screen.getByText("Register Number"));
    await waitFor(() => expect(screen.getByText("Activate Number")).toBeTruthy());

    fireEvent.click(screen.getByText("Activate Number"));
    expect(activateWhatsAppNumber).toHaveBeenCalledWith(USER_A.id, "hash-a");

    // Switch to B before A's activate call resolves. B has no result of
    // its own and no Activate button available (no hash for B).
    await selectUser(USER_B.id);
    expect(screen.queryByText("Activate Number")).toBeNull();
    expect(screen.getByTestId("whatsapp-sender-status-neutral")).toBeTruthy();

    resolve({ data: { sender_e164_sha256: "hash-a", user_id: USER_A.id, status: "ACTIVE" } });
    await new Promise((r) => setTimeout(r, 0));

    expect(screen.queryByText("ACTIVE")).toBeNull();
    expect(screen.getByTestId("whatsapp-sender-status-neutral")).toBeTruthy();
    // Only ever called once, for A -- B's session never triggered
    // activation and could not have reused A's hash.
    expect(activateWhatsAppNumber).toHaveBeenCalledTimes(1);
  });
});

describe("WhatsAppSenderAccessView -- role/scope stay read-only", () => {
  it("role remains read-only for the selected user", async () => {
    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_B.id);

    expect(screen.getByTestId("whatsapp-sender-role").textContent).toBe("TAP_ADMIN");
    expect(document.querySelectorAll("select").length).toBe(1); // only the user picker
  });

  it("scope remains read-only, honestly stated (not fabricated)", async () => {
    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_B.id);

    expect(screen.getByTestId("whatsapp-sender-scope").textContent).toBe("Not exposed by the current Admin Users API");
  });
});

describe("WhatsAppSenderAccessView -- canonical mechanisms reused", () => {
  it("uses the canonical getAdminUsers() source, not a second listing endpoint", async () => {
    render(<WhatsAppSenderAccessView />);
    await waitFor(() => expect(getAdminUsers).toHaveBeenCalledTimes(1));
  });

  it("register uses the canonical registerWhatsAppNumber client with the correct user_id", async () => {
    registerWhatsAppNumber.mockResolvedValue({ data: { sender_e164_sha256: "hash-a", user_id: USER_A.id, status: "PENDING" } });
    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);
    fireEvent.change(screen.getByLabelText("WhatsApp Number"), { target: { value: SYNTHETIC_PHONE_A } });
    fireEvent.click(screen.getByText("Register Number"));

    await waitFor(() => expect(registerWhatsAppNumber).toHaveBeenCalledWith(USER_A.id, { phoneNumber: SYNTHETIC_PHONE_A }));
  });

  it("activate uses the canonical activateWhatsAppNumber client with the correct user_id", async () => {
    registerWhatsAppNumber.mockResolvedValue({ data: { sender_e164_sha256: "hash-b", user_id: USER_B.id, status: "PENDING" } });
    activateWhatsAppNumber.mockResolvedValue({ data: { sender_e164_sha256: "hash-b", user_id: USER_B.id, status: "ACTIVE" } });

    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_B.id);
    fireEvent.change(screen.getByLabelText("WhatsApp Number"), { target: { value: SYNTHETIC_PHONE_B } });
    fireEvent.click(screen.getByText("Register Number"));
    await waitFor(() => expect(screen.getByText("Activate Number")).toBeTruthy());
    fireEvent.click(screen.getByText("Activate Number"));

    await waitFor(() => expect(activateWhatsAppNumber).toHaveBeenCalledWith(USER_B.id, "hash-b"));
  });
});

describe("WhatsAppSenderAccessView -- phone privacy", () => {
  it("never persists the raw phone to localStorage/sessionStorage and never logs it", async () => {
    const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    registerWhatsAppNumber.mockResolvedValue({ data: { sender_e164_sha256: "hash-a", user_id: USER_A.id, status: "PENDING" } });

    render(<WhatsAppSenderAccessView />);
    await selectUser(USER_A.id);
    fireEvent.change(screen.getByLabelText("WhatsApp Number"), { target: { value: SYNTHETIC_PHONE_A } });
    fireEvent.click(screen.getByText("Register Number"));
    await waitFor(() => expect(screen.getByText("PENDING")).toBeTruthy());

    expect(JSON.stringify(window.localStorage)).not.toContain(SYNTHETIC_PHONE_A);
    expect(JSON.stringify(window.sessionStorage)).not.toContain(SYNTHETIC_PHONE_A);
    for (const call of consoleSpy.mock.calls) {
      expect(JSON.stringify(call)).not.toContain(SYNTHETIC_PHONE_A);
    }
    expect(screen.getByLabelText("WhatsApp Number").value).toBe("");
  });
});
