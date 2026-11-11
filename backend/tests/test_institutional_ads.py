"""Closed P9 documents, provenance and provider normalization without SQL."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.institutional.ads import stable
from app.institutional.ads_models import Account, Campaign, Credential, Intake
from app.institutional.ads_receipts import normalize


def test_account_normalizes_Meta_prefix_without_inventing_verification():
    value = Account(external_account_id="act_12345", name="CBN")
    assert value.external_account_id == "12345" and value.integration_id is None


@pytest.mark.parametrize(
    "extra",
    [
        {"timezone": "Mars/CBN"},
        {"external_account_id": " secret id"},
        {"form_ids": ["1", "1"]},
        {"provider": "woocommerce"},
        {"name": "x" * 181},
        {"currency": "cop"},
    ],
)
def test_closed_account_rejects_invalid_or_unsupported_fields(extra):
    with pytest.raises(ValidationError):
        Account(**(dict(external_account_id="123", name="CBN") | extra))


@pytest.mark.parametrize(
    "metrics",
    [{"ctr": float("nan")}, {"cpc": float("inf")}, {"ctr": 101}, {"leads": -1}],
)
def test_metrics_are_finite_bounded_and_require_explicit_period(metrics):
    with pytest.raises(ValidationError):
        Campaign(
            account_id=uuid4(),
            external_campaign_id="123",
            name="CBN",
            metrics_json=metrics,
            period_start="2026-10-01",
            period_end="2026-10-27",
        )


@pytest.mark.parametrize(
    "extra",
    [
        {"metrics_json": {}},
        {"period_start": "2026-10-27", "period_end": "2026-10-01"},
        {"period_start": "2026-02-30", "period_end": "2026-10-01"},
        {"daily_budget_cents": -1},
    ],
)
def test_campaign_budget_and_period_are_recorded_local_values(extra):
    with pytest.raises(ValidationError):
        Campaign(account_id=uuid4(), external_campaign_id="123", name="CBN", **extra)


def test_unknown_privilege_or_credential_cannot_be_mass_assigned():
    with pytest.raises(ValidationError):
        Account(external_account_id="123", name="CBN", provider_verified=True)
    with pytest.raises(ValidationError):
        Intake(account_id=uuid4(), external_id="lead", consent=True)


def test_meta_leadgen_keeps_route_and_explicit_ids_but_drops_injected_state():
    raw = dict(
        object="page",
        entry=[
            dict(
                id="page123",
                changes=[
                    dict(
                        field="leadgen",
                        value=dict(
                            leadgen_id="lead123",
                            form_id="form1",
                            field_data=[dict(name="full_name", values=["Ana"])],
                            _crm={"consent": True, "contact_id": str(uuid4())},
                        ),
                    )
                ],
            )
        ],
    )
    result = normalize("meta", raw, datetime(2026, 10, 27))
    assert (
        len(result) == 1
        and result[0]["route"] == "page123"
        and result[0]["document"]["contact_name"] == "Ana"
    )
    assert (
        result[0]["document"]["external_id"] == "lead123"
        and "_crm" not in result[0]["document"]
    )


def test_social_comment_delete_is_distinct_from_DM_or_permission():
    result = normalize(
        "meta",
        dict(
            object="instagram",
            entry=[
                dict(
                    id="ig1",
                    changes=[
                        dict(
                            field="comments",
                            value=dict(
                                id="comment1",
                                text="Info",
                                verb="remove",
                                **{"from": {"id": "author1", "username": "Ana"}},
                            ),
                        )
                    ],
                )
            ],
        ),
        datetime(2026, 10, 27),
    )
    assert (
        result[0]["document"]["status"] == "deleted"
        and result[0]["document"]["author_id"] == "author1"
    )
    assert result[0]["kind"] == "comment"


def test_DM_payload_is_not_reclassified_as_ad_lead():
    assert (
        normalize(
            "meta",
            dict(
                object="page",
                entry=[
                    dict(
                        id="page1",
                        messaging=[{"message": {"mid": "x", "text": "Info"}}],
                    )
                ],
            ),
            datetime(2026, 10, 27),
        )
        == []
    )


def test_missing_lead_id_is_not_invented_from_phone_or_email():
    with pytest.raises(ValueError):
        normalize(
            "meta",
            dict(
                entry=[
                    dict(
                        id="page1",
                        changes=[
                            dict(field="leadgen", value=dict(email="a@example.invalid"))
                        ],
                    )
                ]
            ),
            datetime(2026, 10, 27),
        )


def test_tiktok_nested_form_answers_have_stable_explicit_identity():
    value = dict(
        event="lead_generation",
        user_openid="business1",
        content={
            "data": [
                {
                    "lead_id": "lead1",
                    "advertiser_id": "123",
                    "answers": {"email": "a@example.invalid", "full_name": "Ana"},
                }
            ]
        },
    )
    result = normalize("tiktok", value, datetime(2026, 10, 27))
    assert (
        len(result) == 1
        and result[0]["route"] == "business1"
        and result[0]["advertiser"] == "123"
        and result[0]["document"]["email"] == "a@example.invalid"
    )


def test_intake_captured_time_requires_timezone():
    with pytest.raises(ValidationError):
        Intake(account_id=uuid4(), external_id="1", captured_at="2026-10-27T00:00:00")


def test_account_scoped_stable_id_differs_for_same_external_identity():
    assert stable("institution", "account-a", "lead", "facebook", "1") != stable(
        "institution", "account-b", "lead", "facebook", "1"
    )


def test_secret_serialization_never_contains_clear_text():
    value = Credential(operation_id=uuid4(), value="controlled-private-token")
    assert "controlled-private-token" not in value.model_dump_json()


@pytest.mark.parametrize(
    "phone", ["abc", "xyz", "+", "123", "+57300+0000000", "５７３０００００００００"]
)
def test_malformed_phone_does_not_merge_unrelated_leads(phone):
    from app.institutional.ads import identity_subject

    doc = dict(author_id="", phone=phone, email="")
    assert identity_subject(doc, "lead", "a") != identity_subject(doc, "lead", "b")


def test_valid_phone_format_variants_share_only_explicit_identity():
    from app.institutional.ads import identity_subject

    assert identity_subject(
        dict(author_id="", phone="+57 (300) 000-0093", email=""), "lead", "a"
    ) == identity_subject(
        dict(author_id="", phone="573000000093", email=""), "lead", "b"
    )


@pytest.mark.parametrize(
    "item,kind",
    [
        (dict(action="form_submit", id="lead1", form_id="f1"), "lead"),
        (dict(id="comment1", commentText="Pregunta"), "comment"),
    ],
)
def test_tiktok_explicit_form_and_comment_aliases_keep_account_route(item, kind):
    out = normalize(
        "tiktok",
        dict(user_openid="business", advertiser_id="ad", content=item),
        datetime(2026, 10, 27),
    )
    assert len(out) == 1 and out[0]["kind"] == kind and out[0]["route"] == "business"


def test_tiktok_nested_comment_keeps_explicit_id_and_author():
    out = normalize(
        "tiktok",
        dict(
            user_openid="business",
            advertiser_id="ad",
            event="comment_received",
            content=dict(comment=dict(id="C1", text="Pregunta", user=dict(id="U1"))),
        ),
        datetime(2026, 10, 27),
    )
    assert (
        len(out) == 1
        and out[0]["document"]["external_id"] == "C1"
        and out[0]["document"]["author_id"] == "U1"
        and out[0]["document"]["message"] == "Pregunta"
    )
