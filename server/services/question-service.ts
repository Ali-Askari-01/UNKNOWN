import { randomUUID } from 'node:crypto'
import type { ClassId, Question } from '@/types'
import type { QuestionRepository } from '@/server/repositories/types'
import { ServiceError } from './errors'

export interface CreateQuestionInput {
  classId: ClassId
  text: string
  options?: string[] | null
  correctAnswer: string
  points?: number
}

export interface UpdateQuestionInput {
  text?: string
  options?: string[] | null
  correctAnswer?: string
  points?: number
  order?: number
}

export class QuestionService {
  constructor(private readonly questions: QuestionRepository) {}

  list(classId: ClassId): Question[] {
    return this.questions.listByClass(classId)
  }

  getById(id: string): Question {
    const question = this.questions.findById(id)
    if (!question) throw ServiceError.notFound('Question not found')
    return question
  }

  create(input: CreateQuestionInput): Question {
    const question: Question = {
      id: randomUUID(),
      classId: input.classId,
      order: this.questions.nextOrder(input.classId),
      text: input.text,
      options: input.options ?? null,
      correctAnswer: input.correctAnswer,
      points: input.points ?? 10,
    }
    this.questions.save(question)
    return question
  }

  update(id: string, patch: UpdateQuestionInput): Question {
    const question = this.getById(id)
    if (patch.text !== undefined) question.text = patch.text
    if (patch.options !== undefined) question.options = patch.options
    if (patch.correctAnswer !== undefined) question.correctAnswer = patch.correctAnswer
    if (patch.points !== undefined) question.points = patch.points
    if (patch.order !== undefined && patch.order !== question.order) {
      this.reorder(question, patch.order)
    }
    this.questions.save(question)
    return question
  }

  remove(id: string): void {
    const question = this.getById(id)
    this.questions.delete(id)
    this.normalizeOrder(question.classId)
  }

  getByIndex(classId: ClassId, index: number): Question | null {
    const list = this.questions.listByClass(classId)
    if (index < 0 || index >= list.length) return null
    return list[index]
  }

  count(classId: ClassId): number {
    return this.questions.listByClass(classId).length
  }

  private reorder(question: Question, targetOrder: number): void {
    const list = this.questions.listByClass(question.classId).filter((q) => q.id !== question.id)
    question.order = targetOrder
    const insertAt = list.findIndex((q) => q.order >= targetOrder)
    if (insertAt === -1) list.push(question)
    else list.splice(insertAt, 0, question)
    list.forEach((q, i) => {
      q.order = i
      this.questions.save(q)
    })
  }

  private normalizeOrder(classId: ClassId): void {
    this.questions.listByClass(classId).forEach((q, i) => {
      q.order = i
      this.questions.save(q)
    })
  }
}
