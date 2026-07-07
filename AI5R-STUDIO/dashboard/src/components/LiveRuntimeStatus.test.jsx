import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import LiveRuntimeStatus from "./LiveRuntimeStatus";

describe("LiveRuntimeStatus", () => {
  it("shows live status after receiving a runtime event", async () => {
    let instance;

    global.EventSource = vi.fn(function EventSourceMock() {
      instance = {
        close: vi.fn(),
        onmessage: null,
        onerror: null,
      };

      return instance;
    });

    render(<LiveRuntimeStatus />);

    expect(screen.getByText("CONNECTING")).toBeTruthy();

    instance.onmessage({
      data: JSON.stringify({
        event_type: "OSA_RUNTIME_HEARTBEAT",
        status: "ACTIVE",
      }),
    });

    await waitFor(() => {
      expect(screen.getByText("LIVE")).toBeTruthy();
      expect(screen.getByText("OSA_RUNTIME_HEARTBEAT")).toBeTruthy();
    });
  });

  it("shows reconnecting status when stream errors", async () => {
    let instance;

    global.EventSource = vi.fn(function EventSourceMock() {
      instance = {
        close: vi.fn(),
        onmessage: null,
        onerror: null,
      };

      return instance;
    });

    render(<LiveRuntimeStatus />);

    instance.onerror({});

    await waitFor(() => {
      expect(screen.getByText("RECONNECTING")).toBeTruthy();
    });
  });
});
