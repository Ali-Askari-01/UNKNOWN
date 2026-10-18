import { NextRequest, NextResponse } from 'next/server'
import { getContainer } from '@/server/container'
import { requireAdmin } from '@/lib/auth'
import { classIdParamSchema, parseOrThrow } from '@/lib/validation'

export async function GET(req: NextRequest) {
  const c = getContainer()
  const classes = ['ix', 'x', 'xi'] as const
  const result = classes.map((id) => {
    const track = c.teams.list(id)
    return {
      id,
      teamCount: track.length,
    }
  })
  return NextResponse.json({ classes: result })
}

export async function POST(req: NextRequest) {
  const guard = await requireAdmin(req)
  if (guard !== true) return guard
  const body = await req.json().catch(() => null)
  const { classId } = parseOrThrow(classIdParamSchema, body)
  const c = getContainer()
  const state = c.quiz.prepare(classId)
  return NextResponse.json({ quiz: { id: state.id, classId: state.classId, status: state.status } }, { status: 201 })
}
