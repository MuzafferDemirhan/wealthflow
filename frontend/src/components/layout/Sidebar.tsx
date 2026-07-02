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
    <aside className="flex h-full w-64 flex-col border-r border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex h-14 items-center gap-2 border-b border-zinc-200 px-5 dark:border-zinc-800">
        <span className="text-lg font-bold tracking-tight">WealthFlow</span>
      </div>

      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {navItems.map((item) => {
          if ("children" in item && item.children) {
            const open = item.children.some((c) => isActive(c.href));
            return (
              <div key={item.label}>
                <div className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-zinc-500">
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
                          ? "bg-zinc-100 font-medium text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50"
                          : "text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-50"
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
                  ? "bg-zinc-100 font-medium text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50"
                  : "text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-50"
              }`}
            >
              <span className="w-5 text-center">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-zinc-200 p-3 dark:border-zinc-800">
        <div className="flex items-center justify-between">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{user?.full_name}</p>
            <p className="truncate text-xs text-zinc-500">{user?.email}</p>
          </div>
          <button
            onClick={logout}
            className="rounded-lg px-2 py-1 text-xs text-zinc-500 hover:text-red-600 transition-colors"
            title="Sign out"
          >
            ✕
          </button>
        </div>
      </div>
    </aside>
  );
}
