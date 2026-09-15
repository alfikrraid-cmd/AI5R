import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import EmployeeCard from "./EmployeeCard";

describe("EmployeeCard", () => {
  const mockEmployee = {
    employee_id: "EMP-001",
    employee_name: "AI CTO",
    position_id: "CTO",
    role: "AI Chief Technology Officer",
    status: "WORKING",
    current_task: {
      task_id: "WORK-001",
      title: "Design Kernel Architecture",
      status: "CLAIMED",
    },
    task_progress: 65,
    skills: ["TECH_STRATEGY", "ARCHITECTURE", "SYSTEM_DESIGN", "SECURITY"],
  };

  it("renders employee details, role, status and progress", () => {
    render(<EmployeeCard employee={mockEmployee} />);

    expect(screen.getByText("AI CTO")).toBeDefined();
    expect(screen.getByText("AI Chief Technology Officer")).toBeDefined();
    expect(screen.getByText("WORKING")).toBeDefined();
    expect(screen.getByText("Design Kernel Architecture")).toBeDefined();
    expect(screen.getByText("65%")).toBeDefined();
    expect(screen.getByText("TECH_STRATEGY")).toBeDefined();
    expect(screen.getByText("ARCHITECTURE")).toBeDefined();
  });

  it("triggers onInspect when Inspect Profile button is clicked", () => {
    const handleInspect = vi.fn();
    render(<EmployeeCard employee={mockEmployee} onInspect={handleInspect} />);

    const button = screen.getByText("Inspect Profile");
    fireEvent.click(button);

    expect(handleInspect).toHaveBeenCalledWith(mockEmployee);
  });

  it("handles employee with no active task gracefully", () => {
    const idleEmployee = {
      ...mockEmployee,
      status: "AVAILABLE",
      current_task: null,
      task_progress: 0,
    };

    render(<EmployeeCard employee={idleEmployee} />);
    expect(screen.getByText("Ready for assignment")).toBeDefined();
    expect(screen.getByText("0%")).toBeDefined();
    expect(screen.getByText("AVAILABLE")).toBeDefined();
  });
});

