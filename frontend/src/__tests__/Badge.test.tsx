import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Badge } from "@/components/ui/Badge";

describe("Badge", () => {
  it("renders children", () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("applies variant styles", () => {
    const { rerender } = render(<Badge variant="success">Success</Badge>);
    expect(screen.getByText("Success")).toHaveClass("bg-emerald-100");

    rerender(<Badge variant="error">Error</Badge>);
    expect(screen.getByText("Error")).toHaveClass("bg-red-100");

    rerender(<Badge variant="warning">Warning</Badge>);
    expect(screen.getByText("Warning")).toHaveClass("bg-amber-100");

    rerender(<Badge variant="info">Info</Badge>);
    expect(screen.getByText("Info")).toHaveClass("bg-blue-100");

    rerender(<Badge variant="neutral">Neutral</Badge>);
    expect(screen.getByText("Neutral")).toHaveClass("bg-zinc-100");
  });
});
