import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { Input } from "@/components/ui/Input";

describe("Input", () => {
  it("renders with label", () => {
    render(<Input label="Email" />);
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
  });

  it("shows error message", () => {
    render(<Input label="Email" error="Invalid email" />);
    expect(screen.getByText("Invalid email")).toBeInTheDocument();
  });

  it("calls onChange when value changes", async () => {
    const onChange = vi.fn();
    render(<Input label="Name" onChange={onChange} />);
    const input = screen.getByLabelText("Name");
    await userEvent.type(input, "a");
    expect(onChange).toHaveBeenCalled();
  });

  it("forwards ref", () => {
    const ref = { current: null };
    render(<Input label="Test" ref={ref} />);
    expect(ref.current).toBeInstanceOf(HTMLInputElement);
  });
});
