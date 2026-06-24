"use client";

import { useEffect } from "react";
import { useContest } from "@/hooks/useContest";
import { resolveDefaultContestId } from "@/lib/contest/resolveDefaultContestId";

export default function AdminSettingsParametersPage() {
  const { contest, contestId, setContestId } = useContest();

  useEffect(() => {
    const id = contestId ?? resolveDefaultContestId();
    if (!contest) {
      void setContestId(id, true);
    }
  }, [contest, contestId, setContestId]);

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Управление конкурсом</h1>
      {contest && (
        <p className="text-gray-700 mb-4">
          Активный конкурс: <span className="font-medium">{contest.name}</span>
        </p>
      )}
      <p className="text-gray-600">Полный интерфейс настроек — этап 2.3</p>
    </div>
  );
}
