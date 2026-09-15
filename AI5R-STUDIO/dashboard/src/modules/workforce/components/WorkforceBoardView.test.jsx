import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import WorkforceBoardView from "./WorkforceBoardView";

describe("WorkforceBoardView", () => {
  const mockBoard = {
    published: [
      {
        work_item_id: "WORK-PUB-01",
        title: "Setup Vitest CI",
        assigned_position_id: "QA_ENGINEER",
        status: "PUBLISHED",
      },
    ],
    claimed: [
      {
        work_item_id: "WORK-CLM-01",
        title: "Implement API Adapter",
        assigned_position_id: "BACKEND_ENGINEER",
        assigned_employee_id: "EMP-BE-01",
        status: "CLAIMED",
      },
    ],
    completed: [
      {
        work_item_id: "WORK-PROD-01",
        title: "Production Cluster Deployment",
        assigned_position_id: "DEVOPS_ENGINEER",
        assigned_employee_id: "EMP-DEVOPS-01",
        status: "COMPLETED",
        is_production: true,
        metadata: { is_production: true },
      },
    ],
    released: [
      {
        work_item_id: "WORK-REL-01",
        title: "Documentation Update",
        assigned_position_id: "DOCUMENTATION_ENGINEER",
        status: "RELEASED",
      },
    ],
  };

  it("renders all 4 columns with titles and items", () => {
    render(<WorkforceBoardView board={mockBoard} />);

    expect(screen.getByText("Available Queue")).toBeDefined();
    expect(screen.getByText("In Progress")).toBeDefined();
    expect(screen.getByText("Completed / Review")).toBeDefined();
    expect(screen.getByText("Released")).toBeDefined();

    expect(screen.getByText("Setup Vitest CI")).toBeDefined();
    expect(screen.getByText("Implement API Adapter")).toBeDefined();
    expect(screen.getByText("Production Cluster Deployment")).toBeDefined();
    expect(screen.getByText("Documentation Update")).toBeDefined();
  });

  it("renders the Chief Approval Required indicator on unapproved production items", () => {
    render(<WorkforceBoardView board={mockBoard} />);

    expect(
      screen.getByText("⚠️ CHIEF APPROVAL REQUIRED BEFORE RELEASE")
    ).toBeDefined();
    expect(screen.getByText("PRODUCTION")).toBeDefined();
  });
});

