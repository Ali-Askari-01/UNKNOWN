/**
 * GET /api/admin/me
 * Returns auth status — used by the admin panel to verify session on mount.
 */

import { NextRequest, NextResponse } from 'next/server'
import { verifySessionToken, COOKIE_NAME } from '@/lib/session'

export async function GET(req: NextRequest) {
  const token = req.cookies.get(COOKIE_NAME)?.value
  const authenticated = await verifySessionToken(token)
  if (!authenticated) {
    return NextResponse.json({ authenticated: false }, { status: 401 })
  }
  return NextResponse.json({ authenticated: true })
}
