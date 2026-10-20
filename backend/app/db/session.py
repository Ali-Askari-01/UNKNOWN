import os
import time
from collections.abc import AsyncGenerator, Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import make_url, select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


@contextmanager
def _sqlite_initialization_lock(database_url: str) -> Iterator[None]:
    """Serialize local SQLite schema seeding when multiple dev workers start together."""
    database = make_url(database_url).database
    if not database or database == ":memory:":
        yield
        return

    lock_path = Path(database).expanduser().resolve()
    lock_path = lock_path.with_name(f"{lock_path.name}.init.lock")
    deadline = time.monotonic() + 60
    while True:
        try:
            descriptor = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(descriptor, "w", encoding="ascii") as lock_file:
                lock_file.write(str(os.getpid()))
            break
        except FileExistsError:
            try:
                stale = time.time() - lock_path.stat().st_mtime > 120
            except FileNotFoundError:
                continue
            if stale:
                lock_path.unlink(missing_ok=True)
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for SQLite initialization lock: {lock_path}")
            time.sleep(0.1)

    try:
        yield
    finally:
        lock_path.unlink(missing_ok=True)


def create_engine() -> AsyncEngine:
    settings = get_settings()
    kwargs: dict[str, object] = {"pool_pre_ping": True, "future": True}
    if settings.database_url.startswith("sqlite+"):
        kwargs["connect_args"] = {"check_same_thread": False}
    elif settings.database_url.startswith("mssql+aioodbc"):
        if settings.environment in {"development", "test"}:
            # Local tests frequently create and destroy event loops; avoiding pooled aioodbc
            # connections prevents stale loop-bound connections in that environment.
            kwargs["poolclass"] = NullPool
        else:
            # Staging/production workers retain a bounded pool so concurrent quiz traffic does not
            # create an unbounded number of SQL Server connections.
            kwargs.update(
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
                pool_timeout=settings.db_pool_timeout,
                pool_recycle=settings.db_pool_recycle,
            )
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


async def get_schema_revision() -> str | None:
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT version_num FROM alembic_version"))
        row = result.first()
        return str(row[0]) if row else None


async def _initialize_local_database_unlocked() -> None:
    """Create and seed the small local development database only."""
    settings = get_settings()
    if not settings.database_url.startswith("sqlite+"):
        return

    from app.db.base import Base
    from app.db.models import (
        ClassTrack,
        EventEdition,
        Question,
        QuestionClass,
        QuestionOption,
        QuizBlueprint,
        QuizDistribution,
        QuizRealtimeRelayLock,
        Round,
        Team,
        TeamClass,
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        columns = {row[1] for row in (await connection.execute(text("PRAGMA table_info('quiz_question')"))).fetchall()}
        if columns and "points_snapshot" not in columns:
            await connection.execute(text("ALTER TABLE quiz_question ADD COLUMN points_snapshot INTEGER NOT NULL DEFAULT 10"))
        if columns and "opened_at" not in columns:
            await connection.execute(text("ALTER TABLE quiz_question ADD COLUMN opened_at DATETIME"))
        if columns and "closed_at" not in columns:
            await connection.execute(text("ALTER TABLE quiz_question ADD COLUMN closed_at DATETIME"))
        round_columns = {row[1] for row in (await connection.execute(text("PRAGMA table_info('round')"))).fetchall()}
        if round_columns and "max_points" not in round_columns:
            await connection.execute(text("ALTER TABLE round ADD COLUMN max_points NUMERIC(10, 2)"))
        team_columns = {row[1] for row in (await connection.execute(text("PRAGMA table_info('team')"))).fetchall()}
        if team_columns and "registration_order" not in team_columns:
            await connection.execute(text("ALTER TABLE team ADD COLUMN registration_order SMALLINT"))
        student_columns = {row[1] for row in (await connection.execute(text("PRAGMA table_info('student')"))).fetchall()}
        if student_columns and "student_reference" not in student_columns:
            await connection.execute(text("ALTER TABLE student ADD COLUMN student_reference VARCHAR(80)"))
        if columns and "code_snippet_snapshot" not in columns:
            await connection.execute(text("ALTER TABLE quiz_question ADD COLUMN code_snippet_snapshot TEXT"))
            await connection.execute(
                text(
                    "UPDATE quiz_question SET code_snippet_snapshot = "
                    "(SELECT question.code_snippet FROM question WHERE question.question_id = quiz_question.question_id)"
                )
            )
        if columns and "question_type_snapshot" not in columns:
            await connection.execute(text("ALTER TABLE quiz_question ADD COLUMN question_type_snapshot VARCHAR(30) NOT NULL DEFAULT 'MCQ'"))
            await connection.execute(text("UPDATE quiz_question SET question_type_snapshot = (SELECT question.question_type FROM question WHERE question.question_id = quiz_question.question_id)"))
        if columns and "accepted_answers_snapshot" not in columns:
            await connection.execute(text("ALTER TABLE quiz_question ADD COLUMN accepted_answers_snapshot TEXT"))
        answer_columns = {row[1] for row in (await connection.execute(text("PRAGMA table_info('answer_submission')"))).fetchall()}
        if answer_columns and "buzzer_press_id" not in answer_columns:
            await connection.execute(text("ALTER TABLE answer_submission ADD COLUMN buzzer_press_id CHAR(36)"))
        if answer_columns and "judged_at" not in answer_columns:
            await connection.execute(text("ALTER TABLE answer_submission ADD COLUMN judged_at DATETIME"))
        question_columns = {row[1] for row in (await connection.execute(text("PRAGMA table_info('question')"))).fetchall()}
        if question_columns and "accepted_answers" not in question_columns:
            await connection.execute(text("ALTER TABLE question ADD COLUMN accepted_answers TEXT"))
        await connection.execute(
            text(
                "UPDATE quiz_question SET accepted_answers_snapshot = "
                "(SELECT question.accepted_answers FROM question "
                "WHERE question.question_id = quiz_question.question_id) "
                "WHERE accepted_answers_snapshot IS NULL"
            )
        )

    async with SessionFactory() as session:
        relay_lock = await session.get(QuizRealtimeRelayLock, 1)
        if relay_lock is None:
            session.add(QuizRealtimeRelayLock(id=1, version=0))
            await session.commit()
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


async def initialize_local_database() -> None:
    settings = get_settings()
    if not settings.database_url.startswith("sqlite+"):
        return
    with _sqlite_initialization_lock(settings.database_url):
        await _initialize_local_database_unlocked()


async def dispose_engine() -> None:
    await engine.dispose()
