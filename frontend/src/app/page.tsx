export default function Home() {
  return (
    <div className="flex flex-col flex-1 items-center justify-center">
      <main className="flex flex-1 w-full max-w-3xl flex-col items-center justify-center py-32 px-16">
        <h1 className="text-4xl font-bold tracking-tight">WealthFlow</h1>
        <p className="mt-4 text-lg text-zinc-600 dark:text-zinc-400">
          Personal Finance & Investment Platform
        </p>
        <div className="mt-8 flex gap-4">
          <a
            href="/login"
            className="rounded-lg bg-zinc-900 px-6 py-3 text-sm font-medium text-white hover:bg-zinc-700 dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-200"
          >
            Sign In
          </a>
          <a
            href="/register"
            className="rounded-lg border border-zinc-300 px-6 py-3 text-sm font-medium hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
          >
            Create Account
          </a>
        </div>
      </main>
    </div>
  );
}