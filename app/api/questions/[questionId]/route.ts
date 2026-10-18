import { NextRequest, NextResponse } from 'next/server'
import { getContainer } from '@/server/container'
import { requireAdmin } from '@/lib/auth'
import { parseOrThrow, questionIdParamSchema } from '@/lib/validation'
import { ServiceError } from '@/server/services/errors'
import { ValidationError } from '@/lib/validation'
import { updateQuestionSchema } from '@/lib/validation/schemas'

export async function GET(req: NextRequest, { params }: { params: { questionId: string } }) {
  const guard = await requireAdmin(req)
  if (guard !== true) return guard
  try {
    const { questionId } = await params
    const c = getContainer()
    const question = c.questions.getById(questionId)
    return NextResponse.json({ question })
  } catch (error) {
    if (error instanceof ServiceError && error.code === 'not_found') {
      return NextResponse.json({ error: error.message }, { status: 404 })
    }
    return NextResponse.json({ error: 'Server error' }, { status: 500 })
  }
}

export async function PATCH(req: NextRequest, { params }: { params: { questionId: string } }) {
  const guard = await requireAdmin(req)
  if (guard !== true) return guard
  try {
    const { questionId } = await params
    const body = await req.json().catch(() => null)
    const patch = parseOrThrow(updateQuestionSchema, body)
    const c = getContainer()
    const question = c.questions.update(questionId, patch)
    return NextResponse.json({ question })
  } catch (error) {
    if (error instanceof ValidationError) {
      return NextResponse.json({ error: error.message }, { status: 400 })
    }
    if (error instanceof ServiceError && error.code === 'not_found') {
      return NextResponse.json({ error: error.message }, { status: 404 })
    }
    return NextResponse.json({ error: 'Server error' }, { status: 500 })
  }
}

export async function DELETE(req: NextRequest, { params }: { params: { questionId: string } }) {
  const guard = await requireAdmin(req)
  if (guard !== true) return guard
  try {
    const { questionId } = await params
    const c = getContainer()
    c.questions.remove(questionId)
    return NextResponse.json({ ok: true })
  } catch (error) {
    if (error instanceof ServiceError && error.code === 'not_found') {
      return NextResponse.json({ error: error.message }, { status: 404 })
    }
    return NextResponse.json({ error: 'Server error' }, { status: 500 })
  }
}
