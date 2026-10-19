from collections.abc import AsyncGenerator

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


def create_engine() -> AsyncEngine:
    settings = get_settings()
    kwargs: dict[str, object] = {"pool_pre_ping": True, "future": True}
    if settings.database_url.startswith("sqlite+"):
        kwargs["connect_args"] = {"check_same_thread": False}
    elif settings.database_url.startswith("mssql+aioodbc"):
        # aioodbc connections are bound to the event loop that created them;
        # NullPool prevents stale connections when test/application loops restart.
        kwargs["poolclass"] = NullPool
    engine = create_async_engine(settings.database_url, **kwargs)
    if settings.database_url.startswith("sqlite+"):
        # The production schema uses the `competition` schema. Mapping it to
        # SQLite's main database keeps local development faithful without
        # requiring a separate database server.
        engine = engine.execution_options(schema_translate_map={"competition": None})
    return engine


engine = create_engine()
SessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionFactory() as session:
        yield session


async def ping_database() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def initialize_local_database() -> None:
    """Create and seed the small local development database only."""
    settings = get_settings()
    if not settings.database_url.startswith("sqlite+"):
        return

    from app.db.base import Base
    from app.db.models import ClassTrack, EventEdition, Question, QuestionClass, QuestionOption, QuizBlueprint, QuizDistribution, Round, Team, TeamClass

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        columns = {row[1] for row in (await connection.execute(text("PRAGMA table_info('quiz_question')"))).fetchall()}
        if columns and "points_snapshot" not in columns:
            await connection.execute(text("ALTER TABLE quiz_question ADD COLUMN points_snapshot INTEGER NOT NULL DEFAULT 10"))

    async with SessionFactory() as session:
        existing = await session.scalar(select(EventEdition).where(EventEdition.event_year == 2026))
        if existing is None:
            edition = EventEdition(name="TLC Technology Competition 2026", event_year=2026, status="ACTIVE")
            session.add(edition)
            await session.flush()
            session.add_all(
                [
                    ClassTrack(event_edition_id=edition.id, code="IX", display_name="Class IX", preferred_language="Python"),
                    ClassTrack(event_edition_id=edition.id, code="X", display_name="Class X", preferred_language="C++"),
                    ClassTrack(event_edition_id=edition.id, code="XI", display_name="Class XI", preferred_language="Python"),
                ]
            )
            session.add(Team(event_edition_id=edition.id, name="Demo Team", slogan="Build, learn, compete", team_type="LEARNING"))
            await session.commit()
        demo_team = await session.scalar(select(Team).where(Team.name == "Demo Team"))
        ix_track = await session.scalar(select(ClassTrack).where(ClassTrack.code == "IX"))
        if demo_team is not None and ix_track is not None:
            team_class_exists = await session.scalar(select(TeamClass).where(TeamClass.team_id == demo_team.id, TeamClass.class_track_id == ix_track.id))
            if team_class_exists is None:
                session.add(TeamClass(team_id=demo_team.id, class_track_id=ix_track.id))
                await session.commit()
        question_exists = await session.scalar(select(Question).limit(1))
        if question_exists is None:
            edition = await session.scalar(select(EventEdition).where(EventEdition.event_year == 2026))
            tracks = list((await session.scalars(select(ClassTrack).where(ClassTrack.event_edition_id == edition.id).order_by(ClassTrack.code))).all())
            question = Question(
                question_type="MCQ",
                difficulty="EASY",
                preferred_language="Python",
                prompt="Which Python keyword defines a function?",
                explanation="The def keyword starts a Python function definition.",
                default_points=10,
            )
            question.options = [
                QuestionOption(option_key="A", option_text="func", is_correct=False, sort_order=0),
                QuestionOption(option_key="B", option_text="def", is_correct=True, sort_order=1),
                QuestionOption(option_key="C", option_text="function", is_correct=False, sort_order=2),
                QuestionOption(option_key="D", option_text="lambda", is_correct=False, sort_order=3),
            ]
            question.class_links = [QuestionClass(class_track_id=track.id) for track in tracks if track.code in {"IX", "XI"}]
            session.add(question)
            await session.commit()
        round_item = await session.scalar(select(Round).where(Round.round_number == 2))
        if round_item is None:
            edition = await session.scalar(select(EventEdition).where(EventEdition.event_year == 2026))
            round_item = Round(
                event_edition_id=edition.id,
                round_number=2,
                name="MCQ Quiz",
                round_type="MCQ",
                status="ACTIVE",
                description="Class-level question bank quiz.",
            )
            session.add(round_item)
            await session.flush()
        blueprint_exists = await session.scalar(select(QuizBlueprint).limit(1))
        if blueprint_exists is None:
            ix = await session.scalar(select(ClassTrack).where(ClassTrack.code == "IX"))
            blueprint = QuizBlueprint(
                round_id=round_item.id,
                class_track_id=ix.id,
                name="Class IX MCQ Quiz",
                question_count=1,
                seconds_per_question=20,
                buzzer_enabled=True,
            )
            blueprint.distributions = [QuizDistribution(question_type="MCQ", difficulty="EASY", quantity=1)]
            session.add(blueprint)
            await session.commit()


async def dispose_engine() -> None:
    await engine.dispose()
