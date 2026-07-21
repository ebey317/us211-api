"""Tests for the iCarol adapter (partner API required)."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import os
import pytest

from us211.adapters.icarol import iCarolAdapter
from us211.models import Location, Organization, Resource, Service


@pytest.mark.asyncio
async def test_ic_senerf_without_key_returns_empty():
    # Without iCAROL_API_KEY, adapter should return []
    adapter = iCarolAdapter(base_url="https://nj.icarol.com/", source_name="iCarol")
    # ensure key is unset
    with patch.dict(os.environ, {}, clear=False):
        if "iCAROL_API_KEY" in os.environ:
            del os.environ["iCAROL_API_KEY"]
        results = await adapter.search("food", postal_code="07101")
        assert results == []


@pytest.mark.asyncio
async def test_ic_senerf_with_key_mocked_fetch():
    # Mock the partner API call to simulate JSON response
    mock_payload = {
        "results": [
            {
                "name": "Food Pantry of New Jersey",
                "url": "https://example.org/pantry",
                "description": "Monthly food assistance.",
                "address_1": "123 Main St",
                "city": "Newark",
                "state": "NJ",
                "zip": "07101",
            }
        ]
    }
    from us211.adapters.icarol import _UA

    with patch.dict(os.environ, {"iCAROL_API_KEY": "fake_key"}):
        adapter = iCarolAdapter(base_url="https://nj.icarol.com/", source_name="iCarol")
        with patch("httpx.AsyncClient.get", new=AsyncMock()) as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = lambda: mock_payload
            mock_get.return_value = mock_response
            results = await adapter.search("food", postal_code="07101")
            assert len(results) == 1
            res = results[0]
            assert isinstance(res, Resource)
            assert res.organization.name == "Food Pantry of New Jersey"
            assert res.organization.url == "https://example.org/pantry"
            assert res.service.description == "Monthly food assistance."
            assert res.address.city == "Newark"
            assert res.address.state_province == "NJ"
            assert res.address.country == "US"


@pytest.mark.asyncio
async def test_ic_senerf_invalid_status_returns_empty():
    with patch.dict(os.environ, {"iCAROL_API_KEY": "fake_key"}):
        adapter = iCarolAdapter(base_url="https://nj.icarol.com/", source_name="iCarol")
        with patch("httpx.AsyncClient.get", new=AsyncMock()) as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_response.json = lambda: {}
            mock_get.return_value = mock_response
            results = await adapter.search("food", postal_code="07101")
            assert results == []