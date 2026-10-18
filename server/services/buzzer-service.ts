import type { ClassId, QuizState } from '@/types'
import type { QuizRepository, TeamRepository } from '@/server/repositories/types'
import { ServiceError } from './errors'
import { ScoringService } from './scoring-service'

export interface BuzzerServiceOptions {
  answerWindowMs?: number
  now?: () => number
  setTimer?: (fn: () => void, ms: number) => ReturnType<typeof setTimeout>
  clearTimer?: (handle: ReturnType<typeof setTimeout>) => void
  onExpire?: (classId: ClassId, state: QuizState) => void
}

export class BuzzerService {
  private readonly timers = new Map<ClassId, ReturnType<typeof setTimeout>>()
  private readonly answerWindowMs: number
  private readonly now: () => number
  private readonly setTimer: (fn: () => void, ms: number) => ReturnType<typeof setTimeout>
  private readonly clearTimer: (handle: ReturnType<typeof setTimeout>) => void
  private onExpire: ((classId: ClassId, state: QuizState) => void) | undefined

  constructor(
    private readonly quizzes: QuizRepository,
    private readonly teams: TeamRepository,
    private readonly scoring: ScoringService,
    options: BuzzerServiceOptions = {},
  ) {
    this.answerWindowMs = options.answerWindowMs ?? 20_000
    this.now = options.now ?? Date.now
    this.setTimer = options.setTimer ?? ((fn, ms) => setTimeout(fn, ms))
    this.clearTimer = options.clearTimer ?? ((handle) => clearTimeout(handle))
    this.onExpire = options.onExpire
  }

  setExpireHandler(handler: (classId: ClassId, state: QuizState) => void): void {
    this.onExpire = handler
  }

  activate(classId: ClassId): QuizState {
    const state = this.quizzes.getOrCreate(classId)
    if (state.status !== 'active') {
      throw ServiceError.invalidState('Quiz must be active to open the buzzer')
    }
    if (state.buzzerState === 'locked') {
      throw ServiceError.invalidState('Buzzer is locked while a team is answering')
    }
    this.cancelTimer(classId)
    state.buzzerState = 'open'
    state.buzzerWinner = null
    state.buzzerActivatedAt = this.now()
    state.answerDeadline = null
    state.buzzedThisQuestion = new Set()
    this.quizzes.save(state)
    return state
  }

  disable(classId: ClassId): QuizState {
    const state = this.quizzes.getOrCreate(classId)
    this.cancelTimer(classId)
    state.buzzerState = 'off'
    state.buzzerWinner = null
    state.buzzerActivatedAt = null
    state.answerDeadline = null
    this.quizzes.save(state)
    return state
  }

  press(classId: ClassId, groupName: string): QuizState {
    const state = this.quizzes.getOrCreate(classId)
    if (state.status !== 'active') {
      throw ServiceError.invalidState('Quiz is not active')
    }
    if (state.buzzerState !== 'open') {
      throw ServiceError.invalidState('Buzzer is not open')
    }
    if (state.buzzedThisQuestion.has(groupName)) {
      throw ServiceError.invalidState('Team has already buzzed this question')
    }
    const team = this.teams.findByName(classId, groupName)
    if (!team) {
      throw ServiceError.unauthorized('Unknown team for this class')
    }

    state.buzzerState = 'locked'
    state.buzzerWinner = team.name
    state.buzzedThisQuestion.add(team.name)
    state.buzzerActivatedAt = this.now()
    state.answerDeadline = this.now() + this.answerWindowMs
    this.scoring.incrementBuzz(classId, team.name)
    this.quizzes.save(state)

    this.cancelTimer(classId)
    const handle = this.setTimer(() => this.expire(classId), this.answerWindowMs)
    this.timers.set(classId, handle)

    return state
  }

  expire(classId: ClassId): QuizState {
    const state = this.quizzes.getOrCreate(classId)
    this.cancelTimer(classId)
    if (state.buzzerState === 'locked' || state.buzzerState === 'open') {
      state.buzzerState = 'expired'
      state.answerDeadline = null
      this.quizzes.save(state)
      this.onExpire?.(classId, state)
    }
    return state
  }

  reopen(classId: ClassId): QuizState {
    const state = this.quizzes.getOrCreate(classId)
    if (state.status !== 'active') {
      throw ServiceError.invalidState('Quiz must be active to reopen the buzzer')
    }
    if (state.buzzerState === 'locked') {
      throw ServiceError.invalidState('Cannot reopen while a team is answering')
    }
    this.cancelTimer(classId)
    state.buzzerState = 'open'
    state.buzzerWinner = null
    state.buzzerActivatedAt = this.now()
    state.answerDeadline = null
    this.quizzes.save(state)
    return state
  }

  forceClose(classId: ClassId): void {
    const state = this.quizzes.getOrCreate(classId)
    this.cancelTimer(classId)
    state.buzzerState = 'off'
    state.buzzerWinner = null
    state.buzzerActivatedAt = null
    state.answerDeadline = null
    this.quizzes.save(state)
  }

  resolveAnswer(classId: ClassId): void {
    this.cancelTimer(classId)
    const state = this.quizzes.getOrCreate(classId)
    state.buzzerState = 'off'
    state.buzzerWinner = null
    state.buzzerActivatedAt = null
    state.answerDeadline = null
    this.quizzes.save(state)
  }

  currentWinner(classId: ClassId): string | null {
    return this.quizzes.get(classId)?.buzzerWinner ?? null
  }

  dispose(): void {
    for (const handle of this.timers.values()) this.clearTimer(handle)
    this.timers.clear()
  }

  private cancelTimer(classId: ClassId): void {
    const handle = this.timers.get(classId)
    if (handle !== undefined) {
      this.clearTimer(handle)
      this.timers.delete(classId)
    }
  }
}
