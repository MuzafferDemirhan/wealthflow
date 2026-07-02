import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { Table, type Column } from "@/components/ui/Table";

interface Item {
  id: string;
  name: string;
}

const columns: Column<Item>[] = [
  { key: "id", header: "ID" },
  { key: "name", header: "Name" },
];

const data: Item[] = [
  { id: "1", name: "Alice" },
  { id: "2", name: "Bob" },
];

describe("Table", () => {
  it("renders column headers", () => {
    render(<Table columns={columns} data={data} keyExtractor={(item) => item.id} />);
    expect(screen.getByText("ID")).toBeInTheDocument();
    expect(screen.getByText("Name")).toBeInTheDocument();
  });

  it("renders data rows", () => {
    render(<Table columns={columns} data={data} keyExtractor={(item) => item.id} />);
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
  });

  it("shows empty message when no data", () => {
    render(<Table columns={columns} data={[]} keyExtractor={(item) => item.id} emptyMessage="No items" />);
    expect(screen.getByText("No items")).toBeInTheDocument();
  });

  it("calls onRowClick when clicking a row", async () => {
    const onRowClick = vi.fn();
    render(<Table columns={columns} data={data} keyExtractor={(item) => item.id} onRowClick={onRowClick} />);
    await userEvent.click(screen.getByText("Alice"));
    expect(onRowClick).toHaveBeenCalledWith(data[0]);
  });

  it("shows spinner when loading", () => {
    render(<Table columns={columns} data={[]} loading keyExtractor={(item) => item.id} />);
    expect(document.querySelector("svg.animate-spin")).toBeInTheDocument();
  });
});
