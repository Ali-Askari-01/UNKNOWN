import { NextRequest, NextResponse } from 'next/server'
import { getContainer } from '@/server/container'
import { parseOrThrow, leaderboardQuerySchema } from '@/lib/validation'
import { ValidationError } from '@/lib/validation'

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url)
    const query = parseOrThrow(leaderboardQuerySchema, {
      classId: searchParams.get('classId'),
    })
    const c = getContainer()
    const entries = c.leaderboard.get(query.classId)
    return NextResponse.json({ entries })
  } catch (error) {
    if (error instanceof ValidationError) {
      return NextResponse.json({ error: error.message }, { status: 400 })
    }
    return NextResponse.json({ error: 'Server error' }, { status: 500 })
  }
}
