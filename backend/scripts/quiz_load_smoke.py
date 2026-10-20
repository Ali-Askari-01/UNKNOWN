"""Run a bounded concurrent buzzer smoke test against an active quiz session.

This intentionally mutates only the supplied staging/local session. It does not create a session,
advance lifecycle state, or read answer keys. Use a disposable active session and never point it at
production without an approved event rehearsal.
"""

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class TeamToken:
    participant_id: str
    token: str


async def run(base_url: str, quiz_code: str, class_code: str, team_limit: int) -> dict[str, object]:
    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=15.0) as client:
        lookup = await client.get(f"/api/v1/quiz-sessions/by-code/{quiz_code.strip().upper()}")
        lookup.raise_for_status()
        quiz = lookup.json()
        if quiz["status"] != "ACTIVE":
            raise RuntimeError(f"Quiz {quiz_code} must be ACTIVE, got {quiz['status']}")

        questions_response = await client.get(f"/api/v1/quiz-sessions/{quiz['id']}/questions")
        questions_response.raise_for_status()
        questions = questions_response.json()
        if len(questions) != 1:
            raise RuntimeError("The load smoke requires exactly one currently open question.")
        question_id = questions[0]["id"]

        teams_response = await client.get("/api/v1/teams", params={"class_code": class_code})
        teams_response.raise_for_status()
        teams = teams_response.json()[:team_limit]
        if len(teams) < 2:
            raise RuntimeError("At least two public teams are required for the concurrent smoke test.")

        joins = await asyncio.gather(
            *[
                client.post(
                    "/api/v1/auth/team/join",
                    json={"quiz_code": quiz["quiz_code"], "team_id": team["id"]},
                )
                for team in teams
            ]
        )
        for response in joins:
            response.raise_for_status()
        identities = [
            TeamToken(participant_id=response.json()["id"], token=response.json()["access_token"])
            for response in joins
        ]

        buzzer_results = await asyncio.gather(
            *[
                client.post(
                    f"/api/v1/quiz-sessions/{quiz['id']}/questions/{question_id}/buzzer",
                    headers={"Authorization": f"Bearer {identity.token}"},
                )
                for identity in identities
            ]
        )
        statuses = sorted(response.status_code for response in buzzer_results)
        if statuses.count(201) != 1 or statuses.count(409) != len(statuses) - 1:
            raise RuntimeError(f"Expected one buzzer winner and {len(statuses) - 1} conflicts; got {statuses}")

        winner = next(response.json() for response in buzzer_results if response.status_code == 201)
        return {
            "quiz_code": quiz["quiz_code"],
            "session_id": quiz["id"],
            "team_count": len(teams),
            "question_id": question_id,
            "winner_team": winner["team_name"],
            "winner_statuses": statuses,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--quiz-code", required=True)
    parser.add_argument("--class-code", default="IX")
    parser.add_argument("--team-limit", type=int, default=5)
    return parser.parse_args()


if __name__ == "__main__":
    try:
        print(json.dumps(asyncio.run(run(**vars(parse_args()))), indent=2))
    except (httpx.HTTPError, RuntimeError) as error:
        print(f"load smoke failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
