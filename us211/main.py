"""FastAPI application exposing a unified US 211 API."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from us211 import __version__
from us211.adapters import get_adapter
from us211.models import Resource
from us211.registry import PlatformType, get_source, list_states

app = FastAPI(
    title="us211-api",
    description=(
        "Unified, HSDS-shaped REST API for US 211 health & human services data "
        "(food, housing, utilities, financial, and more) across all 50 states, "
        "DC, and territories. Federates multiple 211 platforms behind one API."
    ),
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict:
    return {
        "name": "us211-api",
        "version": __version__,
        "docs": "/docs",
        "endpoints": ["/health", "/states", "/resources"],
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/states")
def states() -> list[dict]:
    return list_states()


@app.get("/resources", response_model=list[Resource])
async def resources(
    category: str = Query(..., description="food | housing | utilities | financial | ..."),
    state: str = Query(..., description="2-letter state/territory code, e.g. IN"),
    zip: str | None = Query(None, description="Optional postal code filter"),
) -> list[Resource]:
    source = get_source(state)
    if source is None:
        raise HTTPException(status_code=404, detail=f"Unknown state/territory: {state!r}")
    if source.platform is PlatformType.UNKNOWN or source.base_url is None:
        raise HTTPException(
            status_code=501,
            detail=f"{source.name} is not wired to a platform adapter yet.",
        )
    adapter = get_adapter(source)
    if adapter is None:
        raise HTTPException(
            status_code=501,
            detail=f"No adapter available for platform {source.platform.value!r}.",
        )
    try:
        return await adapter.search(category=category, postal_code=zip, state=state)
    except Exception as exc:  # noqa: BLE001 - surface upstream failures cleanly
        raise HTTPException(status_code=502, detail=f"Upstream error: {exc}") from exc
