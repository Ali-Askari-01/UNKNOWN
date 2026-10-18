import type { ClassId, Team } from '@/types'
import type { TeamRepository } from '../types'

function normalize(name: string): string {
  return name.trim().toLowerCase().replace(/\s+/g, ' ')
}

export class InMemoryTeamRepository implements TeamRepository {
  private teams = new Map<string, Team>()

  listByClass(classId: ClassId): Team[] {
    return Array.from(this.teams.values())
      .filter((t) => t.classId === classId)
      .sort((a, b) => a.createdAt - b.createdAt)
  }

  listAll(): Team[] {
    return Array.from(this.teams.values()).sort((a, b) => a.createdAt - b.createdAt)
  }

  findById(id: string): Team | null {
    return this.teams.get(id) ?? null
  }

  findByName(classId: ClassId, name: string): Team | null {
    const key = normalize(name)
    for (const team of this.teams.values()) {
      if (team.classId === classId && normalize(team.name) === key) return team
    }
    return null
  }

  save(team: Team): void {
    this.teams.set(team.id, team)
  }

  delete(id: string): boolean {
    return this.teams.delete(id)
  }

  clear(): void {
    this.teams.clear()
  }
}
