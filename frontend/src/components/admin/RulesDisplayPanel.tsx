"use client";

import { parseRulesForDisplay } from "@/lib/admin/rulesDisplay";

interface RulesDisplayPanelProps {
  rulesJson: Record<string, unknown>;
}

function Column({ title, rows }: { title: string; rows: { label: string; value: string }[] }) {
  return (
    <div>
      <h4 className="text-sm font-semibold text-gray-900 mb-2">{title}</h4>
      <dl className="space-y-2">
        {rows.map((row) => (
          <div key={row.label} className="border border-gray-200 rounded p-2 text-sm">
            <dt className="text-gray-500 text-xs">{row.label}</dt>
            <dd className="font-medium text-gray-900">{row.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function RulesDisplayPanel({ rulesJson }: RulesDisplayPanelProps) {
  const sections = parseRulesForDisplay(rulesJson);

  return (
    <section className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-900">Правила начисления (только просмотр)</h3>
      {sections.structure.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {sections.structure.map((row) => (
            <div key={row.label} className="border border-gray-200 rounded p-2 text-sm">
              <span className="text-gray-500 block text-xs">{row.label}</span>
              <span className="font-medium">{row.value}</span>
            </div>
          ))}
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Column title="Основные очки" rows={sections.basePoints} />
        <Column title="Бонусы" rows={sections.bonuses} />
      </div>
    </section>
  );
}
