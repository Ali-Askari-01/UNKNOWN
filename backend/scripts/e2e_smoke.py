"""Exercise the disposable end-to-end admin and student quiz flow.

Use only against a disposable local/staging database. The script creates and ends one quiz
session, joins one team, submits one answer, judges it, and verifies idempotent replay.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any

import httpx
import websockets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--class-code", default="IX")
    parser.add_argument("--admin-password-env", default="SMOKE_ADMIN_PASSWORD")
    return parser.parse_args()


async def require(response: httpx.Response, operation: str) -> dict[str, Any]:
    if not response.is_success:
        raise RuntimeError(f"{operation} failed with HTTP {response.status_code}")
    return response.json() if response.content else {}


async def run(base_url: str, class_code: str, admin_password_env: str) -> dict[str, Any]:
    admin_password = os.environ.get(admin_password_env)
    if not admin_password:
        raise RuntimeError(f"Set {admin_password_env} in the disposable smoke-test environment.")
    admin_username = os.environ.get("SMOKE_ADMIN_USERNAME", os.environ.get("BACKEND_ADMIN_USERNAME", "admin"))
    base_url = base_url.rstrip("/")
    ws_base_url = base_url.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
    session_id: str | None = None

    async with httpx.AsyncClient(base_url=base_url, timeout=20.0) as client:
        login = await require(
            await client.post("/api/v1/auth/login", json={"username": admin_username, "password": admin_password}),
            "admin login",
        )
        admin_headers = {"Authorization": f"Bearer {login['access_token']}"}

        blueprints = await require(await client.get("/api/v1/quiz-blueprints", headers=admin_headers), "blueprint lookup")
        if not blueprints:
            raise RuntimeError("No quiz blueprint is available for the smoke test.")
        created = await require(
            await client.post("/api/v1/admin/quiz-sessions", headers=admin_headers, json={"blueprint_id": blueprints[0]["id"]}),
            "session creation",
        )
        session_id = created["id"]
        open_headers = {**admin_headers, "Idempotency-Key": f"e2e-open-{session_id}"}
        opened = await require(await client.post(f"/api/v1/admin/quiz-sessions/{session_id}/actions/open", headers=open_headers), "session open")
        replayed_open = await require(await client.post(f"/api/v1/admin/quiz-sessions/{session_id}/actions/open", headers=open_headers), "idempotent session open replay")
        if replayed_open != opened:
            raise RuntimeError("Idempotent session action replay did not match the original response.")
        await require(await client.post(f"/api/v1/admin/quiz-sessions/{session_id}/actions/start", headers=admin_headers), "session start")

        questions = await require(await client.get(f"/api/v1/quiz-sessions/{session_id}/questions"), "question lookup")
        if len(questions) != 1:
            raise RuntimeError("The smoke test requires exactly one generated question.")
        question_id = questions[0]["id"]
        teams = await require(await client.get("/api/v1/teams", params={"class_code": class_code}), "team lookup")
        if not teams:
            raise RuntimeError(f"No public team is available for class {class_code}.")

        team_join_key = f"e2e-team-join-{session_id}-{teams[0]['id']}"
        joined = await require(
            await client.post(
                "/api/v1/auth/team/join",
                headers={"Idempotency-Key": team_join_key},
                json={"quiz_code": created["quiz_code"], "team_id": teams[0]["id"]},
            ),
            "team join",
        )
        replayed_join = await require(
            await client.post(
                "/api/v1/auth/team/join",
                headers={"Idempotency-Key": team_join_key},
                json={"quiz_code": created["quiz_code"], "team_id": teams[0]["id"]},
            ),
            "idempotent team join replay",
        )
        if replayed_join != joined:
            raise RuntimeError("Idempotent team join replay did not match the original response.")
        team_headers = {"Authorization": f"Bearer {joined['access_token']}"}

        websocket_url = f"{ws_base_url}/api/v1/ws/quiz/{session_id}"
        async with websockets.connect(
            websocket_url,
            subprotocols=[f"auth.{joined['access_token']}"],
        ) as socket:
            snapshot = json.loads(await socket.recv())
            if snapshot.get("type") != "quiz.state.snapshot":
                raise RuntimeError("WebSocket did not deliver an initial quiz snapshot.")
            if not snapshot.get("payload", {}).get("scores"):
                raise RuntimeError("WebSocket snapshot did not include joined-team scores.")
            await socket.send(json.dumps({"type": "quiz.ping"}))
            pong = json.loads(await socket.recv())
            if pong.get("type") != "quiz.ping.ack":
                raise RuntimeError("WebSocket ping did not receive a quiz.ping.ack response.")

        async with websockets.connect(
            websocket_url,
            subprotocols=[f"auth.{joined['access_token']}"],
        ) as socket:
            reconnected_snapshot = json.loads(await socket.recv())
            if reconnected_snapshot.get("type") != "quiz.state.snapshot":
                raise RuntimeError("WebSocket reconnect did not deliver a fresh snapshot.")
            if reconnected_snapshot.get("sequence", 0) <= snapshot.get("sequence", 0):
                raise RuntimeError("WebSocket snapshot sequence did not advance after reconnect.")

        buzzer = await require(
            await client.post(
                f"/api/v1/quiz-sessions/{session_id}/questions/{question_id}/buzzer", headers=team_headers
            ),
            "buzzer press",
        )
        answer_key = f"e2e-answer-{session_id}-{question_id}-{joined['id']}"
        answer = await require(
            await client.post(
                f"/api/v1/quiz-sessions/{session_id}/answers",
                headers={**team_headers, "Content-Type": "application/json", "Idempotency-Key": answer_key},
                json={"participant_id": joined["id"], "quiz_question_id": question_id, "submitted_answer": "B"},
            ),
            "answer submission",
        )
        replayed_answer = await require(
            await client.post(
                f"/api/v1/quiz-sessions/{session_id}/answers",
                headers={**team_headers, "Content-Type": "application/json", "Idempotency-Key": answer_key},
                json={"participant_id": joined["id"], "quiz_question_id": question_id, "submitted_answer": "B"},
            ),
            "idempotent answer replay",
        )
        if replayed_answer != answer:
            raise RuntimeError("Idempotent answer replay did not match the original response.")
        idempotency_key = f"e2e-judge-{answer['id']}"
        judgment = await require(
            await client.post(
                f"/api/v1/admin/quiz-sessions/{session_id}/answers/{answer['id']}/judge",
                headers={**admin_headers, "Idempotency-Key": idempotency_key},
                json={"is_correct": True},
            ),
            "answer judging",
        )
        replay = await require(
            await client.post(
                f"/api/v1/admin/quiz-sessions/{session_id}/answers/{answer['id']}/judge",
                headers={**admin_headers, "Idempotency-Key": idempotency_key},
                json={"is_correct": True},
            ),
            "idempotent judgment replay",
        )
        if replay != judgment:
            raise RuntimeError("Idempotent judgment replay did not match the original response.")
        leaderboard = await require(await client.get(f"/api/v1/quiz-sessions/{session_id}/leaderboard"), "leaderboard lookup")
        if not leaderboard or leaderboard[0]["points"] != judgment["awarded_points"]:
            raise RuntimeError("Leaderboard did not reflect the judged answer.")
        async with websockets.connect(
            websocket_url,
            subprotocols=[f"auth.{joined['access_token']}"],
        ) as socket:
            final_snapshot = json.loads(await socket.recv())
            final_scores = final_snapshot.get("payload", {}).get("scores", [])
            if not final_scores or final_scores[0].get("score") != judgment["awarded_points"]:
                raise RuntimeError("WebSocket reconnect snapshot did not include the published score.")
        await require(await client.post(f"/api/v1/admin/quiz-sessions/{session_id}/actions/end", headers=admin_headers), "session end")

    return {
        "session_id": session_id,
        "quiz_code": created["quiz_code"],
        "question_id": question_id,
        "team_id": joined["team_id"],
        "buzzer_id": buzzer["id"],
        "answer_id": answer["id"],
        "awarded_points": judgment["awarded_points"],
        "websocket_snapshot": True,
        "websocket_ping": True,
        "websocket_reconnect": True,
        "idempotent_session_action": True,
        "idempotent_team_join": True,
        "idempotent_answer": True,
        "idempotent_judging": True,
        "leaderboard_points": leaderboard[0]["points"],
    }


if __name__ == "__main__":
    args = parse_args()
    try:
        print(json.dumps(asyncio.run(run(args.base_url, args.class_code, args.admin_password_env)), indent=2))
    except (httpx.HTTPError, OSError, RuntimeError) as error:
        print(f"e2e smoke failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
