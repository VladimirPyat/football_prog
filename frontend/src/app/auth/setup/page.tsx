"use client";

import { Suspense } from "react";
import { SetupPasswordForm } from "@/components/auth/SetupPasswordForm";
import { LoadingState } from "@/components/ui/LoadingState";

export default function AuthSetupPage() {
  return (
    <div className="max-w-md mx-auto">
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Подтверждение участия</h1>
        <p className="text-gray-600 text-sm mb-6">Перейдите по ссылке из письма приглашения.</p>
        <Suspense fallback={<LoadingState />}>
          <SetupPasswordForm />
        </Suspense>
      </div>
    </div>
  );
}
