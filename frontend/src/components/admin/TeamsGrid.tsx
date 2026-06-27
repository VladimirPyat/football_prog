"use client";

import { DEFAULT_TEAM_LOGO_URL } from "@/lib/admin/format";
import { resolveAssetUrl } from "@/lib/api/resolveAssetUrl";
import type { TeamOut } from "@/types/api";
import { TeamForm } from "@/components/admin/TeamForm";
import { TeamLogoUpload } from "@/components/admin/TeamLogoUpload";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useState } from "react";

interface TeamsGridProps {
  teams: TeamOut[];
  readonly: boolean;
  onCreate: (data: { name: string; short_name: string }) => Promise<void>;
  onPatch: (teamId: number, data: { name: string; short_name: string }) => Promise<void>;
  onDelete: (teamId: number) => Promise<void>;
  onUploadLogo: (teamId: number, file: File) => Promise<void>;
}

export function TeamsGrid({
  teams,
  readonly,
  onCreate,
  onPatch,
  onDelete,
  onUploadLogo,
}: TeamsGridProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  return (
    <div className="space-y-6">
      {!readonly && (
        <section className="border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Добавить команду</h3>
          <TeamForm onSubmit={onCreate} submitLabel="Добавить" />
        </section>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {teams.map((team) => (
          <article key={team.id} className="border border-gray-200 rounded-lg p-4">
            <div className="flex items-center gap-3 mb-3">
              {/* eslint-disable-next-line @next/next/no-img-element -- team logos from API may be external */}
              <img
                src={resolveAssetUrl(team.logo_url || DEFAULT_TEAM_LOGO_URL)}
                alt=""
                width={40}
                height={40}
                className="rounded object-cover w-10 h-10"
                onError={(e) => {
                  e.currentTarget.onerror = null;
                  e.currentTarget.src = resolveAssetUrl(DEFAULT_TEAM_LOGO_URL);
                }}
              />
              <div>
                <span className="inline-block text-xs font-bold bg-gray-100 px-2 py-0.5 rounded mr-2">
                  {team.short_name}
                </span>
                <span className="font-medium text-gray-900">{team.name}</span>
              </div>
            </div>
            {editingId === team.id ? (
              <TeamForm
                initial={{ name: team.name, short_name: team.short_name }}
                onSubmit={async (data) => {
                  await onPatch(team.id, data);
                  setEditingId(null);
                }}
                onCancel={() => setEditingId(null)}
                readonly={readonly}
              />
            ) : (
              <div className="flex flex-wrap gap-2">
                {!readonly && (
                  <>
                    <button
                      type="button"
                      onClick={() => setEditingId(team.id)}
                      className="text-sm text-blue-600 hover:underline"
                    >
                      Редактировать
                    </button>
                    <button
                      type="button"
                      onClick={() => setDeleteId(team.id)}
                      className="text-sm text-red-600 hover:underline"
                    >
                      Удалить
                    </button>
                    <TeamLogoUpload onUpload={(file) => onUploadLogo(team.id, file)} />
                  </>
                )}
              </div>
            )}
          </article>
        ))}
      </div>

      <ConfirmDialog
        open={deleteId !== null}
        title="Удалить команду?"
        message="Команда будет удалена из конкурса."
        confirmLabel="Удалить"
        danger
        onConfirm={async () => {
          if (deleteId !== null) {
            await onDelete(deleteId);
            setDeleteId(null);
          }
        }}
        onCancel={() => setDeleteId(null)}
      />
    </div>
  );
}
