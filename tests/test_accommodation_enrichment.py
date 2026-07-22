from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.models.trip import TripRequest
from app.services.accommodation_enrichment import enrich_accommodations
from tests.helpers import sample_plan


def _request(**kwargs) -> TripRequest:
    defaults = {
        "origin": "San Jose, CA",
        "destination": "Monterey, CA",
        "start_date": date(2026, 7, 15),
        "end_date": date(2026, 7, 15),
    }
    defaults.update(kwargs)
    return TripRequest(**defaults)


@pytest.mark.asyncio
async def test_enrich_accommodations_skips_when_property_name_present():
    plan = sample_plan(days=1)
    plan.days[0].overnight.property_name = "Existing Hotel"
    request = _request()

    with patch(
        "app.services.accommodation_enrichment._fetch_accommodations_nearby",
        new=AsyncMock(),
    ) as fetch_mock:
        result = await enrich_accommodations(plan, request)

    fetch_mock.assert_not_called()
    assert result.days[0].overnight.property_name == "Existing Hotel"


@pytest.mark.asyncio
async def test_enrich_accommodations_fills_missing_property_name():
    plan = sample_plan(days=1)
    plan.days[0].overnight.property_name = None
    request = _request()

    with patch(
        "app.services.accommodation_enrichment._fetch_accommodations_nearby",
        new=AsyncMock(
            return_value=[
                {
                    "property_name": "Monterey Inn",
                    "phone": "+1-555-0100",
                    "website": "https://hotel.example",
                    "address": "1 Main St",
                    "opening_hours": "24/7",
                    "reservation_required": True,
                }
            ]
        ),
    ):
        result = await enrich_accommodations(plan, request)

    overnight = result.days[0].overnight
    assert overnight.property_name == "Monterey Inn"
    assert overnight.contact.phone == "+1-555-0100"
    assert overnight.contact.website == "https://hotel.example"
