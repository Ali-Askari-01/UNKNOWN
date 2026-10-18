import { NextRequest, NextResponse } from 'next/server'
import { getContainer } from '@/server/container'
import { requireAdmin } from '@/lib/auth'
import { parseOrThrow, teamsQuerySchema } from '@/lib/validation'

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const query = parseOrThrow(teamsQuerySchema, {
    classId: searchParams.get('classId'),
  })
  const c = getContainer()
  const teams = c.teams.list(query.classId)
  return NextResponse.json({ teams })
}
