import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import SearchBox from "./SearchBox";

describe("SearchBox", () => {
  it("renders a text input with the given placeholder", () => {
    render(<SearchBox placeholder="Search agents..." value="" onChange={() => {}} />);

    expect(screen.getByPlaceholderText("Search agents...")).toBeTruthy();
  });

  it("calls onChange with the typed value", () => {
    const onChange = vi.fn();
    render(<SearchBox value="" onChange={onChange} />);

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "abc" } });

    expect(onChange).toHaveBeenCalledWith("abc");
  });
});
