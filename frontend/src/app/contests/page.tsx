"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet } from "@/lib/api/client";
import { contests as contestEndpoints } from "@/lib/api/endpoints";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { ContestList } from "@/components/contest/ContestList";
import { useAuth } from "@/hooks/useAuth";
import { useMyContests } from "@/hooks/useMyContests";
import { useContest } from "@/hooks/useContest";
import { isSupervisorOrAbove } from "@/lib/auth/guards";
import { resolveDefaultContestId } from "@/lib/contest/resolveDefaultContestId";
import type { ContestListItem, ContestOut } from "@/types/api";

export default function ContestsPage() {
  return (
    <ProtectedRoute requireAuth requireNotTempPassword>
      <ContestsContent />
    </ProtectedRoute>
  );
}

function ContestsContent() {
  const { role } = useAuth();
  const { contests: myContests, loading: myLoading } = useMyContests(role === "USER");
  const [supervisorContests, setSupervisorContests] = useState<ContestListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const { setContestId } = useContest();
  const router = useRouter();

  useEffect(() => {
    if (!isSupervisorOrAbove(role)) return;
    const load = async () => {
      setLoading(true);
      try {
        const data = await apiGet<ContestOut[]>(contestEndpoints.list());
        setSupervisorContests(data.map((c) => ({ id: c.id, name: c.name, status: c.status })));
      } catch {
        setSupervisorContests([
          {
            id: resolveDefaultContestId(),
            name: "Конкурс по умолчанию",
            status: "RUNNING",
          },
        ]);
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [role]);

  const items = isSupervisorOrAbove(role) ? supervisorContests : myContests;
  const isLoading = isSupervisorOrAbove(role) ? loading : myLoading;

  const handleSelect = async (id: number) => {
    await setContestId(id, isSupervisorOrAbove(role));
    router.push(`/contest/${id}`);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Конкурсы</h1>
      <ContestList contests={items} loading={isLoading} onSelect={handleSelect} />
    </div>
  );
}
