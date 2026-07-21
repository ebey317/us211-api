"""FastAPI application exposing a unified US 211 API + assistant layer."""
from __future__ import annotations

import ipaddress

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from us211 import __version__
from us211.adapters import FindhelpAdapter, get_adapter
from us211.agent import CAPABILITIES, recommend_actions, summarize
from us211.models import Resource
from us211.registry import PlatformType, get_source, list_states
from us211.statepacks import exists, load

app = FastAPI(
    title="us211-api",
    description=(
        "Unified, HSDS-shaped REST API + assistant for US 211 health & human "
        "services data (food, housing, utilities, financial, and more) across all "
        "50 states, DC, and territories. Federates multiple 211 platforms behind "
        "one API, and proactively offers actions: summarize, read aloud, print, "
        "email a copy, pinpoint the exact document, or fill out a form."
    ),
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskResponse(BaseModel):
    state: str
    category: str
    summary: str
    resources: list[Resource]
    actions: list[dict]
    capabilities: list[dict]
    resolved_from: str = "param"


class StandardResponse(BaseModel):
    state: str
    state_name: str
    audience: str
    last_verified: str
    sections: list[dict]
    actions: list[dict]
    capabilities: list[dict]
    resolved_from: str = "param"


# --- IP -> state/city resolution -------------------------------------------
# When a caller omits `state`, we resolve it from the request IP using a
# free geolocation service (ip-api.com, no key). This lets a person just open
# the endpoint and get help for THEIR state automatically — no config.
_GEO_URL = "http://ip-api.com/json/{ip}?fields=status,message,region,regionName,city,countryCode"


def _client_ip(request: Request) -> str:
    # Respect X-Forwarded-For when behind a proxy; otherwise peer IP.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def _is_public(ip: str) -> bool:
    try:
        return not ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


async def resolve_location(request: Request) -> tuple[str | None, str | None, str]:
    """Return (state_code, city, resolution_method)."""
    ip = _client_ip(request)
    if not _is_public(ip):
        return None, None, "local"
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(_GEO_URL.format(ip=ip))
        data = r.json()
        if data.get("status") == "success" and data.get("countryCode") == "US":
            # map full state name -> 2-letter code via registry names
            name = (data.get("regionName") or "").strip()
            code = _state_code_from_name(name)
            return code, data.get("city"), "ip"
    except Exception:
        return None, None, "geo-failed"
    return None, None, "geo-failed"


_STATE_NAMES_TO_CODE: dict[str, str] = {}


def _state_names() -> dict[str, str]:
    # imported lazily to avoid circular import at module load
    from us211.registry import _STATE_NAMES

    return {v: k for k, v in _STATE_NAMES.items()}


def _state_code_from_name(name: str) -> str | None:
    return _state_names().get(name)


async def _search_for(state: str, category: str, zip: str | None) -> list[Resource]:
    """Search a state's primary adapter; fall back to the findhelp national
    network when the state's own platform isn't wired yet."""
    src = get_source(state)
    if src is None:
        return []
    if src.platform is not PlatformType.UNKNOWN and src.base_url:
        ad = get_adapter(src)
        if ad is not None:
            try:
                return await ad.search(category=category, postal_code=zip, state=state)
            except Exception:
                return []
    # Fallback: findhelp national network covers all 50 states.
    ad = FindhelpAdapter(base_url="https://www.findhelp.com", source_name="findhelp (national)")
    try:
        return await ad.search(category=category, postal_code=zip, state=state)
    except Exception:
        return []


@app.get("/")
def root() -> dict:
    return {
        "name": "us211-api",
        "version": __version__,
        "docs": "/docs",
        "endpoints": ["/health", "/states", "/resources", "/ask", "/standard", "/capabilities"],
        "note": "Omit ?state= and we resolve it from your IP address. Try /standard?state=IN for an arrival pack.",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/states")
def states() -> list[dict]:
    return list_states()


@app.get("/capabilities")
def capabilities() -> list[dict]:
    return CAPABILITIES


@app.get("/resources", response_model=list[Resource])
async def resources(
    request: Request,
    category: str = Query(..., description="food | housing | utilities | financial | ..."),
    state: str | None = Query(None, description="2-letter state code; if omitted, resolved from IP"),
    zip: str | None = Query(None, description="Optional postal code filter"),
) -> list[Resource]:
    resolved_state, _, method = (state, None, "param")
    if not state:
        resolved_state, _, method = await resolve_location(request)
    if not resolved_state:
        raise HTTPException(
            status_code=400,
            detail="Could not resolve a US state. Pass ?state= explicitly (e.g. IN).",
        )
    src = get_source(resolved_state)
    if src is None:
        raise HTTPException(status_code=404, detail=f"Unknown state/territory: {resolved_state!r}")
    return await _search_for(resolved_state, category, zip)


@app.get("/ask", response_model=AskResponse)
async def ask(
    request: Request,
    state: str | None = Query(None, description="2-letter state code; if omitted, resolved from IP"),
    category: str = Query("food", description="food | housing | utilities | financial | ..."),
    zip: str | None = Query(None, description="Optional postal code filter"),
) -> AskResponse:
    resolved_state, city, method = (state, None, "param")
    if not state:
        resolved_state, city, method = await resolve_location(request)
    if not resolved_state:
        raise HTTPException(
            status_code=400,
            detail="Could not resolve a US state. Pass ?state= explicitly (e.g. IN).",
        )
    src = get_source(resolved_state)
    if src is None:
        raise HTTPException(status_code=404, detail=f"Unknown state/territory: {resolved_state!r}")
    try:
        found = await _search_for(resolved_state, category, zip)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Upstream error: {exc}") from exc

    return AskResponse(
        state=resolved_state,
        category=category,
        summary=summarize(found, category, resolved_state),
        resources=found,
        actions=[a.__dict__ for a in recommend_actions(found)],
        capabilities=CAPABILITIES,
        resolved_from=method,
    )


@app.get("/standard", response_model=StandardResponse)
async def standard(
    request: Request,
    state: str | None = Query(None, description="2-letter state code; if omitted, resolved from IP"),
) -> StandardResponse:
    """Return a structured arrival + establishment pack for a state."""
    resolved_state, _, method = (state, None, "param")
    if not state:
        resolved_state, _, method = await resolve_location(request)
    if not resolved_state:
        raise HTTPException(
            status_code=400,
            detail="Could not resolve a US state. Pass ?state= explicitly (e.g. IN).",
        )
    src = get_source(resolved_state)
    if src is None:
        raise HTTPException(status_code=404, detail=f"Unknown state/territory: {resolved_state!r}")
    if not exists(resolved_state):
        raise HTTPException(
            status_code=404,
            detail=f"Standard arrival pack not yet available for {resolved_state}.",
        )
    pack = load(resolved_state)
    return StandardResponse(
        state=resolved_state,
        state_name=pack["state_name"],
        audience=pack["audience"],
        last_verified=pack["last_verified"],
        sections=pack["sections"],
        actions=[
            {"kind": "summarize", "label": "Summarize this pack", "detail": "Short version for quick reading."},
            {"kind": "read_aloud", "label": "Read aloud", "detail": "Hands-free playback of the arrival guide."},
            {"kind": "email", "label": "Email me a copy", "detail": "Send this pack to an email address."},
            {"kind": "print", "label": "Print this pack", "detail": "Print-ready arrival guide."},
        ],
        capabilities=CAPABILITIES,
        resolved_from=method,
    )
