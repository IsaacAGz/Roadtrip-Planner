from datetime import date

import pytest
from pydantic import ValidationError

from app.models.preferences import TripPreferences, format_preferences_for_prompt
from app.models.trip import TripRequest


def test_default_preferences():
    prefs = TripPreferences()
    assert prefs.pace == "moderate"
    assert prefs.budget == "moderate"
    assert prefs.accessibility is False
    assert prefs.interests == []


def test_interests_normalized_and_deduplicated():
    prefs = TripPreferences(interests=[" Breweries ", "breweries", "Scenic Views"])
    assert prefs.interests == ["breweries", "scenic_views"]


def test_interests_max_length_rejected():
    with pytest.raises(ValidationError):
        TripPreferences(interests=[f"interest_{i}" for i in range(11)])


def test_invalid_pace_rejected():
    with pytest.raises(ValidationError):
        TripPreferences(pace="fast")  # type: ignore[arg-type]


def test_invalid_budget_rejected():
    with pytest.raises(ValidationError):
        TripPreferences(budget="expensive")  # type: ignore[arg-type]


def test_format_preferences_includes_structured_fields():
    text = format_preferences_for_prompt(
        structured=TripPreferences(
            pace="relaxed",
            budget="budget",
            accessibility=True,
            interests=["museums", "coastal_views"],
        ),
        free_text="avoid toll roads",
    )
    assert "pace: relaxed" in text
    assert "budget: budget" in text
    assert "accessibility: True" in text
    assert "interests: museums, coastal_views" in text
    assert "additional notes: avoid toll roads" in text


def test_format_preferences_omits_empty_interests_and_notes():
    text = format_preferences_for_prompt(
        structured=TripPreferences(),
        free_text=None,
    )
    assert "interests:" not in text
    assert "additional notes:" not in text


def test_trip_request_defaults_structured_preferences():
    request = TripRequest(
        origin="San Jose, CA",
        destination="Monterey, CA",
        start_date=date(2026, 7, 15),
        end_date=date(2026, 7, 15),
    )
    assert request.structured_preferences.pace == "moderate"
    assert request.preferences is None


def test_trip_request_accepts_structured_preferences():
    request = TripRequest(
        origin="San Jose, CA",
        destination="Monterey, CA",
        start_date=date(2026, 7, 15),
        end_date=date(2026, 7, 16),
        preferences="coastal scenery",
        structured_preferences=TripPreferences(
            pace="relaxed",
            budget="moderate",
            accessibility=True,
            interests=["beaches"],
        ),
    )
    assert request.structured_preferences.pace == "relaxed"
    assert request.structured_preferences.interests == ["beaches"]
    assert request.preferences == "coastal scenery"
