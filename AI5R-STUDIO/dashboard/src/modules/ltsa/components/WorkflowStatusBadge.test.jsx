import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TechnicalOutcomeBadge, WorkflowStatusBadge } from "./WorkflowStatusBadge";

describe("WorkflowStatusBadge", () => {
  it("renders each real backend workflow_status value honestly", () => {
    for (const status of ["DRAFT", "SUBMITTED", "RETURNED_FOR_CORRECTION", "FINALIZED"]) {
      const { unmount } = render(<WorkflowStatusBadge status={status} />);
      expect(screen.getByText(status.replace(/_/g, " "))).toBeTruthy();
      unmount();
    }
  });

  it("renders UNKNOWN rather than fabricating a status when none is given", () => {
    render(<WorkflowStatusBadge status={null} />);
    expect(screen.getByText("UNKNOWN")).toBeTruthy();
  });
});

describe("TechnicalOutcomeBadge", () => {
  it("renders nothing when there is no technical outcome yet -- never fabricates one", () => {
    const { container } = render(<TechnicalOutcomeBadge outcome={null} />);
    expect(container.textContent).toBe("");
  });

  it("renders ACKNOWLEDGED and TECHNICALLY_APPROVED as distinct, human-readable labels", () => {
    const { rerender } = render(<TechnicalOutcomeBadge outcome="ACKNOWLEDGED" />);
    expect(screen.getByText("Acknowledged")).toBeTruthy();

    rerender(<TechnicalOutcomeBadge outcome="TECHNICALLY_APPROVED" />);
    expect(screen.getByText("Technically Approved")).toBeTruthy();
  });

  it("is a visually separate concept from workflow status -- both can render together", () => {
    render(
      <div>
        <WorkflowStatusBadge status="FINALIZED" />
        <TechnicalOutcomeBadge outcome="TECHNICALLY_APPROVED" />
      </div>
    );

    expect(screen.getByText("FINALIZED")).toBeTruthy();
    expect(screen.getByText("Technically Approved")).toBeTruthy();
  });
});
