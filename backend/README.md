# UNKNOWN FastAPI backend

Phase 1 foundation for the FastAPI + SQL Server migration.

## Local development

From the repository root:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -e "backend[dev]"
$env:PYTHONPATH = "backend"
backend/.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

The default local database is SQLite for foundation tests. Production/staging should set:

```text
BACKEND_DATABASE_URL=mssql+aioodbc://user:password@server:1433/database?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=no
```

The SQL Server ODBC driver must be installed on the host. Do not commit real connection strings.

## Local SQL Server Express setup

The local Express instance is configured as `SQLEXPRESS` and uses Windows authentication
over Shared Memory. The checked-out local configuration is stored in `backend/.env` (ignored
from Git). After applying the Alembic baseline, seed the reusable event foundation with:

```powershell
$env:PYTHONPATH = "."
python -m alembic upgrade head
python scripts/seed_demo_data.py
```

## Health endpoints

- `GET /health/live` checks process liveness only.
- `GET /health/ready` checks required dependencies, including the database.
- `GET /docs` exposes the local OpenAPI UI.
