'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

type ClassTrack = { code: string; display_name: string; preferred_language: string }
type Team = { id: string; name: string; slogan: string | null; members: Array<{ display_name: string }> }
type Standing = { team_id: string; team_name: string; class_code: string; score: number | null; completed_rounds: number; is_provisional: boolean }

export default function ClassTrackPage({ params }: { params: Promise<{ classId: string }> }) {
  const [classTrack, setClassTrack] = useState<ClassTrack | null>(null)
  const [teams, setTeams] = useState<Team[]>([])
  const [standings, setStandings] = useState<Standing[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    void params.then(async ({ classId }) => {
      const code = classId.toUpperCase()
      try {
        const [classesResponse, teamsResponse, standingsResponse] = await Promise.all([
          fetch('/api/v1/classes', { cache: 'no-store' }),
          fetch(`/api/v1/teams?class_code=${encodeURIComponent(code)}`, { cache: 'no-store' }),
          fetch('/api/v1/leaderboard', { cache: 'no-store' }),
        ])
        if (!classesResponse.ok || !teamsResponse.ok || !standingsResponse.ok) throw new Error('Track data is unavailable.')
        const classes = await classesResponse.json() as ClassTrack[]
        const track = classes.find((item) => item.code.toUpperCase() === code)
        if (!track) throw new Error('That class track does not exist.')
        if (!cancelled) {
          setClassTrack(track)
          setTeams(await teamsResponse.json() as Team[])
          setStandings((await standingsResponse.json() as Standing[]).filter((entry) => entry.class_code.toUpperCase() === code))
        }
      } catch (cause) {
        if (!cancelled) setError(cause instanceof Error ? cause.message : 'Track data is unavailable.')
      }
    })
    return () => { cancelled = true }
  }, [params])

  return (
    <main className="ap-root">
      <header className="ap-header">
        <Link href="/" className="ap-wordmark"><span className="mark">[ ]</span> TECH EVENT</Link>
        <span className="ap-header-title">CLASS TRACK</span>
      </header>
      <div className="ap-body" style={{ display: 'block', maxWidth: 1100, margin: '0 auto', width: '100%' }}>
        <section className="ap-section">
          <Link href="/#competition" className="ap-label">← ALL CLASS TRACKS</Link>
          {error ? <p className="ap-error-text" role="alert">{error}</p> : classTrack ? (
            <>
              <p className="ap-section-title" style={{ marginTop: 24 }}>TRACK // {classTrack.code}</p>
              <h1>{classTrack.display_name}</h1>
              <p>{classTrack.preferred_language} learning path · {teams.length} registered teams</p>
            </>
          ) : <p className="ap-loading-text">LOADING TRACK DATA…</p>}
        </section>
        <section className="ap-section">
          <h2 className="ap-section-title">CLASS RANKING</h2>
          {standings.length ? <div className="ap-ranking-list">{standings.map((entry, index) => <article key={entry.team_id} className={`ap-ranking-row ${index === 0 ? 'is-first' : ''}`}><span className="ap-ranking-place">{String(index + 1).padStart(2, '0')}</span><strong>{entry.team_name}<small style={{ display: 'block' }}>{entry.completed_rounds}/5 scored rounds {entry.is_provisional ? '· PROVISIONAL' : ''}</small></strong><span>{entry.score === null ? '—' : `${(entry.score * 100).toFixed(2)}%`}</span></article>)}</div> : <p className="ap-loading-text">OFFICIAL STANDINGS ARE NOT AVAILABLE YET.</p>}
          <p className="ap-label">Provisional standings use completed event rounds only.</p>
        </section>
        <section className="ap-section">
          <h2 className="ap-section-title">REGISTERED TEAMS</h2>
          {teams.length === 0 ? <p className="ap-loading-text">NO PUBLIC TEAM DATA.</p> : teams.map((team) => (
            <article key={team.id} className="ap-room-panel" style={{ padding: 16, marginBottom: 12 }}>
              <h2>{team.name}</h2>
              {team.slogan && <p>{team.slogan}</p>}
              <p className="ap-label">{team.members.length} PLAYERS</p>
              {team.members.length > 0 && <p>{team.members.map((member) => member.display_name).join(' · ')}</p>}
            </article>
          ))}
        </section>
      </div>
    </main>
  )
}
