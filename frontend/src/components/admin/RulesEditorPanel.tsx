"use client";

import type { ReactNode } from "react";
import type { Bonus2Threshold, RulesFormState } from "@/lib/admin/rulesEditor";

interface RulesEditorPanelProps {
  form: RulesFormState;
  readonly: boolean;
  onChange: (next: RulesFormState) => void;
}

function NumberField({
  label,
  value,
  onChange,
  disabled,
  className = "",
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  disabled: boolean;
  className?: string;
}) {
  return (
    <div className={className}>
      <label className="block text-sm text-gray-700 mb-1">{label}</label>
      <input
        type="number"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-100"
      />
    </div>
  );
}

function BonusCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="border border-gray-200 rounded-lg p-4 space-y-3 bg-white">
      <h4 className="text-sm font-semibold text-gray-900">{title}</h4>
      {children}
    </div>
  );
}

export function RulesEditorPanel({ form, readonly, onChange }: RulesEditorPanelProps) {
  const patch = (partial: Partial<RulesFormState>) => onChange({ ...form, ...partial });

  const patchBase = (key: keyof RulesFormState["basePoints"], value: number) =>
    patch({ basePoints: { ...form.basePoints, [key]: value } });

  const patchThreshold = (index: number, field: keyof Bonus2Threshold, value: number) => {
    const next = form.bonus2Thresholds.map((row, i) =>
      i === index ? { ...row, [field]: value } : row,
    );
    patch({ bonus2Thresholds: next });
  };

  return (
    <section className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-900">
        {readonly ? "Правила начисления (зафиксированы)" : "Правила начисления"}
      </h3>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="border border-gray-200 rounded-lg p-4 space-y-3">
          <h4 className="text-sm font-semibold text-gray-900">Основные очки</h4>
          <NumberField
            label="За предсказанный крупный счёт"
            value={form.basePoints.exact_high_score}
            disabled={readonly}
            onChange={(v) => patchBase("exact_high_score", v)}
          />
          <NumberField
            label="За точный счёт"
            value={form.basePoints.exact_score}
            disabled={readonly}
            onChange={(v) => patchBase("exact_score", v)}
          />
          <NumberField
            label="За правильную разницу мячей"
            value={form.basePoints.diff_plus_outcome}
            disabled={readonly}
            onChange={(v) => patchBase("diff_plus_outcome", v)}
          />
          <NumberField
            label="За правильный исход"
            value={form.basePoints.outcome_only}
            disabled={readonly}
            onChange={(v) => patchBase("outcome_only", v)}
          />
        </div>

        <div className="space-y-4">
          <BonusCard title="Бонус 1: Уникальный прогноз">
            <NumberField
              label="Процент от основных очков (%)"
              value={form.bonus1MultiplierPct}
              disabled={readonly}
              onChange={(v) => patch({ bonus1MultiplierPct: v })}
            />
          </BonusCard>

          <BonusCard title="Бонус 2: Угадано N матчей в туре">
            {form.bonus2Thresholds.map((row, index) => (
              <div key={index} className="grid grid-cols-2 gap-2">
                <NumberField
                  label={`Матчей ≥ (${index + 1})`}
                  value={row.min_correct_outcomes}
                  disabled={readonly}
                  onChange={(v) => patchThreshold(index, "min_correct_outcomes", v)}
                />
                <NumberField
                  label="Очков"
                  value={row.points}
                  disabled={readonly}
                  onChange={(v) => patchThreshold(index, "points", v)}
                />
              </div>
            ))}
          </BonusCard>

          <BonusCard title="Бонус 3: Топ-3 места в туре">
            <div className="grid grid-cols-3 gap-2">
              <NumberField
                label="1 место"
                value={form.bonus3Rank.first}
                disabled={readonly}
                onChange={(v) => patch({ bonus3Rank: { ...form.bonus3Rank, first: v } })}
              />
              <NumberField
                label="2 место"
                value={form.bonus3Rank.second}
                disabled={readonly}
                onChange={(v) => patch({ bonus3Rank: { ...form.bonus3Rank, second: v } })}
              />
              <NumberField
                label="3 место"
                value={form.bonus3Rank.third}
                disabled={readonly}
                onChange={(v) => patch({ bonus3Rank: { ...form.bonus3Rank, third: v } })}
              />
            </div>
            <div className="grid grid-cols-2 gap-2 pt-2">
              <NumberField
                label="Доп. порог (базовые очки ≥)"
                value={form.bonus3BaseThresholdExtra}
                disabled={readonly}
                onChange={(v) => patch({ bonus3BaseThresholdExtra: v })}
              />
              <NumberField
                label="Доп. очки"
                value={form.bonus3ExtraPoints}
                disabled={readonly}
                onChange={(v) => patch({ bonus3ExtraPoints: v })}
              />
            </div>
          </BonusCard>
        </div>
      </div>
    </section>
  );
}
