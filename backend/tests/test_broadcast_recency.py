"""Campaign recency uses observed inbound messages, never imported dates."""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.institutional import broadcast_audience as audience

TODAY = date(2026, 11, 17)
PERSON = {"CustomValues": '{"genero":"Mujer"}'}
DOCUMENT = {"demographic_fields": {"gender": "genero"}, "filters": {}}


@pytest.mark.parametrize(
    "days,bucket",
    [
        (0, "0_29"),
        (29, "0_29"),
        (30, "30_59"),
        (59, "30_59"),
        (60, "60_89"),
        (89, "60_89"),
        (90, "90_plus"),
        (200, "90_plus"),
        (-1, "unknown"),
    ],
)
def test_incoming_recency_boundaries_and_combined_filters(days, bucket):
    stamp = datetime(2026, 11, 17, 17, tzinfo=timezone.utc) - timedelta(days=days)
    person = dict(PERSON, LastIncomingAt=stamp)
    assert audience.incoming_bucket(person, DOCUMENT, TODAY) == bucket
    assert audience.matches(
        person, dict(DOCUMENT, filters={"last_incoming_bucket": bucket}), TODAY
    )
    assert not audience.matches(
        person,
        dict(DOCUMENT, filters={"last_incoming_bucket": bucket, "genders": ["Hombre"]}),
        TODAY,
    )


@pytest.mark.parametrize("stamp", [None, "invalid", ""])
def test_missing_contact_evidence_never_falls_back_to_registration(stamp):
    person = dict(
        PERSON,
        LastIncomingAt=stamp,
        CreatedAt="2026-01-01",
        CustomValues='{"pre_ultima_gestion":"2026-09-01"}',
    )
    assert audience.incoming_bucket(person, DOCUMENT, TODAY) == "unknown"
    assert not audience.matches(
        person, dict(filters={"last_incoming_bucket": "60_89"}), TODAY
    )


def test_incoming_date_uses_campaign_timezone_and_profile_snapshot():
    person = dict(PERSON, LastIncomingAt="2026-10-19T02:00:00Z")
    assert audience.incoming_bucket(person, DOCUMENT, TODAY) == "30_59"
    assert audience.incoming_bucket(person, dict(timezone="UTC"), TODAY) == "0_29"
    assert audience.details(person, DOCUMENT, TODAY)[0]["last_incoming"] == "30–59 días"


def test_program_interest_contains_is_explicit_and_exact_stays_default():
    person = dict(PERSON, CustomValues='{"programas":"BARISMO | BARTENDER"}')
    field = dict(field_key="programas", values=["Barismo"])
    assert not audience.matches(person, dict(filters={"custom_fields": [field]}), TODAY)
    assert audience.matches(
        person, dict(filters={"custom_fields": [dict(field, match="contains")]}), TODAY
    )
    assert not audience.matches(
        person,
        dict(
            filters={
                "custom_fields": [dict(field, values=["Aduanas"], match="contains")]
            }
        ),
        TODAY,
    )
    assert not audience.matches(
        dict(PERSON, CustomValues="{}"),
        dict(filters={"custom_fields": [dict(field, match="contains")]}),
        TODAY,
    )
