"""Tests for the findhelp adapter + IP auto-resolution."""
from __future__ import annotations

import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from us211.adapters.findhelp import FindhelpAdapter, _FindhelpCardParser
from us211.main import app, resolve_location

client = TestClient(app)


def test_findhelp_parser_extracts_cards():
    html = """
    <div class="result">
      <a href="https://example.org/pantry">Food Pantry Of Town</a>
      <div>123 Main St, Springfield, IL 62701</div>
    </div>
    <div class="result">
      <a href="https://example.org/soup">Community Soup Kitchen</a>
    </div>
    """
    p = _FindhelpCardParser()
    p.feed(html)
    assert len(p.cards) >= 2
    names = {c["name"] for c in p.cards}
    assert "Food Pantry Of Town" in names


def test_findhelp_parser_splits_address():
    html = '<div class="listing"><a href="https://x.org">Helping Hands</a><div>9 Elm St, Austin, TX 73301</div></div>'
    p = _FindhelpCardParser()
    p.feed(html)
    assert p.cards[0]["name"] == "Helping Hands"
    assert p.cards[0]["address"] == "9 Elm St, Austin, TX 73301"


def test_ip_resolution_local_returns_none():
    class FakeReq:
        class _Client:
            host = "127.0.0.1"

        headers = {}
        client = _Client()

    state, city, method = asyncio.run(resolve_location(FakeReq()))
    assert state is None
    assert method == "local"


def test_ip_resolution_public_returns_state():
    class FakeResp:
        status_code = 200

        def json(self):
            return {
                "status": "success",
                "countryCode": "US",
                "regionName": "Indiana",
                "city": "Indianapolis",
            }

    class FakeReq:
        class _Client:
            host = "8.8.8.8"

        headers = {}
        client = _Client()

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=FakeResp())):
        state, city, method = asyncio.run(resolve_location(FakeReq()))
    assert state == "IN"
    assert method == "ip"
    assert city == "Indianapolis"
