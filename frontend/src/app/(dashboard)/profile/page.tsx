"use client";

import { useAuth } from "@/lib/auth-context";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

export default function ProfilePage() {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Profile</h1>

      <Card className="max-w-lg">
        <div className="space-y-4">
          <div>
            <p className="text-xs text-zinc-500">Full Name</p>
            <p className="font-medium">{user.full_name}</p>
          </div>
          <div>
            <p className="text-xs text-zinc-500">Email</p>
            <p className="font-medium">{user.email}</p>
          </div>
          <div>
            <p className="text-xs text-zinc-500">Role</p>
            <Badge variant="info">{user.role}</Badge>
          </div>
          <div>
            <p className="text-xs text-zinc-500">Account Status</p>
            <Badge variant={user.is_active ? "success" : "error"}>
              {user.is_active ? "Active" : "Inactive"}
            </Badge>
          </div>
          <div>
            <p className="text-xs text-zinc-500">Member Since</p>
            <p className="font-medium">{new Date(user.created_at).toLocaleDateString()}</p>
          </div>
        </div>
      </Card>
    </div>
  );
}
