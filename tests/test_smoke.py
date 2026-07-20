"""Smoke tests for the us211-api surface (registry + adapter parsing)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from us211.adapters.visionlink import VisionLinkAdapter
from us211.main import app
from us211.models import Resource
from us211.registry import PlatformType, get_source

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_states_count():
    r = client.get("/states")
    assert r.status_code == 200
    # 50 states + DC + 5 territories
    assert len(r.json()) >= 56


def test_resources_indiana_live():
    # Indiana is wired to VisionLink and returns real food data when the
    # upstream is responsive. We accept an empty list (upstream flaky/rate
    # limited) but never a crash / fabricated record.
    r = client.get("/resources", params={"state": "IN", "category": "food"})
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    for rec in body:
        assert rec["organization"]["name"]
        assert rec["source"] == "Indiana 211"


def test_resources_unknown_state_501():
    r = client.get("/resources", params={"state": "WY", "category": "food"})
    assert r.status_code == 501


def test_resources_bad_state_404():
    r = client.get("/resources", params={"state": "ZZ", "category": "food"})
    assert r.status_code == 404


def test_visionlink_parsing_wisconsin():
    """Lock the per-instance field-code parsing for Wisconsin (sc_388 etc.).

    Uses a captured-shape row so the logic is regression-tested without
    depending on the flaky upstream endpoint.
    """
    row = {
        "sc_388": "GRACE EPISCOPAL CHURCH",
        "sc_384": "http://www.gracechurchmadison.org",
        "sc_510": "GRACE FOOD PANTRY",
        "sc_521": "ID required for Dane County residents.",
        "sc_1665": "608-255-5147",
        "sc_493_address_1": "116 West Washington Avenue",
        "sc_493_city": "Madison",
        "sc_493_state": "WI",
        "sc_493_zip": "53703",
        "sc_493_latitude": 43.0739585,
        "sc_493_longitude": -89.3861384,
    }
    fmap = {
        "org_name": "sc_388", "org_url": "sc_384", "svc_name": "sc_510",
        "svc_desc": "sc_521", "phone": "sc_1665", "addr_1": "sc_493_address_1",
        "city": "sc_493_city", "state": "sc_493_state", "zip": "sc_493_zip",
        "lat": "sc_493_latitude", "lng": "sc_493_longitude",
    }
    ad = VisionLinkAdapter(base_url="https://211wisconsin.communityos.org/",
                            source_name="Wisconsin 211")
    res: Resource = ad._to_resource(row, fmap, "food")
    assert res.organization.name == "GRACE EPISCOPAL CHURCH"
    assert res.phone == "608-255-5147"
    assert res.address.city == "Madison"
    assert res.address.state_province == "WI"
    assert res.location.latitude == pytest.approx(43.0739585)
    assert res.source == "Wisconsin 211"
