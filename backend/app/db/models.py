from datetime import datetime
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base


class EventEdition(Base):
    __tablename__ = "event_edition"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "competition"}

    id: Mapped[UUID] = mapped_column("event_edition_id", Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160))
    event_year: Mapped[int] = mapped_column(Integer, unique=True)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    classes: Mapped[list["ClassTrack"]] = relationship(back_populates="edition")
    teams: Mapped[list["Team"]] = relationship(back_populates="edition")


class ClassTrack(Base):
    __tablename__ = "class_track"
    __table_args__ = (UniqueConstraint("event_edition_id", "code", name="uq_class_track_code"), {"schema": "competition"})

    id: Mapped[UUID] = mapped_column("class_track_id", Uuid, primary_key=True, default=uuid4)
    event_edition_id: Mapped[UUID] = mapped_column(ForeignKey("competition.event_edition.event_edition_id"))
    code: Mapped[str] = mapped_column(String(8))
    display_name: Mapped[str] = mapped_column(String(80))
    preferred_language: Mapped[str] = mapped_column(String(40))

    edition: Mapped[EventEdition] = relationship(back_populates="classes")
    teams: Mapped[list["TeamClass"]] = relationship(back_populates="class_track")


class Team(Base):
    __tablename__ = "team"
    __table_args__ = (UniqueConstraint("event_edition_id", "name", name="uq_team_name_per_edition"), {"schema": "competition"})

    id: Mapped[UUID] = mapped_column("team_id", Uuid, primary_key=True, default=uuid4)
    event_edition_id: Mapped[UUID] = mapped_column(ForeignKey("competition.event_edition.event_edition_id"))
    name: Mapped[str] = mapped_column(String(120))
    registration_order: Mapped[int | None] = mapped_column(SmallInteger)
    slogan: Mapped[str | None] = mapped_column(String(240))
    team_type: Mapped[str] = mapped_column(String(20), default="LEARNING")
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    edition: Mapped[EventEdition] = relationship(back_populates="teams")
    classes: Mapped[list["TeamClass"]] = relationship(back_populates="team", cascade="all, delete-orphan")
    members: Mapped[list["TeamMember"]] = relationship(back_populates="team", cascade="all, delete-orphan")


class TeamClass(Base):
    __tablename__ = "team_class"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "competition"}

    team_id: Mapped[UUID] = mapped_column(ForeignKey("competition.team.team_id"), primary_key=True)
    class_track_id: Mapped[UUID] = mapped_column(ForeignKey("competition.class_track.class_track_id"), primary_key=True)

    team: Mapped[Team] = relationship(back_populates="classes")
    class_track: Mapped[ClassTrack] = relationship(back_populates="teams")


class Student(Base):
    __tablename__ = "student"
    __table_args__ = (
        UniqueConstraint("event_edition_id", "student_reference", name="uq_student_reference"),
        {"schema": "competition"},
    )

    id: Mapped[UUID] = mapped_column("student_id", Uuid, primary_key=True, default=uuid4)
    event_edition_id: Mapped[UUID] = mapped_column(ForeignKey("competition.event_edition.event_edition_id"))
    student_reference: Mapped[str | None] = mapped_column(String(80))
    display_name: Mapped[str] = mapped_column(String(120))
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)


class TeamMember(Base):
    __tablename__ = "team_member"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "competition"}

    id: Mapped[UUID] = mapped_column("team_member_id", Uuid, primary_key=True, default=uuid4)
    team_id: Mapped[UUID] = mapped_column(ForeignKey("competition.team.team_id"))
    student_id: Mapped[UUID] = mapped_column(ForeignKey("competition.student.student_id"))
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_captain: Mapped[bool] = mapped_column(Boolean, default=False)

    team: Mapped[Team] = relationship(back_populates="members")
    student: Mapped[Student] = relationship()


class RateLimitEvent(Base):
    __tablename__ = "rate_limit_event"
    __table_args__ = (Index("ix_rate_limit_event_bucket_time", "bucket_key", "occurred_at"), {"schema": "competition"})

    id: Mapped[UUID] = mapped_column("rate_limit_event_id", Uuid, primary_key=True, default=uuid4)
    bucket_key: Mapped[str] = mapped_column(String(240))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RateLimitBucket(Base):
    __tablename__ = "rate_limit_bucket"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "competition"}

    bucket_key: Mapped[str] = mapped_column(String(240), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_record"
    __table_args__ = (UniqueConstraint("scope_key", "idempotency_key", name="uq_idempotency_scope_key"), {"schema": "competition"})

    id: Mapped[UUID] = mapped_column("idempotency_record_id", Uuid, primary_key=True, default=uuid4)
    scope_key: Mapped[str] = mapped_column(String(240))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QuizRealtimeEvent(Base):
    __tablename__ = "quiz_realtime_event"
    __table_args__ = (Index("ix_quiz_realtime_event_session_id", "session_id"), {"schema": "competition"})

    id: Mapped[int] = mapped_column("realtime_event_id", Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("competition.quiz_session.quiz_session_id"))
    event_type: Mapped[str] = mapped_column(String(80))
    payload_json: Mapped[str] = mapped_column(Text)
    should_broadcast: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QuizRealtimeRelayLock(Base):
    __tablename__ = "quiz_realtime_relay_lock"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "competition"}

    id: Mapped[int] = mapped_column("lock_id", Integer, primary_key=True, autoincrement=False)
    version: Mapped[int] = mapped_column("lock_version", Integer, nullable=False, default=0)


class Question(Base):
    __tablename__ = "question"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "competition"}

    id: Mapped[UUID] = mapped_column("question_id", Uuid, primary_key=True, default=uuid4)
    question_type: Mapped[str] = mapped_column(String(30))
    difficulty: Mapped[str] = mapped_column(String(20))
    preferred_language: Mapped[str | None] = mapped_column(String(40))
    prompt: Mapped[str] = mapped_column(Text)
    code_snippet: Mapped[str | None] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text)
    accepted_answers: Mapped[str | None] = mapped_column(Text)
    default_points: Mapped[int] = mapped_column(Integer, default=10)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    options: Mapped[list["QuestionOption"]] = relationship(back_populates="question", cascade="all, delete-orphan")
    class_links: Mapped[list["QuestionClass"]] = relationship(back_populates="question", cascade="all, delete-orphan")
    tag_links: Mapped[list["QuestionTagLink"]] = relationship(back_populates="question", cascade="all, delete-orphan")


class QuestionOption(Base):
    __tablename__ = "question_option"
    __table_args__ = (UniqueConstraint("question_id", "option_key", name="uq_question_option_key"), {"schema": "competition"})

    id: Mapped[UUID] = mapped_column("question_option_id", Uuid, primary_key=True, default=uuid4)
    question_id: Mapped[UUID] = mapped_column(ForeignKey("competition.question.question_id"))
    option_key: Mapped[str] = mapped_column(String(10))
    option_text: Mapped[str] = mapped_column(String(500))
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0)

    question: Mapped[Question] = relationship(back_populates="options")


class QuestionClass(Base):
    __tablename__ = "question_class"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "competition"}

    question_id: Mapped[UUID] = mapped_column(ForeignKey("competition.question.question_id"), primary_key=True)
    class_track_id: Mapped[UUID] = mapped_column(ForeignKey("competition.class_track.class_track_id"), primary_key=True)

    question: Mapped[Question] = relationship(back_populates="class_links")
    class_track: Mapped[ClassTrack] = relationship()


class QuestionTag(Base):
    __tablename__ = "question_tag"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "competition"}

    code: Mapped[str] = mapped_column("tag_code", String(40), primary_key=True)
    description: Mapped[str | None] = mapped_column(String(200))
    links: Mapped[list["QuestionTagLink"]] = relationship(back_populates="tag")


class QuestionTagLink(Base):
    __tablename__ = "question_tag_link"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "competition"}

    question_id: Mapped[UUID] = mapped_column(ForeignKey("competition.question.question_id"), primary_key=True)
    tag_code: Mapped[str] = mapped_column(ForeignKey("competition.question_tag.tag_code"), primary_key=True)

    question: Mapped[Question] = relationship(back_populates="tag_links")
    tag: Mapped[QuestionTag] = relationship(back_populates="links")


class Round(Base):
    __tablename__ = "round"
    __table_args__ = (UniqueConstraint("event_edition_id", "round_number", name="uq_round_number"), {"schema": "competition"})

    id: Mapped[UUID] = mapped_column("round_id", Uuid, primary_key=True, default=uuid4)
    event_edition_id: Mapped[UUID] = mapped_column(ForeignKey("competition.event_edition.event_edition_id"))
    round_number: Mapped[int] = mapped_column(SmallInteger)
    name: Mapped[str] = mapped_column(String(160))
    round_type: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    description: Mapped[str | None] = mapped_column(String(1000))
    max_points: Mapped[float | None] = mapped_column(Numeric(10, 2))


class QuizBlueprint(Base):
    __tablename__ = "quiz_blueprint"
    __table_args__ = (UniqueConstraint("round_id", "class_track_id", name="uq_blueprint_round_class"), {"schema": "competition"})

    id: Mapped[UUID] = mapped_column("blueprint_id", Uuid, primary_key=True, default=uuid4)
    round_id: Mapped[UUID] = mapped_column(ForeignKey("competition.round.round_id"))
    class_track_id: Mapped[UUID] = mapped_column(ForeignKey("competition.class_track.class_track_id"))
    name: Mapped[str] = mapped_column(String(160))
    question_count: Mapped[int] = mapped_column(Integer)
    seconds_per_question: Mapped[int] = mapped_column(Integer, default=20)
    buzzer_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    distributions: Mapped[list["QuizDistribution"]] = relationship(back_populates="blueprint", cascade="all, delete-orphan")


class QuizDistribution(Base):
    __tablename__ = "quiz_distribution"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "competition"}

    id: Mapped[UUID] = mapped_column("distribution_id", Uuid, primary_key=True, default=uuid4)
    blueprint_id: Mapped[UUID] = mapped_column(ForeignKey("competition.quiz_blueprint.blueprint_id"))
    question_type: Mapped[str] = mapped_column(String(30))
    difficulty: Mapped[str | None] = mapped_column(String(20))
    quantity: Mapped[int] = mapped_column(Integer)

    blueprint: Mapped[QuizBlueprint] = relationship(back_populates="distributions")


class QuizSession(Base):
    __tablename__ = "quiz_session"
    __table_args__ = (UniqueConstraint("quiz_code", name="uq_quiz_session_code"), {"schema": "competition"})

    id: Mapped[UUID] = mapped_column("quiz_session_id", Uuid, primary_key=True, default=uuid4)
    blueprint_id: Mapped[UUID] = mapped_column(ForeignKey("competition.quiz_blueprint.blueprint_id"))
    quiz_code: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(20), default="WAITING")
    version_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    questions: Mapped[list["QuizQuestion"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class QuizQuestion(Base):
    __tablename__ = "quiz_question"
    __table_args__ = (
        UniqueConstraint("quiz_session_id", "question_order", name="uq_quiz_question_order"),
        UniqueConstraint("quiz_session_id", "question_id", name="uq_quiz_question_once"),
        {"schema": "competition"},
    )

    id: Mapped[UUID] = mapped_column("quiz_question_id", Uuid, primary_key=True, default=uuid4)
    quiz_session_id: Mapped[UUID] = mapped_column(ForeignKey("competition.quiz_session.quiz_session_id"))
    question_id: Mapped[UUID] = mapped_column(ForeignKey("competition.question.question_id"))
    question_order: Mapped[int] = mapped_column(Integer)
    prompt_snapshot: Mapped[str] = mapped_column(Text)
    code_snippet_snapshot: Mapped[str | None] = mapped_column(Text)
    question_type_snapshot: Mapped[str] = mapped_column(String(30), default="MCQ", server_default="MCQ")
    accepted_answers_snapshot: Mapped[str | None] = mapped_column(Text)
    points_snapshot: Mapped[int] = mapped_column(Integer, default=10)
    answer_key_snapshot: Mapped[str | None] = mapped_column(Text)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    session: Mapped[QuizSession] = relationship(back_populates="questions")
    question: Mapped[Question] = relationship()


class BuzzerPress(Base):
    __tablename__ = "buzzer_press"
    __table_args__ = (
        Index("ux_buzzer_one_winner", "quiz_question_id", unique=True, sqlite_where=text("is_winner = 1"), mssql_where=text("is_winner = 1")),
        {"schema": "competition"},
    )

    id: Mapped[UUID] = mapped_column("buzzer_press_id", Uuid, primary_key=True, default=uuid4)
    quiz_question_id: Mapped[UUID] = mapped_column(ForeignKey("competition.quiz_question.quiz_question_id"))
    participant_id: Mapped[UUID] = mapped_column(ForeignKey("competition.quiz_participant.participant_id"))
    pressed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_winner: Mapped[bool] = mapped_column(Boolean, default=False)


class QuizParticipant(Base):
    __tablename__ = "quiz_participant"
    __table_args__ = (UniqueConstraint("quiz_session_id", "team_id", name="uq_quiz_participant_team"), {"schema": "competition"})

    id: Mapped[UUID] = mapped_column("participant_id", Uuid, primary_key=True, default=uuid4)
    quiz_session_id: Mapped[UUID] = mapped_column(ForeignKey("competition.quiz_session.quiz_session_id"))
    team_id: Mapped[UUID] = mapped_column(ForeignKey("competition.team.team_id"))
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AnswerSubmission(Base):
    __tablename__ = "answer_submission"
    __table_args__ = (UniqueConstraint("quiz_question_id", "participant_id", "is_final", name="uq_answer_one_final"), {"schema": "competition"})

    id: Mapped[UUID] = mapped_column("answer_submission_id", Uuid, primary_key=True, default=uuid4)
    quiz_question_id: Mapped[UUID] = mapped_column(ForeignKey("competition.quiz_question.quiz_question_id"))
    participant_id: Mapped[UUID] = mapped_column(ForeignKey("competition.quiz_participant.participant_id"))
    buzzer_press_id: Mapped[UUID | None] = mapped_column(ForeignKey("competition.buzzer_press.buzzer_press_id"))
    submitted_answer: Mapped[str] = mapped_column(Text)
    is_final: Mapped[bool] = mapped_column(Boolean, default=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    awarded_points: Mapped[int] = mapped_column(Integer, default=0)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    judged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ScoreEntry(Base):
    __tablename__ = "score_entry"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "competition"}

    id: Mapped[UUID] = mapped_column("score_entry_id", Uuid, primary_key=True, default=uuid4)
    team_id: Mapped[UUID] = mapped_column(ForeignKey("competition.team.team_id"))
    round_id: Mapped[UUID] = mapped_column(ForeignKey("competition.round.round_id"))
    quiz_session_id: Mapped[UUID | None] = mapped_column(ForeignKey("competition.quiz_session.quiz_session_id"))
    answer_submission_id: Mapped[UUID | None] = mapped_column(ForeignKey("competition.answer_submission.answer_submission_id"))
    points_delta: Mapped[float] = mapped_column(Numeric(10, 2))
    reason: Mapped[str] = mapped_column(String(40))
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "competition"}

    id: Mapped[int] = mapped_column("audit_log_id", Integer, primary_key=True, autoincrement=True)
    action_code: Mapped[str] = mapped_column(String(80))
    entity_name: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[UUID | None] = mapped_column(Uuid)
    details_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
