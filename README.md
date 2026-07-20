# us211-api

An open, unified REST API **and assistant** for **2-1-1 health & human services
data** across all 50 US states, DC, and the five territories (PR, USVI, Guam,
American Samoa, Northern Mariana Islands).

211 is not one system — it's ~200 independent local/state services running on a
handful of different platforms (VisionLink/CommunityOS, iCarol, findhelp,
home-grown DBs). There is **no single public API** for housing, utilities, or
food assistance nationwide, and the national 211 API (apiportal.211.org) is
**gated to contributing orgs**. This project is the **open front door** — for
everybody, whether or not they work in the field. It federates those sources
behind one clean API that speaks the **Open Referral HSDS** standard, and layers
an **assistant** on top that does the busywork for the person asking.

## Why this exists

- **The gap:** no unified, developer-friendly, *public* API for 211 data.
- **The users:** app builders, researchers, caseworkers, and — most of all —
  **people in need** of food / shelter / utility / financial assistance.
- **The standard:** [Open Referral HSDS](https://docs.openreferral.org) — the
  interoperable schema big 211s and Google already use.

## What it does (the assistant)

This isn't a search box. It's a helper.

> **Person:** "What type of help can I get from Indiana?"
> **us211-api:** pulls a *slew* of information — food, housing, utilities,
> financial, health, employment, crisis — not a dead-end "call 211."
>
> **Person:** "Okay, well, I need those food pantries."
> **us211-api:** returns a *list*, and **proactively recommends the next step**
> instead of waiting to be told.

The actions it offers (see `GET /capabilities`):

| Action | What it does |
|--------|--------------|
| **summarize** | Turns a long list into a short, plain-language recap. |
| **read aloud** | Reads results out loud via text-to-speech — hands-free / low-vision. |
| **print** | Generates a print-ready copy of the list or one resource. |
| **email** | Emails a copy — and **automatically attaches any forms**. |
| **pinpoint** | Jumps straight to the **exact document / page / form** instead of making you scroll through a whole site. |
| **fill form** | **Pre-fills an intake/application form** from the person's details, then emails copies automatically. |

## Who actually runs this? (an agent, not the repo)

**`us211-api` is a tool *for* AI agents — it is not a standalone app.** The repo
is just Python files; the *doing* (sending email, speaking aloud, printing,
filling forms) requires an agent with tools and an LLM loop. That agent is
whatever imported the library and supplied capabilities via
`register_hooks(send_email=…, speak=…, print_doc=…)`.

Concretely, a human only ever uses this **through an agent**, e.g.:

- **Hermes** (email MCP + `text_to_speech`)
- **Kimi CLI**, **OpenCLAW**, **Anthropic Claude**, **MiniMax** — each with its own tool surface
- any **desktop agent** or **chat box** that can import Python and call functions

Even "copy the code into a chat and ask it to run" still means *an agent* is in
the loop. There is no path where a person gets email/TTS/form-fill out of the
raw repo without an agent executing it. That's intentional: the library stays
portable and never pretends to send mail it can't.

**No agent?** The endpoints still return data and the action functions still
return honest *"draft prepared, not sent"* status — nothing breaks, nothing is
faked. Wire your agent's tools in and the actions go live. See
[HOSTS.md](HOSTS.md) for example wirings across several agents.

## Why use this instead of just going to the website?

You *can* go to your state's 211 website and do all the work yourself. Here's
the honest comparison:

| Doing it yourself | Using us211-api |
|---|---|
| Open the site, dig through menus and a dozen PDFs to find the right form. | Ask in plain language; we **pinpoint the exact file** for you. |
| Read a long resource page yourself. | We **summarize** it, or **read it aloud** while you're doing something else. |
| Write down the phone number, copy the address, print it by hand. | We **print** a clean copy or **email** it to you. |
| Fill out the intake form by hand, then scan/email it yourself. | We **fill out the form** from your details and **email copies automatically**. |
| Repeat for every state if you move or help someone out of state. | One API, all 50 states + DC wired (territories noted as not operating a standalone 211 program). |

**Bottom line:** the website makes *you* do the work. The agent does it *for
you* — summarize, read aloud, pinpoint the exact document, fill the form, email
copies — automatically.

> **Honesty note:** not every state is wired to a live adapter yet (see Scope
> below). For an unwired state we say so plainly and point you to the official
> site — and we'll still summarize anything you paste in. We never fabricate
> listings.

## Architecture

```
   Unified REST API + assistant  (FastAPI, HSDS-shaped)
   GET /ask?state=IN&category=food   -> summary + list + recommended actions
   GET /resources?state=IN&category=food
                    │  normalizes everything into HSDS
        ┌───────────┴────────────┐
        │     Adapter layer       │  one adapter per PLATFORM,
        │  visionlink | icarol    │  not per state — one adapter
        │  findhelp  | custom     │  covers many states
        └───────────┬────────────┘
                    │
     registry: state/territory -> platform + endpoint
```

The leverage: **~4 platform adapters** + a state→platform **registry** cover the
whole country. "Nationwide" becomes adding registry rows, not writing 56
scrapers.

## Scope ladder

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Indiana (VisionLink) → HSDS → API + assistant | ✅ live (real data) |
| 2 | VisionLink adapter → all VisionLink states | 🟡 IN/WI/ID field maps pinned; upstream endpoint rate-limits under load (adapter retries + returns [] honestly) |
| 3 | + iCarol + findhelp adapters | planned |
| 4 | 50 + DC + 5 territories, registry-driven | 🟡 all 51 state/DC web addresses mapped into registry; territories have no standalone 211 program |

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

Try it:

```bash
curl "http://127.0.0.1:8000/ask?state=IN&category=food"
```

## License

MIT — see [LICENSE](LICENSE).
