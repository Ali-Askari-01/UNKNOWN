/**
 * quiz-state.ts
 * Server-side only. Single source of truth for all quiz rooms.
 * Never imported by client components.
 */

import { groups } from '@/data/event'

// ─── Types ────────────────────────────────────────────────────────────────────

export type ClassId = 'ix' | 'x' | 'xi'

export type BuzzerState =
  | 'off'       // admin has not activated buzzer
  | 'open'      // buzzer active, waiting for first press
  | 'locked'    // a team won, answering in progress
  | 'expired'   // 20s timer ran out (admin must re-enable)

export type RoomStatus = 'waiting' | 'open' | 'active' | 'ended'

export interface TeamScore {
  groupName: string
  score: number
  buzzCount: number   // how many times this team won the buzzer
}

export interface QuizRoom {
  classId: ClassId
  code: string                        // e.g. 'IX2026'
  status: RoomStatus
  questionNumber: number
  buzzerState: BuzzerState
  buzzerWinner: string | null         // group name of winning team
  buzzerActivatedAt: number | null    // server timestamp (Date.now())
  answerDeadline: number | null       // server timestamp (buzzerActivatedAt + 20000)
  answerTimerHandle: ReturnType<typeof setTimeout> | null
  scores: Record<string, TeamScore>   // keyed by group name
  connectedTeams: Set<string>         // socket ids currently in this room
  // Dedupe: track which groups have already buzzed this question
  buzzedThisQuestion: Set<string>
}

// ─── Initial room factory ────────────────────────────────────────────────────

function makeRoom(classId: ClassId, code: string): QuizRoom {
  const scores: Record<string, TeamScore> = {}
  groups
    .filter((g) => g.classId === classId)
    .forEach((g) => {
      scores[g.name] = { groupName: g.name, score: 0, buzzCount: 0 }
    })

  return {
    classId,
    code,
    status: 'waiting',
    questionNumber: 0,
    buzzerState: 'off',
    buzzerWinner: null,
    buzzerActivatedAt: null,
    answerDeadline: null,
    answerTimerHandle: null,
    scores,
    connectedTeams: new Set(),
    buzzedThisQuestion: new Set(),
  }
}

// ─── Rooms singleton ─────────────────────────────────────────────────────────

const rooms = new Map<ClassId, QuizRoom>([
  ['ix', makeRoom('ix', 'IX2026')],
  ['x',  makeRoom('x',  'X2026')],
  ['xi', makeRoom('xi', 'XI2026')],
])

export function getRoom(classId: ClassId): QuizRoom {
  return rooms.get(classId)!
}

export function getAllRooms(): QuizRoom[] {
  return Array.from(rooms.values())
}

// ─── Serialisable snapshot (safe to emit over Socket.IO) ─────────────────────

export interface RoomSnapshot {
  classId: ClassId
  code: string
  status: RoomStatus
  questionNumber: number
  buzzerState: BuzzerState
  buzzerWinner: string | null
  answerDeadline: number | null   // ms epoch; client calculates remaining secs
  scores: TeamScore[]
  connectedCount: number
}

export function snapshot(room: QuizRoom): RoomSnapshot {
  return {
    classId: room.classId,
    code: room.code,
    status: room.status,
    questionNumber: room.questionNumber,
    buzzerState: room.buzzerState,
    buzzerWinner: room.buzzerWinner,
    answerDeadline: room.answerDeadline,
    scores: Object.values(room.scores).sort((a, b) => b.score - a.score),
    connectedCount: room.connectedTeams.size,
  }
}

// ─── Room mutations (all called from server.ts) ───────────────────────────────

/** Admin opens a room (allows students to join). */
export function openRoom(classId: ClassId): QuizRoom {
  const room = getRoom(classId)
  room.status = 'open'
  return room
}

/** Admin closes/resets a room back to waiting, clears all state. */
export function resetRoom(classId: ClassId): QuizRoom {
  const room = getRoom(classId)
  clearAnswerTimer(room)
  // Preserve connected teams set — sockets stay but state resets
  const connected = room.connectedTeams
  const newRoom = makeRoom(classId, room.code)
  newRoom.connectedTeams = connected
  rooms.set(classId, newRoom)
  return rooms.get(classId)!
}

/** Admin sets a custom room code. */
export function setRoomCode(classId: ClassId, code: string): QuizRoom {
  const room = getRoom(classId)
  room.code = code.trim().toUpperCase()
  return room
}

/** Admin starts the quiz (moves from open → active). */
export function startQuiz(classId: ClassId): QuizRoom {
  const room = getRoom(classId)
  room.status = 'active'
  room.questionNumber = 1
  room.buzzerState = 'off'
  return room
}

/** Admin ends the quiz. */
export function endQuiz(classId: ClassId): QuizRoom {
  const room = getRoom(classId)
  clearAnswerTimer(room)
  room.status = 'ended'
  room.buzzerState = 'off'
  room.buzzerWinner = null
  room.answerDeadline = null
  return room
}

/** Admin activates buzzer for current question. */
export function activateBuzzer(classId: ClassId): QuizRoom {
  const room = getRoom(classId)
  clearAnswerTimer(room)
  room.buzzerState = 'open'
  room.buzzerWinner = null
  room.buzzerActivatedAt = Date.now()
  room.answerDeadline = null
  room.buzzedThisQuestion = new Set() // allow all teams to buzz again
  return room
}

/** Admin disables buzzer immediately. */
export function disableBuzzer(classId: ClassId): QuizRoom {
  const room = getRoom(classId)
  clearAnswerTimer(room)
  room.buzzerState = 'off'
  room.answerDeadline = null
  return room
}

/**
 * A team presses the buzzer.
 * Returns the room if the press is valid (team wins), or null if rejected.
 * onExpire is called by the server when the 20s timer fires.
 */
export function pressBuzzer(
  classId: ClassId,
  groupName: string,
  onExpire: (classId: ClassId) => void
): QuizRoom | null {
  const room = getRoom(classId)

  // Only accept when buzzer is open
  if (room.buzzerState !== 'open') return null
  // Reject if this team already buzzed this question
  if (room.buzzedThisQuestion.has(groupName)) return null
  // Must be a valid group for this class
  const validGroups = groups.filter((g) => g.classId === classId).map((g) => g.name)
  if (!validGroups.includes(groupName)) return null

  // ── Winner! ───────────────────────────────────────────────────────────────
  room.buzzerState = 'locked'
  room.buzzerWinner = groupName
  room.buzzedThisQuestion.add(groupName)
  room.answerDeadline = Date.now() + 20_000
  room.scores[groupName].buzzCount++

  // Start authoritative 20-second server timer
  clearAnswerTimer(room)
  room.answerTimerHandle = setTimeout(() => {
    expireAnswer(classId)
    onExpire(classId)
  }, 20_000)

  return room
}

/** Called when 20s expires (internally or by server). */
export function expireAnswer(classId: ClassId): QuizRoom {
  const room = getRoom(classId)
  clearAnswerTimer(room)
  room.buzzerState = 'expired'
  room.answerDeadline = null
  return room
}

/** Admin marks answer correct → award points. */
export function markCorrect(classId: ClassId, points: number): QuizRoom {
  const room = getRoom(classId)
  if (!room.buzzerWinner) return room
  room.scores[room.buzzerWinner].score += points
  clearAnswerTimer(room)
  room.buzzerState = 'off'
  room.buzzerWinner = null
  room.answerDeadline = null
  return room
}

/** Admin marks answer incorrect → optionally deduct, leave buzzer state for admin to decide. */
export function markIncorrect(classId: ClassId, deduct: number): QuizRoom {
  const room = getRoom(classId)
  if (!room.buzzerWinner) return room
  if (deduct > 0) {
    room.scores[room.buzzerWinner].score -= deduct
  }
  clearAnswerTimer(room)
  room.buzzerState = 'off'
  room.buzzerWinner = null
  room.answerDeadline = null
  return room
}

/** Admin adjusts a team's score directly. */
export function adjustScore(classId: ClassId, groupName: string, delta: number): QuizRoom {
  const room = getRoom(classId)
  if (!room.scores[groupName]) return room
  room.scores[groupName].score += delta
  return room
}

/** Admin moves to the next question — resets buzzer, clears timer/winner. */
export function nextQuestion(classId: ClassId): QuizRoom {
  const room = getRoom(classId)
  clearAnswerTimer(room)
  room.questionNumber++
  room.buzzerState = 'off'
  room.buzzerWinner = null
  room.buzzerActivatedAt = null
  room.answerDeadline = null
  room.buzzedThisQuestion = new Set()
  return room
}

/** Admin resets current question state without advancing the number. */
export function resetQuestion(classId: ClassId): QuizRoom {
  const room = getRoom(classId)
  clearAnswerTimer(room)
  room.buzzerState = 'off'
  room.buzzerWinner = null
  room.buzzerActivatedAt = null
  room.answerDeadline = null
  room.buzzedThisQuestion = new Set()
  return room
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function clearAnswerTimer(room: QuizRoom) {
  if (room.answerTimerHandle !== null) {
    clearTimeout(room.answerTimerHandle)
    room.answerTimerHandle = null
  }
}

/** Validate that a room code + classId combination is correct. */
export function validateRoomEntry(classId: ClassId, code: string): boolean {
  const room = getRoom(classId)
  return (
    room.code === code.trim().toUpperCase() &&
    (room.status === 'open' || room.status === 'active')
  )
}
