import type { RoundOut } from "@/types/api";
import { roundStatusLabel } from "@/lib/admin/format";
import { effectiveRoundStatus } from "@/lib/admin/roundEffectiveStatus";

type RoundLabelInput = Pick<
  RoundOut,
  "number" | "kind" | "supplementary_index" | "source_round_numbers"
>;

export function formatRoundTitle(round: RoundLabelInput): string {
  if (round.kind === "SUPPLEMENTARY" && round.supplementary_index != null) {
    let title = `ДопТур${round.supplementary_index}`;
    const sources = [...(round.source_round_numbers ?? [])].sort((a, b) => a - b);
    if (sources.length === 1) {
      title += ` (из тура ${sources[0]})`;
    } else if (sources.length > 1) {
      title += ` (из туров ${sources.join(", ")})`;
    }
    return title;
  }
  return `Тур ${round.number}`;
}

export function formatRoundOptionLabel(round: RoundOut): string {
  const displayStatus = effectiveRoundStatus(round);
  return `${formatRoundTitle(round)} — ${roundStatusLabel(displayStatus)}`;
}
