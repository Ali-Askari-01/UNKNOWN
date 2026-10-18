import { NextRequest, NextResponse } from 'next/server'
import { getContainer } from '@/server/container'
import { parseOrThrow, joinSchema } from '@/lib/validation'
import { ServiceError } from '@/server/services/errors'
import { ValidationError } from '@/lib/validation'

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => null)
    const input = parseOrThrow(joinSchema, body)
    const c = getContainer()
    const result = c.quiz.join(input.classId, input.code, input.groupName)
    return NextResponse.json({ ok: true, team: result.team, snapshot: result.snapshot })
  } catch (error) {
    if (error instanceof ValidationError) {
      return NextResponse.json({ error: error.message }, { status: 400 })
    }
    if (error instanceof ServiceError) {
      if (error.code === 'unauthorized') return NextResponse.json({ error: error.message }, { status: 401 })
      if (error.code === 'not_found') return NextResponse.json({ error: error.message }, { status: 404 })
      if (error.code === 'invalid_state') return NextResponse.json({ error: error.message }, { status: 409 })
    }
    return NextResponse.json({ error: 'Server error' }, { status: 500 })
  }
}
