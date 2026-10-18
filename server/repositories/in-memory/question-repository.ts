import type { ClassId, Question } from '@/types'
import type { QuestionRepository } from '../types'

export class InMemoryQuestionRepository implements QuestionRepository {
  private questions = new Map<string, Question>()

  listByClass(classId: ClassId): Question[] {
    return Array.from(this.questions.values())
      .filter((q) => q.classId === classId)
      .sort((a, b) => a.order - b.order)
  }

  findById(id: string): Question | null {
    return this.questions.get(id) ?? null
  }

  nextOrder(classId: ClassId): number {
    const list = this.listByClass(classId)
    if (list.length === 0) return 0
    return list[list.length - 1].order + 1
  }

  save(question: Question): void {
    this.questions.set(question.id, question)
  }

  delete(id: string): boolean {
    return this.questions.delete(id)
  }

  clear(): void {
    this.questions.clear()
  }
}
