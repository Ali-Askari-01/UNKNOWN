import type { ClassId } from '@/types'
import { AuthConfigError, getSessionSecret } from './config'
import { sign, timingSafeEqualString } from './hmac'

export const TEAM_TOKEN_MAX_AGE = 60 * 60 * 8

export interface TeamTokenPayload {
  role: 'team'
  classId: ClassId
  teamName: string
  exp: number
}

function toBase64(str: string): string {
  const bytes = new TextEncoder().encode(str)
  let bin = ''
  for (const b of bytes) bin += String.fromCharCode(b)
  return btoa(bin)
}

function fromBase64(b64: string): string {
  const bin = atob(b64)
  const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0))
  return new TextDecoder().decode(bytes)
}

export async function createTeamToken(classId: ClassId, teamName: string): Promise<string> {
  const payload: TeamTokenPayload = {
    role: 'team',
    classId,
    teamName,
    exp: Date.now() + TEAM_TOKEN_MAX_AGE * 1000,
  }
  const b64 = toBase64(JSON.stringify(payload))
  const sig = await sign(b64, getSessionSecret())
  return `${b64}.${sig}`
}

export async function verifyTeamToken(
  token: string | undefined | null,
): Promise<TeamTokenPayload | null> {
  if (!token) return null
  try {
    const dot = token.lastIndexOf('.')
    if (dot === -1) return null
    const b64 = token.slice(0, dot)
    const sig = token.slice(dot + 1)
    if (sig.length !== 32) return null
    const expected = await sign(b64, getSessionSecret())
    if (!timingSafeEqualString(sig, expected)) return null
    const payload = JSON.parse(fromBase64(b64)) as TeamTokenPayload
    if (payload.role !== 'team') return null
    if (typeof payload.classId !== 'string' || typeof payload.teamName !== 'string') return null
    if (Date.now() >= payload.exp) return null
    return payload
  } catch (error) {
    if (error instanceof AuthConfigError) throw error
    return null
  }
}

export function extractBearerToken(header: string | null): string | null {
  if (!header) return null
  const match = /^Bearer\s+(.+)$/i.exec(header.trim())
  return match ? match[1].trim() : null
}
