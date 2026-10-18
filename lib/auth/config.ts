export class AuthConfigError extends Error {
  readonly code = 'auth_config'
  constructor(message: string) {
    super(message)
    this.name = 'AuthConfigError'
  }
}

const DEV_FALLBACK_SECRET = 'dev-secret-change-me-in-production'

export function isProduction(): boolean {
  return process.env.NODE_ENV === 'production'
}

export function getSessionSecret(): string {
  const secret = process.env.SESSION_SECRET?.trim()
  if (secret) return secret
  if (isProduction()) {
    throw new AuthConfigError(
      'SESSION_SECRET must be set in production. Refusing to use the development fallback.',
    )
  }
  return DEV_FALLBACK_SECRET
}

export function assertSessionSecretConfigured(): void {
  if (isProduction() && !process.env.SESSION_SECRET?.trim()) {
    throw new AuthConfigError('SESSION_SECRET must be set in production.')
  }
}

export function getAdminCredentials(): { username: string; passwordHash: string } {
  return {
    username: process.env.ADMIN_USERNAME ?? 'admin',
    passwordHash: decodePasswordHash(process.env.ADMIN_PASSWORD_HASH ?? ''),
  }
}

function decodePasswordHash(raw: string): string {
  const trimmed = raw.trim()
  if (trimmed.startsWith('base64:')) {
    return Buffer.from(trimmed.slice('base64:'.length), 'base64').toString('utf8')
  }
  return trimmed
}

export function adminPasswordConfigured(): boolean {
  return getAdminCredentials().passwordHash.length > 0
}
