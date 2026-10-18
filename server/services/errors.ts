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
