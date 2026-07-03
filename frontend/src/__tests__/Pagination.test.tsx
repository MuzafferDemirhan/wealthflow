import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { Pagination } from "@/components/ui/Pagination";

describe("Pagination", () => {
  it("renders nothing when total pages is 1", () => {
    const { container } = render(
      <Pagination offset={0} limit={50} total={30} onChange={vi.fn()} />,
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders page info", () => {
    render(<Pagination offset={0} limit={10} total={100} onChange={vi.fn()} />);
    expect(screen.getByText("1–10 of 100")).toBeInTheDocument();
  });

  it("calls onChange with next offset", async () => {
    const onChange = vi.fn();
    render(<Pagination offset={0} limit={10} total={100} onChange={onChange} />);
    await userEvent.click(screen.getByText("Next"));
    expect(onChange).toHaveBeenCalledWith(10);
  });

  it("calls onChange with previous offset", async () => {
    const onChange = vi.fn();
    render(<Pagination offset={20} limit={10} total={100} onChange={onChange} />);
    await userEvent.click(screen.getByText("Prev"));
    expect(onChange).toHaveBeenCalledWith(10);
  });

  it("disables prev on first page", () => {
    render(<Pagination offset={0} limit={10} total={100} onChange={vi.fn()} />);
    expect(screen.getByText("Prev")).toBeDisabled();
  });

  it("disables next on last page", () => {
    render(<Pagination offset={90} limit={10} total={100} onChange={vi.fn()} />);
    expect(screen.getByText("Next")).toBeDisabled();
  });
});
