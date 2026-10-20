'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

type Blueprint = { id: string; name: string; question_count: number; class_track_id: string; distributions: Array<{ question_type: string; quantity: number }> }
type QuizSession = { id: string; blueprint_id: string; quiz_code: string; status: string; question_count: number }
type AdminAnswer = { id: string; quiz_question_id: string; question_order: number; team_name: string; submitted_answer: string; is_correct: boolean | null; awarded_points: number; submitted_at: string }
type ClassTrack = { id: string; code: string; display_name: string }
type Team = { id: string; name: string; slogan: string | null; team_type: string; members: { display_name: string }[] }
type Standing = { team_id: string; team_name: string; class_code: string; score: number | null; completed_rounds: number; is_provisional: boolean }
type ApiError = { error?: { message?: string }; detail?: string }
type AdminTab = 'quizzes' | 'teams' | 'rankings'

const actions: Record<string, string[]> = {
  WAITING: ['open', 'end'],
  OPEN: ['start', 'end'],
  ACTIVE: ['pause', 'advance', 'end'],
  PAUSED: ['resume', 'end'],
  ENDED: [],
}

async function readError(response: Response): Promise<string> {
  const body = await response.json().catch(() => ({})) as ApiError
  return body.error?.message ?? body.detail ?? 'The request failed.'
}

export default function DurableQuizAdminPage() {
  const router = useRouter()
  const [sessions, setSessions] = useState<QuizSession[]>([])
  const [standardClassId, setStandardClassId] = useState('')
  const [createdQuiz, setCreatedQuiz] = useState<QuizSession | null>(null)
  const [showAllSessions, setShowAllSessions] = useState(false)
  const [copiedCode, setCopiedCode] = useState(false)
  const [selectedSession, setSelectedSession] = useState<string | null>(null)
  const [answers, setAnswers] = useState<AdminAnswer[]>([])
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [tab, setTab] = useState<AdminTab>('quizzes')
  const [classes, setClasses] = useState<ClassTrack[]>([])
  const [classCode, setClassCode] = useState('')
  const [teams, setTeams] = useState<Team[]>([])
  const [standings, setStandings] = useState<Standing[]>([])
  const [loadingMore, setLoadingMore] = useState(false)
  const [hasMoreSessions, setHasMoreSessions] = useState(true)

  const load = useCallback(async () => {
    const auth = await fetch('/api/v1/auth/me')
    const authData = await auth.json().catch(() => ({})) as { authenticated?: boolean }
    if (!auth.ok || !authData.authenticated) {
      router.replace('/admin/login?next=/admin/durable-quiz')
      return
    }
    const [sessionResponse] = await Promise.all([
      fetch('/api/v1/admin/quiz-sessions?limit=25&offset=0', { cache: 'no-store' }),
    ])
    if (!sessionResponse.ok) {
      setError('Could not load database-backed quiz configuration.')
      return
    }
    const recentSessions = await sessionResponse.json() as QuizSession[]
    setSessions((current) => {
      const recentIds = new Set(recentSessions.map((item) => item.id))
      return [...recentSessions, ...current.filter((item) => !recentIds.has(item.id))]
    })
    setHasMoreSessions(recentSessions.length === 25)
    const classResponse = await fetch('/api/v1/classes', { cache: 'no-store' })
    if (classResponse.ok) setClasses(await classResponse.json() as ClassTrack[])
  }, [router])

  async function loadMoreSessions() {
    if (loadingMore || !hasMoreSessions) return
    setLoadingMore(true)
    try {
      const response = await fetch(`/api/v1/admin/quiz-sessions?limit=25&offset=${sessions.length}`, { cache: 'no-store' })
      if (!response.ok) throw new Error(await readError(response))
      const nextPage = await response.json() as QuizSession[]
      setSessions((current) => [...current, ...nextPage.filter((item) => !current.some((loaded) => loaded.id === item.id))])
      setHasMoreSessions(nextPage.length === 25)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load more quizzes.')
    } finally {
      setLoadingMore(false)
    }
  }

  useEffect(() => {
    void load()
    const interval = window.setInterval(() => void load(), 2000)
    return () => window.clearInterval(interval)
  }, [load])

  const loadAnswers = useCallback(async (sessionId: string) => {
    const response = await fetch(`/api/v1/admin/quiz-sessions/${sessionId}/answers`, { cache: 'no-store' })
    if (!response.ok) return
    setAnswers(await response.json() as AdminAnswer[])
  }, [])

  useEffect(() => {
    if (selectedSession) void loadAnswers(selectedSession)
    else setAnswers([])
  }, [loadAnswers, selectedSession])

  useEffect(() => {
    if (tab !== 'teams') return
    const query = classCode ? `?class_code=${encodeURIComponent(classCode)}` : ''
    void fetch(`/api/v1/admin/teams${query}`, { cache: 'no-store' }).then(async (response) => {
      if (response.ok) setTeams(await response.json() as Team[])
    })
  }, [classCode, tab])

  useEffect(() => {
    if (tab !== 'rankings') return
    void fetch('/api/v1/leaderboard', { cache: 'no-store' }).then(async (response) => {
      if (response.ok) setStandings(await response.json() as Standing[])
    })
  }, [tab])

  async function createStandardQuiz() {
    if (!standardClassId || busy) return
    setBusy(true)
    setError('')
    setMessage('')
    setCreatedQuiz(null)
    try {
      const blueprintResponse = await fetch(`/api/v1/admin/quiz-blueprints/standard?class_track_id=${encodeURIComponent(standardClassId)}`, { method: 'POST' })
      if (blueprintResponse.status === 404) {
        throw new Error('The quiz API running on localhost is outdated. Restart the backend with the latest code and apply migration 0010 before creating a standard quiz.')
      }
      if (!blueprintResponse.ok) throw new Error(await readError(blueprintResponse))
      const blueprint = await blueprintResponse.json() as Blueprint
      const distributionTotal = blueprint.distributions.reduce((total, item) => total + item.quantity, 0)
      if (blueprint.question_count !== 30 || distributionTotal !== 30) {
        throw new Error(`Blueprint mismatch: expected 30 questions, received ${blueprint.question_count} across ${distributionTotal} category slots. No quiz was created.`)
      }
      const response = await fetch('/api/v1/admin/quiz-sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ blueprint_id: blueprint.id }),
      })
      if (!response.ok) throw new Error(await readError(response))
      const created = await response.json() as QuizSession
      if (created.question_count !== 30) {
        throw new Error(`The server returned a ${created.question_count}-question session instead of 30. Do not share its code; this needs an API/database update.`)
      }
      setCreatedQuiz(created)
      setSelectedSession(created.id)
      setShowAllSessions(false)
      setMessage(`30-question quiz ${created.quiz_code} is ready for teams to join.`)
      await load()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not create the quiz session.')
    } finally {
      setBusy(false)
    }
  }

  async function copyJoinCode() {
    if (!createdQuiz) return
    await navigator.clipboard.writeText(createdQuiz.quiz_code)
    setCopiedCode(true)
    window.setTimeout(() => setCopiedCode(false), 1800)
  }

  const visibleSessions = showAllSessions ? sessions : sessions.slice(0, 5)

  async function runAction(sessionId: string, action: string) {
    setBusy(true)
    setError('')
    setMessage('')
    try {
      const response = await fetch(`/api/v1/admin/quiz-sessions/${sessionId}/actions/${action}`, {
        method: 'POST',
        headers: { 'Idempotency-Key': `session-action-${sessionId}-${action}` },
      })
      if (!response.ok) throw new Error(await readError(response))
      const result = await response.json() as QuizSession
      setMessage(`${action.toUpperCase()} applied. Session is now ${result.status}.`)
      await load()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The lifecycle action failed.')
    } finally {
      setBusy(false)
    }
  }

  async function judgeAnswer(answer: AdminAnswer, isCorrect: boolean) {
    if (!selectedSession || busy) return
    setBusy(true)
    setError('')
    try {
      const response = await fetch(`/api/v1/admin/quiz-sessions/${selectedSession}/answers/${answer.id}/judge`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': `judge-${answer.id}-${isCorrect ? 'correct' : 'incorrect'}`,
        },
        body: JSON.stringify({ is_correct: isCorrect }),
      })
      if (!response.ok) throw new Error(await readError(response))
      setMessage(`${answer.team_name} · Question ${answer.question_order} judged ${isCorrect ? 'correct' : 'incorrect'}.`)
      await loadAnswers(selectedSession)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not judge the answer.')
    } finally {
      setBusy(false)
    }
  }

  async function logout() {
    await fetch('/api/v1/auth/logout', { method: 'POST' })
    router.replace('/admin/login')
  }

  return (
    <main className="ap-root">
      <header className="ap-header">
        <Link href="/" className="ap-wordmark"><span className="mark">[ ]</span> TECH EVENT</Link>
        <nav className="ap-admin-nav" aria-label="Admin sections">
          <button type="button" className={tab === 'quizzes' ? 'is-current' : ''} onClick={() => setTab('quizzes')}>QUIZ CONTROL</button>
          <button type="button" className={tab === 'teams' ? 'is-current' : ''} onClick={() => setTab('teams')}>TEAMS</button>
          <button type="button" className={tab === 'rankings' ? 'is-current' : ''} onClick={() => setTab('rankings')}>RANKINGS</button>
          <Link href="/admin/questions">QUESTION BANK</Link>
        </nav>
        <button type="button" className="ap-btn ap-btn-secondary ap-logout" onClick={logout}>LOGOUT</button>
      </header>
      <div className="ap-admin-content">
        <div className="ap-admin-intro">
          <div><p className="ap-section-title">EVENT OPERATIONS</p><h1>{tab === 'quizzes' ? 'Quiz control' : tab === 'teams' ? 'Registered teams' : 'Live rankings'}</h1><p>Manage the competition from one place. Changes sync with the event database.</p></div>
          <div className="ap-admin-stats"><span><strong>{sessions.length}</strong> QUIZZES LOADED</span><span><strong>{teams.length || '—'}</strong> TEAMS</span></div>
        </div>
        {tab === 'teams' ? <section className="ap-admin-card">
          <div className="ap-admin-card-head"><div><h2>Teams</h2><p>Teams registered for the active event.</p></div><select aria-label="Filter teams by class" className="ap-select ap-filter-select" value={classCode} onChange={(event) => setClassCode(event.target.value)}><option value="">ALL CLASSES</option>{classes.map((item) => <option key={item.id} value={item.code}>{item.code} · {item.display_name}</option>)}</select></div>
          {teams.length ? <div className="ap-team-grid">{teams.map((team) => <article className="ap-team-card" key={team.id}><div className="ap-team-mark">{team.name.slice(0, 1).toUpperCase()}</div><div><h3>{team.name}</h3><p>{team.slogan || team.team_type}</p><small>{team.members.length} PLAYERS{team.members.length ? ` · ${team.members.map((member) => member.display_name).join(', ')}` : ''}</small></div></article>)}</div> : <p className="ap-empty-state">No teams found for this event and class filter.</p>}
        </section> : tab === 'rankings' ? <section className="ap-admin-card">
          <div className="ap-admin-card-head"><div><h2>Leaderboard</h2><p>Scores update as answers are judged.</p></div><select aria-label="Choose quiz for rankings" className="ap-select ap-filter-select" value={selectedSession ?? ''} onChange={(event) => setSelectedSession(event.target.value || null)}><option value="">SELECT A QUIZ</option>{sessions.map((session) => <option key={session.id} value={session.id}>{session.quiz_code} · {session.status}</option>)}</select></div>
          {standings.length ? <><p className="ap-empty-state">Weighted event standings · Round 0: 5% · Round 1: 10% · Round 2: 15% · Round 3: 30% · Round 4: 40%. Incomplete rounds are excluded until every entered team has a score.</p><div className="ap-ranking-list">{standings.map((entry, index) => <article key={entry.team_id} className={`ap-ranking-row ${index === 0 ? 'is-first' : ''}`}><span className="ap-ranking-place">{String(index + 1).padStart(2, '0')}</span><strong>{entry.team_name}<small style={{ display: 'block' }}>{entry.class_code} · {entry.completed_rounds}/5 rounds {entry.is_provisional ? '· PROVISIONAL' : ''}</small></strong><span>{entry.score === null ? '—' : `${(entry.score * 100).toFixed(2)}%`}</span></article>)}</div></> : <p className="ap-empty-state">No official round scores are available yet. Import the event scorecard to populate standings.</p>}
        </section> : <>
        <section className="ap-admin-card">
          <div className="ap-admin-card-head"><div><h2>Create the standard quiz</h2><p>30 questions: 10 conceptual · 5 riddles · 5 theory · 10 debugging. Only riddles use the buzzer.</p></div></div>
          <div className="ap-code-row">
            <select className="ap-select" aria-label="Class for standard quiz" value={standardClassId} onChange={(event) => setStandardClassId(event.target.value)}>
              <option value="">SELECT CLASS</option>
              {classes.map((item) => <option key={item.id} value={item.id}>{item.code} · {item.display_name}</option>)}
            </select>
            <button type="button" className="ap-btn ap-btn-primary" disabled={!standardClassId || busy} onClick={() => void createStandardQuiz()}>{busy ? 'CHECKING QUESTION BANK…' : 'CREATE 30-QUESTION QUIZ'}</button>
          </div>
          <details style={{ marginTop: 16 }}>
            <summary>How do teams join?</summary>
            <p>After creating the quiz, share its six-character join code. On one device per team, open <Link href="/quiz">the student quiz page</Link>, choose the class, enter the code, select the registered team, then press JOIN ROOM.</p>
          </details>
        </section>
        {error && <p className="ap-error-text" role="alert">{error}</p>}
        {message && <p className="ap-action-msg" role="status">{message}</p>}
        {createdQuiz && <section className="ap-admin-card" aria-live="polite">
          <div className="ap-admin-card-head"><div><h2>Quiz ready · {createdQuiz.question_count} questions</h2><p>Teams can join while the session is waiting or open.</p></div></div>
          <div className="ap-status-row"><strong>JOIN CODE</strong><code style={{ fontSize: '1.4rem', letterSpacing: '.12em' }}>{createdQuiz.quiz_code}</code><button type="button" className="ap-btn ap-btn-secondary" onClick={() => void copyJoinCode()}>{copiedCode ? 'COPIED' : 'COPY CODE'}</button><Link className="ap-btn ap-btn-primary" href="/quiz">OPEN STUDENT JOIN PAGE</Link></div>
          <p style={{ marginTop: 14 }}>Student steps: open <code>{typeof window === 'undefined' ? '' : window.location.origin}/quiz</code> → choose class → enter code → choose team → JOIN ROOM.</p>
        </section>}
        <section className="ap-admin-card">
          <div className="ap-admin-card-head"><div><h2>Recent sessions</h2><p>Showing the latest five; older records and scores are kept in history.</p></div></div>
          {sessions.length === 0 ? <p className="ap-loading-text">NO QUIZ SESSIONS YET.</p> : visibleSessions.map((session) => (
            <article key={session.id} className={`ap-room-panel ap-room-blue ${selectedSession === session.id ? 'is-active' : ''}`} style={{ marginBottom: 16 }}>
              <div className="ap-room-body" style={{ display: 'block' }}>
                <div className="ap-status-row"><strong>{session.quiz_code}</strong><span className={`ap-value ap-status-${session.status.toLowerCase()}`}>{session.status}</span><span>{session.question_count} {session.question_count === 1 ? 'QUESTION' : 'QUESTIONS'}</span></div>
                <div className="ap-btn-row">
                  {actions[session.status]?.map((action) => <button key={action} type="button" className="ap-btn ap-btn-secondary" disabled={busy} onClick={() => void runAction(session.id, action)}>{action.toUpperCase()}</button>)}
                  <button type="button" className="ap-btn ap-btn-primary" onClick={() => setSelectedSession(session.id)}>VIEW SUBMISSIONS</button>
                </div>
              </div>
            </article>
          ))}
          {sessions.length > 5 && <button type="button" className="ap-btn ap-btn-secondary ap-load-more" onClick={() => setShowAllSessions((current) => !current)}>{showAllSessions ? 'SHOW LATEST FIVE' : `SHOW LOADED HISTORY (${sessions.length})`}</button>}
          {hasMoreSessions && <button type="button" className="ap-btn ap-btn-secondary ap-load-more" disabled={loadingMore} onClick={() => void loadMoreSessions()}>{loadingMore ? 'LOADING…' : 'LOAD OLDER QUIZZES'}</button>}
        </section>
        {selectedSession && <section className="ap-section">
          <h2 className="ap-section-title">ANSWER JUDGING QUEUE</h2>
          {answers.length === 0 ? <p className="ap-loading-text">NO SUBMISSIONS FOR THIS SESSION.</p> : answers.map((answer) => (
            <article key={answer.id} className="ap-room-panel ap-room-blue" style={{ marginBottom: 12 }}>
              <div className="ap-room-body" style={{ display: 'block' }}>
                <div className="ap-status-row">
                  <strong>{answer.team_name}</strong>
                  <span>QUESTION {answer.question_order}</span>
                  <span className={`ap-value ${answer.is_correct === null ? 'ap-status-active' : answer.is_correct ? 'ap-status-open' : 'ap-status-ended'}`}>
                    {answer.is_correct === null ? 'PENDING' : answer.is_correct ? `CORRECT · +${answer.awarded_points}` : 'INCORRECT'}
                  </span>
                </div>
                <p style={{ whiteSpace: 'pre-wrap', margin: '12px 0' }}>{answer.submitted_answer}</p>
                {answer.is_correct === null && <div className="ap-btn-row">
                  <button type="button" className="ap-btn ap-btn-primary" disabled={busy} onClick={() => void judgeAnswer(answer, true)}>MARK CORRECT</button>
                  <button type="button" className="ap-btn ap-btn-secondary" disabled={busy} onClick={() => void judgeAnswer(answer, false)}>MARK INCORRECT</button>
                </div>}
              </div>
            </article>
          ))}
        </section>}
        </>}
      </div>
    </main>
  )
}
