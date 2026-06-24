"use client";

import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { ContactsForm } from "@/components/profile/ContactsForm";
import { ProfileMenu } from "@/components/profile/ProfileMenu";
import { useAuth } from "@/hooks/useAuth";
import { LoadingState } from "@/components/ui/LoadingState";

export default function ProfilePage() {
  return (
    <ProtectedRoute requireAuth requireRole="USER" requireNotTempPassword>
      <ProfileContent />
    </ProtectedRoute>
  );
}

function ProfileContent() {
  const { user, loading } = useAuth();

  if (loading || !user) {
    return <LoadingState />;
  }

  const displayName = [user.last_name, user.first_name].filter(Boolean).join(" ") || user.login;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div className="md:col-span-1">
        <ProfileMenu />
      </div>
      <div className="md:col-span-2 space-y-6">
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-1">Личный кабинет</h1>
          <p className="text-gray-600">
            {displayName} ({user.login})
          </p>
        </div>
        <ContactsForm />
      </div>
    </div>
  );
}
