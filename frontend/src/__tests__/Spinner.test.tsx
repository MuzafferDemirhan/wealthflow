import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Spinner } from "@/components/ui/Spinner";

describe("Spinner", () => {
  it("renders an SVG", () => {
    const { container } = render(<Spinner />);
    expect(container.querySelector("svg")).toBeInTheDocument();
  });

  it("applies size classes", () => {
    const { container: sm } = render(<Spinner size="sm" />);
    expect(sm.querySelector("svg")).toHaveClass("h-4");

    const { container: lg } = render(<Spinner size="lg" />);
    expect(lg.querySelector("svg")).toHaveClass("h-12");
  });
});
