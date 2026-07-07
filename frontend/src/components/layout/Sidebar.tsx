"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useTheme } from "@/hooks/useTheme";

interface NavGroup {
  label: string | null;
  hasSeparator?: boolean;
  items: {
    label: string;
    href: string;
    subtitle?: string;
  }[];
}

const navGroups: NavGroup[] = [
  {
    label: null,
    items: [{ label: "Home", href: "/" }],
  },
  {
    label: "CORE",
    items: [
      { label: "Accounts", href: "/accounts", subtitle: "Detailed balances" },
      { label: "Transactions", href: "/transactions", subtitle: "History and search" },
      { label: "Budgets", href: "/budgets", subtitle: "Planning tools" },
      { label: "Portfolio", href: "/portfolio", subtitle: "Selected - showing active focus" },
    ],
  },
  {
    label: "REPORTS",
    hasSeparator: true,
    items: [
      { label: "Category Breakdown", href: "/reports/category-breakdown" },
      { label: "Income vs Expenses", href: "/reports/income-vs-expenses" },
      { label: "Monthly Trends", href: "/reports/monthly-trends" },
      { label: "Net Worth", href: "/reports/net-worth" },
    ],
  },
  {
    label: "AI",
    items: [
      { label: "AI Advisor", href: "/chat", subtitle: "Financial assistant" },
    ],
  },
  {
    label: "ACCOUNT",
    hasSeparator: true,
    items: [
      { label: "Bank Connections", href: "/connect" },
      { label: "Profile", href: "/profile" },
    ],
  },
];

interface SidebarProps {
  isOpen: boolean;
  onNav?: () => void;
  onClose?: () => void;
}

function getFirstName(fullName: string): string {
  return fullName.split(" ")[0] ?? fullName;
}

function getLastName(fullName: string): string {
  const parts = fullName.split(" ");
  return parts.length > 1 ? parts[parts.length - 1] : "";
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function Sidebar({ isOpen, onNav, onClose }: SidebarProps) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  const firstName = user?.full_name ? getFirstName(user.full_name) : "";
  const lastName = user?.full_name ? getLastName(user.full_name) : "";

  return (
    <aside
      className={`flex h-full flex-col border-r border-outline-variant bg-surface transition-all duration-300 ease-in-out ${
        isOpen ? "w-64" : "w-0 overflow-hidden"
      }`}
    >
      <div className="flex h-16 shrink-0 items-center gap-3 px-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
          <svg className="h-4 w-4 text-on-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <span className="text-lg font-semibold tracking-tight text-on-surface">WealthFlow</span>
      </div>

      <div className="shrink-0 px-6 pb-3">
        <p className="text-sm text-on-surface-variant">
          Welcome back, {firstName} {lastName}
        </p>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 pb-4">
        {navGroups.map((group) => (
          <div key={group.label ?? "root"}>
            {group.hasSeparator && (
              <div className="my-3 border-t border-outline-variant" />
            )}

            {group.label && (
              <div className="mb-1 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-widest text-on-surface-variant/60">
                {group.label}
              </div>
            )}

            {group.items.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={onNav}
                className={`flex flex-col rounded-lg px-3 py-2 text-sm transition-colors ${
                  isActive(item.href)
                    ? "bg-primary/10 font-medium text-primary"
                    : "text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface"
                }`}
              >
                <span>{item.label}</span>
                {item.subtitle && (
                  <span className="text-[11px] text-on-surface-variant/60">{item.subtitle}</span>
                )}
              </Link>
            ))}
          </div>
        ))}
      </nav>

      <div className="shrink-0 border-t border-outline-variant p-4">
        <button
          onClick={toggleTheme}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface transition-colors"
        >
          {theme === "dark" ? (
            <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          ) : (
            <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
          )}
          <span>Site Settings</span>
        </button>
      </div>

      <div className="shrink-0 border-t border-outline-variant p-4">
        <div className="flex items-center justify-between">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-on-surface">{user?.full_name}</p>
            <p className="truncate text-xs text-on-surface-variant">{user?.email}</p>
          </div>
          <button
            onClick={logout}
            className="rounded-lg p-2 text-on-surface-variant hover:text-error transition-colors"
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
