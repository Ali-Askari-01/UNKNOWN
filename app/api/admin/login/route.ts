/**
 * POST /api/admin/login
 * Verifies username + password, issues a signed session cookie.
 */

import { NextRequest, NextResponse } from 'next/server'
import bcrypt from 'bcryptjs'
import {
  createSessionToken,
  buildSetCookieHeader,
  verifySessionToken,
  COOKIE_NAME,
} from '@/lib/session'

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { username, password } = body as { username?: string; password?: string }

    if (!username || !password) {
      return NextResponse.json({ error: 'Missing credentials.' }, { status: 400 })
    }

    const expectedUsername = process.env.ADMIN_USERNAME ?? 'admin'
    const passwordHash = process.env.ADMIN_PASSWORD_HASH ?? ''

    if (!passwordHash) {
      return NextResponse.json(
        { error: 'Admin account not configured. Set ADMIN_PASSWORD_HASH in .env.local.' },
        { status: 503 }
      )
    }

    const usernameOk = username === expectedUsername
    const passwordOk = await bcrypt.compare(password, passwordHash)

    if (!usernameOk || !passwordOk) {
      return NextResponse.json({ error: 'Invalid credentials.' }, { status: 401 })
    }

    const token = await createSessionToken()
    const res = NextResponse.json({ ok: true })
    res.headers.set('Set-Cookie', buildSetCookieHeader(token))
    return res
  } catch {
    return NextResponse.json({ error: 'Server error.' }, { status: 500 })
  }
}

export async function GET(req: NextRequest) {
  const token = req.cookies.get(COOKIE_NAME)?.value
  return NextResponse.json({ authenticated: await verifySessionToken(token) })
}
