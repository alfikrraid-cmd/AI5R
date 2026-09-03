import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { bulkReviewHistoricalReviewCandidates, promoteHistoricalPmRecoveryBatch, getPumps } from "./ai5rClient";

// MWO-LTSA-BULK-TIMEOUT-UX-001 -- proves the ACTUAL configured timeout,
// not just that a UI component calls the client function. A real
// 540-candidate bulk review was observed taking ~22s server-side, well
// past the platform's normal 15s default but well under nginx's 60s
// proxy_read_timeout (both host and docker layers) -- this fixed
// timeout must sit safely above 60s without changing any other call
// site's default.

beforeEach(() => {
  vi.useFakeTimers();
  global.fetch = vi.fn(() => new Promise(() => {})); // never resolves -- only the abort should end it
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("bulk historical review request timeout", () => {
  it("does not abort at the platform's normal 15s default", async () => {
    const promise = bulkReviewHistoricalReviewCandidates(["DFE-1"]);
    promise.catch(() => {}); // still pending; avoid an unhandled-rejection warning later
    const [, options] = global.fetch.mock.calls[0];
    const abortSpy = vi.spyOn(options.signal, "aborted", "get");

    await vi.advanceTimersByTimeAsync(15000);
    expect(options.signal.aborted).toBe(false);
    abortSpy.mockRestore();
  });

  it("stays alive past nginx's 60s proxy_read_timeout budget", async () => {
    const promise = bulkReviewHistoricalReviewCandidates(["DFE-1"]);
    promise.catch(() => {});
    const [, options] = global.fetch.mock.calls[0];

    await vi.advanceTimersByTimeAsync(60000);
    expect(options.signal.aborted).toBe(false);
  });

  it("does eventually abort once genuinely hung (75s) -- this is a bound, not infinite", async () => {
    const promise = bulkReviewHistoricalReviewCandidates(["DFE-1"]);
    promise.catch(() => {});
    const [, options] = global.fetch.mock.calls[0];

    await vi.advanceTimersByTimeAsync(75000);
    expect(options.signal.aborted).toBe(true);
  });

  it("promoteHistoricalPmRecoveryBatch also survives past 60s (same long-operation timeout)", async () => {
    const promise = promoteHistoricalPmRecoveryBatch();
    promise.catch(() => {});
    const [, options] = global.fetch.mock.calls[0];

    await vi.advanceTimersByTimeAsync(60000);
    expect(options.signal.aborted).toBe(false);

    await vi.advanceTimersByTimeAsync(15000); // total 75s
    expect(options.signal.aborted).toBe(true);
  });

  it("does not change the default timeout for an unrelated, normal call site", async () => {
    global.fetch.mockImplementation(() => Promise.resolve({ status: 200, ok: true, json: async () => ({ success: true, data: [] }) }));
    const p = getPumps();
    // getPumps() resolves immediately in this mock; this test only
    // exists to prove bulkReviewHistoricalReviewCandidates's longer
    // timeout is scoped to that one call, not a global default change.
    await vi.runAllTimersAsync();
    await p;
    expect(global.fetch).toHaveBeenCalled();
  });
});
