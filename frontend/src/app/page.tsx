"use client";

import { useAuth } from "@/lib/auth-context";
import { useTheme } from "@/hooks/useTheme";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";

function LandingHeader() {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="flex items-center justify-between border-b border-outline-variant px-6 py-4 sm:px-10">
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
          <svg className="h-4 w-4 text-on-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <span className="text-lg font-semibold text-on-surface">WealthFlow</span>
      </div>

      <nav className="hidden items-center gap-6 sm:flex">
        <a href="#" className="text-sm font-medium text-on-surface hover:text-primary transition-colors">Home</a>
        <a href="#about-us" className="text-sm text-on-surface-variant hover:text-on-surface transition-colors">About Us</a>
        <button
          onClick={toggleTheme}
          className="flex items-center gap-1.5 text-sm text-on-surface-variant hover:text-on-surface transition-colors"
        >
          {theme === "dark" ? (
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          ) : (
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
          )}
          Site Theme
        </button>
      </nav>

      <div className="flex items-center gap-3">
        <a href="/login">
          <Button variant="ghost" size="sm">Sign In</Button>
        </a>
        <a href="/register">
          <Button size="sm">Get Started</Button>
        </a>
      </div>
    </header>
  );
}

function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <LandingHeader />

      <main className="flex flex-1 flex-col items-center px-6 py-20 sm:px-10">
        {/* Hero */}
        <div className="mx-auto max-w-3xl text-center">
          <div className="mx-auto mb-8 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
            <svg className="h-8 w-8 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>

          <h1 className="text-[3.5rem] font-medium leading-tight tracking-tight text-on-surface sm:text-[3.563rem] sm:leading-[4rem]">
            Take control of your
            <br />
            financial future
          </h1>

          <p className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-on-surface-variant">
            Connect your bank accounts, track transactions, manage budgets and monitor your investments all in one place.
          </p>

          <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <a href="/register">
              <Button size="lg">Create Free Account</Button>
            </a>
            <a href="/login">
              <Button variant="tonal" size="lg">Sign In</Button>
            </a>
          </div>
        </div>

        {/* Features */}
        <div className="mt-24 grid w-full max-w-5xl gap-6 sm:grid-cols-3">
          <div className="rounded-xl border border-outline-variant bg-surface p-6">
            <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <svg className="h-5 w-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
              </svg>
            </div>
            <h3 className="text-base font-semibold text-on-surface">Connect Banks</h3>
            <p className="mt-2 text-sm text-on-surface-variant">
              Securely link your accounts via Plaid and automatically sync transactions.
            </p>
          </div>

          <div className="rounded-xl border border-outline-variant bg-surface p-6">
            <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <svg className="h-5 w-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h3 className="text-base font-semibold text-on-surface">Track Spending</h3>
            <p className="mt-2 text-sm text-on-surface-variant">
              Categorize transactions, set budgets and visualize your spending patterns.
            </p>
          </div>

          <div className="rounded-xl border border-outline-variant bg-surface p-6">
            <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <svg className="h-5 w-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
            <h3 className="text-base font-semibold text-on-surface">Monitor Investments</h3>
            <p className="mt-2 text-sm text-on-surface-variant">
              Track your portfolio, view allocation and measure performance over time.
            </p>
          </div>
        </div>

        {/* About Me */}
        <section className="mt-24 max-w-3xl text-center">
          <h2 className="text-2xl font-semibold text-on-surface">About Me</h2>
          <p className="mt-4 text-base leading-relaxed text-on-surface-variant">
            Hi, I&apos;m a software engineer passionate about building tools that help people take
            control of their financial lives. WealthFlow is the result of combining modern web
            technology with practical personal finance concepts. When I&apos;m not coding, I enjoy exploring financial
            markets, reading about behavioral economics and finding better ways to manage money.
          </p>
        </section>

        {/* About Us */}
        <section id="about-us" className="mt-24 w-full max-w-5xl">
          <h2 className="text-2xl font-semibold text-on-surface text-center">About WealthFlow</h2>
          <p className="mt-4 text-base leading-relaxed text-on-surface-variant text-center max-w-3xl mx-auto">
            WealthFlow is an open-source personal finance platform that gives you full visibility
            into your financial life. Connect your bank accounts, track transactions, set budgets
            and monitor your investments. Built with Next.js, FastAPI and Plaid. It&apos;s designed to be secure, fast and completely under your control.
          </p>
          <div className="mt-10 grid gap-6 sm:grid-cols-3 text-center">
            <div className="p-6">
              <h3 className="font-semibold text-on-surface">Open Source</h3>
              <p className="mt-2 text-sm text-on-surface-variant">
                Fully transparent codebase. No hidden fees, no data selling.
              </p>
            </div>
            <div className="p-6">
              <h3 className="font-semibold text-on-surface">Privacy First</h3>
              <p className="mt-2 text-sm text-on-surface-variant">
                Your financial data stays yours. End-to-end encryption.
              </p>
            </div>
            <div className="p-6">
              <h3 className="font-semibold text-on-surface">Self-Hostable</h3>
              <p className="mt-2 text-sm text-on-surface-variant">
                Run your own instance. Full control over your data.
              </p>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

function DashboardHome() {
  const { user } = useAuth();
  const firstName = user?.full_name ? user.full_name.split(" ")[0] ?? user.full_name : "";

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-medium tracking-tight text-on-surface">
          Welcome back, {firstName}
        </h1>
        <p className="mt-1 text-sm text-on-surface-variant">
          Here&apos;s an overview of your financial world.
        </p>
      </div>

      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <a href="/accounts" className="block">
          <Card>
            <p className="font-medium text-on-surface">Accounts</p>
            <p className="text-xs text-on-surface-variant mt-1">Detailed balances</p>
          </Card>
        </a>
        <a href="/transactions" className="block">
          <Card>
            <p className="font-medium text-on-surface">Transactions</p>
            <p className="text-xs text-on-surface-variant mt-1">History and search</p>
          </Card>
        </a>
        <a href="/budgets" className="block">
          <Card>
            <p className="font-medium text-on-surface">Budgets</p>
            <p className="text-xs text-on-surface-variant mt-1">Planning tools</p>
          </Card>
        </a>
        <a href="/portfolio" className="block">
          <Card>
            <p className="font-medium text-on-surface">Portfolio</p>
            <p className="text-xs text-on-surface-variant mt-1">Selected - showing active focus</p>
          </Card>
        </a>
      </div>

      <div className="rounded-xl border border-outline-variant bg-surface p-6">
        <h2 className="text-base font-semibold text-on-surface">Quick Links</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <a href="/reports/category-breakdown" className="text-sm text-primary hover:underline">
            Category Breakdown
          </a>
          <a href="/reports/income-vs-expenses" className="text-sm text-primary hover:underline">
            Income vs Expenses
          </a>
          <a href="/reports/monthly-trends" className="text-sm text-primary hover:underline">
            Monthly Trends
          </a>
          <a href="/reports/net-worth" className="text-sm text-primary hover:underline">
            Net Worth
          </a>
          <a href="/connect" className="text-sm text-primary hover:underline">
            Bank Connections
          </a>
          <a href="/profile" className="text-sm text-primary hover:underline">
            Profile
          </a>
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LandingPage />;
  }

  return (
    <DashboardLayout>
      <DashboardHome />
    </DashboardLayout>
  );
}
