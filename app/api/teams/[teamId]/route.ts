import { NextRequest, NextResponse } from 'next/server'
import { getContainer } from '@/server/container'
import { requireAdmin } from '@/lib/auth'
import { createTeamSchema, parseOrThrow, teamIdParamSchema } from '@/lib/validation'
import { ServiceError } from '@/server/services/errors'
import { ValidationError } from '@/lib/validation'

export async function GET(req: NextRequest, { params }: { params: { teamId: string } }) {
  try {
    const { teamId } = await params
    const c = getContainer()
    const team = c.teams.getById(teamId)
    return NextResponse.json({ team })
  } catch (error) {
    if (error instanceof ServiceError && error.code === 'not_found') {
      return NextResponse.json({ error: 'Team not found' }, { status: 404 })
    }
    return NextResponse.json({ error: 'Server error' }, { status: 500 })
  }
}

export async function POST(req: NextRequest) {
  const guard = await requireAdmin(req)
  if (guard !== true) return guard
  try {
    const body = await req.json().catch(() => null)
    const input = parseOrThrow(createTeamSchema, body)
    const c = getContainer()
    const team = c.teams.create(input)
    return NextResponse.json({ team }, { status: 201 })
  } catch (error) {
    if (error instanceof ValidationError) {
      return NextResponse.json({ error: error.message }, { status: 400 })
    }
    if (error instanceof ServiceError && error.code === 'conflict') {
      return NextResponse.json({ error: error.message }, { status: 409 })
    }
    return NextResponse.json({ error: 'Server error' }, { status: 500 })
  }
}

export async function PATCH(req: NextRequest, { params }: { params: { teamId: string } }) {
  const guard = await requireAdmin(req)
  if (guard !== true) return guard
  try {
    const { teamId } = await params
    const body = await req.json().catch(() => null)
    const input = parseOrThrow(require('zod').object({ name: undefined, members: undefined, slogan: undefined }).partial().refine(() => true), body) // placeholder; use proper schema
    // easier: import updateTeamSchema
    const { updateTeamSchema } = await import('@/lib/validation')
    const patch = parseOrThrow(updateTeamSchema, body)
    const c = getContainer()
    const team = c.teams.update(teamId, patch)
    return NextResponse.json({ team })
  } catch (error) {
    if (error instanceof ValidationError) {
      return NextResponse.json({ error: error.message }, { status: 400 })
    }
    if (error instanceof ServiceError) {
      if (error.code === 'not_found') return NextResponse.json({ error: error.message }, { status: 404 })
      if (error.code === 'conflict') return NextResponse.json({ error: error.message }, { status: 409 })
    }
    return NextResponse.json({ error: 'Server error' }, { status: 500 })
  }
}

export async function DELETE(req: NextRequest, { params }: { params: { teamId: string } }) {
  const guard = await requireAdmin(req)
  if (guard !== true) return guard
  try {
    const { teamId } = await params
    const c = getContainer()
    c.teams.remove(teamId)
    return NextResponse.json({ ok: true })
  } catch (error) {
    if (error instanceof ServiceError && error.code === 'not_found') {
      return NextResponse.json({ error: error.message }, { status: 404 })
    }
    return NextResponse.json({ error: 'Server error' }, { status: 500 })
  }
}
