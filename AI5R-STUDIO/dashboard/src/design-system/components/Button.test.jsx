import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Button from "./Button";

describe("Button", () => {
  it("renders its children as label text", () => {
    render(<Button>Execute</Button>);

    expect(screen.getByRole("button", { name: "Execute" })).toBeTruthy();
  });

  it("calls onClick when clicked", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Execute</Button>);

    fireEvent.click(screen.getByRole("button", { name: "Execute" }));

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("respects the disabled prop", () => {
    render(<Button disabled>Execute</Button>);

    expect(screen.getByRole("button", { name: "Execute" }).disabled).toBe(true);
  });

  it("defaults type to button, not submit", () => {
    render(<Button>Execute</Button>);

    expect(screen.getByRole("button", { name: "Execute" }).type).toBe("button");
  });

  it("allows overriding type, e.g. for form submission", () => {
    render(<Button type="submit">Execute</Button>);

    expect(screen.getByRole("button", { name: "Execute" }).type).toBe("submit");
  });
});
