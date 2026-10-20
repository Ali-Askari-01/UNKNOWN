# FastAPI Security Requirements

## Required controls

- TLS at the ingress; secure cookies and trusted proxy configuration.
- Strict CORS allowlist for the deployed frontend origin.
- Rate limits on login, join, buzzer, answer, imports, and media upload endpoints. Login, join,
  buzzer, and answer limits use SQL-backed sliding windows with locked per-bucket coordination, so
  multiple API workers observe the same abuse window.
- Argon2id/bcrypt password hashing with a rotation/recovery procedure.
- Request size limits and MIME/content validation for uploads.
- Authorization checks in services, not only router or frontend gates.
- SQL injection prevention through SQLAlchemy parameters and reviewed raw SQL only.
- Redaction of tokens, passwords, answer keys, connection strings, and private student fields from logs.
- Security headers, CSRF protection where cookie-authenticated state-changing routes require it, and safe error messages.
- Dependency scanning, secret scanning, static typing/linting, and patch management in CI.

## Threat scenarios

| Threat | Control |
|---|---|
| Student impersonates another team | Team-scoped token plus server ownership check |
| Student reads answer key | Separate response schemas and service authorization |
| Double buzzer winner | Database transaction plus unique winner constraint |
| Replayed answer request | Idempotency key and final-answer uniqueness |
| Admin brute force | Rate limit, audit, optional lockout/MFA |
| Malicious media | MIME/size checks, malware scanning, private object storage, moderation |
| Session theft | HTTPS, HttpOnly/SameSite cookies, short TTL, revocation |
| Data leak in backups | Encryption, restricted keys, restore access controls |
