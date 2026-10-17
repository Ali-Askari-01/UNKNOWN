/**
 * lib/session.ts
 * Session utilities using the Web Crypto API (works in both Edge Runtime
 * and Node.js >= 15).  No node:crypto imports.
 */

export const COOKIE_NAME = 'quiz_admin_session'
export const COOKIE_MAX_AGE = 60 * 60 * 8 // 8 hours in seconds

function getSecret(): string {
  return process.env.SESSION_SECRET ?? 'dev-secret-change-me-in-production'
}

// ── HMAC-SHA256 using Web Crypto ──────────────────────────────────────────────

async function importKey(secret: string): Promise<CryptoKey> {
  const enc = new TextEncoder()
  return crypto.subtle.importKey(
    'raw',
    enc.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign', 'verify']
  )
}

async function sign(data: string, secret: string): Promise<string> {
  const key = await importKey(secret)
  const enc = new TextEncoder()
  const sig = await crypto.subtle.sign('HMAC', key, enc.encode(data))
  // Convert to hex, take first 32 chars
  return Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
    .slice(0, 32)
}

// ── Token creation / verification ────────────────────────────────────────────

interface SessionPayload {
  role: 'admin'
  exp: number // ms epoch
}

/** Create a signed session token. Async because Web Crypto sign is async. */
export async function createSessionToken(): Promise<string> {
  const payload: SessionPayload = {
    role: 'admin',
    exp: Date.now() + COOKIE_MAX_AGE * 1000,
  }
  const b64 = btoa(JSON.stringify(payload))
  const sig = await sign(b64, getSecret())
  return `${b64}.${sig}`
}

/** Verify a session token. Returns true if valid and not expired. */
export async function verifySessionToken(token: string | undefined): Promise<boolean> {
  if (!token) return false
  try {
    const dot = token.lastIndexOf('.')
    if (dot === -1) return false
    const b64 = token.slice(0, dot)
    const sig = token.slice(dot + 1)
    const expected = await sign(b64, getSecret())
    if (sig !== expected) return false
    const payload = JSON.parse(atob(b64)) as SessionPayload
    return payload.role === 'admin' && Date.now() < payload.exp
  } catch {
    return false
  }
}

/** Build Set-Cookie header string. */
export function buildSetCookieHeader(token: string): string {
  return [
    `${COOKIE_NAME}=${token}`,
    `Max-Age=${COOKIE_MAX_AGE}`,
    'Path=/',
    'HttpOnly',
    'SameSite=Lax',
    ...(process.env.NODE_ENV === 'production' ? ['Secure'] : []),
  ].join('; ')
}

/** Build a clearing Set-Cookie header. */
export function buildClearCookieHeader(): string {
  return `${COOKIE_NAME}=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax`
}
