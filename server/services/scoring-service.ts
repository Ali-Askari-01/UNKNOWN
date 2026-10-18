import type { ClassId, TeamScore } from '@/types'
import type { QuizRepository } from '@/server/repositories/types'
import { ServiceError } from './errors'

export class ScoringService {
  constructor(private readonly quizzes: QuizRepository) {}

  ensureTeam(classId: ClassId, groupName: string): TeamScore {
    const state = this.quizzes.getOrCreate(classId)
    let entry = state.scores[groupName]
    if (!entry) {
      entry = { groupName, score: 0, buzzCount: 0 }
      state.scores[groupName] = entry
      this.quizzes.save(state)
    }
    return entry
  }

  removeTeam(classId: ClassId, groupName: string): void {
    const state = this.quizzes.getOrCreate(classId)
    delete state.scores[groupName]
    this.quizzes.save(state)
  }

  renameTeam(classId: ClassId, oldName: string, newName: string): void {
    const state = this.quizzes.getOrCreate(classId)
    const entry = state.scores[oldName]
    if (!entry) return
    delete state.scores[oldName]
    entry.groupName = newName
    state.scores[newName] = entry
    if (state.buzzerWinner === oldName) state.buzzerWinner = newName
    if (state.buzzedThisQuestion.has(oldName)) {
      state.buzzedThisQuestion.delete(oldName)
      state.buzzedThisQuestion.add(newName)
    }
    this.quizzes.save(state)
  }

  award(classId: ClassId, groupName: string, points: number): TeamScore {
    const entry = this.ensureTeam(classId, groupName)
    entry.score += points
    const state = this.quizzes.getOrCreate(classId)
    this.quizzes.save(state)
    return entry
  }

  deduct(classId: ClassId, groupName: string, amount: number): TeamScore {
    const entry = this.ensureTeam(classId, groupName)
    entry.score -= amount
    const state = this.quizzes.getOrCreate(classId)
    this.quizzes.save(state)
    return entry
  }

  adjust(classId: ClassId, groupName: string, delta: number): TeamScore {
    const entry = this.ensureTeam(classId, groupName)
    entry.score += delta
    const state = this.quizzes.getOrCreate(classId)
    this.quizzes.save(state)
    return entry
  }

  incrementBuzz(classId: ClassId, groupName: string): TeamScore {
    const entry = this.ensureTeam(classId, groupName)
    entry.buzzCount += 1
    const state = this.quizzes.getOrCreate(classId)
    this.quizzes.save(state)
    return entry
  }

  listScores(classId: ClassId): TeamScore[] {
    const state = this.quizzes.get(classId)
    if (!state) return []
    return Object.values(state.scores)
  }

  requireTeam(classId: ClassId, groupName: string): TeamScore {
    const entry = this.listScores(classId).find(
      (s) => s.groupName.trim().toLowerCase() === groupName.trim().toLowerCase(),
    )
    if (!entry) {
      throw ServiceError.notFound(`Team "${groupName}" is not registered for this class`)
    }
    return entry
  }
}
