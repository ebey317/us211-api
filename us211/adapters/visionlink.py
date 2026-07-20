"""VisionLink CommunityOS adapter.

VisionLink powers several state 211s (Indiana confirmed). The public site is a
single-page app backed by a JSON API layer: requests to the API return
`application/json`, and wrong paths return `{"error": "pagenotfound"}` — which
tells us the API is live but the exact resource-search path is not yet
reverse-engineered.

This adapter is structured for that reality:
- It attempts a small set of CANDIDATE endpoints.
- If none return usable resource data, it returns an empty list (never crashes,
  never fabricates).
- The confirmed endpoint + payload shape go where marked TODO once captured
  from the site's own network traffic.
"""
from __future__ import annotations

import httpx

from us211.adapters.base import BaseAdapter
from us211.models import Resource

_UA = "us211-api/0.1 (+https://github.com/ebey317/us211-api; open civic data)"

# Candidate API paths observed to return application/json on the CommunityOS
# host. NONE are confirmed to return resource results yet — see module docstring.
_CANDIDATE_PATHS = [
    "/api/resource/search",
    "/api/search",
    "/api/v1/resources",
]


class VisionLinkAdapter(BaseAdapter):
    """Adapter for VisionLink CommunityOS 211 sites."""

    # Normalized category -> VisionLink taxonomy hint (stub; refine once the
    # real taxonomy query params are confirmed).
    CATEGORY_MAP = {
        "food": "Food",
        "housing": "Shelter and Housing",
        "shelter": "Shelter and Housing",
        "financial": "Financial",
        "utilities": "Financial",
        "health": "Health Care",
        "mental_health": "Mental Health and SUD",
        "employment": "Employment",
        "legal": "Criminal Justice and Legal",
    }

    async def search(
        self,
        category: str,
        postal_code: str | None = None,
        state: str | None = None,
    ) -> list[Resource]:
        if not self.base_url:
            return []

        taxonomy = self.CATEGORY_MAP.get(category.lower(), category)
        params = {"q": taxonomy}
        if postal_code:
            params["postalCode"] = postal_code

        headers = {"User-Agent": _UA, "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
            for path in _CANDIDATE_PATHS:
                try:
                    resp = await client.get(f"{self.base_url}{path}", params=params)
                except httpx.HTTPError:
                    continue
                if resp.status_code != 200:
                    continue
                try:
                    data = resp.json()
                except ValueError:
                    continue
                # Known "endpoint not found" sentinel from CommunityOS.
                if isinstance(data, dict) and data.get("error") == "pagenotfound":
                    continue
                parsed = self._parse(data, category)
                if parsed:
                    return parsed
        # No confirmed endpoint returned usable data — honest empty result.
        return []

    def _parse(self, data: object, category: str) -> list[Resource]:
        """Normalize a VisionLink JSON payload into Resource objects.

        TODO: implement once the real payload shape is captured from the site's
        network traffic. Until then we cannot honestly map fields, so return [].
        """
        # Intentionally not fabricating a mapping against an unconfirmed shape.
        return []
