/**
 * FlockKeyPool — multi-key rotation with 429/Retry-After tracking.
 *
 * Absorbed from the standalone super-ralph nimProxy integration so the
 * flock-client SDK carries the same resilience without a proxy in front:
 * keys are deduplicated on registration, rotation is round-robin over
 * keys whose rate limit has expired, and a 429 parks the offending key
 * for the server's Retry-After (default 60s) instead of burning retries
 * against it. Key values never appear in stats or error labels.
 */

const DEFAULT_RETRY_AFTER_MS = 60_000;

export type FlockKeyStats = {
  /** Opaque label ("key#1") — never the key value. */
  label: string;
  successCount: number;
  failureCount: number;
  rateLimitCount: number;
  rateLimitedUntil: number | null;
  isRateLimited: boolean;
  isAvailable: boolean;
  lastFailureReason: string | null;
};

type KeyState = {
  key: string;
  successCount: number;
  failureCount: number;
  rateLimitCount: number;
  rateLimitedUntil: number | null;
  lastFailureReason: string | null;
};

export class FlockKeyPool {
  private keys: KeyState[] = [];
  private cursor = 0;

  constructor(keys: string[]) {
    const seen = new Set<string>();
    for (const raw of keys) {
      const key = raw.trim();
      if (!key || seen.has(key)) continue;
      seen.add(key);
      this.keys.push({
        key,
        successCount: 0,
        failureCount: 0,
        rateLimitCount: 0,
        rateLimitedUntil: null,
        lastFailureReason: null,
      });
    }
  }

  get size(): number {
    return this.keys.length;
  }

  private isLimited(state: KeyState, now: number): boolean {
    return state.rateLimitedUntil !== null && state.rateLimitedUntil > now;
  }

  /** Next available key (round-robin), or null when all are rate-limited. */
  nextAvailable(): string | null {
    const now = Date.now();
    for (let i = 0; i < this.keys.length; i++) {
      const idx = (this.cursor + i) % this.keys.length;
      if (!this.isLimited(this.keys[idx], now)) {
        this.cursor = (idx + 1) % this.keys.length;
        return this.keys[idx].key;
      }
    }
    return null;
  }

  recordSuccess(key: string): void {
    const s = this.keys.find((k) => k.key === key);
    if (!s) return;
    s.successCount++;
    s.rateLimitedUntil = null;
    s.lastFailureReason = null;
  }

  recordFailure(key: string, reason: string): void {
    const s = this.keys.find((k) => k.key === key);
    if (!s) return;
    s.failureCount++;
    s.lastFailureReason = reason;
  }

  recordRateLimit(key: string, retryAfterMs?: number): void {
    const s = this.keys.find((k) => k.key === key);
    if (!s) return;
    s.rateLimitCount++;
    s.lastFailureReason = "Rate limited (429)";
    s.rateLimitedUntil = Date.now() + (retryAfterMs ?? DEFAULT_RETRY_AFTER_MS);
  }

  /** Earliest ms-epoch at which a rate-limited key becomes usable, or null. */
  earliestRetryAt(): number | null {
    const times = this.keys
      .map((k) => k.rateLimitedUntil)
      .filter((t): t is number => t !== null);
    return times.length ? Math.min(...times) : null;
  }

  getStats(): FlockKeyStats[] {
    const now = Date.now();
    return this.keys.map((s, i) => {
      const limited = this.isLimited(s, now);
      return {
        label: "key#" + (i + 1),
        successCount: s.successCount,
        failureCount: s.failureCount,
        rateLimitCount: s.rateLimitCount,
        rateLimitedUntil: s.rateLimitedUntil,
        isRateLimited: limited,
        isAvailable: !limited,
        lastFailureReason: s.lastFailureReason,
      };
    });
  }
}

/** Split a comma-separated key string into deduplicated keys. */
export function splitKeys(raw: string | string[] | undefined): string[] {
  const list = Array.isArray(raw) ? raw : raw ? raw.split(",") : [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const k of list) {
    const key = k.trim();
    if (key && !seen.has(key)) {
      seen.add(key);
      out.push(key);
    }
  }
  return out;
}

/** Parse a Retry-After header (seconds or HTTP date) into ms. */
export function parseRetryAfterMs(value: string | null): number {
  if (!value) return DEFAULT_RETRY_AFTER_MS;
  const secs = Number(value.trim());
  if (Number.isFinite(secs) && secs >= 0) return secs * 1000;
  const dateMs = Date.parse(value);
  if (!Number.isNaN(dateMs)) return Math.max(0, dateMs - Date.now());
  return DEFAULT_RETRY_AFTER_MS;
}
