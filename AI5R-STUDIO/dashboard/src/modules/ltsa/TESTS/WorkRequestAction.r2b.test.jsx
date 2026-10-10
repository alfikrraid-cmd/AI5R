import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import WorkRequestAction from "../components/WorkRequestAction";
import { createWorkRequest } from "../../../api/ai5rClient";
import { useOptionalAuth } from "../auth/AuthContext";

// LTSA_PERTAMINA_WORK_REQUEST_UI_R2B -- Asset 360 "Request Work" action.
// The client module is mocked down to createWorkRequest only, so any other
// API call (PM/CM result, installation write) would fail loudly.
vi.mock("../../../api/ai5rClient", () => ({
  createWorkRequest: vi.fn(),
}));
vi.mock("../auth/AuthContext", () => ({
  useOptionalAuth: vi.fn(),
}));

const TAG = "211-P-10A";

// Real backend permission arrays (CORE-SERVICES/API/auth_service.py).
const PERTAMINA_ENGINEER = {
  role: "PERTAMINA_ENGINEER",
  permissions: [
    "pump.read", "seal.read", "inventory.read", "maintenance.read", "condition.read",
    "drawing.read", "engineering_ai.ask", "dashboard.read", "maintenance.request", "installation.request",
  ],
};
const PERTAMINA_VIEWER = { role: "PERTAMINA_VIEWER", permissions: ["pump.read", "seal.read", "maintenance.read"] };
const TAP_ENGINEER = {
  role: "TAP_ENGINEER",
  permissions: ["pump.read", "seal.read", "maintenance.read", "maintenance.write", "seal.lifecycle_write"],
};

function asSession(session) {
  useOptionalAuth.mockReturnValue(session ? { session } : null);
}

function openAndChoose(type) {
  fireEvent.click(screen.getByTestId("work-request-open"));
  fireEvent.click(screen.getByTestId(`work-request-type-${type}`));
}

function fillAndReview(text = "Seal leak observed at DE side") {
  fireEvent.change(screen.getByTestId("work-request-description"), { target: { value: text } });
  fireEvent.click(screen.getByRole("button", { name: "Review request" }));
}

let fetchSpy;
beforeEach(() => {
  fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => {
    throw new Error("unexpected network call");
  });
});
afterEach(() => {
  fetchSpy.mockRestore();
  vi.clearAllMocks();
});

describe("WorkRequestAction visibility", () => {
  it("offers PM, CM and Installation to a PERTAMINA_ENGINEER", () => {
    asSession(PERTAMINA_ENGINEER);
    render(<WorkRequestAction assetTag={TAG} />);
    fireEvent.click(screen.getByTestId("work-request-open"));
    expect(screen.getByRole("button", { name: "Request PM" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Request CM" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Request Installation" })).toBeInTheDocument();
  });

  it.each([
    ["TAP_ENGINEER (write roles, no request permission)", TAP_ENGINEER],
    ["PERTAMINA_VIEWER", PERTAMINA_VIEWER],
    ["no session", null],
  ])("renders nothing for %s", (_label, session) => {
    asSession(session);
    const { container } = render(<WorkRequestAction assetTag={TAG} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("is permission-driven, not role-name driven", () => {
    asSession({ role: "PERTAMINA_ENGINEER", permissions: ["pump.read", "installation.request"] });
    render(<WorkRequestAction assetTag={TAG} />);
    fireEvent.click(screen.getByTestId("work-request-open"));
    expect(screen.queryByRole("button", { name: "Request PM" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Request CM" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Request Installation" })).toBeInTheDocument();
  });

  it("renders nothing without an asset tag", () => {
    asSession(PERTAMINA_ENGINEER);
    const { container } = render(<WorkRequestAction assetTag={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("WorkRequestAction submission", () => {
  it.each(["PM", "CM", "INSTALLATION"])("confirms then submits a %s request with the page asset tag", async (type) => {
    asSession(PERTAMINA_ENGINEER);
    createWorkRequest.mockResolvedValue({
      success: true,
      data: { request_code: "WR-ABC123DEF456", request_type: type, asset_code: TAG, status: "SUBMITTED" },
    });
    render(<WorkRequestAction assetTag={TAG} />);
    openAndChoose(type);
    fillAndReview("  Please schedule  ");

    expect(screen.getByTestId("work-request-confirm-asset")).toHaveTextContent(TAG);
    expect(screen.getByTestId("work-request-confirm-type")).toHaveTextContent(type === "INSTALLATION" ? "Installation" : type);
    expect(createWorkRequest).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId("work-request-submit"));
    await screen.findByTestId("work-request-success");

    expect(createWorkRequest).toHaveBeenCalledTimes(1);
    expect(createWorkRequest).toHaveBeenCalledWith({ requestType: type, assetCode: TAG, description: "Please schedule" });
    expect(screen.getByTestId("work-request-success")).toHaveTextContent("WR-ABC123DEF456");
    expect(screen.getByTestId("work-request-success")).toHaveTextContent("SUBMITTED");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("exposes no requester or status input", () => {
    asSession(PERTAMINA_ENGINEER);
    render(<WorkRequestAction assetTag={TAG} />);
    openAndChoose("PM");
    expect(screen.getAllByRole("textbox")).toHaveLength(1);
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("requires a description before review", () => {
    asSession(PERTAMINA_ENGINEER);
    render(<WorkRequestAction assetTag={TAG} />);
    openAndChoose("CM");
    expect(screen.getByRole("button", { name: "Review request" })).toBeDisabled();
    fireEvent.change(screen.getByTestId("work-request-description"), { target: { value: "   " } });
    expect(screen.getByRole("button", { name: "Review request" })).toBeDisabled();
  });

  it.each([
    [403, "Missing permission: maintenance.request", /not authorized/i],
    [404, "Pump not found", /not found or is outside your access scope/i],
    [422, "asset_code and description are required", /rejected: asset_code and description are required/i],
    [500, "boom", /not submitted \(HTTP 500\)/i],
  ])("shows a safe error for HTTP %s and never claims success", async (status, message, expected) => {
    asSession(PERTAMINA_ENGINEER);
    createWorkRequest.mockRejectedValue(Object.assign(new Error(message), { status }));
    render(<WorkRequestAction assetTag={TAG} />);
    openAndChoose("PM");
    fillAndReview();
    fireEvent.click(screen.getByTestId("work-request-submit"));

    expect(await screen.findByTestId("work-request-error")).toHaveTextContent(expected);
    expect(screen.queryByTestId("work-request-success")).not.toBeInTheDocument();
    expect(screen.getByTestId("work-request-submit")).toBeEnabled();
  });

  it("treats a network failure as unconfirmed", async () => {
    asSession(PERTAMINA_ENGINEER);
    createWorkRequest.mockRejectedValue(new TypeError("Failed to fetch"));
    render(<WorkRequestAction assetTag={TAG} />);
    openAndChoose("INSTALLATION");
    fillAndReview();
    fireEvent.click(screen.getByTestId("work-request-submit"));

    expect(await screen.findByTestId("work-request-error")).toHaveTextContent(/could not be confirmed/i);
    expect(screen.queryByTestId("work-request-success")).not.toBeInTheDocument();
  });

  it("does not claim success when the API response is not a confirmed request", async () => {
    asSession(PERTAMINA_ENGINEER);
    createWorkRequest.mockResolvedValue({ success: false });
    render(<WorkRequestAction assetTag={TAG} />);
    openAndChoose("PM");
    fillAndReview();
    fireEvent.click(screen.getByTestId("work-request-submit"));

    expect(await screen.findByTestId("work-request-error")).toHaveTextContent(/did not confirm/i);
    expect(screen.queryByTestId("work-request-success")).not.toBeInTheDocument();
  });

  it("disables submit while the request is in flight", async () => {
    asSession(PERTAMINA_ENGINEER);
    let resolve;
    createWorkRequest.mockReturnValue(new Promise((r) => { resolve = r; }));
    render(<WorkRequestAction assetTag={TAG} />);
    openAndChoose("PM");
    fillAndReview();
    fireEvent.click(screen.getByTestId("work-request-submit"));
    expect(screen.getByTestId("work-request-submit")).toBeDisabled();
    fireEvent.click(screen.getByTestId("work-request-submit"));
    expect(createWorkRequest).toHaveBeenCalledTimes(1);
    resolve({ success: true, data: { request_code: "WR-1", request_type: "PM", asset_code: TAG, status: "SUBMITTED" } });
    await waitFor(() => expect(screen.getByTestId("work-request-success")).toBeInTheDocument());
  });
});
