"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { isSupervisorOrAbove } from "@/lib/auth/guards";
import { usePublicContests } from "@/hooks/usePublicContests";
import { useContest } from "@/hooks/useContest";
import { ContestList } from "@/components/contest/ContestList";
import { LoadingState } from "@/components/ui/LoadingState";
import { resolveDefaultContestId } from "@/lib/contest/resolveDefaultContestId";
import { consumeSkipHomeRedirect } from "@/lib/auth/postLoginNavigation";

export default function HomePage() {
  const { isAuthenticated, loading: authLoading, user } = useAuth();
  const { contests, loading: contestsLoading } = usePublicContests();
  const { setContestId } = useContest();
  const router = useRouter();

  useEffect(() => {
    if (authLoading) return;
    if (consumeSkipHomeRedirect()) return;
    if (isAuthenticated && user) {
      if (isSupervisorOrAbove(user.role)) {
        router.replace("/admin");
      } else {
        router.replace("/contests");
      }
    }
  }, [isAuthenticated, authLoading, user, router]);

  useEffect(() => {
    if (authLoading || isAuthenticated || contestsLoading) return;
    if (!contests.length) {
      const defaultId = resolveDefaultContestId();
      void setContestId(defaultId);
      router.replace(`/contest/${defaultId}`);
    }
  }, [authLoading, isAuthenticated, contestsLoading, contests.length, router, setContestId]);

  const handleSelect = async (id: number) => {
    await setContestId(id);
    router.push(`/contest/${id}`);
  };

  if (authLoading || isAuthenticated) {
    return <LoadingState />;
  }

  if (contestsLoading) {
    return <LoadingState />;
  }

  if (!contests.length) {
    return <LoadingState message="Переход к конкурсу…" />;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Конкурс спортивных прогнозов</h1>
      <p className="text-gray-600 mb-6">Выберите конкурс для просмотра</p>
      <ContestList contests={contests} onSelect={handleSelect} title="Активные конкурсы" />
    </div>
  );
}
