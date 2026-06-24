"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet } from "@/lib/api/client";
import { contests as contestEndpoints } from "@/lib/api/endpoints";
import { useAuth } from "@/hooks/useAuth";
import { useContest } from "@/hooks/useContest";
import { useMyContests } from "@/hooks/useMyContests";
import { isSupervisorOrAbove } from "@/lib/auth/guards";
import { resolveDefaultContestId } from "@/lib/contest/resolveDefaultContestId";
import type { ContestListItem, ContestOut } from "@/types/api";

function toListItemFromContest(c: ContestOut): ContestListItem {
  return { id: c.id, name: c.name, status: c.status };
}

interface ContestPickerProps {
  /** When true, changing contest stays on current admin page */
  adminMode?: boolean;
}

export function ContestPicker({ adminMode = false }: ContestPickerProps) {
  const { role } = useAuth();
  const { contestId, setContestId } = useContest();
  const { contests: myContests } = useMyContests(role === "USER");
  const router = useRouter();
  const [supervisorContests, setSupervisorContests] = useState<ContestListItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isSupervisorOrAbove(role)) return;
    const load = async () => {
      setLoading(true);
      try {
        const data = await apiGet<ContestOut[]>(contestEndpoints.list());
        setSupervisorContests(data.map(toListItemFromContest));
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
  const value = contestId ?? resolveDefaultContestId();

  const handleChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = Number(e.target.value);
    await setContestId(id, isSupervisorOrAbove(role));
    if (!adminMode) {
      router.push(`/contest/${id}`);
    }
  };

  if (loading && !items.length) {
    return <span className="text-sm text-gray-500">…</span>;
  }

  return (
    <select
      value={value}
      onChange={handleChange}
      className="text-sm border border-gray-300 rounded px-2 py-1 bg-white"
      aria-label="Выбор конкурса"
    >
      {items.map((c) => (
        <option key={c.id} value={c.id}>
          {c.name}
        </option>
      ))}
    </select>
  );
}
