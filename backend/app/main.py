from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_error_handler,
)
from app.core.logging import configure_logging
from app.core.middleware import (
    CookieOriginMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.observability import RequestLoggingMiddleware
from app.db.session import dispose_engine, initialize_local_database
from app.realtime.manager import connection_manager


@asynccontextmanager
async def lifespan(_: FastAPI):
    await initialize_local_database()
    await connection_manager.start()
    yield
    await connection_manager.stop()
    await dispose_engine()


settings = get_settings()
configure_logging(settings.log_level)
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CookieOriginMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Idempotency-Key"],
)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.include_router(api_router)


@app.get("/", include_in_schema=False)
async def root(request: Request) -> dict[str, str]:
    return {"name": settings.app_name, "environment": settings.environment, "requestId": request.state.request_id}
