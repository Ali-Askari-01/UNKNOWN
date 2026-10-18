import { NextRequest, NextResponse } from 'next/server'
import bcrypt from 'bcryptjs'
import {
  COOKIE_NAME,
  LoginRateLimiter,
  buildSetCookieHeader,
  clientKeyFromRequest,
  createSessionToken,
  getAdminCredentials,
  verifySessionToken,
} from '@/lib/auth'
import { loginSchema, parseOrThrow } from '@/lib/validation'
import { ValidationError } from '@/lib/validation'

const rateLimiter = new LoginRateLimiter()

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => null)
    const { username, password } = parseOrThrow(loginSchema, body)

    const clientKey = clientKeyFromRequest(req)
    if (rateLimiter.isBlocked(clientKey)) {
      const retryAfter = Math.ceil(rateLimiter.retryAfterMs(clientKey) / 1000)
      return NextResponse.json(
        { error: 'Too many attempts. Try again later.' },
        { status: 429, headers: { 'Retry-After': String(retryAfter) } },
      )
    }

    const { username: expectedUsername, passwordHash } = getAdminCredentials()
    if (!passwordHash) {
      return NextResponse.json(
        { error: 'Admin account not configured. Set ADMIN_PASSWORD_HASH in .env.local.' },
        { status: 503 },
      )
    }

    const usernameOk = timingSafeStringEqual(username, expectedUsername)
    const passwordOk = await bcrypt.compare(password, passwordHash)

    if (!usernameOk || !passwordOk) {
      rateLimiter.recordFailure(clientKey)
      return NextResponse.json({ error: 'Invalid credentials.' }, { status: 401 })
    }

    rateLimiter.recordSuccess(clientKey)
    const token = await createSessionToken()
    const res = NextResponse.json({ ok: true })
    res.headers.set('Set-Cookie', buildSetCookieHeader(token))
    return res
  } catch (error) {
    if (error instanceof ValidationError) {
      return NextResponse.json({ error: error.message }, { status: 400 })
    }
    return NextResponse.json({ error: 'Server error.' }, { status: 500 })
  }
}

export async function GET(req: NextRequest) {
  const token = req.cookies.get(COOKIE_NAME)?.value
  return NextResponse.json({ authenticated: await verifySessionToken(token) })
}

function timingSafeStringEqual(a: string, b: string): boolean {
  const len = Math.max(a.length, b.length)
  let diff = a.length ^ b.length
  for (let i = 0; i < len; i++) {
    diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0)
  }
  return diff === 0
}
