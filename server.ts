/**
 * server.ts
 * Custom Node.js HTTP server that hosts both Socket.IO and Next.js.
 * Run with: node --import tsx/esm server.ts   (dev)
 *       or: node --import tsx/esm server.ts   (prod after next build)
 *
 * All quiz state mutations happen here. Clients never mutate state directly.
 */

import { createServer } from 'node:http'
import { parse } from 'node:url'
import next from 'next'
import { Server as SocketIOServer, type Socket } from 'socket.io'
import { parse as parseCookie } from 'cookie'
import { verifySessionToken } from './lib/session'

import {
  type ClassId,
  type RoomSnapshot,
  getRoom,
  getAllRooms,
  snapshot,
  openRoom,
  resetRoom,
  setRoomCode,
  startQuiz,
  endQuiz,
  activateBuzzer,
  disableBuzzer,
  pressBuzzer,
  markCorrect,
  markIncorrect,
  adjustScore,
  nextQuestion,
  resetQuestion,
  validateRoomEntry,
} from './lib/quiz-state'

// ─── Next.js app ─────────────────────────────────────────────────────────────

const dev = process.env.NODE_ENV !== 'production'
const hostname = process.env.HOSTNAME ?? 'localhost'
const port = parseInt(process.env.PORT ?? '3000', 10)

const app = next({ dev, hostname, port })
const handle = app.getRequestHandler()

// ─── Session helper ───────────────────────────────────────────────────────────

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

// ─── Emitters ─────────────────────────────────────────────────────────────────

function broadcastRoom(io: SocketIOServer, classId: ClassId) {
  const room = getRoom(classId)
  const snap = snapshot(room)
  io.to(`room:${classId}`).emit('room:state', snap)
}

// ─── Boot ─────────────────────────────────────────────────────────────────────

app.prepare().then(() => {
  const httpServer = createServer((req, res) => {
    const parsedUrl = parse(req.url ?? '/', true)
    handle(req, res, parsedUrl)
  })

  const io = new SocketIOServer(httpServer, {
    cors: { origin: '*', methods: ['GET', 'POST'] },
    // Allow polling fallback for networks that block WS
    transports: ['websocket', 'polling'],
  })

  // ── Middleware: tag each socket as admin or student ──────────────────────
  io.use(async (socket, next) => {
    socket.data.isAdmin = await isAdminSocket(socket)
    next()
  })

  // ─── Connection handler ──────────────────────────────────────────────────
  io.on('connection', (socket) => {
    // ── Student: join a room ───────────────────────────────────────────────
    socket.on(
      'room:join',
      (
        payload: { classId: ClassId; code: string; groupName: string },
        cb: (res: { ok: boolean; error?: string; state?: RoomSnapshot }) => void
      ) => {
        const { classId, code, groupName } = payload ?? {}
        if (!classId || !code || !groupName) {
          return cb({ ok: false, error: 'Missing fields.' })
        }
        if (!validateRoomEntry(classId, code)) {
          return cb({ ok: false, error: 'Invalid room code or room is closed.' })
        }
        // Validate group belongs to this class
        const room = getRoom(classId)
        if (!room.scores[groupName]) {
          return cb({ ok: false, error: 'This group is not registered in this room.' })
        }

        // Leave any previous room
        Array.from(socket.rooms)
          .filter((r) => r.startsWith('room:'))
          .forEach((r) => socket.leave(r))

        socket.data.classId = classId
        socket.data.groupName = groupName
        socket.join(`room:${classId}`)
        room.connectedTeams.add(socket.id)
        broadcastRoom(io, classId)

        cb({ ok: true, state: snapshot(room) })
      }
    )

    // ── Admin: join admin room (receives all class updates) ───────────────
    socket.on('admin:join', (cb: (res: { ok: boolean; states?: RoomSnapshot[] }) => void) => {
      if (!socket.data.isAdmin) return cb({ ok: false })
      socket.join('admin')
      const states = getAllRooms().map(snapshot)
      cb({ ok: true, states })
    })

    // ── Student: press buzzer ─────────────────────────────────────────────
    socket.on('buzzer:press', (cb: (res: { ok: boolean; error?: string }) => void) => {
      const { classId, groupName } = socket.data
      if (!classId || !groupName) return cb({ ok: false, error: 'Not in a room.' })

      const result = pressBuzzer(classId, groupName, (expiredClass) => {
        // Timer expired — broadcast to room + admin
        broadcastRoom(io, expiredClass)
        const snap = snapshot(getRoom(expiredClass))
        io.to('admin').emit('room:state', snap)
      })

      if (!result) {
        return cb({ ok: false, error: 'Buzzer not active or already pressed.' })
      }

      broadcastRoom(io, classId)
      io.to('admin').emit('room:state', snapshot(result))
      cb({ ok: true })
    })

    // ── Admin: open room ──────────────────────────────────────────────────
    socket.on('admin:openRoom', (classId: ClassId, cb?: Function) => {
      if (!socket.data.isAdmin) return cb?.({ ok: false })
      const room = openRoom(classId)
      broadcastRoom(io, classId)
      io.to('admin').emit('room:state', snapshot(room))
      cb?.({ ok: true })
    })

    // ── Admin: reset room ─────────────────────────────────────────────────
    socket.on('admin:resetRoom', (classId: ClassId, cb?: Function) => {
      if (!socket.data.isAdmin) return cb?.({ ok: false })
      const room = resetRoom(classId)
      broadcastRoom(io, classId)
      io.to('admin').emit('room:state', snapshot(room))
      cb?.({ ok: true })
    })

    // ── Admin: set room code ──────────────────────────────────────────────
    socket.on('admin:setCode', (payload: { classId: ClassId; code: string }, cb?: Function) => {
      if (!socket.data.isAdmin) return cb?.({ ok: false })
      const room = setRoomCode(payload.classId, payload.code)
      io.to('admin').emit('room:state', snapshot(room))
      cb?.({ ok: true })
    })

    // ── Admin: start quiz ─────────────────────────────────────────────────
    socket.on('admin:startQuiz', (classId: ClassId, cb?: Function) => {
      if (!socket.data.isAdmin) return cb?.({ ok: false })
      const room = startQuiz(classId)
      broadcastRoom(io, classId)
      io.to('admin').emit('room:state', snapshot(room))
      cb?.({ ok: true })
    })

    // ── Admin: end quiz ───────────────────────────────────────────────────
    socket.on('admin:endQuiz', (classId: ClassId, cb?: Function) => {
      if (!socket.data.isAdmin) return cb?.({ ok: false })
      const room = endQuiz(classId)
      broadcastRoom(io, classId)
      io.to('admin').emit('room:state', snapshot(room))
      cb?.({ ok: true })
    })

    // ── Admin: activate buzzer ────────────────────────────────────────────
    socket.on('admin:activateBuzzer', (classId: ClassId, cb?: Function) => {
      if (!socket.data.isAdmin) return cb?.({ ok: false })
      const room = activateBuzzer(classId)
      broadcastRoom(io, classId)
      io.to('admin').emit('room:state', snapshot(room))
      cb?.({ ok: true })
    })

    // ── Admin: disable buzzer ─────────────────────────────────────────────
    socket.on('admin:disableBuzzer', (classId: ClassId, cb?: Function) => {
      if (!socket.data.isAdmin) return cb?.({ ok: false })
      const room = disableBuzzer(classId)
      broadcastRoom(io, classId)
      io.to('admin').emit('room:state', snapshot(room))
      cb?.({ ok: true })
    })

    // ── Admin: re-enable buzzer (alias of activateBuzzer) ─────────────────
    socket.on('admin:reEnableBuzzer', (classId: ClassId, cb?: Function) => {
      if (!socket.data.isAdmin) return cb?.({ ok: false })
      const room = activateBuzzer(classId)
      broadcastRoom(io, classId)
      io.to('admin').emit('room:state', snapshot(room))
      cb?.({ ok: true })
    })

    // ── Admin: mark correct ───────────────────────────────────────────────
    socket.on(
      'admin:markCorrect',
      (payload: { classId: ClassId; points: number }, cb?: Function) => {
        if (!socket.data.isAdmin) return cb?.({ ok: false })
        const room = markCorrect(payload.classId, payload.points ?? 10)
        broadcastRoom(io, payload.classId)
        io.to('admin').emit('room:state', snapshot(room))
        cb?.({ ok: true })
      }
    )

    // ── Admin: mark incorrect ─────────────────────────────────────────────
    socket.on(
      'admin:markIncorrect',
      (payload: { classId: ClassId; deduct: number }, cb?: Function) => {
        if (!socket.data.isAdmin) return cb?.({ ok: false })
        const room = markIncorrect(payload.classId, payload.deduct ?? 0)
        broadcastRoom(io, payload.classId)
        io.to('admin').emit('room:state', snapshot(room))
        cb?.({ ok: true })
      }
    )

    // ── Admin: adjust score directly ──────────────────────────────────────
    socket.on(
      'admin:adjustScore',
      (payload: { classId: ClassId; groupName: string; delta: number }, cb?: Function) => {
        if (!socket.data.isAdmin) return cb?.({ ok: false })
        const room = adjustScore(payload.classId, payload.groupName, payload.delta)
        broadcastRoom(io, payload.classId)
        io.to('admin').emit('room:state', snapshot(room))
        cb?.({ ok: true })
      }
    )

    // ── Admin: next question ──────────────────────────────────────────────
    socket.on('admin:nextQuestion', (classId: ClassId, cb?: Function) => {
      if (!socket.data.isAdmin) return cb?.({ ok: false })
      const room = nextQuestion(classId)
      broadcastRoom(io, classId)
      io.to('admin').emit('room:state', snapshot(room))
      cb?.({ ok: true })
    })

    // ── Admin: reset question ─────────────────────────────────────────────
    socket.on('admin:resetQuestion', (classId: ClassId, cb?: Function) => {
      if (!socket.data.isAdmin) return cb?.({ ok: false })
      const room = resetQuestion(classId)
      broadcastRoom(io, classId)
      io.to('admin').emit('room:state', snapshot(room))
      cb?.({ ok: true })
    })

    // ── Admin: poll current state for all rooms ───────────────────────────
    socket.on('admin:getStates', (cb: (states: RoomSnapshot[]) => void) => {
      if (!socket.data.isAdmin) return cb([])
      cb(getAllRooms().map(snapshot))
    })

    // ── Student: poll current room state ─────────────────────────────────
    socket.on('room:getState', (cb: (state: RoomSnapshot | null) => void) => {
      const { classId } = socket.data
      if (!classId) return cb(null)
      cb(snapshot(getRoom(classId)))
    })

    // ── Disconnect: clean up connected-teams set ──────────────────────────
    socket.on('disconnect', () => {
      const { classId } = socket.data
      if (classId) {
        const room = getRoom(classId)
        room.connectedTeams.delete(socket.id)
        broadcastRoom(io, classId)
        io.to('admin').emit('room:state', snapshot(room))
      }
    })
  })

  // ─── Start listening ──────────────────────────────────────────────────────
  httpServer.listen(port, () => {
    console.log(`\n▲ Tech Event server ready`)
    console.log(`  Local:   http://${hostname}:${port}`)
    console.log(`  Admin:   http://${hostname}:${port}/admin/quiz`)
    console.log(`  Student: http://${hostname}:${port}/quiz\n`)
  })
})
