"""Idempotently seed the local TLC event content into the configured database."""

import asyncio

from sqlalchemy import select

from app.db.models import (
    ClassTrack,
    EventEdition,
    Question,
    QuestionClass,
    QuestionOption,
    QuizBlueprint,
    QuizDistribution,
    Round,
    Team,
    TeamClass,
)
from app.db.session import SessionFactory, dispose_engine


async def seed() -> None:
    async with SessionFactory() as session:
        edition = await session.scalar(select(EventEdition).where(EventEdition.event_year == 2026))
        if edition is None:
            edition = EventEdition(name="TLC Technology Competition 2026", event_year=2026, status="ACTIVE")
            session.add(edition)
            await session.flush()

        tracks = {}
        for code, language in (("IX", "Python"), ("X", "C++"), ("XI", "Python")):
            track = await session.scalar(select(ClassTrack).where(ClassTrack.event_edition_id == edition.id, ClassTrack.code == code))
            if track is None:
                track = ClassTrack(event_edition_id=edition.id, code=code, display_name=f"Class {code}", preferred_language=language)
                session.add(track)
                await session.flush()
            tracks[code] = track

        team = await session.scalar(select(Team).where(Team.event_edition_id == edition.id, Team.name == "Demo Team"))
        if team is None:
            team = Team(event_edition_id=edition.id, name="Demo Team", slogan="Build, learn, compete", team_type="LEARNING")
            session.add(team)
            await session.flush()
        if await session.scalar(select(TeamClass).where(TeamClass.team_id == team.id, TeamClass.class_track_id == tracks["IX"].id)) is None:
            session.add(TeamClass(team_id=team.id, class_track_id=tracks["IX"].id))

        question = await session.scalar(select(Question).where(Question.prompt == "Which Python keyword defines a function?"))
        if question is None:
            question = Question(
                question_type="MCQ", difficulty="EASY", preferred_language="Python",
                prompt="Which Python keyword defines a function?",
                explanation="The def keyword starts a Python function definition.", default_points=10,
            )
            question.options = [
                QuestionOption(option_key="A", option_text="func", is_correct=False, sort_order=0),
                QuestionOption(option_key="B", option_text="def", is_correct=True, sort_order=1),
                QuestionOption(option_key="C", option_text="function", is_correct=False, sort_order=2),
                QuestionOption(option_key="D", option_text="lambda", is_correct=False, sort_order=3),
            ]
            question.class_links = [QuestionClass(class_track_id=tracks[code].id) for code in ("IX", "XI")]
            session.add(question)

        round_item = await session.scalar(select(Round).where(Round.event_edition_id == edition.id, Round.round_number == 2))
        if round_item is None:
            round_item = Round(event_edition_id=edition.id, round_number=2, name="MCQ Quiz", round_type="MCQ", status="ACTIVE", description="Class-level question bank quiz.")
            session.add(round_item)
            await session.flush()

        blueprint = await session.scalar(select(QuizBlueprint).where(QuizBlueprint.round_id == round_item.id, QuizBlueprint.class_track_id == tracks["IX"].id))
        if blueprint is None:
            blueprint = QuizBlueprint(round_id=round_item.id, class_track_id=tracks["IX"].id, name="Class IX MCQ Quiz", question_count=1, seconds_per_question=20, buzzer_enabled=True)
            blueprint.distributions = [QuizDistribution(question_type="MCQ", difficulty="EASY", quantity=1)]
            session.add(blueprint)

        await session.commit()
        print(f"Seeded edition={edition.id} team={team.id} question={question.id} blueprint={blueprint.id}")


async def main() -> None:
    try:
        await seed()
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
