import type { Server as SocketIOServer } from 'socket.io'
import type { ClassId } from '@/types'
import { getContainer } from '@/server/container'

/**
 * The Socket.IO server instance lives on globalThis for the same reason as the
 * container: server.ts registers `io` from the tsx module graph while API
 * routes are compiled by Next into a separate module graph.
 */
const IO_KEY = Symbol.for('UNKNOWN.quiz.io')

interface IOGlobal {
  [IO_KEY]?: SocketIOServer | null
}

export function registerIO(instance: SocketIOServer | null): void {
  ;(globalThis as IOGlobal)[IO_KEY] = instance
}

function io(): SocketIOServer | null {
  return (globalThis as IOGlobal)[IO_KEY] ?? null
}

export function broadcastRoom(classId: ClassId): void {
  const ioServer = io()
  if (!ioServer) return
  const snap = getContainer().quiz.snapshot(classId)
  ioServer.to(`room:${classId}`).emit('room:state', snap)
  ioServer.to('admin').emit('room:state', snap)
}

export function broadcastLeaderboard(classId: ClassId): void {
  const ioServer = io()
  if (!ioServer) return
  const entries = getContainer().leaderboard.get(classId)
  ioServer.to(`room:${classId}`).emit('leaderboard:update', { classId, entries })
  ioServer.to('admin').emit('leaderboard:update', { classId, entries })
}

export function emitAnswerResult(
  classId: ClassId,
  teamName: string,
  correct: boolean,
  pointsAwarded: number,
): void {
  const ioServer = io()
  if (!ioServer) return
  const payload = { classId, teamName, correct, pointsAwarded }
  ioServer.to(`room:${classId}`).emit('answer:result', payload)
  ioServer.to('admin').emit('answer:result', payload)
}
