import { useContest } from "@/hooks/useContest";

/** Returns maxScore from contest rules — never hardcode in validation or labels. */
export function useMaxScore(): number {
  const { maxScore } = useContest();
  return maxScore;
}
