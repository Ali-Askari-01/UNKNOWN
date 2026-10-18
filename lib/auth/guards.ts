import { NextResponse } from 'next/server'
import { COOKIE_NAME, verifySessionCookieHeader, verifySessionToken } from './session'

export interface AdminSessionResult {
  authenticated: boolean
  token?: string
}

export async function getAdminSessionFromRequest(req: Request): Promise<AdminSessionResult> {
  const token = req.headers.get('cookie')
    ? readCookieFromHeader(req.headers.get('cookie') ?? undefined, COOKIE_NAME)
    : undefined
  if (!token) return { authenticated: false }
  const ok = await verifySessionToken(token)
  return ok ? { authenticated: true, token } : { authenticated: false }
}

export async function isAdminRequest(req: Request): Promise<boolean> {
  const result = await getAdminSessionFromRequest(req)
  return result.authenticated
}

export function unauthorizedResponse(message = 'Unauthorized'): NextResponse {
  return NextResponse.json({ error: message, authenticated: false }, { status: 401 })
}

export async function requireAdmin(req: Request): Promise<true | NextResponse> {
  if (await isAdminRequest(req)) return true
  return unauthorizedResponse()
}

function readCookieFromHeader(header: string | undefined, name: string): string | undefined {
  if (!header) return undefined
  for (const part of header.split(';')) {
    const eq = part.indexOf('=')
    if (eq === -1) continue
    if (part.slice(0, eq).trim() === name) {
      return decodeURIComponent(part.slice(eq + 1).trim())
    }
  }
  return undefined
}

export { verifySessionCookieHeader }
