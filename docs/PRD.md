# UNKNOWN / TLC Technology Competition — Product Requirements Document

Version: 1.0  
Status: baseline for implementation  
Primary users: TLC committee, teachers, mentors, students, visitors

## 1. Product vision

UNKNOWN is a reusable event operations and quiz competition platform for TLC. It must preserve the complete story of each annual event—people, teams, creative work, rounds, scores, evidence, and decisions—while providing a fair, real-time quiz experience for Classes IX, X, and XI.

The system is an event platform, not only a quiz screen. Quiz execution is the first critical workflow; team portfolios, round submissions, scoring history, and public showcases make the platform reusable for future editions.

## 2. Goals

- Run reliable, server-authoritative quiz rounds for IX, X, and XI.
- Preserve event data across years and server restarts.
- Let students view approved team information, media, standings, and published results.
- Let authorized staff manage teams, members, content, questions, rounds, scoring, and publishing.
- Support Python questions for IX/XI and C++ questions for X by default, while allowing explicit question overrides.
- Configure question distributions by type and difficulty instead of hard-coding a quiz.
- Make every score and administrative change explainable through history and audit logs.
- Allow future editions to reuse teams, question templates, categories, and operational rules without copying fragile code.

## 3. Non-goals for the first release

- Full school information-system integration.
- Student self-service accounts with grades, attendance, or private academic records.
- Automated code execution or arbitrary code judging. Code questions are initially stored and manually/administratively evaluated.
- Storing large media binaries directly in SQL Server.
- Anonymous public editing or public access to answer keys.

## 4. Roles and permissions

| Role | Main capabilities |
|---|---|
| Super admin | Users, roles, settings, event editions, recovery, audit access |
| Event admin | Teams, rounds, questions, quiz control, scoring, publishing |
| Teacher | Assigned classes, students, team verification, submissions, judging |
| Committee | Round operations, quiz control, scoring, announcements |
| Mentor | Assigned team guidance and permitted feedback |
| Student/team | Join a quiz, buzz, answer, view own/team public data |
| Visitor | View approved public team and event content |

## 5. Functional requirements

### Event and content management

1. Create an event edition with year, dates, status, rules, and public visibility.
2. Configure class tracks and preferred languages: IX/Python, X/C++, XI/Python by default.
3. Create rounds such as MCQ, presentation, debugging, project, and competitive programming.
4. Publish announcements and schedule items.

### Students and teams

1. Register students with display name and optional photo consent/media.
2. Create learning-stage teams within a class.
3. Create mixed main-event teams spanning classes.
4. Track dated memberships and captains without losing previous membership history.
5. Store team name, slogan, logo, posters, photos, links, descriptions, and approved evidence.

### Question bank and quiz configuration

1. Create reusable questions with type, difficulty, class eligibility, language, points, explanation, code snippet, options, and answer key.
2. Support MCQ, riddle, code, debugging, conceptual, and theory categories.
3. Define a quiz blueprint per round/class with count, timing, buzzer rules, and distribution.
4. Validate that requested distributions sum to the configured question count.
5. Select eligible questions randomly while preventing duplicate selection in a session.
6. Snapshot selected question text/points/order for historical integrity.

### Live quiz

1. Admin opens, starts, pauses, resumes, advances, resets, and ends a quiz session.
2. Teams join using a short-lived event/quiz code and receive a team-scoped token.
3. Server accepts the first valid buzzer press for the active question.
4. The winner receives a configured answer window; the server owns the timer.
5. Admin marks answers correct/incorrect or applies approved adjustments.
6. Students see sanitized question state and live standings; answer keys remain private.

### Results and audit

1. Store answer attempts, buzzer presses, judging decisions, score entries, and corrections.
2. Publish class and overall leaderboards only when authorized.
3. Provide team, round, class, and event reports.
4. Record actor, action, entity, time, and structured details for administrative changes.

## 6. Non-functional requirements

- Correctness: no double winners or duplicate final answers.
- Durability: no data loss on application restart; documented backups and restore tests.
- Security: HTTPS in production, hashed passwords, short-lived team tokens, least privilege, answer-key isolation, auditability.
- Performance: normal page/API responses under 500 ms at the expected event load; buzzer decisions serialized and observable.
- Availability: restart-safe deployment and a documented recovery procedure.
- Accessibility: keyboard navigation, readable contrast, meaningful labels, responsive student UI.
- Maintainability: API, database migrations, tests, and runbooks committed to the repository.

## 7. Success criteria

- A committee member can create a new annual edition without code changes.
- A complete quiz can be configured, run, paused, resumed, scored, and reported.
- Restarting the API does not erase teams, questions, or published results.
- A second operator cannot alter answer keys or score history without an authorized action and audit entry.
- A new backend deployment can be rolled back without corrupting the database.
- The same question bank and team history can support the next event edition safely.

## 8. Open decisions to confirm before production

- Student identity source and consent policy.
- Maximum concurrent teams/connections.
- Whether answers are manually judged only or later code-judged.
- Media storage provider and retention limits.
- Exact scoring/tie-break rules for every round.
- Production hosting location and SQL Server edition.
