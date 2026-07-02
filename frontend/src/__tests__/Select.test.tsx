import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { Select } from "@/components/ui/Select";

describe("Select", () => {
  const options = [
    { value: "a", label: "Option A" },
    { value: "b", label: "Option B" },
  ];

  it("renders with label", () => {
    render(<Select label="Category" options={options} />);
    expect(screen.getByLabelText("Category")).toBeInTheDocument();
  });

  it("renders options", () => {
    render(<Select label="Cat" options={options} />);
    expect(screen.getByText("Option A")).toBeInTheDocument();
    expect(screen.getByText("Option B")).toBeInTheDocument();
  });

  it("renders placeholder when provided", () => {
    render(<Select label="Cat" options={options} placeholder="Choose..." />);
    expect(screen.getByText("Choose...")).toBeInTheDocument();
  });

  it("calls onChange when selection changes", async () => {
    const onChange = vi.fn();
    render(<Select label="Cat" options={options} onChange={onChange} />);
    await userEvent.selectOptions(screen.getByLabelText("Cat"), "a");
    expect(onChange).toHaveBeenCalled();
  });

  it("shows error message", () => {
    render(<Select label="Cat" options={options} error="Required" />);
    expect(screen.getByText("Required")).toBeInTheDocument();
  });
});
