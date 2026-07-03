"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { PasswordInput } from "@/components/ui/PasswordInput";
import { ApiError } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

    if (!fullName || !email || !password || !confirmPassword) {
      setError("All fields are required");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setLoading(true);
    try {
      await register(email, password, fullName);
      router.replace("/login");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <h1 className="text-2xl font-bold tracking-tight text-text-primary">Create Account</h1>
      <p className="mt-1 text-sm text-text-secondary">Join WealthFlow today</p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4" autoComplete="off">
        {error && (
          <div className="rounded-lg bg-error/10 p-3 text-sm text-error">
            {error}
          </div>
        )}

        <Input
          label="Full Name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          placeholder="Name Surname"
          required
        />

        <Input
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          autoComplete="off"
          required
        />

        <PasswordInput
          label="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="At least 8 characters"
          autoComplete="new-password"
          required
        />

        <PasswordInput
          label="Confirm Password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          placeholder="Repeat your password"
          autoComplete="off"
          required
        />

        <Button type="submit" loading={loading} className="w-full">
          Create Account
        </Button>
      </form>

      <p className="mt-4 text-center text-sm text-text-secondary">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-brand hover:text-brand-hover">
          Sign in
        </Link>
      </p>
    </Card>
  );
}
