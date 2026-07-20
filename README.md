# us211-api

An open, unified REST API for **2-1-1 health & human services data** across all
50 US states, DC, and the five territories (PR, USVI, Guam, American Samoa,
Northern Mariana Islands).

211 is not one system — it's ~200 independent local/state services running on a
handful of different platforms (VisionLink/CommunityOS, iCarol, findhelp,
home-grown DBs). There is **no single public API** for housing, utilities, or
food assistance nationwide. This project fixes that by federating those sources
behind one clean API that speaks the **Open Referral HSDS** standard.

## Why

- **The gap:** no unified, developer-friendly, public API for 211 data.
- **The users:** app builders, researchers, caseworkers, and people in need of
  food / shelter / utility / financial assistance.
- **The standard:** [Open Referral HSDS](https://docs.openreferral.org) — the
  interoperable schema big 211s and Google already use.

## Architecture

```
        Unified REST API  (FastAPI, HSDS-shaped responses)
        GET /resources?category=food&zip=46201&state=IN
                         │
                normalizes everything into HSDS
                         │
              ┌──────────┴───────────┐
              │     Adapter layer     │   one adapter per PLATFORM,
              │  visionlink | icarol  │   not per state — a single
              │  findhelp  | custom   │   adapter covers many states
              └──────────┬───────────┘
                         │
         registry: state/territory -> platform + endpoint
```

The leverage: **~4 platform adapters** + a state→platform **registry** cover the
whole country. "Nationwide" becomes adding registry rows, not writing 56
scrapers.

## Scope ladder

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Indiana (VisionLink) → HSDS → API | 🚧 in progress |
| 2 | VisionLink adapter → all VisionLink states | planned |
| 3 | + iCarol + findhelp adapters | planned |
| 4 | 50 + DC + 5 territories, registry-driven | planned |

## Legal / ethical stance

- Prefer **official/partner APIs** (e.g. findhelp partner API) over scraping.
- Where we read public pages, we **honor robots.txt**, rate-limit, cache, and
  attribute the source 211.
- This project **re-serves public resource listings**; it does not touch private
  client/case data. No PII.
- Not affiliated with United Way, VisionLink, iCarol, or findhelp.

## Quickstart

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
uvicorn us211.main:app --reload
# open http://127.0.0.1:8000/docs
```

## License

MIT — see [LICENSE](LICENSE).
