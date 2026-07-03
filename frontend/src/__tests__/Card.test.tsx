import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Card } from "@/components/ui/Card";

describe("Card", () => {
  it("renders children", () => {
    render(<Card><p>Content</p></Card>);
    expect(screen.getByText("Content")).toBeInTheDocument();
  });

  it("renders title when provided", () => {
    render(<Card title="My Card"><p>Content</p></Card>);
    expect(screen.getByText("My Card")).toBeInTheDocument();
  });

  it("renders action when provided", () => {
    render(<Card title="Card" action={<button>Action</button>}><p>Content</p></Card>);
    expect(screen.getByRole("button", { name: /action/i })).toBeInTheDocument();
  });
});
