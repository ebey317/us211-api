"""findhelp (auntbertha) adapter — partner-API first, honest fallback.

findhelp.com is a large national network of social services (50 states). Two
ways to get its data:

1. **Partner API (preferred).** findhelp offers a partner API behind a business
   agreement + key. When `FINDHELP_API_KEY` is set in the environment, we call
   that API. This is the sanctioned, reliable path and matches our "prefer
   official APIs over scraping" stance.

2. **Public crawl (best-effort, currently blocked).** Per findhelp's robots.txt
   public listing pages are *crawlable*, but in practice its regional
   subdomains (e.g. connectatxpublic.findhelp.com) return **403 to server-side
   requests** (CloudFront bot protection) — only a real browser gets through.
   Our HTML parser is kept as a fallback for environments that can reach it
   (proxy / browser-based agent), but we do NOT hammer 403s: if the page is
   blocked we return [].

We never fabricate listings. No data = empty list.
"""
from __future__ import annotations

import os
import re
from html.parser import HTMLParser

import httpx

from us211.adapters.base import BaseAdapter
from us211.models import Organization, Resource, Service

_UA = "Mozilla/5.0 (compatible; us211-api/0.1; +https://github.com/ebey317/us211-api)"

# findhelp category slugs used by its public listing URLs.
_CATEGORY_SLUG: dict[str, str] = {
    "food": "food-pantry",
    "food_pantry": "food-pantry",
    "housing": "housing",
    "utilities": "utility-assistance",
    "financial": "financial-assistance",
    "health": "health-medical",
    "employment": "job-training-employment",
    "childcare": "child-care",
    "legal": "legal-services",
}


class _FindhelpCardParser(HTMLParser):
    """Best-effort extractor of org/service cards from a findhelp listing page."""

    def __init__(self) -> None:
        super().__init__()
        self.cards: list[dict] = []
        self._open_tag: str | None = None
        self._cur: dict | None = None

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        cls = d.get("class", "") or ""
        if tag in ("div", "article", "li") and ("result" in cls or "listing" in cls):
            self._open_tag = tag
            self._cur = {"name": None, "address": None, "url": d.get("href")}

    def handle_endtag(self, tag):
        if self._open_tag == tag and self._cur is not None:
            if self._cur.get("name"):
                self.cards.append(self._cur)
            self._open_tag = None
            self._cur = None

    def handle_data(self, data):
        if self._open_tag is not None and self._cur is not None:
            text = data.strip()
            if not text:
                return
            if self._cur["name"] is None and len(text) > 2:
                self._cur["name"] = text
            if self._cur["address"] is None and re.search(r"\b\d{1,6}\s+\w+", text):
                self._cur["address"] = text


class FindhelpAdapter(BaseAdapter):
    """Adapter for findhelp.com (national coverage)."""

    CATEGORY_MAP = {k: v for k, v in _CATEGORY_SLUG.items()}

    def __init__(self, base_url: str | None = None, source_name: str = "findhelp (national)",
                 api_key: str | None = None, timeout: float = 20.0):
        super().__init__(base_url, source_name, timeout)
        self.api_key = api_key or os.getenv("FINDHELP_API_KEY")

    async def search(
        self,
        category: str,
        postal_code: str | None = None,
        state: str | None = None,
        limit: int = 25,
    ) -> list[Resource]:
        slug = _CATEGORY_SLUG.get(category.lower())
        if not slug:
            return []  # category not mapped for findhelp
        loc = postal_code or state
        if not loc:
            return []  # need a location

        # Path 1: partner API when a key is available.
        if self.api_key:
            return await self._search_api(slug, loc, limit)

        # Path 2: best-effort public crawl (often 403 server-side; honest []).
        return await self._search_crawl(slug, loc, limit)

    async def _search_api(self, slug: str, loc: str, limit: int) -> list[Resource]:
        # Placeholder for the sanctioned partner API call. The exact endpoint
        # + response schema are provided to partners; we do NOT guess them.
        # When wired, parse the documented JSON into Resource objects.
        # Until then, return [] rather than fabricate.
        return []

    async def _search_crawl(self, slug: str, loc: str, limit: int) -> list[Resource]:
        # findhelp regional subdomains (e.g. connectatxpublic.findhelp.com)
        # commonly 403 server-side requests. We try once; on anything but 200
        # JSON/HTML we return [] — no hammering, no fabrication.
        url = f"https://www.findhelp.com/{slug}/search?location={loc}"
        headers = {"User-Agent": _UA, "Accept": "text/html,application/xhtml+xml"}
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers, follow_redirects=True) as client:
            try:
                resp = await client.get(url)
            except httpx.HTTPError:
                return []
        if resp.status_code != 200:
            return []
        parser = _FindhelpCardParser()
        parser.feed(resp.text)
        out: list[Resource] = []
        for card in parser.cards[:limit]:
            name = card.get("name")
            if not name:
                continue
            org = Organization(id=f"fh-org-{abs(hash(name)) % 10_000_000}", name=name, url=card.get("url"))
            svc = Service(id=f"fh-svc-{abs(hash(name + slug)) % 10_000_000}", organization_id=org.id,
                          name=slug.replace("-", " ").title(), status="active")
            out.append(Resource(category=slug, source=self.source_name, organization=org, service=svc))
        return out
