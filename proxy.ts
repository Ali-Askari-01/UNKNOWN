/**
 * proxy.ts  (Next.js 16 Edge Runtime)
 *
 * Fast first-pass guard: checks that the session cookie *exists*.
 * Full cryptographic verification happens in FastAPI's auth dependency.
 *
 * Edge Runtime does not reliably load .env.local values into process.env
 * for custom secrets, so we do not attempt HMAC verification here.
 * The API routes (Node.js runtime) perform full verification.
 */

import { NextRequest, NextResponse } from 'next/server'
const FASTAPI_ADMIN_COOKIE_NAME = 'unknown_admin_session'

export async function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl

  // Always allow the login page through; the API is owned by FastAPI and is not matched here.
  if (pathname === '/admin/login') {
    return NextResponse.next()
  }

  // Protect the admin UI. FastAPI validates the cookie cryptographically.
  if (pathname.startsWith('/admin')) {
    const backendToken = req.cookies.get(FASTAPI_ADMIN_COOKIE_NAME)?.value
    // If cookie is completely absent, redirect immediately (saves a round-trip)
    if (!backendToken || backendToken.length < 10) {
      const loginUrl = new URL('/admin/login', req.url)
      loginUrl.searchParams.set('next', pathname)
      return NextResponse.redirect(loginUrl)
    }
    // Cookie is present — FastAPI validates it when the page loads its data.
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/admin/:path*'],
}
