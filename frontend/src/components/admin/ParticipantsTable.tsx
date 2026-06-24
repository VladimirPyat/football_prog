"use client";

import { participantStatusLabel } from "@/lib/admin/format";
import type { ParticipantOut } from "@/types/api";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useState } from "react";
import { TiebreakForm } from "@/components/admin/TiebreakForm";

interface ParticipantsTableProps {
  participants: ParticipantOut[];
  readonly: boolean;
  isAdmin: boolean;
  onDelete: (userId: number) => Promise<void>;
  onTiebreak: (userId: number, points: number) => Promise<void>;
}

export function ParticipantsTable({
  participants,
  readonly,
  isAdmin,
  onDelete,
  onTiebreak,
}: ParticipantsTableProps) {
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [tiebreakUser, setTiebreakUser] = useState<ParticipantOut | null>(null);

  return (
    <>
      <div className="overflow-x-auto border border-gray-200 rounded-lg">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left font-medium text-gray-700">Имя</th>
              <th className="px-4 py-2 text-left font-medium text-gray-700">Email</th>
              <th className="px-4 py-2 text-left font-medium text-gray-700">Статус</th>
              <th className="px-4 py-2 text-left font-medium text-gray-700">Действия</th>
            </tr>
          </thead>
          <tbody>
            {participants.map((p) => (
              <tr key={p.user_id} className="border-t border-gray-200">
                <td className="px-4 py-2">
                  {p.first_name} {p.last_name}
                </td>
                <td className="px-4 py-2">{p.email ?? "—"}</td>
                <td className="px-4 py-2">{participantStatusLabel(p.status)}</td>
                <td className="px-4 py-2 space-x-2">
                  {!readonly && (
                    <button
                      type="button"
                      onClick={() => setDeleteId(p.user_id)}
                      className="text-red-600 hover:underline"
                    >
                      Удалить
                    </button>
                  )}
                  {isAdmin && (
                    <button
                      type="button"
                      onClick={() => setTiebreakUser(p)}
                      className="text-blue-600 hover:underline"
                    >
                      Тай-брейк ({p.exceptional_tiebreak_points})
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {!participants.length && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-gray-500">
                  Участников пока нет
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        open={deleteId !== null}
        title="Удалить участника?"
        message="Участник будет исключён из конкурса."
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

      {tiebreakUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-lg shadow-lg max-w-sm w-full p-6">
            <h3 className="text-lg font-semibold mb-2">
              Тай-брейк: {tiebreakUser.first_name} {tiebreakUser.last_name}
            </h3>
            <TiebreakForm
              initialPoints={tiebreakUser.exceptional_tiebreak_points}
              onSubmit={async (points) => {
                await onTiebreak(tiebreakUser.user_id, points);
                setTiebreakUser(null);
              }}
              onCancel={() => setTiebreakUser(null)}
            />
          </div>
        </div>
      )}
    </>
  );
}
