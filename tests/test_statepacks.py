"""Tests for state standard arrival packs."""
from __future__ import annotations

from fastapi.testclient import TestClient

from us211.main import app
from us211.statepacks import exists, list_states, load

client = TestClient(app)


def test_statepack_exists():
    assert exists("IN")


def test_statepack_loader():
    pack = load("IN")
    assert pack["state_code"] == "IN"
    assert pack["state_name"] == "Indiana"
    assert pack["sections"]
    section_ids = {s["id"] for s in pack["sections"]}
    assert "emergency" in section_ids
    assert "documents" in section_ids
    assert "food" in section_ids


def test_standard_endpoint_indiana():
    r = client.get("/standard", params={"state": "IN"})
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "IN"
    assert body["state_name"] == "Indiana"
    assert body["audience"]
    assert body["sections"]
    assert body["actions"]


def test_standard_endpoint_missing_state_404():
    r = client.get("/standard", params={"state": "ZZ"})
    assert r.status_code == 404


def test_standard_endpoint_unwired_state_404():
    # Alaska is a real state but has no pack yet
    if not exists("AK"):
        r = client.get("/standard", params={"state": "AK"})
        assert r.status_code == 404
