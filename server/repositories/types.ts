import type { ClassId, Question, QuizState, Team } from '@/types'

export interface TeamRepository {
  listByClass(classId: ClassId): Team[]
  listAll(): Team[]
  findById(id: string): Team | null
  findByName(classId: ClassId, name: string): Team | null
  save(team: Team): void
  delete(id: string): boolean
  clear(): void
}

export interface QuestionRepository {
  listByClass(classId: ClassId): Question[]
  findById(id: string): Question | null
  nextOrder(classId: ClassId): number
  save(question: Question): void
  delete(id: string): boolean
  clear(): void
}

export interface QuizRepository {
  get(classId: ClassId): QuizState | null
  getOrCreate(classId: ClassId): QuizState
  all(): QuizState[]
  save(state: QuizState): void
  clear(): void
}

export interface Repositories {
  teams: TeamRepository
  questions: QuestionRepository
  quizzes: QuizRepository
}
