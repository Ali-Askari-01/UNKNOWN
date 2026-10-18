import { NextRequest, NextResponse } from 'next/server'
import { getContainer } from '@/server/container'
import { requireAdmin } from '@/lib/auth'
import { parseOrThrow, classIdParamSchema, quizIdParamSchema, setCodeSchema, classOnlySchema } from '@/lib/validation'
import { isServiceError } from '@/server/services/errors'
import { ValidationError } from '@/lib/validation'

export async function POST(req: NextRequest, { params }: { params: { quizId: string; action: string } }) {
  const guard = await requireAdmin(req)
  if (guard !== true) return guard
  try {
    const { quizId, action } = await params
    const body = await req.json().catch(() => null)
    const c = getContainer()
    const state = c.quiz.getState('ix') // fallback; action handlers should resolve classId
    // minimal pass-through
    if (action === 'start') {
      const { classId } = parseOrThrow(classOnlySchema, body ?? { classId: 'ix' })
      c.quiz.start(classId)
      return NextResponse.json({ ok: true })
    }
    if (action === 'pause') {
      const { classId } = parseOrThrow(classOnlySchema, body ?? { classId: 'ix' })
      c.quiz.pause(classId)
      return NextResponse.json({ ok: true })
    }
    if (action === 'resume') {
      const { classId } = parseOrThrow(classOnlySchema, body ?? { classId: 'ix' })
      c.quiz.resume(classId)
      return NextResponse.json({ ok: true })
    }
    if (action === 'finish') {
      const { classId } = parseOrThrow(classOnlySchema, body ?? { classId: 'ix' })
      c.quiz.finish(classId)
      return NextResponse.json({ ok: true })
    }
    if (action === 'code') {
      const input = parseOrThrow(setCodeSchema, body ?? { classId: 'ix', code: 'CODE' })
      c.quiz.setCode(input.classId, input.code)
      return NextResponse.json({ ok: true, code: c.quiz.getState(input.classId).code })
    }
    return NextResponse.json({ error: 'Unknown action' }, { status: 400 })
  } catch (error) {
    if (error instanceof ValidationError) return NextResponse.json({ error: error.message }, { status: 400 })
    if (isServiceError(error) && error.code === 'invalid_state') return NextResponse.json({ error: error.message }, { status: 409 })
    return NextResponse.json({ error: 'Server error' }, { status: 500 })
  }
}
