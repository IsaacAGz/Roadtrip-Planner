from datetime import date

from app.models.itinerary import DayPlan, OvernightStop, PlaceContact, RoadtripPlan, Stop


def test_place_contact_defaults():
    contact = PlaceContact()
    assert contact.phone is None
    assert contact.reservation_required is False


def test_stop_includes_contact_with_defaults():
    stop = Stop(name="Museum", lat=36.6, lon=-121.9, category="museum", country_code="US")
    assert stop.contact.phone is None


def test_overnight_includes_property_name_and_contact():
    overnight = OvernightStop(
        city="Monterey",
        lat=36.6,
        lon=-121.9,
        property_name="Monterey Bay Inn",
        contact=PlaceContact(phone="+1-555-0100", website="https://example.com"),
        country_code="US",
    )
    assert overnight.property_name == "Monterey Bay Inn"
    assert overnight.contact.phone == "+1-555-0100"


def test_plan_json_for_llm_prompt_excludes_route_geometry():
    plan = RoadtripPlan(
        title="Test",
        total_days=1,
        origin_lat=36.0,
        origin_lon=-121.0,
        destination_lat=36.1,
        destination_lon=-121.1,
        route_geometry=[[36.0, -121.0], [36.1, -121.1]],
        days=[
            DayPlan(
                day=1,
                date=date(2026, 7, 15),
                route_summary="Drive",
                overnight=OvernightStop(city="Monterey", lat=36.6, lon=-121.9, country_code="US"),
                stops=[
                    Stop(
                        name="Museum",
                        lat=36.6,
                        lon=-121.9,
                        category="museum",
                        country_code="US",
                        contact=PlaceContact(phone="+1-555-0100"),
                    )
                ],
            )
        ],
    )

    prompt_json = plan.json_for_llm_prompt()

    assert "route_geometry" not in prompt_json
    assert "+1-555-0100" in prompt_json
