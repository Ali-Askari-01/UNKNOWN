# Free deployment

The free pilot topology keeps the existing SQL Server and Socket.IO architecture intact:

```text
Render unknown-web  ->  Render unknown-api  ->  Azure SQL Database free offer
```

Both Render services use the Free plan. The frontend remains a long-running Node service because
the quiz currently uses Socket.IO. The backend image installs Microsoft's ODBC Driver 18 and runs
Alembic migrations before starting FastAPI.

## Required secrets

Set these values in Render; never commit them:

- `FASTAPI_INTERNAL_URL`: the internal or public URL of `unknown-api`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD_HASH`
- `CORS_ORIGIN`: the public URL of `unknown-web`
- `BACKEND_DATABASE_URL`: Azure SQL SQLAlchemy `mssql+aioodbc` URL
- `BACKEND_CORS_ORIGINS`: the public URL of `unknown-web`
- `BACKEND_TRUSTED_HOSTS`: Render hostnames and the custom domain, comma-separated
- `BACKEND_ADMIN_USERNAME`
- `BACKEND_ADMIN_PASSWORD`

## Known free-tier limitations

- Render free services sleep after inactivity and may take about a minute to wake.
- Render free filesystems are ephemeral; do not store uploaded media locally.
- Azure SQL free offer has monthly compute/storage limits and no SLA.
- A live competition should be load-tested and monitored before relying on this topology.
