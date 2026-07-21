from app.tools.osm_contact import (
    cuisine_for_interest,
    extract_osm_contact,
    format_contact_suffix,
)


def test_extract_osm_contact_reads_phone_and_website():
    contact = extract_osm_contact(
        {
            "phone": "+1-555-0100",
            "contact:website": "https://example.com",
            "addr:street": "Main St",
            "addr:housenumber": "100",
            "addr:city": "Monterey",
            "addr:state": "CA",
            "opening_hours": "Mo-Sa 09:00-17:00",
        },
        category="museum",
    )

    assert contact["phone"] == "+1-555-0100"
    assert contact["website"] == "https://example.com"
    assert contact["address"] == "100 Main St, Monterey, CA"
    assert contact["opening_hours"] == "Mo-Sa 09:00-17:00"
    assert contact["reservation_required"] is True


def test_extract_osm_contact_respects_reservation_tag():
    contact = extract_osm_contact({"reservation": "no"}, category="museum")
    assert contact["reservation_required"] is False


def test_cuisine_for_interest_maps_thai_food():
    assert cuisine_for_interest("thai food") == "thai"


def test_format_contact_suffix_includes_available_fields():
    suffix = format_contact_suffix(
        {
            "phone": "+1-555-0100",
            "website": "https://example.com",
            "reservation_required": True,
        }
    )
    assert "phone=+1-555-0100" in suffix
    assert "website=https://example.com" in suffix
    assert "reservation recommended" in suffix
