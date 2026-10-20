"""Checks for the tables and columns owned by the current FastAPI application."""

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.base import Base


async def find_schema_contract_errors(engine: AsyncEngine) -> list[str]:
    """Return missing FastAPI-owned schema objects without claiming legacy objects as owned."""
    actual_schema = None if engine.url.drivername.startswith("sqlite") else "competition"

    def inspect_schema(connection) -> list[str]:
        inspector = inspect(connection)
        actual_tables = set(inspector.get_table_names(schema=actual_schema))
        errors: list[str] = []
        for table in Base.metadata.tables.values():
            if table.schema != "competition":
                continue
            if table.name not in actual_tables:
                errors.append(f"missing table competition.{table.name}")
                continue
            actual_columns = {column["name"] for column in inspector.get_columns(table.name, schema=actual_schema)}
            for column in table.columns:
                if column.name not in actual_columns:
                    errors.append(f"missing column competition.{table.name}.{column.name}")
        return errors

    async with engine.connect() as connection:
        return await connection.run_sync(inspect_schema)
