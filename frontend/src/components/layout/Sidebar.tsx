"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const navItems = [
  { label: "Dashboard", href: "/", icon: "◉" },
  { label: "Accounts", href: "/accounts", icon: "▣" },
  { label: "Transactions", href: "/transactions", icon: "⇄" },
  { label: "Budgets", href: "/budgets", icon: "◎" },
  { label: "Portfolio", href: "/portfolio", icon: "◆" },
  {
    label: "Reports",
    icon: "▤",
    children: [
      { label: "Category Breakdown", href: "/reports/category-breakdown" },
      { label: "Income vs Expenses", href: "/reports/income-vs-expenses" },
      { label: "Monthly Trends", href: "/reports/monthly-trends" },
      { label: "Net Worth", href: "/reports/net-worth" },
    ],
  },
  { label: "Bank Connections", href: "/connect", icon: "⊕" },
  { label: "Profile", href: "/profile", icon: "⊙" },
];

interface SidebarProps {
  onNav?: () => void;
}

export function Sidebar({ onNav }: SidebarProps) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <aside className="flex h-full w-64 flex-col border-r border-border bg-surface-dim">
      <div className="flex h-14 items-center gap-2 border-b border-border-light px-5">
        <span className="text-lg font-bold tracking-tight text-text-primary">WealthFlow</span>
      </div>

      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {navItems.map((item) => {
          if ("children" in item && item.children) {
            const open = item.children.some((c) => isActive(c.href));
            return (
              <div key={item.label}>
                <div className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-text-muted">
                  <span className="w-5 text-center">{item.icon}</span>
                  {item.label}
                </div>
                <div className="ml-4 space-y-0.5">
                  {item.children.map((child) => (
                    <Link
                      key={child.href}
                      href={child.href}
                      onClick={onNav}
                      className={`flex items-center gap-3 rounded-lg px-3 py-1.5 text-sm transition-colors ${
                        isActive(child.href)
                          ? "bg-brand/10 font-medium text-brand"
                          : "text-text-muted hover:text-text-primary hover:bg-surface-container-low"
                      }`}
                    >
                      {child.label}
                    </Link>
                  ))}
                </div>
              </div>
            );
          }

          return (
            <Link
              key={item.href}
              href={item.href!}
              onClick={onNav}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                isActive(item.href!)
                  ? "bg-brand/10 font-medium text-brand"
                  : "text-text-muted hover:text-text-primary hover:bg-surface-container-low"
              }`}
            >
              <span className="w-5 text-center">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border-light p-3">
        <div className="flex items-center justify-between">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-text-primary">{user?.full_name}</p>
            <p className="truncate text-xs text-text-muted">{user?.email}</p>
          </div>
          <button
            onClick={logout}
            className="rounded-lg px-2 py-1 text-xs text-text-muted hover:text-error transition-colors"
            title="Sign out"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </div>
    </aside>
  );
}
