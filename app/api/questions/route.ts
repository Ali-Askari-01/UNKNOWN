import { NextRequest, NextResponse } from 'next/server'
import { getContainer } from '@/server/container'
import { requireAdmin } from '@/lib/auth'
import { createQuestionSchema, parseOrThrow, questionsQuerySchema } from '@/lib/validation'
import { ValidationError } from '@/lib/validation'

export async function GET(req: NextRequest) {
  const guard = await requireAdmin(req)
  if (guard !== true) return guard
  const { searchParams } = new URL(req.url)
  const query = parseOrThrow(questionsQuerySchema, {
    classId: searchParams.get('classId'),
  })
  const c = getContainer()
  const questions = c.questions.list(query.classId)
  return NextResponse.json({ questions })
}

export async function POST(req: NextRequest) {
  const guard = await requireAdmin(req)
  if (guard !== true) return guard
  try {
    const body = await req.json().catch(() => null)
    const input = parseOrThrow(createQuestionSchema, body)
    const c = getContainer()
    const question = c.questions.create(input)
    return NextResponse.json({ question }, { status: 201 })
  } catch (error) {
    if (error instanceof ValidationError) {
      return NextResponse.json({ error: error.message }, { status: 400 })
    }
    return NextResponse.json({ error: 'Server error' }, { status: 500 })
  }
}
