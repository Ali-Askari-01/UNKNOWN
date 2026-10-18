import { groups } from '@/data/event'
import type { Repositories } from '@/server/repositories/types'
import { InMemoryTeamRepository } from '@/server/repositories/in-memory/team-repository'
import { InMemoryQuestionRepository } from '@/server/repositories/in-memory/question-repository'
import { InMemoryQuizRepository } from '@/server/repositories/in-memory/quiz-repository'
import { BuzzerService, type BuzzerServiceOptions } from '@/server/services/buzzer-service'
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

  for (const group of groups) {
    teams.seed(group.classId, group.name, group.slogan, [...group.members])
  }
  for (const classId of ['ix', 'x', 'xi'] as const) {
    quiz.prepare(classId)
  }

  return { repos, teams, questions, scoring, leaderboard, buzzer, quiz }
}

let singleton: AppContainer | null = null

export function getContainer(): AppContainer {
  if (!singleton) singleton = createContainer()
  return singleton
}
