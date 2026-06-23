"use client";

import { useEffect } from "react";
import { useParams } from "next/navigation";
import { useContest } from "@/hooks/useContest";

export default function ContestPage() {
  const params = useParams();
  const contestId = Number(params.contestId);
  const { setContestId } = useContest();

  useEffect(() => {
    if (Number.isInteger(contestId) && contestId > 0) {
      void setContestId(contestId);
    }
  }, [contestId, setContestId]);

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-8 text-center">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Конкурс #{contestId}</h1>
      <p className="text-gray-600">Раздел в разработке (2.4)</p>
    </div>
  );
}
