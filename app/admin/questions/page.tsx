'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { type FormEvent, useCallback, useEffect, useState } from 'react'

type ClassTrack = { id: string; code: string; display_name: string; preferred_language: string }
type QuestionOption = { key: string; text: string; is_correct: boolean }
type Question = {
  id: string
  question_type: string
  difficulty: string
  preferred_language: string | null
  prompt: string
  code_snippet: string | null
  explanation: string | null
  accepted_answers: string[]
  default_points: number
  is_active: boolean
  class_track_ids: string[]
  options: QuestionOption[]
}
type ApiError = { error?: { message?: string }; detail?: string }

const types = ['MCQ', 'RIDDLE', 'CODE', 'DEBUGGING', 'CONCEPTUAL', 'THEORY']
const difficulties = ['EASY', 'MEDIUM', 'HARD']

async function readError(response: Response): Promise<string> {
  const body = await response.json().catch(() => ({})) as ApiError
  return body.error?.message ?? body.detail ?? 'The request failed.'
}

export default function AdminQuestionsPage() {
  const router = useRouter()
  const [classes, setClasses] = useState<ClassTrack[]>([])
  const [questions, setQuestions] = useState<Question[]>([])
  const [type, setType] = useState('MCQ')
  const [difficulty, setDifficulty] = useState('MEDIUM')
  const [language, setLanguage] = useState('')
  const [prompt, setPrompt] = useState('')
  const [codeSnippet, setCodeSnippet] = useState('')
  const [explanation, setExplanation] = useState('')
  const [acceptedAnswers, setAcceptedAnswers] = useState('')
  const [points, setPoints] = useState('10')
  const [classIds, setClassIds] = useState<string[]>([])
  const [options, setOptions] = useState<QuestionOption[]>([
    { key: 'A', text: '', is_correct: true },
    { key: 'B', text: '', is_correct: false },
  ])
  const [editingId, setEditingId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const load = useCallback(async () => {
    const auth = await fetch('/api/v1/auth/me')
    const authData = await auth.json().catch(() => ({})) as { authenticated?: boolean }
    if (!auth.ok || !authData.authenticated) {
      router.replace('/admin/login?next=/admin/questions')
      return
    }
    const [classResponse, questionResponse] = await Promise.all([
      fetch('/api/v1/classes', { cache: 'no-store' }),
      fetch('/api/v1/admin/questions', { cache: 'no-store' }),
    ])
    if (!classResponse.ok || !questionResponse.ok) {
      setError('Could not load the database-backed question bank.')
      return
    }
    setClasses(await classResponse.json() as ClassTrack[])
    setQuestions(await questionResponse.json() as Question[])
  }, [router])

  useEffect(() => { void load() }, [load])

  function toggleClass(id: string) {
    setClassIds((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id])
  }

  function updateOption(index: number, patch: Partial<QuestionOption>) {
    setOptions((current) => current.map((option, optionIndex) => optionIndex === index ? { ...option, ...patch } : option))
  }

  function addOption() {
    setOptions((current) => [...current, { key: String.fromCharCode(65 + current.length), text: '', is_correct: false }])
  }

  function removeOption(index: number) {
    setOptions((current) => current.length <= 2 ? current : current.filter((_, optionIndex) => optionIndex !== index).map((option, optionIndex) => ({ ...option, key: String.fromCharCode(65 + optionIndex) })))
  }

  function editQuestion(question: Question) {
    setEditingId(question.id)
    setType(question.question_type)
    setDifficulty(question.difficulty)
    setLanguage(question.preferred_language ?? '')
    setPrompt(question.prompt)
    setCodeSnippet(question.code_snippet ?? '')
    setExplanation(question.explanation ?? '')
    setAcceptedAnswers(question.accepted_answers.join('\n'))
    setPoints(String(question.default_points))
    setClassIds(question.class_track_ids)
    setOptions(question.options.length ? question.options : [
      { key: 'A', text: '', is_correct: true },
      { key: 'B', text: '', is_correct: false },
    ])
    setError('')
    setMessage(`Editing ${question.question_type} question.`)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function resetForm() {
    setEditingId(null)
    setType('MCQ')
    setDifficulty('MEDIUM')
    setLanguage('')
    setPrompt('')
    setCodeSnippet('')
    setExplanation('')
    setAcceptedAnswers('')
    setPoints('10')
    setClassIds([])
    setOptions([
      { key: 'A', text: '', is_correct: true },
      { key: 'B', text: '', is_correct: false },
    ])
  }

  async function saveQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setMessage('')
    const payload = {
      question_type: type,
      difficulty,
      preferred_language: language || null,
      prompt,
      code_snippet: codeSnippet || null,
      explanation: explanation || null,
      accepted_answers: acceptedAnswers.split('\n').map((answer) => answer.trim()).filter(Boolean),
      default_points: Number(points),
      class_track_ids: classIds,
      options: type === 'MCQ' ? options : [],
    }
    try {
      const response = await fetch(editingId ? `/api/v1/admin/questions/${editingId}` : '/api/v1/admin/questions', {
        method: editingId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!response.ok) throw new Error(await readError(response))
      const wasEditing = editingId !== null
      resetForm()
      setMessage(wasEditing ? 'Question updated. Existing quiz sessions keep their saved version.' : 'Question created and persisted in the database.')
      await load()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save the question.')
    } finally {
      setBusy(false)
    }
  }

  async function setQuestionActive(question: Question, isActive: boolean) {
    setBusy(true)
    setError('')
    setMessage('')
    try {
      const response = await fetch(`/api/v1/admin/questions/${question.id}/active`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: isActive }),
      })
      if (!response.ok) throw new Error(await readError(response))
      setMessage(isActive ? 'Question reactivated.' : 'Question retired from future quiz sessions.')
      await load()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not change question status.')
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
        <span className="ap-header-title">QUESTION BANK</span>
        <Link href="/admin/durable-quiz" className="ap-btn ap-btn-secondary">QUIZ CONTROL</Link>
        <button type="button" className="ap-btn ap-btn-secondary ap-logout" onClick={() => void logout()}>LOGOUT</button>
      </header>
      <div className="ap-body" style={{ display: 'block', maxWidth: 1100, margin: '0 auto' }}>
        <section className="ap-section">
          <h2 className="ap-section-title">{editingId ? 'EDIT QUESTION' : 'CREATE QUESTION'}</h2>
          <form onSubmit={(event) => void saveQuestion(event)} style={{ display: 'grid', gap: 14 }}>
            <div className="ap-code-row">
              <select className="ap-select" value={type} onChange={(event) => setType(event.target.value)}>{types.map((item) => <option key={item}>{item}</option>)}</select>
              <select className="ap-select" value={difficulty} onChange={(event) => setDifficulty(event.target.value)}>{difficulties.map((item) => <option key={item}>{item}</option>)}</select>
              <input className="ap-code-input" type="number" min={1} max={100} value={points} onChange={(event) => setPoints(event.target.value)} aria-label="Points" />
              <input className="ap-code-input" value={language} onChange={(event) => setLanguage(event.target.value)} placeholder="Language (optional)" />
            </div>
            <textarea className="ap-textarea" required value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Question prompt" rows={4} />
            <textarea className="ap-textarea" value={codeSnippet} onChange={(event) => setCodeSnippet(event.target.value)} placeholder="Code snippet (optional)" rows={3} />
            <textarea className="ap-textarea" value={explanation} onChange={(event) => setExplanation(event.target.value)} placeholder="Explanation (optional)" rows={2} />
            {type !== 'MCQ' && <textarea className="ap-textarea" required value={acceptedAnswers} onChange={(event) => setAcceptedAnswers(event.target.value)} placeholder="Accepted answers — one per line (used for automatic grading)" rows={3} />}
            <fieldset style={{ border: '1px solid currentColor', padding: 14 }}>
              <legend className="ap-label">AVAILABLE CLASS TRACKS</legend>
              <div className="ap-btn-row">{classes.map((item) => <label key={item.id} className="ap-check"><input type="checkbox" checked={classIds.includes(item.id)} onChange={() => toggleClass(item.id)} /> {item.code} · {item.display_name}</label>)}</div>
            </fieldset>
            {type === 'MCQ' && <fieldset style={{ border: '1px solid currentColor', padding: 14, display: 'grid', gap: 8 }}>
              <legend className="ap-label">MULTIPLE-CHOICE OPTIONS</legend>
              {options.map((option, index) => <div className="ap-code-row" key={option.key}>
                <input type="radio" name="correct-option" checked={option.is_correct} onChange={() => setOptions((current) => current.map((item, optionIndex) => ({ ...item, is_correct: optionIndex === index })))} aria-label={`Mark option ${option.key} correct`} />
                <strong>{option.key}</strong>
                <input className="ap-code-input" style={{ flex: 1 }} required value={option.text} onChange={(event) => updateOption(index, { text: event.target.value })} placeholder={`Option ${option.key}`} />
                <button type="button" className="ap-btn ap-btn-secondary" onClick={() => removeOption(index)} disabled={options.length <= 2}>REMOVE</button>
              </div>)}
              <button type="button" className="ap-btn ap-btn-secondary" onClick={addOption}>ADD OPTION</button>
            </fieldset>}
            {error && <p className="ap-error-text" role="alert">{error}</p>}
            {message && <p className="ap-action-msg" role="status">{message}</p>}
            <div className="ap-btn-row">
              <button type="submit" className="ap-btn ap-btn-primary" disabled={busy || classIds.length === 0}>{busy ? 'SAVING…' : editingId ? 'SAVE CHANGES' : 'CREATE QUESTION'}</button>
              {editingId && <button type="button" className="ap-btn ap-btn-secondary" disabled={busy} onClick={resetForm}>CANCEL EDIT</button>}
            </div>
          </form>
        </section>
        <section className="ap-section">
          <h2 className="ap-section-title">PERSISTED QUESTIONS · {questions.length}</h2>
          {questions.length === 0 ? <p className="ap-loading-text">NO QUESTIONS YET.</p> : questions.map((question) => <article key={question.id} className="ap-room-panel ap-room-blue" style={{ marginBottom: 12 }}>
            <div className="ap-room-body" style={{ display: 'block' }}>
              <div className="ap-status-row"><strong>{question.question_type} · {question.difficulty}</strong><span>{question.default_points} POINTS</span><span>{question.is_active ? 'ACTIVE' : 'INACTIVE'}</span></div>
              <p>{question.prompt}</p>
              <small>{question.class_track_ids.map((id) => classes.find((item) => item.id === id)?.code ?? id).join(' · ')}</small>
              <div className="ap-btn-row" style={{ marginTop: 12 }}>
                <button type="button" className="ap-btn ap-btn-secondary" disabled={busy} onClick={() => editQuestion(question)}>EDIT</button>
                <button type="button" className="ap-btn ap-btn-secondary" disabled={busy} onClick={() => void setQuestionActive(question, !question.is_active)}>{question.is_active ? 'RETIRE' : 'REACTIVATE'}</button>
              </div>
            </div>
          </article>)}
        </section>
      </div>
    </main>
  )
}
