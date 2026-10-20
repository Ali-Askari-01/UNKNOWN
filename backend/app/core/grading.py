import json
import re
import unicodedata


def normalize_answer(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    return re.sub(r"\s+", " ", normalized)


def grade_answer(question_type: str, answer: str, answer_key_snapshot: str | None, accepted_answers_snapshot: str | None) -> bool | None:
    """Return correctness when a saved answer key exists; None means manual review."""
    candidates: list[str] = []
    if question_type == "MCQ":
        try:
            options = json.loads(answer_key_snapshot or "[]")
            candidates = [str(option["key"]) for option in options if option.get("is_correct")]
            candidates += [str(option["text"]) for option in options if option.get("is_correct")]
        except (TypeError, ValueError, KeyError):
            return None
    else:
        try:
            candidates = [str(item) for item in json.loads(accepted_answers_snapshot or "[]")]
        except (TypeError, ValueError):
            return None
    if not candidates:
        return None
    normalized = normalize_answer(answer)
    return any(normalize_answer(candidate) == normalized for candidate in candidates)
