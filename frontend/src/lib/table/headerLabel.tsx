/** Multiline table header label — one font size/weight for all lines. */
export function headerLabel(lines: string[]) {
  return (
    <span className="block leading-snug text-sm font-medium">
      {lines.map((line) => (
        <span key={line} className="block whitespace-nowrap">
          {line}
        </span>
      ))}
    </span>
  );
}
