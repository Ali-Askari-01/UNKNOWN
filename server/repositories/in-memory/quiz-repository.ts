import { randomUUID } from 'node:crypto'
import type { ClassId, QuizState } from '@/types'
import type { QuizRepository } from '../types'

export function createQuizState(classId: ClassId): QuizState {
  return {
    id: randomUUID(),
    classId,
    code: null,
    status: 'waiting',
    currentQuestionIndex: 0,
    buzzerState: 'off',
    buzzerWinner: null,
    buzzerActivatedAt: null,
    answerDeadline: null,
    scores: {},
    buzzedThisQuestion: new Set(),
    connectedTeams: new Set(),
  }
}

export class InMemoryQuizRepository implements QuizRepository {
  private quizzes = new Map<ClassId, QuizState>()

  get(classId: ClassId): QuizState | null {
    return this.quizzes.get(classId) ?? null
  }

  getOrCreate(classId: ClassId): QuizState {
    let state = this.quizzes.get(classId)
    if (!state) {
      state = createQuizState(classId)
      this.quizzes.set(classId, state)
    }
    return state
  }

  all(): QuizState[] {
    return Array.from(this.quizzes.values())
  }

  save(state: QuizState): void {
    this.quizzes.set(state.classId, state)
  }

  clear(): void {
    this.quizzes.clear()
  }
}
