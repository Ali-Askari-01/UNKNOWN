import { randomBytes } from 'node:crypto'
import type { ClassId, QuizState, RoomSnapshot, Team } from '@/types'
import type { QuestionRepository, QuizRepository, TeamRepository } from '@/server/repositories/types'
import { BuzzerService } from './buzzer-service'
import { LeaderboardService } from './leaderboard-service'
import { QuestionService } from './question-service'
import { ScoringService } from './scoring-service'
import { ServiceError } from './errors'

const CODE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'

export interface JoinResult {
  state: QuizState
  team: Team
  snapshot: RoomSnapshot
}

export class QuizService {
  constructor(
    private readonly quizzes: QuizRepository,
    private readonly teams: TeamRepository,
    private readonly questions: QuestionRepository,
    private readonly scoring: ScoringService,
    private readonly buzzer: BuzzerService,
    private readonly questionService: QuestionService,
    private readonly leaderboard: LeaderboardService,
  ) {}

  getState(classId: ClassId): QuizState {
    return this.quizzes.getOrCreate(classId)
  }

  getAllStates(): QuizState[] {
    return this.quizzes.all()
  }

  prepare(classId: ClassId): QuizState {
    const existing = this.quizzes.get(classId)
    const connected = existing?.connectedTeams ?? new Set<string>()
    this.buzzer.forceClose(classId)
    const state = this.quizzes.getOrCreate(classId)
    this.buzzer.forceClose(classId)
    state.code = existing?.code ?? null
    state.status = 'waiting'
    state.currentQuestionIndex = 0
    state.buzzedThisQuestion = new Set()
    state.connectedTeams = connected
    state.scores = {}
    for (const team of this.teams.listByClass(classId)) {
      state.scores[team.name] = { groupName: team.name, score: 0, buzzCount: 0 }
    }
    this.quizzes.save(state)
    return state
  }

  open(classId: ClassId): QuizState {
    const state = this.quizzes.getOrCreate(classId)
    if (state.status === 'ended') {
      throw ServiceError.invalidState('Cannot open an ended quiz — reset it first')
    }
    if (!state.code) state.code = this.generateCode(classId)
    state.status = 'open'
    this.quizzes.save(state)
    return state
  }

  start(classId: ClassId): QuizState {
    const state = this.quizzes.getOrCreate(classId)
    if (state.status !== 'open' && state.status !== 'paused') {
      throw ServiceError.invalidState('Quiz must be open (or paused) to start')
    }
    if (!state.code) state.code = this.generateCode(classId)
    state.status = 'active'
    if (state.currentQuestionIndex < 0) state.currentQuestionIndex = 0
    this.buzzer.forceClose(classId)
    const refreshed = this.quizzes.getOrCreate(classId)
    refreshed.status = 'active'
    this.quizzes.save(refreshed)
    return refreshed
  }

  pause(classId: ClassId): QuizState {
    const state = this.quizzes.getOrCreate(classId)
    if (state.status !== 'active') {
      throw ServiceError.invalidState('Only an active quiz can be paused')
    }
    this.buzzer.forceClose(classId)
    const refreshed = this.quizzes.getOrCreate(classId)
    refreshed.status = 'paused'
    this.quizzes.save(refreshed)
    return refreshed
  }

  resume(classId: ClassId): QuizState {
    const state = this.quizzes.getOrCreate(classId)
    if (state.status !== 'paused') {
      throw ServiceError.invalidState('Only a paused quiz can be resumed')
    }
    state.status = 'active'
    this.quizzes.save(state)
    return state
  }

  finish(classId: ClassId): QuizState {
    const state = this.quizzes.getOrCreate(classId)
    this.buzzer.forceClose(classId)
    const refreshed = this.quizzes.getOrCreate(classId)
    refreshed.status = 'ended'
    this.quizzes.save(refreshed)
    return refreshed
  }

  reset(classId: ClassId): QuizState {
    return this.prepare(classId)
  }

  setCode(classId: ClassId, code: string): QuizState {
    const state = this.quizzes.getOrCreate(classId)
    state.code = code.trim().toUpperCase()
    this.quizzes.save(state)
    return state
  }

  rotateCode(classId: ClassId): QuizState {
    const state = this.quizzes.getOrCreate(classId)
    state.code = this.generateCode(classId)
    this.quizzes.save(state)
    return state
  }

  nextQuestion(classId: ClassId): QuizState {
    const state = this.quizzes.getOrCreate(classId)
    if (state.status !== 'active' && state.status !== 'paused') {
      throw ServiceError.invalidState('Quiz must be running to advance questions')
    }
    this.buzzer.forceClose(classId)
    const refreshed = this.quizzes.getOrCreate(classId)
    refreshed.currentQuestionIndex += 1
    refreshed.buzzedThisQuestion = new Set()
    this.quizzes.save(refreshed)
    return refreshed
  }

  resetQuestion(classId: ClassId): QuizState {
    const state = this.quizzes.getOrCreate(classId)
    this.buzzer.forceClose(classId)
    const refreshed = this.quizzes.getOrCreate(classId)
    refreshed.buzzedThisQuestion = new Set()
    this.quizzes.save(refreshed)
    return refreshed
  }

  validateEntry(classId: ClassId, code: string): boolean {
    const state = this.quizzes.get(classId)
    if (!state || !state.code) return false
    if (state.status !== 'open' && state.status !== 'active') return false
    return state.code === code.trim().toUpperCase()
  }

  join(classId: ClassId, code: string, groupName: string): JoinResult {
    if (!this.validateEntry(classId, code)) {
      throw ServiceError.unauthorized('Invalid quiz code or room is not joinable')
    }
    const team = this.teams.findByName(classId, groupName)
    if (!team) {
      throw ServiceError.notFound('Unknown team for this class')
    }
    this.scoring.ensureTeam(classId, team.name)
    const state = this.quizzes.getOrCreate(classId)
    this.quizzes.save(state)
    return { state, team, snapshot: this.snapshot(classId) }
  }

  addConnected(classId: ClassId, socketId: string): void {
    const state = this.quizzes.getOrCreate(classId)
    state.connectedTeams.add(socketId)
    this.quizzes.save(state)
  }

  removeConnected(classId: ClassId, socketId: string): void {
    const state = this.quizzes.get(classId)
    if (!state) return
    state.connectedTeams.delete(socketId)
    this.quizzes.save(state)
  }

  snapshot(classId: ClassId): RoomSnapshot {
    const state = this.quizzes.getOrCreate(classId)
    const questionCount = this.questionService.count(classId)
    const question =
      state.status === 'active' || state.status === 'paused'
        ? this.questionService.getByIndex(classId, state.currentQuestionIndex)
        : null
    return {
      classId: state.classId,
      code: state.code,
      status: state.status,
      questionNumber:
        state.status === 'active' || state.status === 'paused'
          ? state.currentQuestionIndex + 1
          : 0,
      questionCount,
      questionText: question?.text ?? null,
      buzzerState: state.buzzerState,
      buzzerWinner: state.buzzerWinner,
      answerDeadline: state.answerDeadline,
      scores: Object.values(state.scores).sort((a, b) => {
        if (b.score !== a.score) return b.score - a.score
        return a.groupName.localeCompare(b.groupName)
      }),
      connectedCount: state.connectedTeams.size,
    }
  }

  getLeaderboard(classId: ClassId) {
    return this.leaderboard.get(classId)
  }

  generateCode(classId: ClassId): string {
    const prefix = classId.toUpperCase()
    let code = ''
    const bytes = randomBytes(6)
    for (let i = 0; i < 6; i++) {
      code += CODE_ALPHABET[bytes[i] % CODE_ALPHABET.length]
    }
    return `${prefix}-${code}`
  }
}
