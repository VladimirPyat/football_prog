const HEADER_LINES: Record<string, string[]> = {
  Место: ["Место"],
  "Фамилия Имя": ["Фамилия", "Имя"],
  "Дано прогнозов": ["Дано", "прогнозов"],
  "Точный кр. счет": ["Точный", "кр.", "счёт"],
  "Точный счет": ["Точный", "счёт"],
  Разница: ["Разница"],
  Исход: ["Исход"],
  "Бонус 1": ["Бонус", "1"],
  "Бонус 2": ["Бонус", "2"],
  "Бонус 3": ["Бонус", "3"],
  "Очки без бонуса": ["Очки", "без", "бонуса"],
  "Очки с бонусами": ["Очки", "с", "бонусами"],
  "Всего очков": ["Всего", "очков"],
  "Итого без бон.": ["Итого", "без", "бон."],
  ИТОГО: ["ИТОГО"],
  Счет: ["Счёт"],
};

interface MultiLineColumnHeaderProps {
  label: string;
  className?: string;
}

export function MultiLineColumnHeader({ label, className = "" }: MultiLineColumnHeaderProps) {
  const lines = HEADER_LINES[label] ?? [label];

  return (
    <div
      className={`flex flex-col items-center justify-center leading-tight gap-0.5 text-xs font-medium text-gray-700 ${className}`}
    >
      {lines.map((line) => (
        <span key={line} className="block text-center">
          {line}
        </span>
      ))}
    </div>
  );
}
