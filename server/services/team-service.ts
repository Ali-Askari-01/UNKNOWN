import { randomUUID } from 'node:crypto'
import type { ClassId, Team } from '@/types'
import type { TeamRepository } from '@/server/repositories/types'
import { ServiceError } from './errors'
import { ScoringService } from './scoring-service'

export interface CreateTeamInput {
  classId: ClassId
  name: string
  slogan?: string | null
  members: string[]
}

export interface UpdateTeamInput {
  name?: string
  slogan?: string | null
  members?: string[]
}

export class TeamService {
  constructor(
    private readonly teams: TeamRepository,
    private readonly scoring: ScoringService,
  ) {}

  list(classId: ClassId): Team[] {
    return this.teams.listByClass(classId)
  }

  listAll(): Team[] {
    return this.teams.listAll()
  }

  getById(id: string): Team {
    const team = this.teams.findById(id)
    if (!team) throw ServiceError.notFound('Team not found')
    return team
  }

  create(input: CreateTeamInput): Team {
    if (this.teams.findByName(input.classId, input.name)) {
      throw ServiceError.conflict(`A team named "${input.name}" already exists in this class`)
    }
    const team: Team = {
      id: randomUUID(),
      classId: input.classId,
      name: input.name,
      slogan: input.slogan ?? null,
      members: [...input.members],
      createdAt: Date.now(),
    }
    this.teams.save(team)
    this.scoring.ensureTeam(team.classId, team.name)
    return team
  }

  update(id: string, patch: UpdateTeamInput): Team {
    const team = this.getById(id)
    if (patch.name !== undefined && patch.name !== team.name) {
      const clash = this.teams.findByName(team.classId, patch.name)
      if (clash && clash.id !== team.id) {
        throw ServiceError.conflict(`A team named "${patch.name}" already exists in this class`)
      }
      this.scoring.renameTeam(team.classId, team.name, patch.name)
      team.name = patch.name
    }
    if (patch.slogan !== undefined) team.slogan = patch.slogan
    if (patch.members !== undefined) team.members = [...patch.members]
    this.teams.save(team)
    return team
  }

  remove(id: string): void {
    const team = this.getById(id)
    this.teams.delete(id)
    this.scoring.removeTeam(team.classId, team.name)
  }

  seed(classId: ClassId, name: string, slogan: string | null, members: string[]): Team {
    const existing = this.teams.findByName(classId, name)
    if (existing) return existing
    const team: Team = {
      id: randomUUID(),
      classId,
      name,
      slogan,
      members: [...members],
      createdAt: Date.now(),
    }
    this.teams.save(team)
    this.scoring.ensureTeam(classId, name)
    return team
  }
}
