import type { ClassId } from '@/types'
import type { QuizRepository } from '@/server/repositories/types'
import { BuzzerService } from './buzzer-service'
import { QuestionService } from './question-service'
import { ScoringService } from './scoring-service'
import { ServiceError } from './errors'

export interface AnswerOutcome {
  correct: boolean
  pointsAwarded: number
  teamName: string
}

function normalize(text: string): string {
  return text.trim().toLowerCase().replace(/\s+/g, ' ')
}

export class AnswerService {
  constructor(
    private readonly quizzes: QuizRepository,
    private readonly questions: QuestionService,
    private readonly scoring: ScoringService,
    private readonly buzzer: BuzzerService,
    private readonly now: () => number = Date.now,
  ) {}

  submitAnswer(classId: ClassId, groupName: string, answer: string): AnswerOutcome {
    const state = this.quizzes.get(classId)
    if (!state || state.status !== 'active') {
      throw ServiceError.invalidState('Quiz is not active')
    }
    if (state.buzzerState !== 'locked') {
      throw ServiceError.invalidState('No open answer window')
    }
    if (state.buzzerWinner !== groupName) {
      throw ServiceError.invalidState("It is not this team's turn to answer")
    }
    if (state.answerDeadline !== null && this.now() > state.answerDeadline) {
      throw ServiceError.invalidState('Answer window has expired')
    }
    const question = this.questions.getByIndex(classId, state.currentQuestionIndex)
    if (!question) {
      throw ServiceError.invalidState('No active question to answer')
    }

    const correct = normalize(answer) === normalize(question.correctAnswer)
    const pointsAwarded = correct ? question.points : 0
    if (correct) this.scoring.award(classId, groupName, pointsAwarded)
    this.buzzer.resolveAnswer(classId)

    return { correct, pointsAwarded, teamName: groupName }
  }
}
