/**
 * proxy.ts  (Next.js 16 Edge Runtime)
 *
 * Fast first-pass guard: checks that the session cookie *exists*.
 * Full cryptographic verification happens in the Node.js API route
 * (app/api/admin/me) and in server.ts (Socket.IO middleware).
 *
 * Edge Runtime does not reliably load .env.local values into process.env
 * for custom secrets, so we do not attempt HMAC verification here.
 * The API routes (Node.js runtime) perform full verification.
 */

import { NextRequest, NextResponse } from 'next/server'
import { COOKIE_NAME } from '@/lib/session'

export async function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl

  // Always allow through: login page, login API, logout API
  if (
    pathname === '/admin/login' ||
    pathname === '/api/admin/login' ||
    pathname === '/api/admin/logout'
  ) {
    return NextResponse.next()
  }

  // Protect /admin/* and /api/admin/*
  if (pathname.startsWith('/admin') || pathname.startsWith('/api/admin')) {
    const token = req.cookies.get(COOKIE_NAME)?.value
    // If cookie is completely absent, redirect immediately (saves a round-trip)
    if (!token || token.length < 10) {
      const loginUrl = new URL('/admin/login', req.url)
      loginUrl.searchParams.set('next', pathname)
      return NextResponse.redirect(loginUrl)
    }
    // Cookie is present — let the request proceed to the Node.js API/page handler
    // which will do full cryptographic verification.
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/admin/:path*', '/api/admin/:path*'],
}
