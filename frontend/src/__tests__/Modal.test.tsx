import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { Modal } from "@/components/ui/Modal";

describe("Modal", () => {
  it("renders nothing when closed", () => {
    render(<Modal open={false} onClose={vi.fn()}><div>Content</div></Modal>);
    expect(screen.queryByText("Content")).not.toBeInTheDocument();
  });

  it("renders content when open", () => {
    render(<Modal open={true} onClose={vi.fn()} title="My Modal"><div>Content</div></Modal>);
    expect(screen.getByText("My Modal")).toBeInTheDocument();
    expect(screen.getByText("Content")).toBeInTheDocument();
  });

  it("calls onClose when clicking the close button", async () => {
    const onClose = vi.fn();
    render(<Modal open={true} onClose={onClose} title="Title"><div>Content</div></Modal>);
    await userEvent.click(screen.getByLabelText("Close"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("calls onClose on Escape key", async () => {
    const onClose = vi.fn();
    render(<Modal open={true} onClose={onClose}><div>Content</div></Modal>);
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("renders title when provided", () => {
    render(<Modal open={true} onClose={vi.fn()} title="Test Title"><div>Content</div></Modal>);
    expect(screen.getByText("Test Title")).toBeInTheDocument();
  });
});
