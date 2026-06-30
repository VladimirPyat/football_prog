"use client";

import { useEffect, useState } from "react";

function formatDateTime(d: Date): string {
  return d.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function HeaderDateTime() {
  const [label, setLabel] = useState("");

  useEffect(() => {
    const tick = () => setLabel(formatDateTime(new Date()));
    tick();
    const id = window.setInterval(tick, 60_000);
    return () => window.clearInterval(id);
  }, []);

  if (!label) return null;

  return (
    <p className="text-xs text-gray-500 font-normal mt-0.5" data-testid="header-datetime">
      {label}
    </p>
  );
}
