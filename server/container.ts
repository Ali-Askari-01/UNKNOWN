import { groups } from '@/data/event'
import type { Repositories } from '@/server/repositories/types'
import { InMemoryTeamRepository } from '@/server/repositories/in-memory/team-repository'
import { InMemoryQuestionRepository } from '@/server/repositories/in-memory/question-repository'
import { InMemoryQuizRepository } from '@/server/repositories/in-memory/quiz-repository'
import { BuzzerService, type BuzzerServiceOptions } from '@/server/services/buzzer-service'
import { AnswerService } from '@/server/services/answer-service'
import { LeaderboardService } from '@/server/services/leaderboard-service'
import { QuestionService } from '@/server/services/question-service'
import { QuizService } from '@/server/services/quiz-service'
import { ScoringService } from '@/server/services/scoring-service'
import { TeamService } from '@/server/services/team-service'

export interface AppContainer {
  repos: Repositories
  teams: TeamService
  questions: QuestionService
  scoring: ScoringService
  leaderboard: LeaderboardService
  buzzer: BuzzerService
  quiz: QuizService
  answer: AnswerService
}

export function createContainer(buzzerOptions: BuzzerServiceOptions = {}): AppContainer {
  const repos: Repositories = {
    teams: new InMemoryTeamRepository(),
    questions: new InMemoryQuestionRepository(),
    quizzes: new InMemoryQuizRepository(),
  }

  const scoring = new ScoringService(repos.quizzes)
  const teams = new TeamService(repos.teams, scoring)
  const questions = new QuestionService(repos.questions)
  const leaderboard = new LeaderboardService(scoring)
  const buzzer = new BuzzerService(repos.quizzes, repos.teams, scoring, buzzerOptions)
  const quiz = new QuizService(
    repos.quizzes,
    repos.teams,
    repos.questions,
    scoring,
    buzzer,
    questions,
    leaderboard,
  )

  const answer = new AnswerService(repos.quizzes, questions, scoring, buzzer)

  for (const group of groups) {
    teams.seed(group.classId, group.name, group.slogan, [...group.members])
  }
  for (const classId of ['ix', 'x', 'xi'] as const) {
    quiz.prepare(classId)
  }

  return { repos, teams, questions, scoring, leaderboard, buzzer, quiz, answer }
}

/**
 * The singleton is stored on globalThis: server.ts (tsx module graph) and the
 * Next.js route handlers (webpack/turbopack bundle) each evaluate this module
 * separately, so a module-level variable would produce two containers with
 * divergent state. Symbol.for gives both graphs the same registry key.
 */
const CONTAINER_KEY = Symbol.for('UNKNOWN.quiz.container')

interface ContainerGlobal {
  [CONTAINER_KEY]?: AppContainer
}

export function getContainer(): AppContainer {
  const g = globalThis as ContainerGlobal
  if (!g[CONTAINER_KEY]) g[CONTAINER_KEY] = createContainer()
  return g[CONTAINER_KEY]!
}
