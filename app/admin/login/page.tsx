'use client'

import { Suspense, useState, useEffect, type FormEvent } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'

function AdminLoginContent() {
  const router = useRouter()
  const params = useSearchParams()
  const next = params.get('next') ?? '/admin/quiz'

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // Auto-redirect if already authenticated
  useEffect(() => {
    fetch('/api/admin/login')
      .then((r) => r.json())
      .then((d) => { if (d.authenticated) router.replace(next) })
      .catch(() => {})
  }, [next, router])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch('/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.error ?? 'Login failed.'); return }
      router.replace(next)
    } catch {
      setError('Network error. Try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="al-root">
      <div className="al-card">
        <div className="al-header">
          <Link href="/" className="al-wordmark"><span className="mark">[ ]</span> TECH EVENT</Link>
          <p className="al-subtitle">ADMIN ACCESS</p>
        </div>

        <form onSubmit={handleSubmit} className="al-form" autoComplete="off">
          <div className="al-field">
            <label htmlFor="username" className="al-label">USERNAME</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="al-input"
              autoComplete="username"
              spellCheck={false}
              required
              disabled={loading}
            />
          </div>
          <div className="al-field">
            <label htmlFor="password" className="al-label">PASSWORD</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="al-input"
              autoComplete="current-password"
              required
              disabled={loading}
            />
          </div>

          {error && <p className="al-error" role="alert">{error}</p>}

          <button type="submit" className="al-submit" disabled={loading}>
            {loading ? 'VERIFYING…' : 'LOGIN →'}
          </button>
        </form>

        <p className="al-foot">
          <Link href="/">← Back to event site</Link>
        </p>
      </div>
    </main>
  )
}

export default function AdminLoginPage() {
  return (
    <Suspense fallback={<main className="al-root" aria-busy="true" />}>
      <AdminLoginContent />
    </Suspense>
  )
}
