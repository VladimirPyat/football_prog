/** ETag cache stub — full implementation deferred to Stage 2.4 */

const etagStore = new Map<string, string>();
const cacheStore = new Map<string, unknown>();

export function getEtag(url: string): string | undefined {
  return etagStore.get(url);
}

export function saveEtag(url: string, etag: string | null): void {
  if (etag) etagStore.set(url, etag);
}

export function getCached<T>(url: string): T | undefined {
  return cacheStore.get(url) as T | undefined;
}

export function setCached<T>(url: string, data: T): void {
  cacheStore.set(url, data);
}

export function clearCache(url?: string): void {
  if (url) {
    etagStore.delete(url);
    cacheStore.delete(url);
  } else {
    etagStore.clear();
    cacheStore.clear();
  }
}
