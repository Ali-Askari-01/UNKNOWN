from app.core.grading import grade_answer, normalize_answer


def test_normalization_ignores_case_unicode_form_and_extra_whitespace() -> None:
    assert normalize_answer("  CAFE\u0301   au lait ") == normalize_answer("Café au lait")


def test_mcq_accepts_correct_option_key_and_text_only() -> None:
    key = '[{"key":"A","text":"Wrong","is_correct":false},{"key":"B","text":"Right","is_correct":true}]'
    assert grade_answer("MCQ", " b ", key, None) is True
    assert grade_answer("MCQ", "Right", key, None) is True
    assert grade_answer("MCQ", "A", key, None) is False


def test_text_answers_match_any_admin_configured_accepted_answer() -> None:
    accepted = '["stack", "LIFO"]'
    assert grade_answer("RIDDLE", "lifo", None, accepted) is True
    assert grade_answer("THEORY", "queue", None, accepted) is False


def test_missing_or_invalid_key_requires_manual_review() -> None:
    assert grade_answer("THEORY", "anything", None, None) is None
    assert grade_answer("MCQ", "anything", "not-json", None) is None
