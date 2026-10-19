export const classes = [
  { id: 'ix', roman: 'IX', label: 'CLASS IX', level: 'Foundation', language: 'Python', students: 'All students, including Biology', accent: 'aqua' },
  { id: 'x', roman: 'X', label: 'CLASS X', level: 'Matric', language: 'C++', students: 'Approximately 20 students', accent: 'blue' },
  { id: 'xi', roman: 'XI', label: 'CLASS XI', level: 'First Year', language: 'Python', students: 'Approximately 10 students', accent: 'cream' },
] as const

export const rounds = [
  { week: '01', round: 'ROUND 0', name: 'GROUPS & NAMES', description: 'Students create equal groups and choose their names.', stage: 'LEARNING STAGE', prep: true, status: 'COMPLETED' },
  { week: '02', round: 'ROUND 2', name: 'MCQ QUIZ', description: 'Syllabus-based multiple choice competition.', stage: 'LEARNING STAGE', prep: true, status: 'COMPLETED' },
  { week: '03', round: 'ROUND 3', name: 'PRESENTATION', description: 'Research a topic and present it as a group.', stage: 'LEARNING STAGE', prep: true, status: 'ACTIVE' },
  { week: '04', round: 'ROUND 4', name: 'ERROR DEBUGGING', description: 'Identify and fix bugs in class-language code.', stage: 'LEARNING STAGE', prep: true, status: 'UPCOMING' },
  { week: '05', round: 'ROUND 5', name: 'PROJECT', description: 'Mixed teams build a teacher-approved technology project. Vibe coding is allowed.', stage: 'MAIN EVENT', prep: true, status: 'LOCKED' },
  { week: '06', round: 'ROUND 6', name: 'COMPETITIVE PROGRAMMING', description: 'Teams solve basic programming questions against the clock.', stage: 'MAIN EVENT', prep: true, status: 'LOCKED' },
] as const

export const scoreboard = [
  { team: 'ALPHA', project: 80, cp: 75, total: 155 },
  { team: 'BYTE', project: 72, cp: 79, total: 151 },
  { team: 'NOVA', project: 68, cp: 74, total: 142 },
]

export const rules = [
  ['GENERAL RULES', 'One round takes place each week. Every round begins with a prep session. Teachers, committee members, and mentors have distinct responsibilities.'],
  ['LEARNING STAGE', 'Weeks 1–4 are separate class competitions. IX and XI use Python. X uses C++.'],
  ['TEAM FORMATION', 'Learning-stage groups stay within one class. Main-event mixed teams combine IX, X, and XI with equal representation where possible.'],
  ['MAIN EVENT', 'Weeks 5–6 combine Project and basic Competitive Programming. Project ideas need teacher or committee approval. Vibe coding is allowed.'],
  ['SCORING', 'Final score equals Project Points + CP Points. All teams participate in both main-event rounds. Ties remain ties unless a future tie-break rule is configured.'],
]

export const announcements = [
  ['PREP SESSION ANNOUNCED', 'Round 3 presentation prep is scheduled before the active challenge.', 'IMPORTANT'],
  ['ROUND RESULTS PUBLISHED', 'MCQ Quiz results are now visible on the class scoreboards.', 'NORMAL'],
  ['PROJECT SUBMISSIONS OPEN', 'Main-event project ideas will open after mixed teams are published.', 'NORMAL'],
]

export const roles = [
  ['CLASS TEACHERS', 'Finalize groups, approve project ideas, and mentor teams during building.'],
  ['COMMITTEE', 'Conduct prep sessions, form mixed teams, maintain points, and rank teams.'],
  ['MENTORS', 'Guide students and help teams improve their approved projects.'],
]

export const groups = [
  // ── Class IX ──────────────────────────────────────────────────────────────
  {
    classId: 'ix' as const,
    number: 1,
    name: 'Black Hat Hackers',
    slogan: 'We don\'t talk, we make history',
    members: ['Mohib', 'Sunny', 'Mujtaba', 'Hasan'],
  },
  {
    classId: 'ix' as const,
    number: 2,
    name: '404 Braincells',
    slogan: '404: normally not found',
    members: ['Hadi', 'Ibrahim', 'Riyaz'],
  },
  {
    classId: 'ix' as const,
    number: 3,
    name: 'Cyber Deceit',
    slogan: 'Imagine about us, we are coming as a deceit',
    members: ['Muntazir', 'Aun', 'Mustafa'],
  },
  {
    classId: 'ix' as const,
    number: 4,
    name: 'Unorthodox Hub',
    slogan: 'Ability to do anything',
    members: ['Arish', 'Safeer', 'Tabish'],
  },
  {
    classId: 'ix' as const,
    number: 5,
    name: 'Tech Nawab',
    slogan: 'Hard work can achieve everything',
    members: ['Akif', 'Saboor', 'Abbas Abdi'],
  },

  // ── Class X ───────────────────────────────────────────────────────────────
  {
    classId: 'x' as const,
    number: 1,
    name: 'Silicotech',
    slogan: 'Tech beyond universe',
    members: ['Minhal', 'Ashad', 'John'],
  },
  {
    classId: 'x' as const,
    number: 2,
    name: 'StarTek',
    slogan: 'Shining above all',
    members: ['Wasi', 'Ali Raza', 'Abuzar'],
  },
  {
    classId: 'x' as const,
    number: 3,
    name: 'The Bio Programmers',
    slogan: 'With great work comes great success',
    members: ['Aliyan', 'Wadood', 'Ahmed'],
  },
  {
    classId: 'x' as const,
    number: 4,
    name: 'The Crusaders',
    slogan: 'Destroyer of tech world',
    members: ['Haider', 'Ali Murtaza', 'Abbas'],
  },
  {
    classId: 'x' as const,
    number: 5,
    name: 'Future O Holic',
    slogan: 'High on future',
    members: ['Ali Mehdi', 'Shahzain', 'Mehdi Ali'],
  },
  {
    classId: 'x' as const,
    number: 6,
    name: 'Total Winners',
    slogan: 'If you are sincere, you will be successful',
    members: ['Ali Abidi', 'Asher', 'Hasnain'],
  },

  // ── Class XI ──────────────────────────────────────────────────────────────
  {
    classId: 'xi' as const,
    number: 1,
    name: 'Syntax Crackers',
    slogan: 'Where error has no chance',
    members: ['Hasnain', 'Hussain', 'Sami'],
  },
  {
    classId: 'xi' as const,
    number: 2,
    name: 'Logi Knights',
    slogan: 'Observe logic, conquer code',
    members: ['Muslim', 'Mehdi', 'Basit', 'Raza'],
  },
  {
    classId: 'xi' as const,
    number: 3,
    name: 'Unknown Brutes',
    slogan: 'Unseen force, unstoppable code',
    members: ['Naqi', 'Minhal', 'Fozan', 'Shabi'],
  },
] as const

export type Group = (typeof groups)[number]

export const adminNav = ['OVERVIEW', 'STUDENTS', 'CLASS IX', 'CLASS X', 'CLASS XI', 'GROUPS', 'ROUNDS', 'MAIN EVENT', 'MIXED TEAMS', 'PROJECTS', 'COMPETITIVE PROGRAMMING', 'SCORES', 'LEADERBOARD', 'ANNOUNCEMENTS', 'SCHEDULE', 'CONTENT', 'USERS & ROLES', 'AUDIT LOG', 'SETTINGS']

export type ClassId = (typeof classes)[number]['id']

export function getClassTrack(id: string) {
  return classes.find((item) => item.id === id) ?? classes[0]
}

export function getRound(id: string) {
  return rounds.find((item) => item.week === id) ?? rounds[2]
}

export const dbModelNotes = ['User', 'StudentProfile', 'ClassTrack', 'Group', 'GroupMember', 'MixedTeam', 'MixedTeamMember', 'Round', 'PrepSession', 'MCQQuestion', 'PresentationAssignment', 'DebugChallenge', 'Project', 'ProjectEvaluation', 'CPProblem', 'Score', 'Announcement', 'ScheduleItem', 'AuditLog', 'SiteSetting']

export const demoDataNotice = 'DEMO DATA // CONNECT POSTGRESQL + PRISMA TO REPLACE THESE VALUES'

export default { classes, rounds, scoreboard, rules, announcements, roles }

// Prisma-ready model sketch. Move to prisma/schema.prisma when database provisioning is enabled.
export const prismaModelSketch = `User, StudentProfile, ClassTrack, Group, GroupMember, MixedTeam, MixedTeamMember, Round, PrepSession, MCQQuestion, PresentationAssignment, DebugChallenge, Project, ProjectEvaluation, CPProblem, Score, Announcement, ScheduleItem, AuditLog, SiteSetting`

export const authArchitecture = { studentLogin: '/login', adminLogin: '/admin/login', protectedAdminPrefix: '/admin/*', adminApiPrefix: '/api/admin/*', roles: ['SUPER_ADMIN', 'ADMIN', 'TEACHER', 'COMMITTEE', 'MENTOR', 'STUDENT'] }

export const adminSeed = { usernameEnv: 'ADMIN_USERNAME', passwordEnv: 'ADMIN_PASSWORD', defaultUsername: 'admin', passwordStorage: 'bcrypt or argon2 hash', role: 'SUPER_ADMIN' }
