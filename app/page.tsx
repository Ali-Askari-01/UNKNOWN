'use client'

import { useState } from 'react'
import Link from 'next/link'
import { groups } from '@/data/event'

const rounds = [
  { week: '01', round: 'ROUND 0', title: 'GROUPS & NAMES', detail: 'Form equal groups and choose your identity.', status: 'COMPLETE' },
  { week: '02', round: 'ROUND 2', title: 'MCQ QUIZ', detail: 'Syllabus-based questions. Speed and accuracy matter.', status: 'COMPLETE' },
  { week: '03', round: 'ROUND 3', title: 'PRESENTATION', detail: 'Research a topic, then make the room listen.', status: 'ACTIVE' },
  { week: '04', round: 'ROUND 4', title: 'ERROR DEBUGGING', detail: 'Find the bug. Fix the code. Keep the points.', status: 'NEXT' },
  { week: '05', round: 'ROUND 5', title: 'PROJECT', detail: 'Build something useful in a mixed team.', status: 'LOCKED' },
  { week: '06', round: 'ROUND 6', title: 'COMPETITIVE PROGRAMMING', detail: 'Basic problems, team solving, against the clock.', status: 'LOCKED' },
]

const tracks = [
  { roman: 'IX', label: 'CLASS IX', language: 'PYTHON', count: 'ALL STUDENTS', next: 'ERROR DEBUGGING', tone: 'blue' },
  { roman: 'X', label: 'CLASS X', language: 'C++', count: '≈ 20 STUDENTS', next: 'ERROR DEBUGGING', tone: 'aqua' },
  { roman: 'XI', label: 'CLASS XI', language: 'PYTHON', count: '≈ 10 STUDENTS', next: 'ERROR DEBUGGING', tone: 'cream' },
]

function Button({ children, href = '#competition', secondary = false }: { children: React.ReactNode; href?: string; secondary?: boolean }) {
  return <Link href={href} className={`pixel-button ${secondary ? 'pixel-button-secondary' : ''}`}>{children}<span aria-hidden="true">↗</span></Link>
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <p className="section-label"><span className="status-dot" />{children}</p>
}

const classTabs = [
  { id: 'ix' as const, label: 'CLASS IX',  roman: 'IX',  language: 'PYTHON', count: 5, students: 16, tone: 'blue' },
  { id: 'x'  as const, label: 'CLASS X',   roman: 'X',   language: 'C++',    count: 6, students: 18, tone: 'aqua' },
  { id: 'xi' as const, label: 'CLASS XI',  roman: 'XI',  language: 'PYTHON', count: 3, students: 11, tone: 'cream' },
] as const

function GroupsSection() {
  const [activeClass, setActiveClass] = useState<'ix' | 'x' | 'xi'>('ix')
  const visible = groups.filter((g) => g.classId === activeClass)
  const tab = classTabs.find((t) => t.id === activeClass)!

  return (
    <section id="groups" className="groups-section">
      <div className="shell">
        <div className="section-heading split-heading">
          <div>
            <SectionLabel>03.5 // CLASS GROUPS</SectionLabel>
            <h2>Teams inside<br /><span>the tracks.</span></h2>
          </div>
          <p>Each class competes as independent groups during the learning stage. Select a class to see its groups and members.</p>
        </div>

        {/* Class tab selector */}
        <div className="groups-tabs">
          {classTabs.map((tab) => (
            <button
              type="button"
              key={tab.id}
              onClick={() => setActiveClass(tab.id)}
              className={`groups-tab groups-tab-${tab.tone} ${activeClass === tab.id ? 'is-active' : ''}`}
            >
              <span className="gtab-roman">{tab.roman}</span>
              <span className="gtab-label">{tab.label}</span>
              <span className="gtab-meta">{tab.count} GROUPS · {tab.students} STUDENTS · {tab.language}</span>
            </button>
          ))}
        </div>

        {/* Active class header strip */}
        <div className={`groups-class-strip groups-strip-${tab.tone}`}>
          <span className="gstrip-roman">{tab.roman}</span>
          <div className="gstrip-info">
            <strong>{tab.label}</strong>
            <span>{tab.language} · {tab.count} GROUPS · {tab.students} STUDENTS</span>
          </div>
          <span className="gstrip-tag">LEARNING STAGE</span>
        </div>

        {/* Group cards grid */}
        <div className="groups-grid">
          {visible.map((group) => (
            <article key={`${group.classId}-${group.number}`} className="group-card">
              <div className="gcard-top">
                <span className="gcard-number">GROUP {String(group.number).padStart(2, '0')}</span>
                <span className="gcard-count">{group.members.length} MEMBERS</span>
              </div>
              <h3 className="gcard-name">{group.name}</h3>
              <p className="gcard-slogan">"{group.slogan}"</p>
              <div className="gcard-divider" />
              <ul className="gcard-members">
                {group.members.map((member) => (
                  <li key={member}><span aria-hidden="true">→</span> {member}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

export default function Page() {
  const [activeTrack, setActiveTrack] = useState('IX')

  return (
    <main>
      <header className="site-header">
        <Link href="#top" className="wordmark"><span className="mark">[ ]</span> TECH EVENT <span className="wordmark-muted">/ 2026</span></Link>
        <nav className="desktop-nav" aria-label="Primary navigation">
          <Link href="#how-it-works">How it works</Link><Link href="#competition">Competition</Link><Link href="#groups">Groups</Link><Link href="#schedule">Schedule</Link><Link href="#leaderboard">Leaderboard</Link><Link href="#rules">Rules</Link>
        </nav>
        <Button href="/login" secondary>LOGIN</Button>
      </header>

      <section id="top" className="hero shell">
        <div className="hero-copy">
          <SectionLabel>EVENT STATUS: ACTIVE // SYSTEM ONLINE</SectionLabel>
          <h1>LEARN.<br /><span>BUILD.</span><br />DEBUG.<br /><em>COMPETE.</em></h1>
          <p className="hero-description">A six-week technology competition where Class IX, X and XI learn within their classes before joining forces for the final main event.</p>
          <div className="button-row"><Button href="#competition">ENTER EVENT</Button><Button href="#how-it-works" secondary>VIEW COMPETITION</Button></div>
        </div>
        <div className="hero-console" aria-label="Event flow visualization">
          <div className="console-top"><span>EVENT_FLOW.EXE</span><span>v1.0.26</span></div>
          <div className="flow-stage"><div className="flow-lines" aria-hidden="true"><i /><i /><i /></div>{tracks.map((track) => <div className={`flow-node node-${track.roman.toLowerCase()}`} key={track.roman}><strong>{track.roman}</strong><small>{track.language}</small></div>)}<div className="main-event-node"><span>MAIN</span><strong>EVENT</strong><small>MIXED TEAMS</small></div></div>
          <div className="console-bottom"><span>INPUTS: 03</span><span>OUTPUT: 01</span><span className="blink">_</span></div>
        </div>
      </section>

      <section className="status-strip"><div><strong>06</strong><span>WEEKS</span></div><div><strong>03</strong><span>CLASSES</span></div><div><strong>06</strong><span>EVENT ROUNDS</span></div><div><strong>01</strong><span>FINAL COMPETITION</span></div></section>

      <section id="how-it-works" className="shell section-block"><div className="section-heading"><SectionLabel>01 // EVENT ARCHITECTURE</SectionLabel><h2>Two stages.<br /><span>One scoreboard.</span></h2></div><div className="stage-grid"><article className="stage-card stage-card-dark"><div className="card-index">STAGE 01</div><h3>LEARNING<br />STAGE</h3><p>Weeks 1–4. Students compete inside their respective classes and build the skills they need for the final challenge.</p><ul><li>Group Formation</li><li>MCQ Quiz</li><li>Presentation</li><li>Error Debugging</li></ul><div className="card-foot">PREP SESSION FIRST <span>→</span></div></article><article className="stage-card stage-card-light"><div className="card-index">STAGE 02</div><h3>MAIN<br />EVENT</h3><p>Weeks 5–6. IX, X and XI combine into mixed teams for the project and coding rounds.</p><ul><li>Project Competition</li><li>Competitive Programming</li><li>Combined Scoring</li><li>Final Ranking</li></ul><div className="card-foot">IX + X + XI <span>→</span></div></article></div></section>

      <section id="competition" className="shell section-block"><div className="section-heading split-heading"><div><SectionLabel>02 // CLASS TRACKS</SectionLabel><h2>Choose your<br /><span>track.</span></h2></div><p>Separate learning paths. Shared ambition. Select a class to inspect its language, progress and next challenge.</p></div><div className="track-grid">{tracks.map((track) => <button type="button" key={track.roman} onClick={() => setActiveTrack(track.roman)} className={`track-card track-${track.tone} ${activeTrack === track.roman ? 'is-active' : ''}`}><div className="track-top"><span>{track.label}</span><span>→</span></div><div className="roman">{track.roman}</div><div className="track-meta"><div><small>LANGUAGE</small><strong>{track.language}</strong></div><div><small>STUDENTS</small><strong>{track.count}</strong></div></div><div className="track-progress"><span /><span /><span /><span className="empty" /><span className="empty" /><span className="empty" /></div><div className="track-next"><small>NEXT ROUND</small><strong>{track.next}</strong></div></button>)}</div><div className="track-detail"><span className="detail-code">TRACK // {activeTrack}</span><strong>{activeTrack === 'IX' || activeTrack === 'XI' ? 'Python debugging, all students included.' : 'Class X students compete in C++ during the learning stage.'}</strong><Link href={`/dashboard/class/${activeTrack.toLowerCase()}`}>VIEW FULL TRACK →</Link></div></section>

      <GroupsSection />

      <section id="schedule" className="timeline-section"><div className="shell"><div className="section-heading split-heading"><div><SectionLabel>03 // PROGRESSION BOARD</SectionLabel><h2>Six weeks.<br /><span>Six signals.</span></h2></div><div className="prep-note">[ PREP SESSION FIRST ]<br /><small>Every learning round begins with preparation.</small></div></div><div className="timeline">{rounds.map((item, index) => <article className={`round ${item.status === 'ACTIVE' ? 'round-active' : ''}`} key={item.week}><div className="round-week">WEEK {item.week}</div><div className="round-number">{item.round}</div><h3>{item.title}</h3><p>{item.detail}</p><span className={`round-status status-${item.status.toLowerCase()}`}>{item.status}</span>{index < rounds.length - 1 && <span className="round-connector" aria-hidden="true">→</span>}</article>)}</div></div></section>

      <section className="shell section-block main-event"><div className="main-event-copy"><SectionLabel>04 // THE MERGE</SectionLabel><h2>Three tracks.<br /><span>One main event.</span></h2><p>In Weeks 5 and 6, students from IX, X and XI join mixed teams. Teams aim for equal representation where possible; teachers and the committee finalize the arrangement.</p><Button href="#leaderboard">VIEW MAIN EVENT</Button></div><div className="merge-diagram"><div className="merge-class">IX</div><div className="merge-class">X</div><div className="merge-class">XI</div><div className="merge-arrow">+</div><div className="merge-result">MIXED<br />TEAM</div></div></section>

      <section id="leaderboard" className="score-section"><div className="shell"><div className="score-header"><div><SectionLabel>05 // LIVE RANKING</SectionLabel><h2>Points become<br /><span>the story.</span></h2></div><span className="demo-tag">DEMO DATA // NOT FINAL</span></div><div className="scoreboard"><div className="score-row score-head"><span>TEAM</span><span>PROJECT</span><span>CP</span><span>TOTAL</span></div>{[['ALPHA', '80', '75', '155'], ['BYTE FORCE', '72', '79', '151'], ['NOVA', '68', '74', '142']].map((row) => <div className="score-row" key={row[0]}><strong>{row[0]}</strong><span>{row[1]}</span><span>{row[2]}</span><strong>{row[3]}</strong></div>)}<div className="score-formula"><span>WINNER SCORE =</span><strong>PROJECT POINTS <b>+</b> CP POINTS</strong></div></div></div></section>

      <section id="rules" className="shell roles-section"><SectionLabel>06 // THE PEOPLE BEHIND THE SYSTEM</SectionLabel><h2>Everyone has<br /><span>a role.</span></h2><div className="roles-grid">{[['CLASS TEACHERS', 'Finalize groups', 'Approve project ideas', 'Mentor teams during building'], ['COMMITTEE', 'Conduct prep sessions', 'Form mixed teams', 'Maintain points and rankings'], ['MENTORS', 'Guide students', 'Help teams improve projects', 'Support approved builds']].map(([title, ...items]) => <article className="role-card" key={title}><h3>{title}</h3>{items.map((item) => <p key={item}>+ {item}</p>)}</article>)}</div></section>

      <section id="access" className="shell section-block access-section">
        <div className="section-heading">
          <SectionLabel>07 // ACCESS PORTALS</SectionLabel>
          <h2>Choose your<br /><span>portal.</span></h2>
        </div>
        <div className="access-grid">
          <article className="access-card access-card-student">
            <div className="access-icon">👤</div>
            <h3>STUDENT<br />PORTAL</h3>
            <p>Access quizzes, view your group details, track your progress, and participate in competition rounds.</p>
            <ul>
              <li>Take MCQ quizzes</li>
              <li>View group rankings</li>
              <li>Track personal progress</li>
              <li>Access competition materials</li>
            </ul>
            <Link href="/quiz" className="access-link">
              ENTER STUDENT PORTAL <span aria-hidden="true">→</span>
            </Link>
          </article>
          <article className="access-card access-card-admin">
            <div className="access-icon">⚙️</div>
            <h3>ADMIN<br />PORTAL</h3>
            <p>Manage competition rounds, configure quiz settings, view results, and oversee the entire event.</p>
            <ul>
              <li>Manage quiz sessions</li>
              <li>Configure competition settings</li>
              <li>View live results</li>
              <li>Monitor student progress</li>
            </ul>
            <Link href="/admin/login" className="access-link">
              ENTER ADMIN PORTAL <span aria-hidden="true">→</span>
            </Link>
          </article>
        </div>
      </section>

      <section className="cta shell"><div><SectionLabel>READY // SYSTEM STANDING BY</SectionLabel><h2>Enter the<br /><span>competition.</span></h2></div><Button href="/login">LOGIN TO EVENT</Button></section>
      <footer className="site-footer shell"><span>EVENT SYSTEM // IX · X · XI</span><div><Link href="#competition">Competition</Link><Link href="#schedule">Schedule</Link><Link href="#rules">Rules</Link><Link href="#leaderboard">Leaderboard</Link><Link href="/admin/login">Admin access</Link></div><span>© 2026 TECH EVENT</span></footer>
    </main>
  )
}
