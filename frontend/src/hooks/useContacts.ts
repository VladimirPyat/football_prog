"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPatch } from "@/lib/api/client";
import { auth } from "@/lib/api/endpoints";
import type { AppError } from "@/lib/api/client";
import type { ContactOut, ContactPatchRequest } from "@/types/api";

interface UseContactsResult {
  contacts: ContactOut | null;
  loading: boolean;
  error: AppError | null;
  readonly: boolean;
  refetch: () => Promise<void>;
  save: (data: ContactPatchRequest) => Promise<void>;
}

const emptyContacts: ContactOut = {
  email: null,
  vk_id: null,
  tg_id: null,
  notify_enabled: false,
};

export function useContacts(enabled = true): UseContactsResult {
  const [contacts, setContacts] = useState<ContactOut | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<AppError | null>(null);
  const [readonly, setReadonly] = useState(false);

  const refetch = useCallback(async () => {
    if (!enabled) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<ContactOut>(auth.contacts());
      setContacts(data);
      setReadonly(false);
    } catch (err) {
      setError(err as AppError);
      setContacts(emptyContacts);
      setReadonly(true);
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  const save = useCallback(async (data: ContactPatchRequest) => {
    const updated = await apiPatch<ContactOut>(auth.contacts(), data);
    setContacts(updated);
  }, []);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { contacts, loading, error, readonly, refetch, save };
}
