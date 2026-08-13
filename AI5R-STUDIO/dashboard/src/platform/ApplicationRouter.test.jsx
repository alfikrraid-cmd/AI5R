import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ApplicationRouter from "./ApplicationRouter";
import PlatformProvider from "./PlatformProvider";

vi.mock("./ApplicationAdapter", () => ({
  default: vi.fn(({ application, organizationContext }) => (
    <div
      data-testid="application-adapter"
      data-application={application?.applicationId ?? ""}
      data-organization={organizationContext?.slug ?? ""}
    />
  )),
}));

function renderRouter(pathname) {
  window.history.replaceState({}, "", pathname);
  render(
    <PlatformProvider>
      <ApplicationRouter />
    </PlatformProvider>
  );
  return screen.getByTestId("application-adapter");
}

afterEach(() => {
  window.history.replaceState({}, "", "/");
  vi.clearAllMocks();
});

describe("ApplicationRouter platform integration", () => {
  it("resolves / to the current platform behavior", () => {
    const adapter = renderRouter("/");

    expect(adapter.dataset.application).toBe("platform-home");
    expect(adapter.dataset.organization).toBe("");
  });

  it("resolves /ltsa to LTSA without organization context", () => {
    const adapter = renderRouter("/ltsa");

    expect(adapter.dataset.application).toBe("ltsa");
    expect(adapter.dataset.organization).toBe("");
  });

  it("resolves /ltsa/{organization} to LTSA with OrganizationContext", () => {
    const adapter = renderRouter("/ltsa/tap");

    expect(adapter.dataset.application).toBe("ltsa");
    expect(adapter.dataset.organization).toBe("tap");
  });

  it("does not resolve reserved LTSA workspace segments as organizations", () => {
    const adapter = renderRouter("/ltsa/pump/641-P-5");

    expect(adapter.dataset.application).toBe("ltsa");
    expect(adapter.dataset.organization).toBe("");
  });
});
