from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.audit import router as audit_router
from app.api.v1.questions import router as questions_router
from app.api.v1.quiz_blueprints import router as quiz_blueprints_router
from app.api.v1.quiz_sessions import router as quiz_sessions_router
from app.api.v1.participation import router as participation_router
from app.api.v1.realtime import router as realtime_router
from app.api.v1.system import router as system_router
from app.api.v1.teams import router as teams_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(audit_router)
api_router.include_router(questions_router)
api_router.include_router(quiz_blueprints_router)
api_router.include_router(quiz_sessions_router)
api_router.include_router(participation_router)
api_router.include_router(realtime_router)
api_router.include_router(system_router)
api_router.include_router(teams_router)
