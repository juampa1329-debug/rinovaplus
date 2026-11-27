import pytest
from fastapi import HTTPException

from app.institutional.workspace import page_changed


def test_live_inbox_page_reports_activity_change_instead_of_blocking_navigation():
    assert page_changed("inbox", 25, "30", "31", live_pages=True)
    assert not page_changed("inbox", 25, "31", "31", live_pages=True)


@pytest.mark.parametrize("area,live", [("clients", True), ("clients", False), ("inbox", False)])
def test_existing_strict_readers_keep_their_consistency_contract(area, live):
    with pytest.raises(HTTPException, match="page_changed"):
        page_changed(area, 25, "30", "31", live_pages=live)


@pytest.mark.parametrize("live", [True, False])
def test_next_page_still_requires_an_anchor(live):
    with pytest.raises(HTTPException, match="page_anchor_required"):
        page_changed("inbox", 25, "", "31", live_pages=live)
