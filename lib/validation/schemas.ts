import { z } from 'zod'
import { ValidationError } from './errors'

export const classIdSchema = z.enum(['ix', 'x', 'xi'])

export const teamNameSchema = z
  .string()
  .trim()
  .min(2, 'Team name must be at least 2 characters')
  .max(40, 'Team name must be at most 40 characters')

export const memberNameSchema = z
  .string()
  .trim()
  .min(1, 'Member name cannot be empty')
  .max(40, 'Member name must be at most 40 characters')

export const createTeamSchema = z.object({
  classId: classIdSchema,
  name: teamNameSchema,
  slogan: z.string().trim().max(120).nullish(),
  members: z.array(memberNameSchema).min(1).max(10),
})

export const updateTeamSchema = z
  .object({
    name: teamNameSchema.optional(),
    slogan: z.string().trim().max(120).nullish(),
    members: z.array(memberNameSchema).min(1).max(10).optional(),
  })
  .refine((v) => v.name !== undefined || v.slogan !== undefined || v.members !== undefined, {
    message: 'At least one field must be provided',
  })

export const createQuestionSchema = z.object({
  classId: classIdSchema,
  text: z.string().trim().min(5).max(500),
  options: z.array(z.string().trim().min(1).max(200)).min(2).max(6).nullish(),
  correctAnswer: z.string().trim().min(1).max(200),
  points: z.number().int().min(1).max(100).optional(),
})

export const updateQuestionSchema = z
  .object({
    text: z.string().trim().min(5).max(500).optional(),
    options: z.array(z.string().trim().min(1).max(200)).min(2).max(6).nullish(),
    correctAnswer: z.string().trim().min(1).max(200).optional(),
    points: z.number().int().min(1).max(100).optional(),
    order: z.number().int().min(0).max(999).optional(),
  })
  .refine(
    (v) =>
      v.text !== undefined ||
      v.options !== undefined ||
      v.correctAnswer !== undefined ||
      v.points !== undefined ||
      v.order !== undefined,
    { message: 'At least one field must be provided' },
  )

export const quizIdSchema = z.string().uuid()

export const prepareQuizSchema = z.object({
  classId: classIdSchema,
})

export const quizIdParamSchema = z.object({
  quizId: quizIdSchema,
})

export const classIdParamSchema = z.object({
  classId: classIdSchema,
})

export const teamIdParamSchema = z.object({
  teamId: z.string().uuid(),
})

export const questionIdParamSchema = z.object({
  questionId: z.string().uuid(),
})

export const setCodeSchema = z.object({
  classId: classIdSchema,
  code: z
    .string()
    .trim()
    .min(4)
    .max(16)
    .regex(/^[A-Za-z0-9-]+$/, 'Code may only contain letters, numbers, and hyphens'),
})

export const pointsSchema = z.number().int().min(1).max(100)

export const markCorrectSchema = z.object({
  classId: classIdSchema,
  points: pointsSchema.optional(),
})

export const markIncorrectSchema = z.object({
  classId: classIdSchema,
  deduct: z.number().int().min(0).max(100),
})

export const adjustScoreSchema = z
  .object({
    classId: classIdSchema,
    groupName: teamNameSchema,
    delta: z.number().int().min(-100).max(100),
  })
  .refine((v) => v.delta !== 0, { message: 'Delta cannot be zero' })

export const classOnlySchema = z.object({
  classId: classIdSchema,
})

export const joinSchema = z.object({
  classId: classIdSchema,
  code: z.string().trim().min(3).max(16),
  groupName: z.string().trim().min(2).max(60),
})

export const answerSchema = z.object({
  answer: z.string().trim().min(1).max(500),
})

export const loginSchema = z.object({
  username: z.string().min(1).max(64),
  password: z.string().min(1).max(128),
})

export const leaderboardQuerySchema = z.object({
  classId: classIdSchema,
})

export const teamsQuerySchema = z.object({
  classId: classIdSchema,
})

export const questionsQuerySchema = z.object({
  classId: classIdSchema,
})

export function parseOrThrow<T>(schema: z.ZodType<T>, input: unknown): T {
  const result = schema.safeParse(input)
  if (!result.success) {
    throw new ValidationError(
      result.error.issues.map((issue) => ({
        path: issue.path.join('.') || '(root)',
        message: issue.message,
      })),
    )
  }
  return result.data
}
