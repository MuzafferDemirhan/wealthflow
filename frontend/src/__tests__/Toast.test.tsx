import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { ToastProvider, useToast } from "@/components/ui/Toast";

function TestButton() {
  const { toast } = useToast();
  return <button onClick={() => toast("Hello", "success")}>Show Toast</button>;
}

describe("Toast", () => {
  it("renders toast message when triggered", async () => {
    render(
      <ToastProvider>
        <TestButton />
      </ToastProvider>,
    );
    await userEvent.click(screen.getByText("Show Toast"));
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  it("throws when useToast is used outside provider", () => {
    function BadComponent() {
      useToast();
      return null;
    }
    expect(() => render(<BadComponent />)).toThrow();
  });
});
