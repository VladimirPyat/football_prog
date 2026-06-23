export function resolveDefaultContestId(): number {
  const raw = process.env.NEXT_PUBLIC_DEFAULT_CONTEST_ID ?? "1";
  const id = Number(raw);
  if (!Number.isInteger(id) || id <= 0) {
    throw new Error("Invalid NEXT_PUBLIC_DEFAULT_CONTEST_ID");
  }
  return id;
}
