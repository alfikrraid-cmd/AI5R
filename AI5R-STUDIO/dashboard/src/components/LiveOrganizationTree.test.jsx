import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import LiveOrganizationTree from "./LiveOrganizationTree";

describe("LiveOrganizationTree", () => {
  it("renders organization snapshot events", async () => {
    let instance;

    global.EventSource = vi.fn(function EventSourceMock() {
      instance = {
        close: vi.fn(),
        onmessage: null,
        onerror: null,
      };

      return instance;
    });

    render(<LiveOrganizationTree />);

    instance.onmessage({
      data: JSON.stringify({
        event_type: "ORGANIZATION_SNAPSHOT",
        departments: [
          {
            department_id: "dept-001",
            name: "Strategy",
          },
        ],
        workers: [
          {
            worker_id: "worker-001",
            name: "Ra'id",
            status: "ACTIVE",
          },
        ],
      }),
    });

    await waitFor(() => {
      expect(screen.getByText("Strategy")).toBeTruthy();
      expect(screen.getByText("Ra'id — ACTIVE")).toBeTruthy();
    });
  });
});
