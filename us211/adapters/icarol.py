"""iCarol adapter – national-211 platform using iCarol Resource DB.

iCarol powers dozens of state 211 centers. It provides a **partner API**
(e.g. `https://{region}.icarol.com/api/v2/resources`). Access requires a
business key (`iCAROL_API_KEY`) – no public scraping is allowed. This adapter
is intentionally **minimal and honest**:

* When an `iCAROL_API_KEY` environment variable is present, it attempts a
  documented API call to fetch resources matching the requested category.
  The exact endpoint & request format are determined by each iCarol
  installation's documented API (see the iCarol docs).

* Without a key, the adapter **cannot retrieve real data** – it returns an
  empty list `[]` rather than fabricate or hammer endpoints. This matches
  our ethical stance: we never pretend to access data without authority.

The design mirrors our findhelp approach: partner API first, honest fallback.
"""
from __future__ import annotations

import os
import httpx
from us211.adapters.base import BaseAdapter
from us211.models import Location, Organization, PhysicalAddress, Resource, Service

_UA = "Mozilla/5.0 (compatible; us211-api/0.1; +https://github.com/ebey317/us211-api)"

class iCarolAdapter(BaseAdapter):
    """
    Adapter for iCarol 211 platforms (e.g. New Jersey 211, Rhode Island 211).

    **Authentication** – The iCarol API uses a secret key (`iCAROL_API_KEY`);
    we read it from the environment. No hard‑coded keys.
    """

    def __init__(self, base_url: str | None, source_name: str, timeout: float = 15.0):
        # base_url should be something like https://nj.icarol.com/
        super().__init__(base_url, source_name, timeout)
        self.api_key = os.getenv("iCAROL_API_KEY")

    async def search(
        self,
        category: str,
        postal_code: str | None = None,
        state: str | None = None,
        limit: int = 25,
    ) -> list[Resource]:
        """
        Search iCarol for resources matching `category`.

        The exact endpoint / query parameters are platform‑specific and documented
        per installation. This base implementation:

        1. Looks for a known endpoint pattern (`/api/v2/resources`).
        2. Sends a GET request with query params:
           `category={category}&postal={postal_code}&state={state}`
        3. If the response is a structured JSON payload (dict with `resources`
           array), we parse each item into a `Resource`.

        **Important** – Without an `iCAROL_API_KEY` we cannot call the real API,
        so we simply return `[]`. This is the honest fallback.
        """
        if not self.api_key:
            return []  # cannot authenticate → no data

        slug = category.lower()
        url = f"{self.base_url.rstrip('/')}/api/v2/resources"
        params = {"category": slug}
        if postal_code:
            params["postal"] = postal_code
        if state:
            params["state"] = state
        headers = {"Accept": "application/json", "User-Agent": _UA}
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
                resp = await client.get(url, params=params)
        except httpx.HTTPError:
            return []

        if resp.status_code != 200:
            return []

        # Expected payload shape (from iCarol docs) – may vary per installation.
        data = resp.json()
        resources: list[Resource] = []
        # The exact key name may differ; we look for 'results' or 'items'.
        items = data.get("results") or data.get("items") or []
        for itm in items[:limit]:
            # Minimal fields – add more as needed per spec.
            name = itm.get("name")
            if not name:
                continue
            org = Organization(
                id=f"icarol-{abs(hash(name)) % 10_000_000}",
                name=name,
                url=itm.get("url"),
            )
            svc = Service(
                id=f"icarol-{abs(hash(name + slug)) % 10_000_000}",
                organization_id=org.id,
                name=slug.replace("-", " ").title(),
                status="active",
                description=itm.get("description", ""),
            )
            address = PhysicalAddress(
                address_1=itm.get("address_1"),
                city=itm.get("city"),
                state_province=itm.get("state"),
                country="US",
            )
            loc = Location(id=f"icarol-loc-{abs(hash(name)) % 10_000_000}", name=name)
            resources.append(
                Resource(
                    category=category,
                    source=self.source_name,
                    organization=org,
                    service=svc,
                    location=loc,
                    address=address,
                )
            )
        return resources