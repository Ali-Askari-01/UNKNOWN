"""Generate a bcrypt admin hash without accepting or printing the plaintext password."""

from __future__ import annotations

import argparse
import getpass
import sys

import bcrypt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rounds",
        type=int,
        default=12,
        choices=range(10, 16),
        help="bcrypt work factor (10–15; default: 12)",
    )
    return parser.parse_args()


def hash_password(password: str, rounds: int = 12) -> str:
    if not password:
        raise ValueError("Password must not be empty.")
    if not 10 <= rounds <= 15:
        raise ValueError("bcrypt rounds must be between 10 and 15.")
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=rounds)).decode()


def main() -> int:
    args = parse_args()
    password = getpass.getpass("New admin password: ")
    confirmation = getpass.getpass("Confirm admin password: ")
    if password != confirmation:
        print("Passwords do not match.", file=sys.stderr)
        return 1
    try:
        print(hash_password(password, args.rounds))
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
