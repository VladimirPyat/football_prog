"use client";

import { useRef, useState } from "react";
import { validateLogoFile } from "@/lib/validation/admin";

interface TeamLogoUploadProps {
  disabled?: boolean;
  onUpload: (file: File) => Promise<void>;
}

export function TeamLogoUpload({ disabled = false, onUpload }: TeamLogoUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const handleChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    const validationError = validateLogoFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }
    setUploading(true);
    try {
      await onUpload(file);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка загрузки");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div>
      <button
        type="button"
        disabled={disabled || uploading}
        onClick={() => inputRef.current?.click()}
        className="text-sm text-blue-600 hover:underline disabled:text-gray-400 disabled:no-underline"
      >
        {uploading ? "Загрузка…" : "Загрузить логотип"}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg,image/gif"
        className="hidden"
        onChange={handleChange}
        disabled={disabled}
      />
      {error && <p className="text-sm text-red-600 mt-1">{error}</p>}
    </div>
  );
}
