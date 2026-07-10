"use client";

import { useState } from "react";
import { TiebreakForm } from "@/components/admin/TiebreakForm";
import { participantStatusLabel } from "@/lib/admin/format";
import type { ParticipantOut } from "@/types/api";
import { AdminTable, AdminTh } from "@/components/ui/AdminTable";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { Modal } from "@/components/ui/Modal";
import { TD_ADMIN, TR_ADMIN_BORDER } from "@/lib/table/tableHeaderStyles";

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

  if (!participants.length) {
    return <EmptyState message="Участников пока нет" />;
  }

  return (
    <>
      <AdminTable
        headers={
          <>
            <AdminTh>Имя</AdminTh>
            <AdminTh>Email</AdminTh>
            <AdminTh>Статус</AdminTh>
            <AdminTh>Действия</AdminTh>
          </>
        }
      >
        {participants.map((p) => (
          <tr key={p.user_id} className={TR_ADMIN_BORDER}>
            <td className={TD_ADMIN}>
              {p.first_name} {p.last_name}
            </td>
            <td className={TD_ADMIN}>{p.email ?? "—"}</td>
            <td className={TD_ADMIN}>{participantStatusLabel(p.status)}</td>
            <td className={`${TD_ADMIN} space-x-2`}>
              {!readonly && (
                <Button variant="ghostLink" onClick={() => setDeleteId(p.user_id)}>
                  Удалить
                </Button>
              )}
              {isAdmin && (
                <Button variant="link" onClick={() => setTiebreakUser(p)}>
                  Тай-брейк ({p.exceptional_tiebreak_points})
                </Button>
              )}
            </td>
          </tr>
        ))}
      </AdminTable>

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

      <Modal
        open={tiebreakUser != null}
        onClose={() => setTiebreakUser(null)}
        title={
          tiebreakUser
            ? `Тай-брейк: ${tiebreakUser.first_name} ${tiebreakUser.last_name}`
            : undefined
        }
        size="sm"
      >
        {tiebreakUser && (
          <TiebreakForm
            initialPoints={tiebreakUser.exceptional_tiebreak_points}
            onSubmit={async (points) => {
              await onTiebreak(tiebreakUser.user_id, points);
              setTiebreakUser(null);
            }}
            onCancel={() => setTiebreakUser(null)}
          />
        )}
      </Modal>
    </>
  );
}
