from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.core.auth import require_admin
from app.core.audit import add_audit
from app.db.models import ClassTrack, QuizBlueprint, QuizDistribution, Round
from app.db.session import get_db_session
from app.schemas.quiz import QuizBlueprintCreate, QuizBlueprintResponse, QuizDistributionResponse

router = APIRouter(prefix="/api/v1", tags=["quiz-blueprints"])


def to_response(blueprint: QuizBlueprint) -> QuizBlueprintResponse:
    return QuizBlueprintResponse(
        id=blueprint.id,
        round_id=blueprint.round_id,
        class_track_id=blueprint.class_track_id,
        name=blueprint.name,
        question_count=blueprint.question_count,
        seconds_per_question=blueprint.seconds_per_question,
        buzzer_enabled=blueprint.buzzer_enabled,
        is_active=blueprint.is_active,
        distributions=[
            QuizDistributionResponse(id=item.id, question_type=item.question_type, difficulty=item.difficulty, quantity=item.quantity)
            for item in blueprint.distributions
        ],
    )


def blueprint_query():
    return select(QuizBlueprint).options(selectinload(QuizBlueprint.distributions)).order_by(QuizBlueprint.name)


@router.get("/quiz-blueprints", response_model=list[QuizBlueprintResponse])
async def list_quiz_blueprints(session: AsyncSession = Depends(get_db_session)) -> list[QuizBlueprintResponse]:
    blueprints = (await session.scalars(blueprint_query().where(QuizBlueprint.is_active == True))).unique().all()
    return [to_response(item) for item in blueprints]


@router.get("/admin/quiz-blueprints", response_model=list[QuizBlueprintResponse])
async def list_admin_quiz_blueprints(session: AsyncSession = Depends(get_db_session), _: dict[str, object] = Depends(require_admin)) -> list[QuizBlueprintResponse]:
    blueprints = (await session.scalars(blueprint_query())).unique().all()
    return [to_response(item) for item in blueprints]


@router.post("/admin/quiz-blueprints", response_model=QuizBlueprintResponse, status_code=201)
async def create_quiz_blueprint(payload: QuizBlueprintCreate, session: AsyncSession = Depends(get_db_session), _: dict[str, object] = Depends(require_admin)) -> QuizBlueprintResponse:
    round_exists = await session.scalar(select(Round.id).where(Round.id == payload.round_id))
    class_exists = await session.scalar(select(ClassTrack.id).where(ClassTrack.id == payload.class_track_id))
    if round_exists is None or class_exists is None:
        raise AppError("INVALID_BLUEPRINT_REFERENCE", "The round and class track must exist.")

    duplicate = await session.scalar(select(QuizBlueprint.id).where(QuizBlueprint.round_id == payload.round_id, QuizBlueprint.class_track_id == payload.class_track_id))
    if duplicate is not None:
        raise AppError("DUPLICATE_BLUEPRINT", "A blueprint already exists for this round and class.", 409)

    blueprint = QuizBlueprint(
        round_id=payload.round_id,
        class_track_id=payload.class_track_id,
        name=payload.name,
        question_count=payload.question_count,
        seconds_per_question=payload.seconds_per_question,
        buzzer_enabled=payload.buzzer_enabled,
    )
    blueprint.distributions = [QuizDistribution(question_type=item.question_type, difficulty=item.difficulty, quantity=item.quantity) for item in payload.distributions]
    session.add(blueprint)
    await session.flush()
    add_audit(session, action_code="BLUEPRINT_CREATED", entity_name="quiz_blueprint", entity_id=blueprint.id, details={"question_count": blueprint.question_count})
    await session.commit()
    created = await session.scalar(blueprint_query().where(QuizBlueprint.id == blueprint.id))
    return to_response(created)
