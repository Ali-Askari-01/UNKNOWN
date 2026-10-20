export type ClassId = 'ix' | 'x' | 'xi'

export const CLASS_IDS = ['ix', 'x', 'xi'] as const

export type QuizStatus = 'waiting' | 'open' | 'active' | 'paused' | 'ended'

export type BuzzerState = 'off' | 'open' | 'locked' | 'expired'

export interface Team {
  id: string
  classId: ClassId
  name: string
  slogan: string | null
  members: string[]
  createdAt: number
}

export interface Question {
  id: string
  classId: ClassId
  order: number
  text: string
  options: string[] | null
  correctAnswer: string
  points: number
}

export interface TeamScore {
  groupName: string
  score: number
  buzzCount: number
}

export interface QuizState {
  id: string
  classId: ClassId
  code: string | null
  status: QuizStatus
  currentQuestionIndex: number
  buzzerState: BuzzerState
  buzzerWinner: string | null
  buzzerActivatedAt: number | null
  answerDeadline: number | null
  scores: Record<string, TeamScore>
  buzzedThisQuestion: Set<string>
  connectedTeams: Set<string>
}

export interface RoomSnapshot {
  classId: ClassId
  code: string | null
  status: QuizStatus
  questionNumber: number
  questionCount: number
  questionText: string | null
  questionType: string | null
  questionCodeSnippet: string | null
  questionOptions: Array<{ key: string; text: string }>
  buzzerState: BuzzerState
  buzzerWinner: string | null
  answerDeadline: number | null
  scores: TeamScore[]
  connectedCount: number
}

export interface LeaderboardEntry {
  rank: number
  teamName: string
  score: number
  buzzCount: number
}
