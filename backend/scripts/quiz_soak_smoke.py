"""Run a bounded repeated end-to-end quiz soak against a disposable/staging service.

Each iteration creates and ends its own one-question session through the checked-in E2E flow. The
command is intentionally capped and never deletes application data; use a disposable database or
an approved staging environment only.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from statistics import mean
from typing import Any

import httpx

from e2e_smoke import run as run_e2e


async def run_soak(
    base_url: str,
    class_code: str,
    admin_password_env: str,
    iterations: int,
    max_concurrency: int,
) -> dict[str, Any]:
    if not 1 <= iterations <= 20:
        raise ValueError("iterations must be between 1 and 20")
    if not 1 <= max_concurrency <= 5:
        raise ValueError("max_concurrency must be between 1 and 5")
    if not os.environ.get(admin_password_env):
        raise ValueError(f"Set {admin_password_env} in the disposable soak environment.")

    semaphore = asyncio.Semaphore(max_concurrency)

    async def one_iteration(index: int) -> tuple[int, dict[str, Any], float]:
        async with semaphore:
            started = time.perf_counter()
            result = await run_e2e(base_url, class_code, admin_password_env)
            return index, result, round(time.perf_counter() - started, 3)

    completed = await asyncio.gather(*(one_iteration(index) for index in range(1, iterations + 1)))
    durations = [duration for _, _, duration in completed]
    return {
        "base_url": base_url.rstrip("/"),
        "iterations": iterations,
        "max_concurrency": max_concurrency,
        "completed": len(completed),
        "duration_seconds": {
            "min": min(durations),
            "max": max(durations),
            "average": round(mean(durations), 3),
        },
        "sessions": [result["session_id"] for _, result, _ in completed],
        "all_websocket_reconnects_verified": all(result["websocket_reconnect"] for _, result, _ in completed),
        "all_scores_published": all(result["leaderboard_points"] == result["awarded_points"] for _, result, _ in completed),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--class-code", default="IX")
    parser.add_argument("--admin-password-env", default="SMOKE_ADMIN_PASSWORD")
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--max-concurrency", type=int, default=2)
    return parser.parse_args()


if __name__ == "__main__":
    try:
        print(json.dumps(asyncio.run(run_soak(**vars(parse_args()))), indent=2))
    except (httpx.HTTPError, OSError, RuntimeError, ValueError) as error:
        print(f"quiz soak failed: {error}")
        raise SystemExit(1) from error
