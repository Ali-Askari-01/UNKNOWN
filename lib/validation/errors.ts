export type ValidationErrorCode = 'invalid'

export class ValidationError extends Error {
  readonly code: ValidationErrorCode = 'invalid'
  readonly issues: Array<{ path: string; message: string }>

  constructor(issues: Array<{ path: string; message: string }>) {
    super(issues.map((i) => `${i.path}: ${i.message}`).join('; ') || 'Invalid input')
    this.name = 'ValidationError'
    this.issues = issues
  }
}
