"use client";

import Link from "next/link";
import type { ContestStartReadiness } from "@/lib/admin/contestStartReadiness";

interface ContestStartReadinessPanelProps {
  readiness: ContestStartReadiness;
  loading?: boolean;
}

function StatusLine({ ok, label, href }: { ok: boolean; label: string; href: string }) {
  return (
    <p className={ok ? "text-gray-700" : "text-red-700"}>
      <span className="font-medium">{label}</span>
      {!ok && (
        <>
          {" "}
          —{" "}
          <Link href={href} className="text-blue-700 underline hover:text-blue-900">
            перейти
          </Link>
        </>
      )}
    </p>
  );
}

export function ContestStartReadinessPanel({
  readiness,
  loading = false,
}: ContestStartReadinessPanelProps) {
  if (loading) {
    return (
      <div className="rounded-md border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-600 max-w-2xl">
        Проверка готовности к запуску…
      </div>
    );
  }

  if (readiness.ready) {
    return (
      <div className="rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-900 max-w-2xl space-y-1">
        <p className="font-medium">Конкурс готов к запуску</p>
        <StatusLine
          ok
          label={`Команды: ${readiness.teamsCount} / ${readiness.totalTeams}`}
          href="/admin/settings/teams"
        />
        <StatusLine
          ok
          label={`Участники (принято): ${readiness.acceptedCount} / 2 мин.`}
          href="/admin/settings/participants"
        />
      </div>
    );
  }

  return (
    <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 max-w-2xl space-y-2">
      <p className="font-medium">Перед запуском выполните настройку:</p>
      <StatusLine
        ok={readiness.teamsOk}
        label={`Команды: ${readiness.teamsCount} / ${readiness.totalTeams}`}
        href="/admin/settings/teams"
      />
      <StatusLine
        ok={readiness.participantsOk}
        label={`Участники (принято): ${readiness.acceptedCount} / 2 мин.`}
        href="/admin/settings/participants"
      />
      {readiness.issues.length > 0 && (
        <ul className="list-disc list-inside text-amber-950/90 space-y-0.5">
          {readiness.issues.map((issue) => (
            <li key={issue}>{issue}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
