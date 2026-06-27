/** Prefix backend static asset paths with API host (B13). */
export function resolveAssetUrl(url: string): string {
  const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  if (url.startsWith("/static/")) return `${api}${url}`;
  return url;
}
