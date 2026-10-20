import pytest

from scripts.import_event_scorecard import canonical_team_name, validate_inputs


def test_confirmed_class_ix_team_rename_is_canonicalized() -> None:
    assert canonical_team_name("IX", "Naam Mai Kia Rakha Hai") == "404 Braincells"
    assert canonical_team_name("IX", "404 braincells") == "404 Braincells"
    assert canonical_team_name("X", "Naam Mai Kia Rakha Hai") == "Naam Mai Kia Rakha Hai"


def test_roster_and_scorecard_must_match_and_have_both_rounds() -> None:
    groups = [{"class_code": "IX", "name": "404 Braincells"}]
    scores = {("IX", "404 Braincells"): {0: (9.0, 10.0), 1: (10.0, 15.0)}}
    validate_inputs(groups, scores)

    with pytest.raises(ValueError, match="roster-only"):
        validate_inputs(groups, {("IX", "Other Team"): {0: (9.0, 10.0), 1: (10.0, 15.0)}})

    with pytest.raises(ValueError, match="Expected Round 0 and Round 1"):
        validate_inputs(groups, {("IX", "404 Braincells"): {0: (9.0, 10.0)}})
