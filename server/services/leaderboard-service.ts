import type { ClassId, LeaderboardEntry } from '@/types'
import { ScoringService } from './scoring-service'

export class LeaderboardService {
  constructor(private readonly scoring: ScoringService) {}

  get(classId: ClassId): LeaderboardEntry[] {
    const sorted = [...this.scoring.listScores(classId)].sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score
      if (a.buzzCount !== b.buzzCount) return a.buzzCount - b.buzzCount
      return a.groupName.localeCompare(b.groupName)
    })

    let rank = 0
    let prevScore: number | null = null
    return sorted.map((entry, index) => {
      if (entry.score !== prevScore) {
        rank = index + 1
        prevScore = entry.score
      }
      return {
        rank,
        teamName: entry.groupName,
        score: entry.score,
        buzzCount: entry.buzzCount,
      }
    })
  }
}
