"use client";

import type { ReactNode } from "react";
import { deriveAdminUiMode } from "@/lib/admin/deriveAdminUiMode";
import { LockBanner } from "@/components/admin/LockBanner";
import { ContestStatusBanner } from "@/components/admin/ContestStatusBanner";
import { SettingsSubNav } from "@/components/admin/SettingsSubNav";
import { useContestAdmin } from "@/hooks/useContestAdmin";
import { LoadingState } from "@/components/ui/LoadingState";

interface AdminPageShellProps {
  title: string;
  children: ReactNode;
  showSettingsNav?: boolean;
  /** Show LockBanner — only relevant on /admin/settings/* pages. Default: false. */
  showSetupLockBanner?: boolean;
}

export function AdminPageShell({
  title,
  children,
  showSettingsNav = false,
  showSetupLockBanner = false,
}: AdminPageShellProps) {
  const { contest, contestId, loading } = useContestAdmin();
  const uiMode = deriveAdminUiMode({ contest, round: null });
  const contestReady = contest != null && contest.id === contestId;

  if (loading || !contestReady) {
    return <LoadingState message="Загрузка конкурса…" />;
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      {contest && (
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          {contest.name} — {title}
        </h1>
      )}
      {!contest && <h1 className="text-2xl font-bold text-gray-900 mb-2">{title}</h1>}

      {showSetupLockBanner && uiMode.showSetupLockBanner && <LockBanner />}
      {uiMode.showPausedBanner && <ContestStatusBanner status="PAUSED" />}
      {uiMode.showFinishedBanner && <ContestStatusBanner status="FINISHED" />}

      {showSettingsNav && <SettingsSubNav />}
      {children}
    </div>
  );
}
