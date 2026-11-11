"Demo data can only enter its new empty bound copy, never the clean source."

from types import SimpleNamespace

import pytest

from tools.prepare_demo_preview import configuration, guard

DEMO = "CBN_P3ES_TRIAL_20261026_1234abcd"
CLEAN = "CBN_P3ES_TRIAL_20261026_606a9bec"


def settings(database=DEMO, username="cbn_workspace_es_1234abcd"):
    return SimpleNamespace(
        connection={"database": database, "username": username},
        ticket={"identity": {"database": DEMO}},
    )


def test_new_empty_bound_demo_is_allowed():
    guard({"database": DEMO}, settings(), CLEAN, False)


@pytest.mark.parametrize(
    "profile,current,clean,occupied",
    [
        ({"database": "HORARIOSSIIE"}, settings(), CLEAN, False),
        ({"database": DEMO}, settings(), DEMO, False),
        ({"database": DEMO}, settings(database=CLEAN), CLEAN, False),
        ({"database": DEMO}, settings(username="sa"), CLEAN, False),
        ({"database": DEMO}, settings(), CLEAN, True),
    ],
)
def test_existing_unbound_or_academic_destinations_are_rejected(
    profile, current, clean, occupied
):
    with pytest.raises(ValueError, match="demo_requires_new_empty_bound_copy"):
        guard(profile, current, clean, occupied)


def test_program_interest_does_not_claim_official_academic_identity():
    document = configuration()
    assert document["fields"][0]["key"] == "programa_interes"
    assert all(stage["probability"] is None for stage in document["stages"])
