export type ServiceErrorCode =
  | 'invalid'
  | 'not_found'
  | 'conflict'
  | 'forbidden'
  | 'unauthorized'
  | 'invalid_state'

export class ServiceError extends Error {
  readonly code: ServiceErrorCode

  constructor(code: ServiceErrorCode, message: string) {
    super(message)
    this.name = 'ServiceError'
    this.code = code
  }

  static notFound(message: string): ServiceError {
    return new ServiceError('not_found', message)
  }

  static conflict(message: string): ServiceError {
    return new ServiceError('conflict', message)
  }

  static invalidState(message: string): ServiceError {
    return new ServiceError('invalid_state', message)
  }

  static forbidden(message = 'Forbidden'): ServiceError {
    return new ServiceError('forbidden', message)
  }

  static unauthorized(message = 'Unauthorized'): ServiceError {
    return new ServiceError('unauthorized', message)
  }
}

const SERVICE_ERROR_CODES: readonly ServiceErrorCode[] = [
  'invalid',
  'not_found',
  'conflict',
  'forbidden',
  'unauthorized',
  'invalid_state',
]

/**
 * Graph-safe ServiceError check.
 *
 * server.ts runs under tsx while Next API routes are bundled separately, so
 * each graph has its own ServiceError class and `instanceof` fails across the
 * boundary. Errors keep `name`/`code` from construction, so match on those.
 */
export function isServiceError(error: unknown): error is ServiceError {
  if (error instanceof ServiceError) return true
  if (!(error instanceof Error)) return false
  if (error.name !== 'ServiceError') return false
  return SERVICE_ERROR_CODES.includes((error as ServiceError).code)
}
