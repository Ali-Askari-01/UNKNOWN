# Database Data Dictionary

## Core event

| Entity | Purpose | Key fields |
|---|---|---|
| `event_edition` | Annual TLC event boundary | year, status, dates |
| `class_track` | IX/X/XI configuration per edition | code, language |
| `round` | Event activity and scoring boundary | number, type, status |
| `round_class` | Class eligibility for a round | round/class pair |
| `schedule_item` | Operational timetable | title, start/end, location |
| `announcement` | Published event communication | title, body, severity |

## Identity and teams

| Entity | Purpose | Key fields |
|---|---|---|
| `user_account` | Staff/admin identity | username, password hash, active |
| `role`, `user_role` | Authorization | role code and assignment |
| `student` | Student profile | display name, reference, photo |
| `team` | Learning or mixed competition team | name, slogan, type |
| `team_class` | Team-to-class relationship | team/class pair |
| `team_member` | Dated student membership | joined/left, captain |
| `media_asset` | External file metadata | object key, type, moderation, visibility |
| `team_media` | Team showcase attachments | team/media pair, caption/order |

## Content and submissions

| Entity | Purpose | Key fields |
|---|---|---|
| `question` | Reusable bank item | type, difficulty, language, prompt, answer |
| `question_option` | MCQ choices | option key/text/correctness |
| `question_class` | Eligible classes | question/class pair |
| `question_tag`, `question_tag_link` | Flexible categorization | tag code and link |
| `submission` | Team work for a round | type, title, status, URL |
| `submission_media` | Submission evidence | submission/media pair |
| `evaluation_criterion` | Rubric criterion | round, max points |
| `submission_evaluation` | Judge decision | evaluator, points, feedback |

## Quiz and results

| Entity | Purpose | Key fields |
|---|---|---|
| `quiz_blueprint` | Rules for a class/round quiz | count, timing, buzzer |
| `quiz_distribution` | Required type/difficulty buckets | type, difficulty, quantity |
| `quiz_session` | Actual run | code, status, timestamps |
| `quiz_question` | Historical selected question | order and snapshots |
| `quiz_participant` | Team joining a session | session/team/join time |
| `buzzer_press` | Every press and winner flag | question, participant, time |
| `answer_submission` | Submitted and judged answer | answer, correctness, points |
| `score_entry` | Append-only score ledger | team, round, delta, reason |
| `audit_log` | Administrative trace | actor, action, entity, JSON details |

## Derived views to implement

- `v_team_current_members`: active memberships only.
- `v_team_public_profile`: approved public team and media data.
- `v_quiz_leaderboard`: sum of score entries by team/session/round.
- `v_event_leaderboard`: aggregate published round scores.
- `v_question_eligibility`: active questions joined with class/type/difficulty/language filters.
- `v_audit_summary`: searchable administrative activity without exposing secrets.
