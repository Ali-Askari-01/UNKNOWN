'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { getSocket } from '@/lib/socket-client'
import type { RoomSnapshot, TeamScore } from '@/types'

type ClassId = 'ix' | 'x' | 'xi'

const CLASS_LABELS: Record<ClassId, string> = { ix: 'CLASS IX', x: 'CLASS X', xi: 'CLASS XI' }
const CLASS_TONES: Record<ClassId, string> = { ix: 'blue', x: 'aqua', xi: 'cream' }

// ─── Countdown display (client-calculated from server deadline) ───────────────
function useCountdown(deadline: number | null): number {
  const [secs, setSecs] = useState(0)
  useEffect(() => {
    if (!deadline) { setSecs(0); return }
    const tick = () => setSecs(Math.max(0, Math.ceil((deadline - Date.now()) / 1000)))
    tick()
    const id = setInterval(tick, 250)
    return () => clearInterval(id)
  }, [deadline])
  return secs
}

// ─── Per-class room panel ─────────────────────────────────────────────────────
function RoomPanel({
  room,
  isActive,
  onSelect,
}: {
  room: RoomSnapshot
  isActive: boolean
  onSelect: () => void
}) {
  const tone = CLASS_TONES[room.classId]
  const label = CLASS_LABELS[room.classId]
  const countdown = useCountdown(room.answerDeadline)

  const socket = getSocket()
  const emit = useCallback(
    (event: string, payload?: unknown) => {
      socket.emit(event, payload ?? room.classId)
    },
    [socket, room.classId]
  )

  const [customCode, setCustomCode] = useState(room.code ?? '')
  const [pointsValue, setPointsValue] = useState(10)
  const [deductValue, setDeductValue] = useState(0)
  const [adjustGroup, setAdjustGroup] = useState(room.scores[0]?.groupName ?? '')
  const [adjustDelta, setAdjustDelta] = useState(0)
  const [actionMsg, setActionMsg] = useState('')
  const msgTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  function flash(msg: string) {
    setActionMsg(msg)
    if (msgTimer.current) clearTimeout(msgTimer.current)
    msgTimer.current = setTimeout(() => setActionMsg(''), 2500)
  }

  // Keep customCode in sync when room.code changes from server
  useEffect(() => { setCustomCode(room.code ?? '') }, [room.code])
  useEffect(() => {
    if (room.scores.length > 0 && !adjustGroup) setAdjustGroup(room.scores[0].groupName)
  }, [room.scores, adjustGroup])

  const buzzerStateLabel: Record<string, string> = {
    off: 'OFF',
    open: 'OPEN — WAITING',
    locked: `LOCKED — ${room.buzzerWinner ?? '?'} ANSWERING`,
    expired: 'EXPIRED',
  }

  return (
    <div className={`ap-room-panel ap-room-${tone} ${isActive ? 'is-active' : ''}`}>
      {/* Header tab */}
      <button type="button" className="ap-room-tab" onClick={onSelect}>
        <span className="ap-room-roman">{room.classId.toUpperCase()}</span>
        <span className="ap-room-label">{label}</span>
        <span className={`ap-room-status-badge ap-status-${room.status}`}>{room.status.toUpperCase()}</span>
      </button>

      {isActive && (
        <div className="ap-room-body">
          {/* Room code management */}
          <section className="ap-section">
            <h3 className="ap-section-title">ROOM CODE</h3>
            <div className="ap-code-row">
              <input
                className="ap-code-input"
                value={customCode}
                onChange={(e) => setCustomCode(e.target.value.toUpperCase())}
                maxLength={16}
                spellCheck={false}
              />
              <button
                type="button"
                className="ap-btn ap-btn-secondary"
                onClick={() => {
                  socket.emit('admin:setCode', { classId: room.classId, code: customCode })
                  flash('Code updated.')
                }}
              >SET CODE</button>
            </div>
            <div className="ap-btn-row">
              <button
                type="button"
                className="ap-btn ap-btn-primary"
                disabled={room.status === 'open' || room.status === 'active'}
                onClick={() => { emit('admin:openRoom'); flash('Room opened.') }}
              >OPEN ROOM</button>
              <button
                type="button"
                className="ap-btn ap-btn-warn"
                onClick={() => { if (confirm(`Reset ${label}? All scores will be cleared.`)) { emit('admin:resetRoom'); flash('Room reset.') } }}
              >RESET ROOM</button>
            </div>
          </section>

          {/* Quiz controls */}
          <section className="ap-section">
            <h3 className="ap-section-title">QUIZ CONTROL</h3>
            <div className="ap-status-row">
              <span className="ap-label">STATUS</span>
              <strong className={`ap-value ap-status-${room.status}`}>{room.status.toUpperCase()}</strong>
              <span className="ap-label">QUESTION</span>
              <strong className="ap-value">#{room.questionNumber}</strong>
            </div>
            <div className="ap-btn-row">
              <button
                type="button"
                className="ap-btn ap-btn-primary"
                disabled={room.status !== 'open'}
                onClick={() => { emit('admin:startQuiz'); flash('Quiz started.') }}
              >▶ START QUIZ</button>
              <button
                type="button"
                className="ap-btn ap-btn-secondary"
                disabled={room.status !== 'active'}
                onClick={() => { emit('admin:nextQuestion'); flash('Next question.') }}
              >NEXT QUESTION →</button>
              <button
                type="button"
                className="ap-btn ap-btn-secondary"
                disabled={room.status !== 'active'}
                onClick={() => { emit('admin:resetQuestion'); flash('Question reset.') }}
              >RESET QUESTION</button>
              <button
                type="button"
                className="ap-btn ap-btn-danger"
                disabled={room.status === 'ended' || room.status === 'waiting'}
                onClick={() => { if (confirm(`End quiz for ${label}?`)) { emit('admin:endQuiz'); flash('Quiz ended.') } }}
              >■ END QUIZ</button>
            </div>
          </section>

          {/* Buzzer controls */}
          <section className="ap-section">
            <h3 className="ap-section-title">BUZZER</h3>
            <div className="ap-buzzer-status">
              <span className="ap-label">STATE</span>
              <strong className={`ap-buzzer-state ap-bstate-${room.buzzerState}`}>
                {buzzerStateLabel[room.buzzerState] ?? room.buzzerState.toUpperCase()}
              </strong>
            </div>

            {room.buzzerWinner && (
              <div className="ap-winner-banner">
                <span className="ap-label">WINNER</span>
                <strong>{room.buzzerWinner}</strong>
                {room.answerDeadline && (
                  <span className={`ap-countdown ${countdown <= 5 ? 'ap-countdown-urgent' : ''}`}>
                    {countdown}s
                  </span>
                )}
              </div>
            )}

            <div className="ap-btn-row">
              <button
                type="button"
                className="ap-btn ap-btn-green"
                disabled={room.status !== 'active' || room.buzzerState === 'open'}
                onClick={() => { emit('admin:activateBuzzer'); flash('Buzzer activated!') }}
              >⚡ ACTIVATE BUZZER</button>
              <button
                type="button"
                className="ap-btn ap-btn-warn"
                disabled={room.buzzerState === 'off' || room.buzzerState === 'expired'}
                onClick={() => { emit('admin:disableBuzzer'); flash('Buzzer disabled.') }}
              >✕ DISABLE BUZZER</button>
              <button
                type="button"
                className="ap-btn ap-btn-secondary"
                disabled={room.status !== 'active'}
                onClick={() => { emit('admin:reEnableBuzzer'); flash('Buzzer re-enabled!') }}
              >↺ RE-ENABLE BUZZER</button>
            </div>
          </section>

          {/* Answer scoring */}
          <section className="ap-section">
            <h3 className="ap-section-title">ANSWER SCORING</h3>
            <div className="ap-score-controls">
              <div className="ap-score-field">
                <label className="ap-label">AWARD PTS</label>
                <div className="ap-score-input-row">
                  <input
                    type="number"
                    min={0}
                    value={pointsValue}
                    onChange={(e) => setPointsValue(Number(e.target.value))}
                    className="ap-num-input"
                  />
                  <button
                    type="button"
                    className="ap-btn ap-btn-green"
                    disabled={!room.buzzerWinner}
                    onClick={() => {
                      socket.emit('admin:markCorrect', { classId: room.classId, points: pointsValue })
                      flash(`+${pointsValue} pts awarded.`)
                    }}
                  >✓ CORRECT</button>
                </div>
              </div>
              <div className="ap-score-field">
                <label className="ap-label">DEDUCT PTS</label>
                <div className="ap-score-input-row">
                  <input
                    type="number"
                    min={0}
                    value={deductValue}
                    onChange={(e) => setDeductValue(Number(e.target.value))}
                    className="ap-num-input"
                  />
                  <button
                    type="button"
                    className="ap-btn ap-btn-danger"
                    disabled={!room.buzzerWinner}
                    onClick={() => {
                      socket.emit('admin:markIncorrect', { classId: room.classId, deduct: deductValue })
                      flash(`Incorrect. −${deductValue} pts.`)
                    }}
                  >✗ INCORRECT</button>
                </div>
              </div>
            </div>

            {/* Manual score adjustment */}
            <div className="ap-adjust-row">
              <select
                className="ap-select"
                value={adjustGroup}
                onChange={(e) => setAdjustGroup(e.target.value)}
              >
                {room.scores.map((s) => (
                  <option key={s.groupName} value={s.groupName}>{s.groupName}</option>
                ))}
              </select>
              <input
                type="number"
                value={adjustDelta}
                onChange={(e) => setAdjustDelta(Number(e.target.value))}
                className="ap-num-input"
                placeholder="±pts"
              />
              <button
                type="button"
                className="ap-btn ap-btn-secondary"
                onClick={() => {
                  socket.emit('admin:adjustScore', { classId: room.classId, groupName: adjustGroup, delta: adjustDelta })
                  flash(`Score adjusted: ${adjustDelta > 0 ? '+' : ''}${adjustDelta} for ${adjustGroup}.`)
                }}
              >ADJUST</button>
            </div>
          </section>

          {/* Scoreboard */}
          <section className="ap-section">
            <h3 className="ap-section-title">SCOREBOARD — {room.connectedCount} CONNECTED</h3>
            <div className="ap-scoreboard">
              <div className="ap-score-head">
                <span>TEAM</span><span>SCORE</span><span>BUZZES</span>
              </div>
              {room.scores.map((s, i) => (
                <div key={s.groupName} className={`ap-score-row ${i === 0 ? 'ap-score-top' : ''}`}>
                  <span>{i + 1}. {s.groupName}</span>
                  <strong>{s.score}</strong>
                  <span>{s.buzzCount}</span>
                </div>
              ))}
            </div>
          </section>

          {actionMsg && <div className="ap-action-msg" role="status">{actionMsg}</div>}
        </div>
      )}
    </div>
  )
}

// ─── Main admin panel ─────────────────────────────────────────────────────────
export default function AdminQuizPage() {
  const router = useRouter()
  const [rooms, setRooms] = useState<RoomSnapshot[]>([])
  const [activeClass, setActiveClass] = useState<ClassId>('ix')
  const [connected, setConnected] = useState(false)
  const [authChecked, setAuthChecked] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)

  // Auth check on mount
  useEffect(() => {
    fetch('/api/admin/me')
      .then((r) => { if (!r.ok) router.replace('/admin/login'); else setAuthChecked(true) })
      .catch(() => router.replace('/admin/login'))
  }, [router])

  // Socket connection
  useEffect(() => {
    if (!authChecked) return
    const socket = getSocket()

    function onConnect() {
      console.log('[Admin] Socket connected')
      setConnected(true)
      socket.emit('admin:join', (res: { ok: boolean; states?: RoomSnapshot[] }) => {
        console.log('[Admin] admin:join response:', res)
        if (res.ok && res.states) {
          setRooms(res.states)
        } else {
          console.error('[Admin] admin:join failed:', res)
        }
      })
    }

    function onDisconnect() {
      console.log('[Admin] Socket disconnected')
      setConnected(false)
    }

    function onRoomState(snap: RoomSnapshot) {
      console.log('[Admin] Room state update:', snap.classId, snap.status)
      setRooms((prev) => {
        const next = prev.filter((r) => r.classId !== snap.classId)
        return [...next, snap].sort((a, b) => {
          const order: ClassId[] = ['ix', 'x', 'xi']
          return order.indexOf(a.classId) - order.indexOf(b.classId)
        })
      })
    }

    function onConnectError(err: Error) {
      console.error('[Admin] Socket connect error:', err)
      setConnectionError(`Connection failed: ${err.message}. Please refresh the page.`)
    }

    socket.on('connect', onConnect)
    socket.on('disconnect', onDisconnect)
    socket.on('room:state', onRoomState)
    socket.on('connect_error', onConnectError)
    
    // If already connected, trigger immediately
    if (socket.connected) {
      console.log('[Admin] Socket already connected')
      onConnect()
    }

    // Timeout fallback - if no rooms after 5 seconds, show error
    const timeout = setTimeout(() => {
      if (rooms.length === 0) {
        setConnectionError('Connection timeout. The server may not be running. Please check if the server is started and refresh the page.')
      }
    }, 5000)

    return () => {
      clearTimeout(timeout)
      socket.off('connect', onConnect)
      socket.off('disconnect', onDisconnect)
      socket.off('room:state', onRoomState)
      socket.off('connect_error', onConnectError)
    }
  }, [authChecked])

  async function handleLogout() {
    await fetch('/api/admin/logout', { method: 'POST' })
    router.replace('/admin/login')
  }

  if (!authChecked) {
    return (
      <main className="ap-loading">
        <p className="ap-loading-text">VERIFYING SESSION…</p>
      </main>
    )
  }

  const activeRoom = rooms.find((r) => r.classId === activeClass)

  return (
    <main className="ap-root">
      {/* Header */}
      <header className="ap-header">
        <Link href="/" className="ap-wordmark"><span className="mark">[ ]</span> TECH EVENT</Link>
        <span className="ap-header-title">ADMIN QUIZ PANEL</span>
        <div className="ap-header-right">
          <span className={`ap-conn-dot ${connected ? 'conn-ok' : 'conn-off'}`} />
          <span className="ap-conn-label">{connected ? 'LIVE' : 'CONNECTING…'}</span>
          <button type="button" className="ap-btn ap-btn-secondary ap-logout" onClick={handleLogout}>
            LOGOUT
          </button>
        </div>
      </header>

      <div className="ap-body">
        {/* Class selector sidebar */}
        <nav className="ap-sidebar" aria-label="Class selector">
          {(['ix', 'x', 'xi'] as ClassId[]).map((cid) => {
            const room = rooms.find((r) => r.classId === cid)
            const tone = CLASS_TONES[cid]
            return (
              <button
                key={cid}
                type="button"
                className={`ap-sidebar-btn ap-sidebar-${tone} ${activeClass === cid ? 'is-active' : ''}`}
                onClick={() => setActiveClass(cid)}
              >
                <span className="ap-sb-roman">{cid.toUpperCase()}</span>
                <span className="ap-sb-label">{CLASS_LABELS[cid]}</span>
                {room && (
                  <span className={`ap-sb-status ap-status-${room.status}`}>
                    {room.status.toUpperCase()}
                  </span>
                )}
              </button>
            )
          })}
        </nav>

        {/* Active room panel */}
        <div className="ap-main">
          {connectionError ? (
            <div className="ap-empty">
              <p className="ap-error-text">{connectionError}</p>
              <button
                type="button"
                className="ap-btn ap-btn-primary"
                onClick={() => window.location.reload()}
                style={{ marginTop: '16px' }}
              >
                REFRESH PAGE
              </button>
            </div>
          ) : rooms.length === 0 ? (
            <div className="ap-empty">
              <p className="ap-loading-text">CONNECTING TO SERVER…</p>
            </div>
          ) : activeRoom ? (
            <RoomPanel
              key={activeRoom.classId}
              room={activeRoom}
              isActive={true}
              onSelect={() => {}}
            />
          ) : null}
        </div>
      </div>
    </main>
  )
}
