import { NextRequest, NextResponse } from 'next/server'
import { getContainer } from '@/server/container'
import { requireAdmin } from '@/lib/auth'
import { classOnlySchema, parseOrThrow, prepareQuizSchema } from '@/lib/validation'
import { isServiceError } from '@/server/services/errors'
import { ValidationError } from '@/lib/validation'
import { classIdParamSchema } from '@/lib/validation/schemas'

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const query = parseOrThrow(classIdParamSchema, { classId: searchParams.get('classId') })
  const c = getContainer()
  const state = c.quiz.getState(query.classId)
  const snapshot = c.quiz.snapshot(query.classId)
  return NextResponse.json({ quiz: state, snapshot })
}

export async function POST(req: NextRequest) {
  const guard = await requireAdmin(req)
  if (guard !== true) return guard
  try {
    const body = await req.json().catch(() => null)
    const input = parseOrThrow(prepareQuizSchema, body)
    const c = getContainer()
    const state = c.quiz.prepare(input.classId)
    return NextResponse.json({ quiz: state }, { status: 201 })
  } catch (error) {
    if (error instanceof ValidationError) {
      return NextResponse.json({ error: error.message }, { status: 400 })
    }
    if (isServiceError(error) && error.code === 'invalid_state') {
      return NextResponse.json({ error: error.message }, { status: 409 })
    }
    return NextResponse.json({ error: 'Server error' }, { status: 500 })
  }
}
