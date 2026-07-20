"""Tests for the assistant layer: /ask endpoint, actions, agent prompts."""
from __future__ import annotations

from fastapi.testclient import TestClient

from us211.actions import email_copy, fill_form, print_list, speak
from us211.agent import recommend_actions, summarize
from us211.main import app
from us211.models import (
    Location,
    Organization,
    PhysicalAddress,
    Resource,
    Service,
)

client = TestClient(app)


def _sample_resource(name: str = "Guidance Ministries") -> Resource:
    return Resource(
        category="food",
        source="Indiana 211",
        organization=Organization(
            id="vl-org-1", name=name, description="A food pantry.", url="https://example.org"
        ),
        service=Service(id="vl-svc-1", organization_id="vl-org-1", name="Food Pantry",
                        description="Weekly food distribution.", status="active"),
        location=Location(id="vl-loc-1", name=name, latitude=41.6, longitude=-85.9),
        address=PhysicalAddress(address_1="216 N 2nd St", city="Elkhart",
                                state_province="IN", postal_code="46516", country="US"),
        phone="574-296-7192",
    )


def test_ask_indiana_live_shape():
    r = client.get("/ask", params={"state": "IN", "category": "food"})
    assert r.status_code in (200, 502)  # 502 only if upstream is flaky right now
    if r.status_code == 200:
        body = r.json()
        assert body["state"] == "IN"
        assert "summary" in body
        assert isinstance(body["resources"], list)
        # actions are always offered when there are results
        if body["resources"]:
            assert any(a["kind"] == "email" for a in body["actions"])
            assert any(a["kind"] == "read_aloud" for a in body["actions"])


def test_ask_unknown_state_404():
    r = client.get("/ask", params={"state": "ZZ", "category": "food"})
    assert r.status_code == 404


def test_ask_unwired_state_501():
    r = client.get("/ask", params={"state": "WY", "category": "food"})
    assert r.status_code == 501


def test_capabilities_endpoint():
    r = client.get("/capabilities")
    assert r.status_code == 200
    kinds = {c["kind"] for c in r.json()}
    assert {"summarize", "read_aloud", "print", "email", "pinpoint", "fill_form"} <= kinds


def test_recommend_actions_offers_all():
    acts = recommend_actions([_sample_resource()])
    kinds = {a.kind for a in acts}
    assert {"summarize", "read_aloud", "print", "email", "pinpoint", "fill_form"} <= kinds


def test_summarize_empty_is_honest():
    assert "No food" in summarize([], "food", "IN")


def test_email_copy_without_hook_is_honest():
    # No mail hook registered -> must NOT claim it sent.
    res = email_copy([_sample_resource()], "food", "IN", to="person@example.com")
    assert res.ok is False
    assert "not sent" in res.message.lower()


def test_speak_without_hook_is_honest():
    res = speak([_sample_resource()], "food", "IN")
    assert res.ok is False
    assert "not available" in res.message.lower()
    assert "script" in res.detail


def test_print_without_hook_is_honest():
    res = print_list([_sample_resource()], "food", "IN")
    assert res.ok is False
    assert "not available" in res.message.lower()


def test_fill_form_builds_draft():
    res = fill_form(_sample_resource(), {"name": "Jane", "email": "jane@example.com"})
    assert res.ok is True
    assert res.message.startswith("Prepared a pre-filled")
    assert res.detail["draft"]["resource"] == "Guidance Ministries"
