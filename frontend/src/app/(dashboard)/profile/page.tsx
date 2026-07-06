"use client";

import { useAuth } from "@/lib/auth-context";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";

export default function ProfilePage() {
  const { user, isLoading } = useAuth();

  if (isLoading || !user) {
    return (
      <div className="space-y-8">
        <Skeleton className="h-9 w-32" />
        <div className="rounded-xl border border-outline-variant bg-surface p-6 space-y-4">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-5 w-60" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-medium tracking-tight text-on-surface">Profile</h1>

      <Card>
        <div className="space-y-4">
          <div>
            <p className="text-xs text-on-surface-variant">Full Name</p>
            <p className="text-sm font-medium text-on-surface">{user.full_name}</p>
          </div>
          <div>
            <p className="text-xs text-on-surface-variant">Email</p>
            <p className="text-sm font-medium text-on-surface">{user.email}</p>
          </div>
        </div>
      </Card>
    </div>
  );
}
