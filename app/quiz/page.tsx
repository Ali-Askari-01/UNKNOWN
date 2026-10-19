'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import Link from 'next/link'
import { getSocket } from '@/lib/socket-client'
import { groups } from '@/data/event'
import type { RoomSnapshot } from '@/types'

type ClassId = 'ix' | 'x' | 'xi'
type JoinStep = 'select-class' | 'enter-code' | 'select-group' | 'in-room'
type BackendClass = { code: string; display_name: string; preferred_language: string }
type BackendTeam = { id: string; name: string; slogan?: string | null }
type BackendSession = { id: string; class_code: string; status: string }

const CLASS_META: Record<ClassId, { label: string; roman: string; language: string; tone: string }> = {
  ix:  { label: 'CLASS IX',  roman: 'IX',  language: 'PYTHON', tone: 'blue'  },
  x:   { label: 'CLASS X',   roman: 'X',   language: 'C++',    tone: 'aqua'  },
  xi:  { label: 'CLASS XI',  roman: 'XI',  language: 'PYTHON', tone: 'cream' },
}

// ─── Countdown hook (client-rendered from server deadline) ───────────────────
function useCountdown(deadline: number | null): number {
  const [secs, setSecs] = useState(0)
  useEffect(() => {
    if (!deadline) { setSecs(0); return }
    const tick = () => setSecs(Math.max(0, Math.ceil((deadline - Date.now()) / 1000)))
    tick()
    const id = setInterval(tick, 200)
    return () => clearInterval(id)
  }, [deadline])
  return secs
}

// ─── Buzzer button ───────────────────────────────────────────────────────────
function BuzzerButton({
  buzzerState,
  buzzerWinner,
  myGroup,
  onPress,
  disabled,
}: {
  buzzerState: string
  buzzerWinner: string | null
  myGroup: string
  onPress: () => void
  disabled: boolean
}) {
  const iWon = buzzerWinner === myGroup
  const someonElseWon = buzzerWinner !== null && !iWon

  let label = 'PRESS BUZZER'
  let cls = 'sp-buzzer-btn'

  if (buzzerState === 'off' || buzzerState === 'expired') {
    label = buzzerState === 'expired' ? 'TIME EXPIRED' : 'WAITING…'
    cls += ' sp-buzzer-inactive'
  } else if (buzzerState === 'open') {
    label = 'PRESS BUZZER!'
    cls += ' sp-buzzer-active'
  } else if (iWon) {
    label = '★ YOU BUZZED FIRST!'
    cls += ' sp-buzzer-won'
  } else if (someonElseWon) {
    label = `${buzzerWinner} BUZZED FIRST`
    cls += ' sp-buzzer-lost'
  }

  return (
    <button
      type="button"
      className={cls}
      onClick={onPress}
      disabled={disabled || buzzerState !== 'open'}
      aria-label="Press buzzer"
    >
      {label}
    </button>
  )
}

// ─── In-room view ─────────────────────────────────────────────────────────────
function QuizRoom({
  room,
  myGroup,
  onLeave,
}: {
  room: RoomSnapshot
  myGroup: string
  onLeave: () => void
}) {
  const socket = getSocket()
  const countdown = useCountdown(room.answerDeadline)
  const iWon = room.buzzerWinner === myGroup
  const [buzzerMsg, setBuzzerMsg] = useState('')
  const msgRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  function flash(msg: string) {
    setBuzzerMsg(msg)
    if (msgRef.current) clearTimeout(msgRef.current)
    msgRef.current = setTimeout(() => setBuzzerMsg(''), 3000)
  }

  function handleBuzz() {
    socket.emit('buzzer:press', (res: { ok: boolean; error?: string }) => {
      if (!res.ok) flash(res.error ?? 'Could not buzz.')
    })
  }

  const meta = CLASS_META[room.classId]

  const statusMessages: Record<string, string> = {
    waiting: 'Waiting for admin to open the room.',
    open: 'Room is open. Quiz starting soon.',
    active: room.buzzerState === 'off'
      ? `Question #${room.questionNumber} — Waiting for buzzer.`
      : room.buzzerState === 'open'
      ? 'BUZZER IS ACTIVE — press now!'
      : room.buzzerState === 'locked'
      ? iWon ? 'YOU ARE ANSWERING!' : `${room.buzzerWinner} is answering.`
      : 'Turn expired. Waiting for admin.',
    ended: 'Quiz has ended. Final scores below.',
  }

  return (
    <main className="sp-root">
      <header className="sp-header">
        <Link href="/" className="sp-wordmark"><span className="mark">[ ]</span> TECH EVENT</Link>
        <div className="sp-header-meta">
          <span className={`sp-class-badge sp-class-${meta.tone}`}>{meta.label}</span>
          <span className="sp-group-badge">{myGroup}</span>
        </div>
        <button type="button" className="sp-leave-btn" onClick={onLeave}>LEAVE</button>
      </header>

      <div className="sp-body">
        {/* Status banner */}
        <div className={`sp-status-banner sp-banner-${room.status}`}>
          <div className="sp-status-row">
            <span className="sp-status-dot" />
            <span className="sp-status-text">{statusMessages[room.status]}</span>
          </div>
          {room.status === 'active' && (
            <span className="sp-q-num">Q #{room.questionNumber}</span>
          )}
        </div>

        {/* Buzzer area */}
        {room.status === 'active' && (
          <div className="sp-buzzer-area">
            <BuzzerButton
              buzzerState={room.buzzerState}
              buzzerWinner={room.buzzerWinner}
              myGroup={myGroup}
              onPress={handleBuzz}
              disabled={room.buzzerState !== 'open'}
            />

            {/* Winner + countdown */}
            {room.buzzerWinner && (
              <div className={`sp-winner-display ${iWon ? 'sp-winner-me' : 'sp-winner-other'}`}>
                {iWon ? (
                  <>
                    <p className="sp-winner-label">YOU BUZZED FIRST</p>
                    {room.answerDeadline && (
                      <div className={`sp-countdown ${countdown <= 5 ? 'sp-countdown-urgent' : ''}`}>
                        <span className="sp-countdown-num">{countdown}</span>
                        <span className="sp-countdown-label">SECONDS TO ANSWER</span>
                      </div>
                    )}
                    {countdown === 0 && !room.answerDeadline && (
                      <p className="sp-expired-label">TIME EXPIRED</p>
                    )}
                  </>
                ) : (
                  <>
                    <p className="sp-winner-label">BUZZED FIRST:</p>
                    <p className="sp-winner-name">{room.buzzerWinner}</p>
                    {room.answerDeadline && (
                      <div className="sp-countdown sp-countdown-other">
                        <span className="sp-countdown-num">{countdown}</span>
                        <span className="sp-countdown-label">s remaining</span>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {buzzerMsg && <p className="sp-buzzer-msg" role="alert">{buzzerMsg}</p>}
          </div>
        )}

        {room.status === 'ended' && (
          <div className="sp-ended-banner">
            <p className="sp-ended-title">QUIZ COMPLETE</p>
            <p className="sp-ended-sub">Final results are below.</p>
          </div>
        )}

        {/* Live scoreboard */}
        <div className="sp-scoreboard">
          <h2 className="sp-score-title">SCOREBOARD</h2>
          <div className="sp-score-head">
            <span>#</span><span>TEAM</span><span>SCORE</span>
          </div>
          {room.scores.map((s, i) => (
            <div
              key={s.groupName}
              className={`sp-score-row ${s.groupName === myGroup ? 'sp-score-mine' : ''} ${i === 0 ? 'sp-score-top' : ''}`}
            >
              <span className="sp-rank">{i + 1}</span>
              <span className="sp-team-name">
                {s.groupName}
                {s.groupName === myGroup && <span className="sp-you-tag"> (YOU)</span>}
              </span>
              <strong className="sp-pts">{s.score}</strong>
            </div>
          ))}
        </div>
      </div>
    </main>
  )
}

// ─── Join flow ────────────────────────────────────────────────────────────────
export default function StudentQuizPage() {
  const [step, setStep] = useState<JoinStep>('select-class')
  const [selectedClass, setSelectedClass] = useState<ClassId | null>(null)
  const [roomCode, setRoomCode] = useState('')
  const [selectedGroup, setSelectedGroup] = useState('')
  const [joinError, setJoinError] = useState('')
  const [joining, setJoining] = useState(false)
  const [room, setRoom] = useState<RoomSnapshot | null>(null)
  const [myGroup, setMyGroup] = useState('')
  const [connected, setConnected] = useState(false)
  const [backendClasses, setBackendClasses] = useState<BackendClass[]>([])
  const [backendGroups, setBackendGroups] = useState<BackendTeam[]>([])

  useEffect(() => {
    let cancelled = false
    fetch('/api/v1/classes')
      .then((response) => response.ok ? response.json() as Promise<BackendClass[]> : [])
      .then((items) => { if (!cancelled) setBackendClasses(items) })
      .catch(() => undefined)
    return () => { cancelled = true }
  }, [])

  const availableClasses = (backendClasses.length ? backendClasses.map((item) => item.code.toLowerCase()) : ['ix', 'x', 'xi']) as ClassId[]

  useEffect(() => {
    if (!selectedClass) { setBackendGroups([]); return }
    let cancelled = false
    fetch(`/api/v1/teams?class_code=${selectedClass.toUpperCase()}`)
      .then((response) => response.ok ? response.json() as Promise<BackendTeam[]> : [])
      .then((items) => { if (!cancelled) setBackendGroups(items) })
      .catch(() => { if (!cancelled) setBackendGroups([]) })
    return () => { cancelled = true }
  }, [selectedClass])

  const classGroups = selectedClass
    ? (backendGroups.length ? backendGroups.map((team) => team.name) : groups.filter((g) => g.classId === selectedClass).map((g) => g.name))
    : []

  // Socket reconnection: re-join room on reconnect
  useEffect(() => {
    const socket = getSocket()

    function onConnect() {
      setConnected(true)
      // If we were already in a room, re-join transparently
      if (myGroup && selectedClass && roomCode) {
        socket.emit(
          'room:join',
          { classId: selectedClass, code: roomCode, groupName: myGroup },
          (res: { ok: boolean; state?: RoomSnapshot }) => {
            if (res.ok && res.state) setRoom(res.state)
          }
        )
      }
    }

    function onDisconnect() { setConnected(false) }

    function onRoomState(snap: RoomSnapshot) {
      if (snap.classId === selectedClass) setRoom(snap)
    }

    socket.on('connect', onConnect)
    socket.on('disconnect', onDisconnect)
    socket.on('room:state', onRoomState)
    if (socket.connected) setConnected(true)

    return () => {
      socket.off('connect', onConnect)
      socket.off('disconnect', onDisconnect)
      socket.off('room:state', onRoomState)
    }
  }, [selectedClass, roomCode, myGroup])

  const handleJoin = useCallback(async () => {
    if (!selectedClass || !roomCode || !selectedGroup) return
    setJoinError('')
    setJoining(true)
    const normalizedCode = roomCode.trim().toUpperCase()
    const selectedBackendTeam = backendGroups.find((team) => team.name === selectedGroup)
    try {
      const sessionResponse = await fetch(`/api/v1/quiz-sessions/by-code/${encodeURIComponent(normalizedCode)}`)
      if (sessionResponse.ok) {
        const backendSession = await sessionResponse.json() as BackendSession
        if (backendSession.class_code.toLowerCase() !== selectedClass) {
          setJoining(false)
          setJoinError(`This room is configured for Class ${backendSession.class_code}.`)
          return
        }
        if (!selectedBackendTeam) {
          setJoining(false)
          setJoinError('This team is not available in the database-backed event edition.')
          return
        }
        const participantResponse = await fetch(`/api/v1/quiz-sessions/${backendSession.id}/participants`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ team_id: selectedBackendTeam.id }),
        })
        if (!participantResponse.ok) {
          const errorBody = await participantResponse.json().catch(() => ({})) as { detail?: string }
          setJoining(false)
          setJoinError(errorBody.detail ?? 'Could not register the team for this quiz.')
          return
        }
      }
    } catch {
      // The legacy Socket.IO room remains available when FastAPI is offline.
    }
    const socket = getSocket()
    socket.emit(
      'room:join',
      { classId: selectedClass, code: normalizedCode, groupName: selectedGroup },
      (res: { ok: boolean; error?: string; state?: RoomSnapshot }) => {
        setJoining(false)
        if (!res.ok) { setJoinError(res.error ?? 'Could not join.'); return }
        setMyGroup(selectedGroup)
        setRoom(res.state!)
        setStep('in-room')
      }
    )
  }, [selectedClass, roomCode, selectedGroup])

  function handleLeave() {
    setStep('select-class')
    setSelectedClass(null)
    setRoomCode('')
    setSelectedGroup('')
    setRoom(null)
    setMyGroup('')
    setJoinError('')
  }

  // ── In room ────────────────────────────────────────────────────────────────
  if (step === 'in-room' && room) {
    return <QuizRoom room={room} myGroup={myGroup} onLeave={handleLeave} />
  }

  // ── Join flow ──────────────────────────────────────────────────────────────
  return (
    <main className="sp-join-root">
      <header className="sp-join-header">
        <Link href="/" className="sp-wordmark"><span className="mark">[ ]</span> TECH EVENT</Link>
        <span className="sp-join-title">JOIN QUIZ</span>
        <span className={`sp-conn-dot ${connected ? 'conn-ok' : 'conn-off'}`} title={connected ? 'Connected' : 'Connecting…'} />
      </header>

      <div className="sp-join-card">
        {/* Step 1: Select class */}
        <div className="sp-step">
          <p className="sp-step-label">STEP 1 — SELECT YOUR CLASS</p>
          <div className="sp-class-grid">
            {availableClasses.map((cid) => {
              const meta = CLASS_META[cid]
              const backendClass = backendClasses.find((item) => item.code.toLowerCase() === cid)
              return (
                <button
                  key={cid}
                  type="button"
                  className={`sp-class-btn sp-class-${meta.tone} ${selectedClass === cid ? 'is-active' : ''}`}
                  onClick={() => { setSelectedClass(cid); setSelectedGroup(''); setJoinError('') }}
                >
                  <span className="sp-class-roman">{meta.roman}</span>
                  <span className="sp-class-label">{meta.label}</span>
                  <span className="sp-class-lang">{backendClass?.preferred_language?.toUpperCase() ?? meta.language}</span>
                </button>
              )
            })}
          </div>
        </div>

        {/* Step 2: Room code */}
        {selectedClass && (
          <div className="sp-step">
            <p className="sp-step-label">STEP 2 — ENTER ROOM CODE</p>
            <div className="sp-code-row">
              <input
                type="text"
                className="sp-code-input"
                value={roomCode}
                onChange={(e) => { setRoomCode(e.target.value.toUpperCase()); setJoinError('') }}
                placeholder="e.g. IX2026"
                maxLength={16}
                spellCheck={false}
                autoComplete="off"
              />
            </div>
          </div>
        )}

        {/* Step 3: Select group */}
        {selectedClass && roomCode.length >= 2 && (
          <div className="sp-step">
            <p className="sp-step-label">STEP 3 — SELECT YOUR GROUP</p>
            <div className="sp-group-grid">
              {classGroups.map((name) => (
                <button
                  key={name}
                  type="button"
                  className={`sp-group-btn ${selectedGroup === name ? 'is-active' : ''}`}
                  onClick={() => { setSelectedGroup(name); setJoinError('') }}
                >
                  {name}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Error */}
        {joinError && <p className="sp-join-error" role="alert">{joinError}</p>}

        {/* Join button */}
        {selectedClass && roomCode && selectedGroup && (
          <button
            type="button"
            className="sp-join-btn"
            onClick={handleJoin}
            disabled={joining || !connected}
          >
            {joining ? 'JOINING…' : `JOIN ROOM →`}
          </button>
        )}

        {!connected && (
          <p className="sp-conn-warn">Connecting to server… please wait.</p>
        )}
      </div>

      <p className="sp-join-foot">
        <Link href="/">← Back to event site</Link>
      </p>
    </main>
  )
}
