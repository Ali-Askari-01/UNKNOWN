import { AuthConfigError, getSessionSecret, isProduction } from './config'

export const COOKIE_NAME = 'quiz_admin_session'
export const COOKIE_MAX_AGE = 60 * 60 * 8

interface SessionPayload {
  role: 'admin'
  exp: number
}

function timingSafeEqualString(a: string, b: string): boolean {
  const len = Math.max(a.length, b.length)
  let diff = a.length ^ b.length
  for (let i = 0; i < len; i++) {
    diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0)
  }
  return diff === 0
}

async function importKey(secret: string): Promise<CryptoKey> {
  const enc = new TextEncoder()
  return crypto.subtle.importKey(
    'raw',
    enc.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  )
}

async function sign(data: string, secret: string): Promise<string> {
  const key = await importKey(secret)
  const enc = new TextEncoder()
  const sig = await crypto.subtle.sign('HMAC', key, enc.encode(data))
  return Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
    .slice(0, 32)
}

export async function createSessionToken(): Promise<string> {
  const payload: SessionPayload = {
    role: 'admin',
    exp: Date.now() + COOKIE_MAX_AGE * 1000,
  }
  const b64 = btoa(JSON.stringify(payload))
  const sig = await sign(b64, getSessionSecret())
  return `${b64}.${sig}`
}

export async function verifySessionToken(token: string | undefined): Promise<boolean> {
  if (!token) return false
  try {
    const dot = token.lastIndexOf('.')
    if (dot === -1) return false
    const b64 = token.slice(0, dot)
    const sig = token.slice(dot + 1)
    if (sig.length !== 32) return false
    const expected = await sign(b64, getSessionSecret())
    if (!timingSafeEqualString(sig, expected)) return false
    const payload = JSON.parse(atob(b64)) as SessionPayload
    return payload.role === 'admin' && Date.now() < payload.exp
  } catch (error) {
    if (error instanceof AuthConfigError) throw error
    return false
  }
}

export async function verifySessionCookieHeader(header: string | undefined): Promise<boolean> {
  if (!header) return false
  const token = extractCookieValue(header, COOKIE_NAME)
  return verifySessionToken(token)
}

export function extractCookieValue(header: string, name: string): string | undefined {
  for (const part of header.split(';')) {
    const eq = part.indexOf('=')
    if (eq === -1) continue
    if (part.slice(0, eq).trim() === name) {
      return decodeURIComponent(part.slice(eq + 1).trim())
    }
  }
  return undefined
}

export function buildSetCookieHeader(token: string): string {
  return [
    `${COOKIE_NAME}=${token}`,
    `Max-Age=${COOKIE_MAX_AGE}`,
    'Path=/',
    'HttpOnly',
    'SameSite=Lax',
    ...(isProduction() ? ['Secure'] : []),
  ].join('; ')
}

export function buildClearCookieHeader(): string {
  return `${COOKIE_NAME}=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax`
}
