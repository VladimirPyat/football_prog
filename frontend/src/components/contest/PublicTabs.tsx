"use client";

type PublicTab = "leaderboard" | "predictions" | "results";

interface PublicTabsProps {
  active: PublicTab;
  onChange: (tab: PublicTab) => void;
}

const TABS: { id: PublicTab; label: string }[] = [
  { id: "leaderboard", label: "Лидерборд" },
  { id: "predictions", label: "Прогнозы" },
  { id: "results", label: "Результаты" },
];

export function PublicTabs({ active, onChange }: PublicTabsProps) {
  return (
    <div className="flex gap-1 bg-gray-100 p-1 rounded-lg" role="tablist">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={active === tab.id}
          onClick={() => onChange(tab.id)}
          className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
            active === tab.id
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-600 hover:text-gray-900"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export type { PublicTab };
