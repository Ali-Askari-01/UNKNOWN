import { NextRequest, NextResponse } from 'next/server'
import { requireAdmin } from '@/lib/auth'

export async function GET(req: NextRequest) {
  const guard = await requireAdmin(req)
  if (guard !== true) return guard
  return NextResponse.json({ authenticated: true })
}
