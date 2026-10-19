/**
 * server.ts
 * Custom Node.js HTTP server that hosts both Socket.IO and Next.js.
 * Run with: node --import tsx/esm server.ts   (dev)
 *       or: node --import tsx/esm server.ts   (prod after next build)
 *
 * All quiz state mutations happen here via the service layer (server/services).
 * Clients never mutate state directly.
 */

import './server/bootstrap-als.ts'
import { createServer } from 'node:http'
import { parse } from 'node:url'
import next from 'next'
import { Server as SocketIOServer, type Socket } from 'socket.io'
import { parseCookie } from 'cookie'
import { verifySessionToken } from './lib/session'
import { assertSessionSecretConfigured } from './lib/auth/index'
import { getContainer } from './server/container'
import { isServiceError } from './server/services/errors'
import type { ClassId, RoomSnapshot } from './types'
import { ValidationError, answerSchema, classIdSchema, parseOrThrow } from './lib/validation/index'
import {
  broadcastLeaderboard,
  broadcastRoom,
  emitAnswerResult,
  registerIO,
} from './server/realtime/emitters'
import { createTeamToken } from './lib/auth/index'

const dev = process.env.NODE_ENV !== 'production'
const hostname = process.env.HOSTNAME ?? 'localhost'
const port = parseInt(process.env.PORT ?? '3000', 10)

const app = next({ dev, hostname, port })
const handle = app.getRequestHandler()

async function isAdminSocket(socket: Socket): Promise<boolean> {
  try {
    const raw = socket.handshake.headers.cookie ?? ''
    const cookies = parseCookie(raw)
    const token = cookies['quiz_admin_session']
    return await verifySessionToken(token)
  } catch {
    return false
  }
}

function safeClassId(raw: unknown): ClassId | null {
  try {
    return parseOrThrow(classIdSchema, raw)
  } catch {
    return null
  }
}

assertSessionSecretConfigured()

app.prepare().then(() => {
  const httpServer = createServer((req, res) => {
    const parsedUrl = parse(req.url ?? '/', true)
    handle(req, res, parsedUrl)
  })

  const io = new SocketIOServer(httpServer, {
    cors: { origin: '*', methods: ['GET', 'POST'] },
    transports: ['websocket', 'polling'],
  })
  registerIO(io)

  io.use(async (socket, next) => {
    socket.data.isAdmin = await isAdminSocket(socket)
    next()
  })

  io.on('connection', (socket) => {
    const container = getContainer()

    container.buzzer.setExpireHandler((expiredClassId) => {
      broadcastRoom(expiredClassId)
      io.to(`room:${expiredClassId}`).emit('buzzer:expired', {
        classId: expiredClassId,
      })
      io.to('admin').emit('buzzer:expired', { classId: expiredClassId })
    })

    socket.on(
      'room:join',
      async (
        payload: { classId: ClassId; code: string; groupName: string },
        cb: (res: { ok: boolean; error?: string; state?: RoomSnapshot; token?: string }) => void
      ) => {
        try {
          const { classId, code, groupName } = payload ?? {}
          if (!classId || !code || !groupName) {
            return cb({ ok: false, error: 'Missing fields.' })
          }
          const result = container.quiz.join(classId, code, groupName)

          Array.from(socket.rooms)
            .filter((r) => r.startsWith('room:'))
            .forEach((r) => socket.leave(r))

          socket.data.classId = classId
          socket.data.groupName = result.team.name
          socket.join(`room:${classId}`)
          container.quiz.addConnected(classId, socket.id)
          broadcastRoom(classId)

          const token = await createTeamToken(result.team.classId, result.team.name)
          cb({ ok: true, state: container.quiz.snapshot(classId), token })
        } catch (error) {
          if (isServiceError(error)) {
            return cb({ ok: false, error: error.message })
          }
          return cb({ ok: false, error: 'Server error' })
        }
      }
    )

    socket.on('admin:join', (cb: (res: { ok: boolean; states?: RoomSnapshot[] }) => void) => {
      if (!socket.data.isAdmin) return cb({ ok: false })
      socket.join('admin')
      const states = (['ix', 'x', 'xi'] as ClassId[]).map((cid) =>
        container.quiz.snapshot(cid)
      )
      cb({ ok: true, states })
    })

    socket.on('buzzer:press', (cb: (res: { ok: boolean; error?: string }) => void) => {
      const { classId, groupName } = socket.data
      if (!classId || !groupName) return cb({ ok: false, error: 'Not in a room.' })

      try {
        container.buzzer.press(classId, groupName)
      } catch (error) {
        if (isServiceError(error)) {
          return cb({ ok: false, error: error.message })
        }
        return cb({ ok: false, error: 'Server error' })
      }

      broadcastRoom(classId)
      io.to(`room:${classId}`).emit('buzzer:winner', {
        classId,
        teamName: groupName,
        answerDeadline: container.quiz.getState(classId).answerDeadline,
      })
      io.to('admin').emit('buzzer:winner', {
        classId,
        teamName: groupName,
        answerDeadline: container.quiz.getState(classId).answerDeadline,
      })
      cb({ ok: true })
    })

    socket.on(
      'answer:submit',
      (
        payload: { answer: string },
        cb?: (res: { ok: boolean; error?: string; correct?: boolean; pointsAwarded?: number }) => void
      ) => {
        const { classId, groupName } = socket.data
        if (!classId || !groupName) return cb?.({ ok: false, error: 'Not in a room.' })
        try {
          const { answer } = parseOrThrow(answerSchema, payload)
          const result = container.answer.submitAnswer(classId, groupName, answer)
          broadcastRoom(classId)
          emitAnswerResult(classId, result.teamName, result.correct, result.pointsAwarded)
          broadcastLeaderboard(classId)
          cb?.({ ok: true, correct: result.correct, pointsAwarded: result.pointsAwarded })
        } catch (error) {
          if (isServiceError(error)) {
            return cb?.({ ok: false, error: error.message })
          }
          if (error instanceof ValidationError) {
            return cb?.({ ok: false, error: error.message })
          }
          return cb?.({ ok: false, error: 'Server error' })
        }
      }
    )

    socket.on('admin:openRoom', (rawClassId: ClassId, cb?: Function) => {
      if (!socket.data.isAdmin) return cb?.({ ok: false })
      const classId = safeClassId(rawClassId)
      if (!classId) return cb?.({ ok: false, error: 'Invalid class' })
      try {
        container.quiz.open(classId)
      } catch (error) {
        if (isServiceError(error)) return cb?.({ ok: false, error: error.message })
        return cb?.({ ok: false })
      }
      broadcastRoom(classId)
      cb?.({ ok: true })
    })

    socket.on('admin:resetRoom', (rawClassId: ClassId, cb?: Function) => {
      if (!socket.data.isAdmin) return cb?.({ ok: false })
      const classId = safeClassId(rawClassId)
      if (!classId) return cb?.({ ok: false, error: 'Invalid class' })
      try {
        container.quiz.reset(classId)
      } catch (error) {
        if (isServiceError(error)) return cb?.({ ok: false, error: error.message })
        return cb?.({ ok: false })
      }
      broadcastRoom(classId)
      cb?.({ ok: true })
    })

    socket.on(
      'admin:setCode',
      (payload: { classId: ClassId; code: string }, cb?: Function) => {
        if (!socket.data.isAdmin) return cb?.({ ok: false })
        const classId = safeClassId(payload?.classId)
        if (!classId || !payload?.code) return cb?.({ ok: false, error: 'Invalid payload' })
        try {
          container.quiz.setCode(classId, payload.code)
        } catch (error) {
          if (isServiceError(error)) return cb?.({ ok: false, error: error.message })
          return cb?.({ ok: false })
        }
        broadcastRoom(classId)
        cb?.({ ok: true, code: container.quiz.getState(classId).code })
      }
    )

    socket.on('admin:startQuiz', (rawClassId: ClassId, cb?: Function) => {
      if (!socket.data.isAdmin) return cb?.({ ok: false })
      const classId = safeClassId(rawClassId)
      if (!classId) return cb?.({ ok: false, error: 'Invalid class' })
      try {
        container.quiz.start(classId)
      } catch (error) {
        if (isServiceError(error)) return cb?.({ ok: false, error: error.message })
        return cb?.({ ok: false })
      }
      broadcastRoom(classId)
      cb?.({ ok: true })
    })

    socket.on('admin:pauseQuiz', (rawClassId: ClassId, cb?: Function) => {
      if (!socket.data.isAdmin) return cb?.({ ok: false })
      const classId = safeClassId(rawClassId)
      if (!classId) return cb?.({ ok: false, error: 'Invalid class' })
      try {
        container.quiz.pause(classId)
      } catch (error) {
        if (isServiceError(error)) return cb?.({ ok: false, error: error.message })
        return cb?.({ ok: false })
      }
      broadcastRoom(classId)
      cb?.({ ok: true })
    })

    socket.on('admin:resumeQuiz', (rawClassId: ClassId, cb?: Function) => {
      if (!socket.data.isAdmin) return cb?.({ ok: false })
      const classId = safeClassId(rawClassId)
      if (!classId) return cb?.({ ok: false, error: 'Invalid class' })
      try {
        container.quiz.resume(classId)
      } catch (error) {
        if (isServiceError(error)) return cb?.({ ok: false, error: error.message })
        return cb?.({ ok: false })
      }
      broadcastRoom(classId)
      cb?.({ ok: true })
    })

    socket.on('admin:endQuiz', (rawClassId: ClassId, cb?: Function) => {
      if (!socket.data.isAdmin) return cb?.({ ok: false })
      const classId = safeClassId(rawClassId)
      if (!classId) return cb?.({ ok: false, error: 'Invalid class' })
      try {
        container.quiz.finish(classId)
      } catch (error) {
        if (isServiceError(error)) return cb?.({ ok: false, error: error.message })
        return cb?.({ ok: false })
      }
      broadcastRoom(classId)
      broadcastLeaderboard(classId)
      cb?.({ ok: true })
    })

    socket.on('admin:activateBuzzer', (rawClassId: ClassId, cb?: Function) => {
      if (!socket.data.isAdmin) return cb?.({ ok: false })
      const classId = safeClassId(rawClassId)
      if (!classId) return cb?.({ ok: false, error: 'Invalid class' })
      try {
        container.buzzer.activate(classId)
      } catch (error) {
        if (isServiceError(error)) return cb?.({ ok: false, error: error.message })
        return cb?.({ ok: false })
      }
      broadcastRoom(classId)
      cb?.({ ok: true })
    })

    socket.on('admin:disableBuzzer', (rawClassId: ClassId, cb?: Function) => {
      if (!socket.data.isAdmin) return cb?.({ ok: false })
      const classId = safeClassId(rawClassId)
      if (!classId) return cb?.({ ok: false, error: 'Invalid class' })
      container.buzzer.disable(classId)
      broadcastRoom(classId)
      cb?.({ ok: true })
    })

    socket.on('admin:reEnableBuzzer', (rawClassId: ClassId, cb?: Function) => {
      if (!socket.data.isAdmin) return cb?.({ ok: false })
      const classId = safeClassId(rawClassId)
      if (!classId) return cb?.({ ok: false, error: 'Invalid class' })
      try {
        container.buzzer.reopen(classId)
      } catch (error) {
        if (isServiceError(error)) return cb?.({ ok: false, error: error.message })
        return cb?.({ ok: false })
      }
      broadcastRoom(classId)
      cb?.({ ok: true })
    })

    socket.on(
      'admin:markCorrect',
      (payload: { classId: ClassId; points: number }, cb?: Function) => {
        if (!socket.data.isAdmin) return cb?.({ ok: false })
        const classId = safeClassId(payload?.classId)
        if (!classId) return cb?.({ ok: false, error: 'Invalid class' })
        const winner = container.buzzer.currentWinner(classId)
        if (!winner) return cb?.({ ok: false, error: 'No buzzer winner' })
        const points = typeof payload?.points === 'number' ? payload.points : 10
        container.scoring.award(classId, winner, points)
        container.buzzer.resolveAnswer(classId)
        broadcastRoom(classId)
        emitAnswerResult(classId, winner, true, points)
        broadcastLeaderboard(classId)
        cb?.({ ok: true })
      }
    )

    socket.on(
      'admin:markIncorrect',
      (payload: { classId: ClassId; deduct: number }, cb?: Function) => {
        if (!socket.data.isAdmin) return cb?.({ ok: false })
        const classId = safeClassId(payload?.classId)
        if (!classId) return cb?.({ ok: false, error: 'Invalid class' })
        const winner = container.buzzer.currentWinner(classId)
        if (!winner) return cb?.({ ok: false, error: 'No buzzer winner' })
        const deduct = typeof payload?.deduct === 'number' ? payload.deduct : 0
        if (deduct > 0) container.scoring.deduct(classId, winner, deduct)
        container.buzzer.resolveAnswer(classId)
        broadcastRoom(classId)
        emitAnswerResult(classId, winner, false, -deduct)
        broadcastLeaderboard(classId)
        cb?.({ ok: true })
      }
    )

    socket.on(
      'admin:adjustScore',
      (payload: { classId: ClassId; groupName: string; delta: number }, cb?: Function) => {
        if (!socket.data.isAdmin) return cb?.({ ok: false })
        const classId = safeClassId(payload?.classId)
        if (!classId || !payload?.groupName || typeof payload?.delta !== 'number') {
          return cb?.({ ok: false, error: 'Invalid payload' })
        }
        container.scoring.adjust(classId, payload.groupName, payload.delta)
        broadcastRoom(classId)
        broadcastLeaderboard(classId)
        cb?.({ ok: true })
      }
    )

    socket.on('admin:nextQuestion', (rawClassId: ClassId, cb?: Function) => {
      if (!socket.data.isAdmin) return cb?.({ ok: false })
      const classId = safeClassId(rawClassId)
      if (!classId) return cb?.({ ok: false, error: 'Invalid class' })
      try {
        container.quiz.nextQuestion(classId)
      } catch (error) {
        if (isServiceError(error)) return cb?.({ ok: false, error: error.message })
        return cb?.({ ok: false })
      }
      broadcastRoom(classId)
      cb?.({ ok: true })
    })

    socket.on('admin:resetQuestion', (rawClassId: ClassId, cb?: Function) => {
      if (!socket.data.isAdmin) return cb?.({ ok: false })
      const classId = safeClassId(rawClassId)
      if (!classId) return cb?.({ ok: false, error: 'Invalid class' })
      try {
        container.quiz.resetQuestion(classId)
      } catch (error) {
        if (isServiceError(error)) return cb?.({ ok: false, error: error.message })
        return cb?.({ ok: false })
      }
      broadcastRoom(classId)
      cb?.({ ok: true })
    })

    socket.on('admin:getStates', (cb: (states: RoomSnapshot[]) => void) => {
      if (!socket.data.isAdmin) return cb([])
      cb((['ix', 'x', 'xi'] as ClassId[]).map((cid) => container.quiz.snapshot(cid)))
    })

    socket.on('room:getState', (cb: (state: RoomSnapshot | null) => void) => {
      const { classId } = socket.data
      if (!classId) return cb(null)
      cb(container.quiz.snapshot(classId))
    })

    socket.on('disconnect', () => {
      const { classId } = socket.data
      if (classId) {
        container.quiz.removeConnected(classId, socket.id)
        broadcastRoom(classId)
      }
    })
  })

  httpServer.listen(port, () => {
    console.log(`\n▲ Tech Event server ready`)
    console.log(`  Local:   http://${hostname}:${port}`)
    console.log(`  Admin:   http://${hostname}:${port}/admin/quiz`)
    console.log(`  Student: http://${hostname}:${port}/quiz\n`)
  })
})
