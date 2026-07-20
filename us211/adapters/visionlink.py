"""VisionLink CommunityOS adapter — reverse-engineered, instance-aware.

VisionLink (a United Way product) powers several state 211s (IN, ID, WI
confirmed) on the CommunityOS platform. Its public SPA is backed by a JSON
search API discovered by capturing the site's own network traffic:

    POST {base_url}/guided_search/results/limit/{n}/offset/{o}/order/.../direction/asc
    Content-Type: application/json
    body: a "guided search" filter document keyed by taxonomy_id

The response is {"result":"success","data":[ {sc_NNN: ...}, ... ]} where sc_NNN
are **opaque, per-instance** column codes. We verified that Indiana's codes
(sc_610 = org name) differ from Wisconsin's (sc_388 = org name), so field codes
are NOT shared across instances. We therefore pin the codes we have *confirmed
against live data* in _KNOWN_INSTANCES, and fall back to heuristic auto-detection
for any new instance.

Category -> taxonomy_id comes from the site's own guided-search subcategory
links (captured once; the food codes 407761/407770 are shared across instances).

No data is fabricated: if the upstream returns no usable rows, we return [].
"""
from __future__ import annotations

import asyncio
import json
import re

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

_PHONE_RE = re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
_URL_RE = re.compile(r"^https?://", re.I)

# Normalized category -> VisionLink taxonomy_id(s). Sourced from the site's own
# guided-search subcategory links. Extend as more categories are mapped.
# (407761 = Food Pantries, 407770 = related food; shared across instances.)
_CATEGORY_TAXONOMY: dict[str, list[int]] = {
    "food": [407761, 407770],
    "food_pantry": [407761],
    "baby_food": [407769, 410327],
    # TODO: capture taxonomy_ids for housing/financial/utilities/etc from the
    # site's subcategory links (same technique) and add them here.
}

_ORDER = "site%5Csite_addressus%5Csite_addressus%5Czdr"

# Confirmed per-instance field codes (verified against live data 2026-07-20).
# VisionLink CommunityOS field codes are per-instance, NOT shared, so we pin
# the ones we've confirmed and fall back to auto-detection for new instances.
_KNOWN_INSTANCES: dict[str, dict] = {
    "https://in211.communityos.org": {
        "org_name": "sc_610", "org_url": "sc_606", "svc_name": "sc_735",
        "svc_desc": "sc_728", "phone": "sc_726", "addr_1": "sc_675_address_1",
        "city": "sc_675_city", "state": "sc_675_state", "zip": "sc_675_zip",
        "lat": "sc_675_latitude", "lng": "sc_675_longitude",
    },
    "https://211wisconsin.communityos.org": {
        "org_name": "sc_388", "org_url": "sc_384", "svc_name": "sc_510",
        "svc_desc": "sc_521", "phone": "sc_1665", "addr_1": "sc_493_address_1",
        "city": "sc_493_city", "state": "sc_493_state", "zip": "sc_493_zip",
        "lat": "sc_493_latitude", "lng": "sc_493_longitude",
    },
    "https://211-idaho.communityos.org": {
        "org_name": "sc_610", "org_url": "sc_606", "svc_name": "sc_735",
        "svc_desc": "sc_728", "phone": "sc_864", "addr_1": "sc_673_address_1",
        "city": "sc_673_city", "state": "sc_673_state", "zip": "sc_673_zip",
        "lat": "sc_673_latitude", "lng": "sc_673_longitude",
    },
    # TN (easttn211) returned 0 rows for food taxonomy 407761 — food may be
    # under a different taxonomy_id there; left to auto-detect once confirmed.
}


def _field_by_suffix(row: dict, suffixes: tuple[str, ...]) -> str | None:
    for k in row:
        if any(k.endswith(s) for s in suffixes):
            return k
    return None


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


def _norm_url(url: str | None) -> str | None:
    if not url:
        return None
    return url if url.startswith("http") else f"https://{url}"


def _auto_detect(row: dict) -> dict:
    """Best-effort field-code detection for unconfirmed VisionLink instances.

    Fallback only. Detects address/geo by suffix and phone/url by pattern;
    name falls back to the longest short title-cased free-text field.
    """
    fm: dict[str, str | None] = {}
    fm["addr_1"] = _field_by_suffix(row, ("_address_1",))
    fm["city"] = _field_by_suffix(row, ("_city",))
    fm["state"] = _field_by_suffix(row, ("_state",))
    fm["zip"] = _field_by_suffix(row, ("_zip",))
    fm["lat"] = _field_by_suffix(row, ("_latitude",))
    fm["lng"] = _field_by_suffix(row, ("_longitude",))
    for k, v in row.items():
        if fm.get("phone") is None and isinstance(v, str) and _PHONE_RE.search(v):
            fm["phone"] = k
        if fm.get("org_url") is None and isinstance(v, str) and _URL_RE.match(v) and len(v) < 200:
            fm["org_url"] = k
    best, best_len = None, 0
    for k, v in row.items():
        if not isinstance(v, str) or not (3 <= len(v) <= 80):
            continue
        if _URL_RE.match(v) or _PHONE_RE.search(v) or re.match(r"^\d{4}-\d{2}", v):
            continue
        if any(k.endswith(s) for s in ("_city", "_state", "_zip", "_county",
                                        "_country", "_latitude", "_longitude",
                                        "_address", "_href_label", "_id", "_ids",
                                        "_taxonomy", "_status")):
            continue
        if " " in v and v == v.title() and len(v) > best_len:
            best, best_len = k, len(v)
    fm["org_name"] = best
    fm["svc_name"] = best
    return {k: v for k, v in fm.items() if v is not None}


class VisionLinkAdapter(BaseAdapter):
    """Adapter for VisionLink CommunityOS 211 sites (IN/ID/WI/...)."""

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
            return []  # category not yet mapped — honest empty result

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
        # The VisionLink endpoint is occasionally flaky (returns an HTML page
        # instead of JSON under load / rate-limiting). Retry a few times with
        # backoff; never fabricate data on failure.
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
                    resp = await client.post(url, json=body)
                if resp.status_code != 200:
                    continue
                try:
                    data = resp.json()
                except ValueError:
                    # got HTML, not JSON — transient; back off and retry
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                break
            except httpx.HTTPError as exc:
                last_err = exc
                await asyncio.sleep(1.5 * (attempt + 1))
        else:
            return []
        if not isinstance(data, dict) or data.get("result") != "success":
            return []
        rows = data.get("data") or []
        if not rows:
            return []
        # Confirmed codes for known instances; else heuristic auto-detect.
        fmap = _KNOWN_INSTANCES.get(self.base_url.rstrip("/"))
        if fmap is None:
            fmap = _auto_detect(rows[0])
        return [
            self._to_resource(r, fmap, category)
            for r in rows
            if r.get(fmap.get("org_name")) or r.get(fmap.get("svc_name"))
        ]

    def _to_resource(self, row: dict, fm: dict, category: str) -> Resource:
        org_name = row.get(fm["org_name"]) or "Unknown organization"
        org = Organization(
            id=f"vl-org-{abs(hash(org_name)) % 10_000_000}",
            name=org_name,
            description=row.get(fm.get("svc_desc")),
            url=_norm_url(row.get(fm.get("org_url"))),
        )
        service = Service(
            id=f"vl-svc-{abs(hash(org_name + str(row.get(fm['svc_name'])))) % 10_000_000}",
            organization_id=org.id,
            name=row.get(fm["svc_name"]) or category.title(),
            description=row.get(fm.get("svc_desc")),
            status="active",
        )
        location = None
        lat, lng = row.get(fm.get("lat")), row.get(fm.get("lng"))
        if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
            location = Location(
                id=f"vl-loc-{abs(hash(str(lat) + str(lng))) % 10_000_000}",
                name=org_name,
                latitude=float(lat),
                longitude=float(lng),
            )
        address = None
        if row.get(fm.get("addr_1")):
            zip_raw = row.get(fm.get("zip"))
            address = PhysicalAddress(
                address_1=row.get(fm["addr_1"]),
                city=row.get(fm.get("city")),
                state_province=row.get(fm.get("state")),
                postal_code=str(zip_raw) if zip_raw is not None else None,
                country="US",
            )
        return Resource(
            category=category,
            source=self.source_name,
            organization=org,
            service=service,
            location=location,
            address=address,
            phone=row.get(fm.get("phone")),
        )
