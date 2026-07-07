import { describe, expect, it, vi } from "vitest";
import { createLiveStreamClient } from "./liveStreamClient";

describe("createLiveStreamClient", () => {
  it("connects to the live stream endpoint and parses events", () => {
    const close = vi.fn();
    let instance;

    global.EventSource = vi.fn((endpoint) => {
      instance = {
        endpoint,
        close,
        onmessage: null,
        onerror: null,
      };

      return instance;
    });

    const onEvent = vi.fn();

    const client = createLiveStreamClient({
      endpoint: "/api/studio/events/stream",
      onEvent,
    });

    expect(global.EventSource).toHaveBeenCalledWith("/api/studio/events/stream");

    instance.onmessage({
      data: JSON.stringify({
        event_type: "OSA_RUNTIME_UPDATED",
        status: "ACTIVE",
      }),
    });

    expect(onEvent).toHaveBeenCalledWith({
      event_type: "OSA_RUNTIME_UPDATED",
      status: "ACTIVE",
    });

    client.close();

    expect(close).toHaveBeenCalled();
  });

  it("reports parse errors", () => {
    global.EventSource = vi.fn(() => ({
      close: vi.fn(),
      onmessage: null,
      onerror: null,
    }));

    const onError = vi.fn();

    createLiveStreamClient({
      onError,
    });

    const instance = global.EventSource.mock.results[0].value;

    instance.onmessage({
      data: "not-json",
    });

    expect(onError).toHaveBeenCalled();
  });
});
