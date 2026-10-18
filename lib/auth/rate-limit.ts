interface AttemptRecord {
  failures: number
  firstFailureAt: number
  lockedUntil: number
}

export interface LoginRateLimiterOptions {
  maxFailures?: number
  windowMs?: number
  lockMs?: number
  now?: () => number
}

export class LoginRateLimiter {
  private readonly attempts = new Map<string, AttemptRecord>()
  private readonly maxFailures: number
  private readonly windowMs: number
  private readonly lockMs: number
  private readonly now: () => number

  constructor(options: LoginRateLimiterOptions = {}) {
    this.maxFailures = options.maxFailures ?? 8
    this.windowMs = options.windowMs ?? 15 * 60 * 1000
    this.lockMs = options.lockMs ?? 30 * 1000
    this.now = options.now ?? Date.now
  }

  isBlocked(key: string): boolean {
    const record = this.attempts.get(key)
    if (!record) return false
    if (this.now() - record.firstFailureAt > this.windowMs) {
      this.attempts.delete(key)
      return false
    }
    return this.now() < record.lockedUntil
  }

  retryAfterMs(key: string): number {
    const record = this.attempts.get(key)
    if (!record) return 0
    return Math.max(0, record.lockedUntil - this.now())
  }

  recordFailure(key: string): void {
    const now = this.now()
    let record = this.attempts.get(key)
    if (!record || now - record.firstFailureAt > this.windowMs) {
      record = { failures: 0, firstFailureAt: now, lockedUntil: 0 }
      this.attempts.set(key, record)
    }
    record.failures += 1
    if (record.failures >= this.maxFailures) {
      record.lockedUntil = now + this.lockMs
      record.failures = 0
      record.firstFailureAt = now
    }
  }

  recordSuccess(key: string): void {
    this.attempts.delete(key)
  }

  clear(): void {
    this.attempts.clear()
  }
}

export function clientKeyFromRequest(req: Request): string {
  const forwarded = req.headers.get('x-forwarded-for')
  if (forwarded) return forwarded.split(',')[0].trim()
  return req.headers.get('x-real-ip') ?? 'unknown'
}
