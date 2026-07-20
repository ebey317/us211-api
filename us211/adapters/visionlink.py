"""VisionLink CommunityOS adapter — reverse-engineered live endpoint.

VisionLink powers several state 211s (Indiana confirmed). Its public SPA is
backed by a JSON search API discovered by capturing the site's own network
traffic:

    POST {base_url}/guided_search/results/limit/{n}/offset/{o}/order/.../direction/asc
    Content-Type: application/json
    body: a "guided search" filter document keyed by taxonomy_id

The response is `{"result":"success","data":[ {sc_NNN: ...}, ... ]}` where the
`sc_NNN` keys are opaque column codes. The mapping below was decoded field by
field against live Indiana data (see FIELD MAP). Category -> taxonomy_id comes
from the site's own subcategory links.

No data is fabricated: if the upstream returns no usable rows, we return [].
"""
from __future__ import annotations

import json

import httpx

from us211.adapters.base import BaseAdapter
from us211.models import (
    Location,
    Organization,
    PhysicalAddress,
    Resource,
    Service,
)

_UA = "Mozilla/5.0 (compatible; us211-api/0.1; +https://github.com/ebey317/us211-api)"

# Decoded VisionLink CommunityOS field codes (verified against live IN data).
F_ORG_NAME = "sc_610"
F_ORG_DESC = "sc_614"
F_ORG_URL = "sc_606"
F_SVC_NAME = "sc_735"
F_SVC_DESC = "sc_728"
F_PHONE = "sc_726"
F_ADDR1 = "sc_675_address_1"
F_CITY = "sc_675_city"
F_STATE = "sc_675_state"
F_ZIP = "sc_675_zip"
F_LAT = "sc_675_latitude"
F_LNG = "sc_675_longitude"
F_STATUS = "sc_706"

# Normalized category -> VisionLink taxonomy_id(s). Sourced from the site's own
# guided-search subcategory links. Extend as more categories are mapped.
_CATEGORY_TAXONOMY: dict[str, list[int]] = {
    "food": [407761, 407770],        # Food Pantries (+ related)
    "food_pantry": [407761],
    "baby_food": [407769, 410327],
    # TODO: capture taxonomy_ids for housing/financial/utilities/etc from the
    # site's subcategory links (same technique) and add them here.
}

_ORDER = "site%5Csite_addressus%5Csite_addressus%5Czdr"


def _build_body(taxonomy_ids: list[int]) -> dict:
    """Construct the guided-search filter document VisionLink expects."""
    value = [{"taxonomy_id": t} for t in taxonomy_ids]
    return {
        "agency\\agency_system\\awtsv_keyword_feature": json.dumps({"operator": ["fulltext"]}),
        "service\\service_geotagus\\service_geotagusalternative": json.dumps(
            {"operator": ["servespart_array"]}
        ),
        "site\\site_addressus\\site_addressus": "{}",
        "agency\\agency\\id": json.dumps({"value": 0, "operator": ["greaterthan"]}),
        "service\\service_taxonomy\\module_servicepost": json.dumps(
            {"value": value, "operator": ["contains_array"]}
        ),
        "agency\\service\\id": json.dumps({"operator": ["equals"]}),
        "agency\\site\\id": json.dumps({"operator": ["equals"]}),
        "revision": {"revision": {"id": "", "record_name": "agency", "token": ""}},
    }


class VisionLinkAdapter(BaseAdapter):
    """Adapter for VisionLink CommunityOS 211 sites."""

    CATEGORY_MAP = {k: ",".join(map(str, v)) for k, v in _CATEGORY_TAXONOMY.items()}

    async def search(
        self,
        category: str,
        postal_code: str | None = None,
        state: str | None = None,
        limit: int = 25,
    ) -> list[Resource]:
        if not self.base_url:
            return []
        taxonomy_ids = _CATEGORY_TAXONOMY.get(category.lower())
        if not taxonomy_ids:
            # Category not yet mapped for this platform — honest empty result.
            return []

        url = (
            f"{self.base_url}/guided_search/results/limit/{limit}/offset/0"
            f"/order/{_ORDER}/direction/asc"
        )
        headers = {
            "User-Agent": _UA,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.base_url}/",
        }
        body = _build_body(taxonomy_ids)
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
            try:
                resp = await client.post(url, json=body)
            except httpx.HTTPError:
                return []
        if resp.status_code != 200:
            return []
        try:
            data = resp.json()
        except ValueError:
            return []
        if not isinstance(data, dict) or data.get("result") != "success":
            return []
        rows = data.get("data") or []
        return [self._to_resource(r, category) for r in rows if self._is_active(r)]

    @staticmethod
    def _is_active(row: dict) -> bool:
        status = (row.get(F_STATUS) or "").lower()
        return status in ("", "active")

    def _to_resource(self, row: dict, category: str) -> Resource:
        org_name = row.get(F_ORG_NAME) or "Unknown organization"
        org = Organization(
            id=f"vl-org-{abs(hash(org_name)) % 10_000_000}",
            name=org_name,
            description=row.get(F_ORG_DESC),
            url=self._norm_url(row.get(F_ORG_URL)),
        )
        service = Service(
            id=f"vl-svc-{abs(hash(org_name + str(row.get(F_SVC_NAME)))) % 10_000_000}",
            organization_id=org.id,
            name=row.get(F_SVC_NAME) or category.title(),
            description=row.get(F_SVC_DESC),
            status="active",
        )
        location = None
        lat, lng = row.get(F_LAT), row.get(F_LNG)
        if lat is not None and lng is not None:
            location = Location(
                id=f"vl-loc-{abs(hash(str(lat) + str(lng))) % 10_000_000}",
                name=org_name,
                latitude=lat,
                longitude=lng,
            )
        address = None
        if row.get(F_ADDR1):
            address = PhysicalAddress(
                address_1=row.get(F_ADDR1),
                city=row.get(F_CITY),
                state_province=row.get(F_STATE),
                postal_code=str(row.get(F_ZIP)) if row.get(F_ZIP) else None,
                country="US",
            )
        return Resource(
            category=category,
            source=self.source_name,
            organization=org,
            service=service,
            location=location,
            address=address,
            phone=row.get(F_PHONE),
        )

    @staticmethod
    def _norm_url(url: str | None) -> str | None:
        if not url:
            return None
        return url if url.startswith("http") else f"https://{url}"
