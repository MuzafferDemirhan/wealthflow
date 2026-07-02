"use client";

import { useState, useEffect, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { PasswordInput } from "@/components/ui/PasswordInput";
import { Spinner } from "@/components/ui/Spinner";
import { ApiError } from "@/lib/api-client";

export default function LoginPage() {
  const { login, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace("/accounts");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return <div className="flex items-center justify-center py-24"><Spinner size="lg" /></div>;
  }

  if (isAuthenticated) return null;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

    if (!email || !password) {
      setError("Email and password are required");
      return;
    }

    setSubmitting(true);
    try {
      await login(email, password);
      router.replace("/accounts");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Login failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Sign In</h1>
      <p className="mt-1 text-sm text-zinc-500">Access your WealthFlow account</p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        {error && (
          <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
            {error}
          </div>
        )}

        <Input
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          required
        />

        <PasswordInput
          label="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Enter your password"
          required
        />

        <Button type="submit" loading={submitting} className="w-full">
          Sign In
        </Button>
      </form>

      <p className="mt-4 text-center text-sm text-zinc-500">
        Don&apos;t have an account?{" "}
        <Link href="/register" className="font-medium text-zinc-900 underline dark:text-zinc-50">
          Create one
        </Link>
      </p>
    </div>
  );
}
