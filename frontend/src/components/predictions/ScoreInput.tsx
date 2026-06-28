"use client";

import { parseScoreInput } from "@/lib/validation/score";
import { scoreInputSchema } from "@/lib/validation/score";
import { useState } from "react";

interface ScoreInputProps {
  value: number | "";
  onChange: (value: number | "") => void;
  maxScore: number;
  disabled?: boolean;
  "aria-label"?: string;
}

export function ScoreInput({
  value,
  onChange,
  maxScore,
  disabled = false,
  "aria-label": ariaLabel,
}: ScoreInputProps) {
  const [error, setError] = useState<string | null>(null);

  const handleChange = (raw: string) => {
    if (raw === "") {
      onChange("");
      setError(null);
      return;
    }
    if (!/^\d*$/.test(raw)) return;
    const parsed = parseScoreInput(raw);
    if (parsed === "") {
      setError("Введите целое число");
      return;
    }
    onChange(parsed);
    setError(null);
  };

  const handleBlur = () => {
    if (value === "") {
      setError(null);
      return;
    }
    const result = scoreInputSchema(maxScore).safeParse(value);
    if (!result.success) {
      setError(result.error.issues[0]?.message ?? "Ошибка");
    } else {
      setError(null);
    }
  };

  return (
    <div>
      <input
        type="text"
        inputMode="numeric"
        pattern="[0-9]*"
        value={value === "" ? "" : String(value)}
        onChange={(e) => handleChange(e.target.value)}
        onBlur={handleBlur}
        disabled={disabled}
        aria-label={ariaLabel}
        className="w-12 border border-gray-300 rounded px-2 py-1 text-sm text-center disabled:bg-gray-100"
      />
      {error && <p className="text-xs text-red-600 mt-0.5">{error}</p>}
    </div>
  );
}
