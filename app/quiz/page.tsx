'use client'

import { useEffect, useState, useCallback, useRef, type FormEvent } from 'react'
import Link from 'next/link'
import { connectFastApiQuiz, type FastApiQuizEvent } from '@/lib/fastapi-realtime'
import type { RoomSnapshot } from '@/types'

type ClassId = 'ix' | 'x' | 'xi'
type JoinStep = 'select-class' | 'enter-code' | 'select-group' | 'in-room'
type BackendClass = { code: string; display_name: string; preferred_language: string }
type BackendTeam = { id: string; name: string; slogan?: string | null }
type BackendSession = { id: string; class_code: string; status: string; question_count?: number }
type BackendTeamJoin = { id: string; access_token: string }

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
  onBuzz,
  onAnswer,
}: {
  room: RoomSnapshot
  myGroup: string
  onLeave: () => void
  onBuzz: () => Promise<void>
  onAnswer: (answer: string) => Promise<{ is_correct: boolean | null; awarded_points: number }>
}) {
  const countdown = useCountdown(room.answerDeadline)
  const iWon = room.buzzerWinner === myGroup
  const [buzzerMsg, setBuzzerMsg] = useState('')
  const [answerText, setAnswerText] = useState('')
  const [answerSubmitted, setAnswerSubmitted] = useState(false)
  const [answerFeedback, setAnswerFeedback] = useState('')
  const msgRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  function flash(msg: string) {
    setBuzzerMsg(msg)
    if (msgRef.current) clearTimeout(msgRef.current)
    msgRef.current = setTimeout(() => setBuzzerMsg(''), 3000)
  }

  async function handleBuzz() {
    try {
      await onBuzz()
    } catch (error) {
      flash(error instanceof Error ? error.message : 'Could not buzz.')
    }
  }

  useEffect(() => {
    setAnswerText('')
    setAnswerSubmitted(false)
    setAnswerFeedback('')
  }, [room.questionNumber])

  async function handleAnswer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!answerText.trim() || answerSubmitted) return
    try {
      const result = await onAnswer(answerText.trim())
      setAnswerSubmitted(true)
      const feedback = result.is_correct === null ? 'Submitted for manual review.' : result.is_correct ? `Correct — +${result.awarded_points} points.` : `Incorrect — ${result.awarded_points} points.`
      setAnswerFeedback(feedback)
      flash(feedback)
    } catch (error) {
      flash(error instanceof Error ? error.message : 'Could not submit answer.')
    }
  }

  const meta = CLASS_META[room.classId]

  const statusMessages: Record<string, string> = {
    waiting: 'Waiting for admin to open the room.',
    open: 'Room is open. Quiz starting soon.',
    active: room.questionType !== 'RIDDLE'
      ? `Question #${room.questionNumber} — answer now.`
      : room.buzzerState === 'off'
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

        {room.status === 'active' && room.questionText && (
          <section className="sp-question-card" aria-live="polite">
            <p className="sp-step-label">QUESTION {room.questionNumber}</p>
            <h1>{room.questionText}</h1>
            {room.questionCodeSnippet && <pre className="sp-question-code"><code>{room.questionCodeSnippet}</code></pre>}
          </section>
        )}

        {/* Buzzer area */}
        {room.status === 'active' && room.questionType === 'RIDDLE' && (
          <div className="sp-buzzer-area">
            <BuzzerButton
              buzzerState={room.buzzerState}
              buzzerWinner={room.buzzerWinner}
              myGroup={myGroup}
              onPress={handleBuzz}
              disabled={room.buzzerState !== 'open' || answerSubmitted}
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
                    {!answerSubmitted && countdown > 0 && (
                      <form onSubmit={handleAnswer} style={{ marginTop: 16 }}>
                        <label htmlFor="quiz-answer" className="sp-winner-label">YOUR ANSWER</label>
                        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                          <input id="quiz-answer" value={answerText} onChange={(event) => setAnswerText(event.target.value)} autoComplete="off" />
                          <button type="submit" className="sp-join-btn">SUBMIT</button>
                        </div>
                      </form>
                    )}
                    {answerSubmitted && <p className="sp-winner-label">{answerFeedback}</p>}
                    {room.answerDeadline && countdown === 0 && !answerSubmitted && (
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

        {room.status === 'active' && room.questionType !== 'RIDDLE' && (
          <div className="sp-buzzer-area">
            {room.answerDeadline && <p className="sp-winner-label">{countdown} SECONDS REMAINING</p>}
            {!answerSubmitted ? <form onSubmit={handleAnswer} style={{ marginTop: 12 }}>
              {room.questionType === 'MCQ' && room.questionOptions.length > 0 ? <select id="quiz-answer" value={answerText} onChange={(event) => setAnswerText(event.target.value)} required aria-label="Choose your answer">
                <option value="">SELECT AN ANSWER</option>{room.questionOptions.map((option) => <option key={option.key} value={option.key}>{option.key}. {option.text}</option>)}
              </select> : <input id="quiz-answer" value={answerText} onChange={(event) => setAnswerText(event.target.value)} autoComplete="off" required aria-label="Your answer" />}
              <button type="submit" className="sp-join-btn" disabled={Boolean(room.answerDeadline && countdown === 0)}>SUBMIT ANSWER</button>
            </form> : <p className="sp-winner-label">{answerFeedback}</p>}
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
  const [backendClasses, setBackendClasses] = useState<BackendClass[]>([])
  const [backendGroups, setBackendGroups] = useState<BackendTeam[]>([])
  const [backendSessionId, setBackendSessionId] = useState<string | null>(null)
  const [backendTeamToken, setBackendTeamToken] = useState<string | null>(null)
  const [backendParticipantId, setBackendParticipantId] = useState<string | null>(null)
  const [backendQuestionId, setBackendQuestionId] = useState<string | null>(null)
  const [fastApiConnected, setFastApiConnected] = useState(false)
  const [configurationLoading, setConfigurationLoading] = useState(true)
  const [configurationError, setConfigurationError] = useState('')
  const [teamsLoading, setTeamsLoading] = useState(false)
  const [teamsError, setTeamsError] = useState('')

  useEffect(() => {
    let cancelled = false
    setConfigurationLoading(true)
    setConfigurationError('')
    fetch('/api/v1/classes')
      .then(async (response) => {
        if (!response.ok) throw new Error('The event configuration could not be loaded.')
        return response.json() as Promise<BackendClass[]>
      })
      .then((items) => {
        if (cancelled) return
        if (items.length === 0) throw new Error('No quiz classes are configured for this event.')
        setBackendClasses(items)
        setConfigurationLoading(false)
      })
      .catch(() => {
        if (cancelled) return
        setBackendClasses([])
        setConfigurationLoading(false)
        setConfigurationError('The quiz service is unavailable. Please refresh and try again.')
      })
    return () => { cancelled = true }
  }, [])

  const availableClasses = backendClasses
    .map((item) => item.code.toLowerCase())
    .filter((code): code is ClassId => code === 'ix' || code === 'x' || code === 'xi')
  const isConnected = fastApiConnected

  useEffect(() => {
    if (!selectedClass) {
      setBackendGroups([])
      setTeamsLoading(false)
      setTeamsError('')
      return
    }
    let cancelled = false
    setTeamsLoading(true)
    setTeamsError('')
    fetch(`/api/v1/teams?class_code=${selectedClass.toUpperCase()}`)
      .then(async (response) => {
        if (!response.ok) throw new Error('The teams could not be loaded.')
        return response.json() as Promise<BackendTeam[]>
      })
      .then((items) => {
        if (cancelled) return
        setBackendGroups(items)
        setTeamsLoading(false)
        if (items.length === 0) setTeamsError('No teams are configured for this class.')
      })
      .catch(() => {
        if (cancelled) return
        setBackendGroups([])
        setTeamsLoading(false)
        setTeamsError('The teams could not be loaded. Please try again.')
      })
    return () => { cancelled = true }
  }, [selectedClass])

  const classGroups = selectedClass
    ? backendGroups.map((team) => team.name)
    : []

  useEffect(() => {
    if (step !== 'in-room' || !backendSessionId || !backendTeamToken || !selectedClass) return
    const socket = connectFastApiQuiz(backendSessionId, backendTeamToken, (event: FastApiQuizEvent) => {
      const payload = event.payload ?? {}
      if (event.type === 'quiz.state.snapshot' || event.type === 'quiz.state.changed') {
        const status = (payload.status ?? 'WAITING').toLowerCase() as RoomSnapshot['status']
        const currentQuestionId = payload.currentQuestionId ?? null
        setBackendQuestionId(currentQuestionId)
        setRoom((previous) => ({
          classId: selectedClass,
          code: roomCode.trim().toUpperCase(),
          status,
          questionNumber: payload.currentQuestionOrder ?? previous?.questionNumber ?? 0,
          questionCount: payload.questionCount ?? previous?.questionCount ?? 0,
          questionText: payload.question?.prompt ?? previous?.questionText ?? null,
          questionType: payload.question?.questionType ?? previous?.questionType ?? null,
          questionOptions: payload.question?.options ?? previous?.questionOptions ?? [],
          questionCodeSnippet: payload.question?.codeSnippet ?? previous?.questionCodeSnippet ?? null,
          buzzerState: (payload.buzzerState ?? (status === 'active' ? 'open' : 'off')) as RoomSnapshot['buzzerState'],
          buzzerWinner: payload.buzzerWinner ?? null,
          answerDeadline: payload.answerDeadline ? Date.parse(payload.answerDeadline) : null,
          scores: payload.scores?.map((score) => ({ ...score, buzzCount: 0 })) ?? previous?.scores ?? [],
          connectedCount: previous?.connectedCount ?? 0,
        }))
      } else if (event.type === 'quiz.buzzer.accepted') {
        setRoom((previous) => previous ? {
          ...previous,
          buzzerState: 'locked',
          buzzerWinner: payload.teamName ?? (payload.participantId === undefined ? 'ANOTHER TEAM' : myGroup),
          answerDeadline: payload.answerDeadline ? Date.parse(payload.answerDeadline) : null,
        } : previous)
      } else if (event.type === 'quiz.answer.submitted' && payload.buzzerOpen) {
        setRoom((previous) => previous ? { ...previous, buzzerState: 'open', buzzerWinner: null, answerDeadline: null } : previous)
      } else if (event.type === 'quiz.answer.submitted' && payload.questionClosed) {
        setRoom((previous) => previous ? { ...previous, buzzerState: 'off', buzzerWinner: null, answerDeadline: null } : previous)
      } else if (event.type === 'quiz.answer.judged') {
        void fetch(`/api/v1/quiz-sessions/${backendSessionId}/leaderboard`, { cache: 'no-store' })
          .then((response) => response.ok ? response.json() as Promise<Array<{ team_name: string; points: number }>> : [])
          .then((entries) => setRoom((previous) => previous ? {
            ...previous,
            scores: entries.map((entry) => ({ groupName: entry.team_name, score: entry.points, buzzCount: 0 })),
          } : previous))
          .catch(() => undefined)
      }
    }, (state) => setFastApiConnected(state === 'connected'))
    return () => {
      socket.close()
      setFastApiConnected(false)
    }
  }, [backendSessionId, backendTeamToken, myGroup, roomCode, selectedClass, step])

  const handleJoin = useCallback(async () => {
    if (!selectedClass || !roomCode || !selectedGroup) return
    setJoinError('')
    setJoining(true)
    const normalizedCode = roomCode.trim().toUpperCase()
    const selectedBackendTeam = backendGroups.find((team) => team.name === selectedGroup)
    try {
      const sessionResponse = await fetch(`/api/v1/quiz-sessions/by-code/${encodeURIComponent(normalizedCode)}`)
      if (!sessionResponse.ok) {
        const errorBody = await sessionResponse.json().catch(() => ({})) as { detail?: string; error?: { message?: string } }
        throw new Error(errorBody.detail ?? errorBody.error?.message ?? 'That quiz room could not be found.')
      }
      const backendSession = await sessionResponse.json() as BackendSession
      if (backendSession.class_code.toLowerCase() !== selectedClass) {
        throw new Error(`This room is configured for Class ${backendSession.class_code}.`)
      }
      if (!selectedBackendTeam) {
        throw new Error('This team is not available in the database-backed event edition.')
      }
      const participantResponse = await fetch('/api/v1/auth/team/join', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': `team-join-${normalizedCode}-${selectedBackendTeam.id}`,
        },
        body: JSON.stringify({ quiz_code: normalizedCode, team_id: selectedBackendTeam.id }),
      })
      if (!participantResponse.ok) {
        const errorBody = await participantResponse.json().catch(() => ({})) as { detail?: string; error?: { message?: string } }
        throw new Error(errorBody.detail ?? errorBody.error?.message ?? 'Could not register the team for this quiz.')
      }
      const joinData = await participantResponse.json() as BackendTeamJoin
      setBackendSessionId(backendSession.id)
      setBackendTeamToken(joinData.access_token)
      setBackendParticipantId(joinData.id)
      setBackendQuestionId(null)
      setMyGroup(selectedGroup)
      setRoom({
        classId: selectedClass,
        code: normalizedCode,
        status: backendSession.status.toLowerCase() as RoomSnapshot['status'],
        questionNumber: 0,
        questionCount: backendSession.question_count ?? 0,
        questionText: null,
        questionType: null,
        questionOptions: [],
        questionCodeSnippet: null,
        buzzerState: 'off',
        buzzerWinner: null,
        answerDeadline: null,
        scores: [],
        connectedCount: 0,
      })
      setJoining(false)
      setStep('in-room')
    } catch (cause) {
      setJoining(false)
      setJoinError(cause instanceof Error ? cause.message : 'The durable quiz service is unavailable. Please try again shortly.')
    }
  }, [backendGroups, selectedClass, roomCode, selectedGroup])

  const handleFastApiBuzz = useCallback(async () => {
    if (!backendSessionId || !backendTeamToken || !backendQuestionId) {
      throw new Error('Waiting for the active question.')
    }
    const response = await fetch(`/api/v1/quiz-sessions/${backendSessionId}/questions/${backendQuestionId}/buzzer`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${backendTeamToken}` },
    })
    if (!response.ok) {
      const body = await response.json().catch(() => ({})) as { detail?: string; error?: { message?: string } }
      throw new Error(body.detail ?? body.error?.message ?? 'Could not buzz.')
    }
  }, [backendQuestionId, backendSessionId, backendTeamToken])

  const handleFastApiAnswer = useCallback(async (answer: string): Promise<{ is_correct: boolean | null; awarded_points: number }> => {
    if (!backendSessionId || !backendTeamToken || !backendQuestionId || !backendParticipantId) {
      throw new Error('Waiting for the active question.')
    }
    const response = await fetch(`/api/v1/quiz-sessions/${backendSessionId}/answers`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${backendTeamToken}`,
        'Idempotency-Key': `answer-${backendSessionId}-${backendQuestionId}-${backendParticipantId}`,
      },
      body: JSON.stringify({ participant_id: backendParticipantId, quiz_question_id: backendQuestionId, submitted_answer: answer }),
    })
    if (!response.ok) {
      const body = await response.json().catch(() => ({})) as { detail?: string; error?: { message?: string } }
      throw new Error(body.detail ?? body.error?.message ?? 'Could not submit answer.')
    }
    return await response.json() as { is_correct: boolean | null; awarded_points: number }
  }, [backendParticipantId, backendQuestionId, backendSessionId, backendTeamToken])

  function handleLeave() {
    setStep('select-class')
    setSelectedClass(null)
    setRoomCode('')
    setSelectedGroup('')
    setRoom(null)
    setMyGroup('')
    setBackendSessionId(null)
    setBackendTeamToken(null)
    setBackendParticipantId(null)
    setBackendQuestionId(null)
    setFastApiConnected(false)
    setJoinError('')
  }

  // ── In room ────────────────────────────────────────────────────────────────
  if (step === 'in-room' && room) {
    return <QuizRoom room={room} myGroup={myGroup} onLeave={handleLeave} onBuzz={handleFastApiBuzz} onAnswer={handleFastApiAnswer} />
  }

  // ── Join flow ──────────────────────────────────────────────────────────────
  return (
    <main className="sp-join-root">
      <header className="sp-join-header">
        <Link href="/" className="sp-wordmark"><span className="mark">[ ]</span> TECH EVENT</Link>
        <span className="sp-join-title">JOIN QUIZ</span>
        <span className={`sp-conn-dot ${isConnected ? 'conn-ok' : 'conn-off'}`} title={isConnected ? 'Connected' : 'Connecting…'} />
      </header>

      <div className="sp-join-card">
        {configurationLoading && <p className="sp-conn-warn">Loading event configuration…</p>}
        {configurationError && <p className="sp-join-error" role="alert">{configurationError}</p>}
        {/* Step 1: Select class */}
        {!configurationLoading && !configurationError && <div className="sp-step">
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
        </div>}

        {/* Step 2: Room code */}
        {!configurationLoading && !configurationError && selectedClass && (
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
        {!configurationLoading && !configurationError && selectedClass && roomCode.length >= 2 && (
          <div className="sp-step">
            <p className="sp-step-label">STEP 3 — SELECT YOUR GROUP</p>
            {teamsLoading && <p className="sp-conn-warn">Loading teams…</p>}
            {teamsError && <p className="sp-join-error" role="alert">{teamsError}</p>}
            {!teamsLoading && !teamsError && <div className="sp-group-grid">
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
            </div>}
          </div>
        )}

        {/* Error */}
        {joinError && <p className="sp-join-error" role="alert">{joinError}</p>}

        {/* Join button */}
        {!configurationLoading && !configurationError && selectedClass && roomCode && selectedGroup && (
          <button
            type="button"
            className="sp-join-btn"
            onClick={handleJoin}
            disabled={joining}
          >
            {joining ? 'JOINING…' : `JOIN ROOM →`}
          </button>
        )}

        {step === 'in-room' && !isConnected && <p className="sp-conn-warn">Connecting to server… please wait.</p>}
      </div>

      <p className="sp-join-foot">
        <Link href="/">← Back to event site</Link>
      </p>
    </main>
  )
}
