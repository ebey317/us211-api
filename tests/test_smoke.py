"""Smoke tests for the us211-api surface."""
from fastapi.testclient import TestClient

from us211.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_states_count():
    r = client.get("/states")
    assert r.status_code == 200
    data = r.json()
    # 50 states + DC + 5 territories = 56
    assert len(data) >= 56


def test_resources_indiana_wired():
    # Indiana is wired to VisionLink; may return an empty list (endpoint not
    # yet confirmed) but must be a successful 200 with a JSON array.
    r = client.get("/resources", params={"state": "IN", "category": "food"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_resources_unknown_state():
    r = client.get("/resources", params={"state": "ZZ", "category": "food"})
    assert r.status_code == 404


def test_resources_unwired_state():
    # Wyoming is registered but platform unknown -> 501.
    r = client.get("/resources", params={"state": "WY", "category": "food"})
    assert r.status_code == 501
