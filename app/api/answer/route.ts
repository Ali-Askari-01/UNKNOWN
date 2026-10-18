import { NextRequest, NextResponse } from 'next/server'
import { getContainer } from '@/server/container'
import { parseOrThrow, answerSchema } from '@/lib/validation'
import { ValidationError } from '@/lib/validation'
import { isServiceError } from '@/server/services/errors'
import { AuthConfigError, extractBearerToken, verifyTeamToken } from '@/lib/auth/index'
import {
  broadcastLeaderboard,
  broadcastRoom,
  emitAnswerResult,
} from '@/server/realtime/emitters'

export async function POST(req: NextRequest) {
  try {
    const token = extractBearerToken(req.headers.get('authorization'))
    const session = await verifyTeamToken(token)
    if (!session) {
      return NextResponse.json({ error: 'Missing or invalid team token' }, { status: 401 })
    }

    const body = await req.json().catch(() => null)
    const { answer } = parseOrThrow(answerSchema, body)

    const c = getContainer()
    const result = c.answer.submitAnswer(session.classId, session.teamName, answer)

    emitAnswerResult(session.classId, result.teamName, result.correct, result.pointsAwarded)
    broadcastRoom(session.classId)
    broadcastLeaderboard(session.classId)

    return NextResponse.json({
      correct: result.correct,
      pointsAwarded: result.pointsAwarded,
      snapshot: c.quiz.snapshot(session.classId),
    })
  } catch (error) {
    if (error instanceof ValidationError) {
      return NextResponse.json({ error: error.message }, { status: 400 })
    }
    if (error instanceof AuthConfigError) {
      return NextResponse.json({ error: error.message }, { status: 500 })
    }
    if (isServiceError(error)) {
      if (error.code === 'unauthorized') return NextResponse.json({ error: error.message }, { status: 401 })
      if (error.code === 'not_found') return NextResponse.json({ error: error.message }, { status: 404 })
      if (error.code === 'invalid_state') return NextResponse.json({ error: error.message }, { status: 409 })
      if (error.code === 'forbidden') return NextResponse.json({ error: error.message }, { status: 403 })
    }
    return NextResponse.json({ error: 'Server error' }, { status: 500 })
  }
}
